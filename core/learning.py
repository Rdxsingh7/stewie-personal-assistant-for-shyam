"""
Stewie Learning Engine — Self-improving AI through interaction patterns.

Tracks command history, learns user preferences, remembers corrections,
and feeds accumulated knowledge back into the NLU for progressively
better intent parsing and response quality.

Storage: SQLite database (lightweight, serverless, survives restarts).
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from loguru import logger


@dataclass
class CommandRecord:
    """A single recorded command interaction."""

    timestamp: str
    source: str  # "voice" or "telegram"
    raw_text: str
    parsed_intent: str
    parsed_params: dict
    success: bool
    execution_time_ms: float
    correction_of: Optional[str] = None  # ID of the command this corrected


@dataclass
class UserPreference:
    """A learned user preference."""

    key: str
    value: Any
    confidence: float  # 0.0 to 1.0 — increases with repeated observations
    last_updated: str
    observation_count: int


class LearningEngine:
    """
    Self-improving learning system for Stewie.

    Capabilities:
    - Command frequency tracking (what you ask most)
    - Success/failure pattern analysis
    - User preference inference (brightness, volume, apps, times)
    - Correction learning (failed command → successful rephrase)
    - Context enrichment for NLU (feed learned patterns into prompts)
    - Periodic self-analysis reports

    All data persists in a local SQLite database.
    """

    DB_SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(
                Path(__file__).parent.parent / "data" / "stewie_memory.db"
            )

        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()

        logger.info(f"Learning engine initialized (db={self.db_path})")

    # ═══════════════════════════════════════════
    # DATABASE SETUP
    # ═══════════════════════════════════════════

    def _initialize_db(self):
        """Create database tables if they don't exist."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        cursor = self._conn.cursor()

        # Command history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                parsed_intent TEXT,
                parsed_params TEXT,
                success INTEGER NOT NULL DEFAULT 1,
                execution_time_ms REAL,
                correction_of INTEGER,
                feedback TEXT,
                FOREIGN KEY (correction_of) REFERENCES command_history(id)
            )
        """)

        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5,
                last_updated TEXT NOT NULL,
                observation_count INTEGER NOT NULL DEFAULT 1
            )
        """)

        # Correction mappings — learned remappings of misunderstood commands
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                corrected_intent TEXT NOT NULL,
                corrected_params TEXT,
                times_applied INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # Intent aliases — custom name → intent mappings the user teaches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intent_aliases (
                alias TEXT PRIMARY KEY,
                intent TEXT NOT NULL,
                params_template TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Feedback log — explicit user feedback on responses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_id INTEGER,
                rating INTEGER,
                comment TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (command_id) REFERENCES command_history(id)
            )
        """)

        # Schema version tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cursor.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("schema_version", str(self.DB_SCHEMA_VERSION)),
        )

        self._conn.commit()

    # ═══════════════════════════════════════════
    # RECORDING INTERACTIONS
    # ═══════════════════════════════════════════

    def record_command(
        self,
        raw_text: str,
        parsed_intent: str,
        parsed_params: dict,
        success: bool,
        execution_time_ms: float = 0.0,
        source: str = "voice",
        correction_of: Optional[int] = None,
    ) -> int:
        """
        Record a command execution for learning.

        Returns:
            The command ID for future reference.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO command_history 
            (timestamp, source, raw_text, parsed_intent, parsed_params, 
             success, execution_time_ms, correction_of)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                source,
                raw_text,
                parsed_intent,
                json.dumps(parsed_params),
                1 if success else 0,
                execution_time_ms,
                correction_of,
            ),
        )
        self._conn.commit()

        cmd_id = cursor.lastrowid

        # Auto-learn from this interaction
        self._auto_learn(raw_text, parsed_intent, parsed_params, success)

        logger.debug(
            f"Recorded command #{cmd_id}: "
            f"'{raw_text}' → {parsed_intent} "
            f"({'✅' if success else '❌'})"
        )

        return cmd_id

    def record_correction(
        self,
        original_text: str,
        corrected_intent: str,
        corrected_params: dict,
    ) -> None:
        """
        Record when a user corrects a misunderstood command.

        This teaches Stewie the correct interpretation for similar
        future commands.
        """
        cursor = self._conn.cursor()

        # Check if this correction already exists
        cursor.execute(
            "SELECT id, times_applied FROM corrections WHERE original_text = ?",
            (original_text.lower(),),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE corrections 
                SET corrected_intent = ?, corrected_params = ?, 
                    times_applied = times_applied + 1
                WHERE id = ?
                """,
                (
                    corrected_intent,
                    json.dumps(corrected_params),
                    existing["id"],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO corrections 
                (original_text, corrected_intent, corrected_params, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    original_text.lower(),
                    corrected_intent,
                    json.dumps(corrected_params),
                    datetime.now().isoformat(),
                ),
            )

        self._conn.commit()
        logger.info(
            f"Learned correction: '{original_text}' → {corrected_intent}"
        )

    def record_feedback(
        self,
        command_id: int,
        rating: int,
        comment: str = "",
    ) -> None:
        """
        Record explicit user feedback on a response.

        Args:
            command_id: ID of the command being rated.
            rating: 1-5 rating (5 = excellent).
            comment: Optional text feedback.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO feedback_log (command_id, rating, comment, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (command_id, rating, comment, datetime.now().isoformat()),
        )
        self._conn.commit()
        logger.debug(f"Feedback recorded for command #{command_id}: {rating}/5")

    # ═══════════════════════════════════════════
    # AUTO-LEARNING
    # ═══════════════════════════════════════════

    def _auto_learn(
        self,
        raw_text: str,
        intent: str,
        params: dict,
        success: bool,
    ) -> None:
        """
        Automatically extract learnable patterns from interactions.

        Called after every command — silently learns:
        - Preferred brightness/volume levels
        - Frequently opened apps
        - Common search topics
        - Time-of-day patterns
        """
        if not success:
            return

        # Learn preferred brightness
        if intent in ("set_brightness", "adjust_brightness"):
            level = params.get("level") or params.get("delta")
            if level is not None:
                self._update_preference(
                    "preferred_brightness",
                    str(level),
                    confidence_boost=0.1,
                )

        # Learn preferred volume
        if intent == "set_volume":
            level = params.get("level")
            if level is not None:
                self._update_preference(
                    "preferred_volume",
                    str(level),
                    confidence_boost=0.1,
                )

        # Learn favorite apps
        if intent == "open_application":
            app_name = params.get("app_name", "")
            if app_name:
                self._update_preference(
                    f"app_frequency_{app_name.lower()}",
                    str(self._get_app_open_count(app_name) + 1),
                    confidence_boost=0.05,
                )

        # Learn time-of-day patterns
        hour = datetime.now().hour
        time_slot = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening" if hour < 21 else "night"
        self._update_preference(
            f"active_time_{time_slot}",
            str(int(self._get_preference_value(f"active_time_{time_slot}") or 0) + 1),
            confidence_boost=0.01,
        )

    def _update_preference(
        self,
        key: str,
        value: str,
        confidence_boost: float = 0.05,
    ) -> None:
        """Update or create a preference with increasing confidence."""
        cursor = self._conn.cursor()

        cursor.execute("SELECT * FROM preferences WHERE key = ?", (key,))
        existing = cursor.fetchone()

        if existing:
            new_confidence = min(1.0, existing["confidence"] + confidence_boost)
            cursor.execute(
                """
                UPDATE preferences 
                SET value = ?, confidence = ?, last_updated = ?,
                    observation_count = observation_count + 1
                WHERE key = ?
                """,
                (value, new_confidence, datetime.now().isoformat(), key),
            )
        else:
            cursor.execute(
                """
                INSERT INTO preferences (key, value, confidence, last_updated, observation_count)
                VALUES (?, ?, ?, ?, 1)
                """,
                (key, value, min(1.0, 0.3 + confidence_boost), datetime.now().isoformat()),
            )

        self._conn.commit()

    def _get_preference_value(self, key: str) -> Optional[str]:
        """Get a preference value."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def _get_app_open_count(self, app_name: str) -> int:
        """Count how many times an app has been opened."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as cnt FROM command_history 
            WHERE parsed_intent = 'open_application' 
            AND parsed_params LIKE ?
            """,
            (f'%{app_name.lower()}%',),
        )
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    # ═══════════════════════════════════════════
    # KNOWLEDGE RETRIEVAL (for NLU enrichment)
    # ═══════════════════════════════════════════

    def get_learned_context(self, max_items: int = 10) -> str:
        """
        Generate a context string from learned patterns for NLU enrichment.

        This is injected into the LLM system prompt to improve
        intent parsing based on user history.

        Returns:
            Formatted string of learned user patterns.
        """
        lines = ["Learned user patterns:"]

        # Top apps
        top_apps = self.get_top_apps(limit=5)
        if top_apps:
            app_list = ", ".join(f"{app} ({count}x)" for app, count in top_apps)
            lines.append(f"  Frequently used apps: {app_list}")

        # Preferences
        prefs = self.get_high_confidence_preferences(min_confidence=0.5)
        for pref in prefs[:5]:
            if pref["key"].startswith("preferred_"):
                name = pref["key"].replace("preferred_", "").replace("_", " ")
                lines.append(
                    f"  Preferred {name}: {pref['value']} "
                    f"(confidence: {pref['confidence']:.0%})"
                )

        # Activity patterns
        for slot in ["morning", "afternoon", "evening", "night"]:
            count = self._get_preference_value(f"active_time_{slot}")
            if count and int(count) > 5:
                lines.append(f"  Active during {slot}: {count} interactions")

        # Recent corrections (teach NLU to avoid past mistakes)
        corrections = self.get_recent_corrections(limit=5)
        if corrections:
            lines.append("  Learned corrections:")
            for corr in corrections:
                lines.append(
                    f"    '{corr['original_text']}' → {corr['corrected_intent']}"
                )

        # Success rate
        stats = self.get_stats()
        if stats["total_commands"] > 0:
            lines.append(
                f"  Overall success rate: {stats['success_rate']:.0%} "
                f"({stats['total_commands']} total commands)"
            )

        return "\n".join(lines) if len(lines) > 1 else ""

    def check_correction(self, text: str) -> Optional[dict]:
        """
        Check if there's a learned correction for this command text.

        If the user previously corrected a similar command, return
        the corrected intent and params to override NLU parsing.

        Returns:
            Dict with 'intent' and 'params' if a correction exists, else None.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT corrected_intent, corrected_params, times_applied
            FROM corrections 
            WHERE original_text = ? AND times_applied >= 2
            ORDER BY times_applied DESC
            LIMIT 1
            """,
            (text.lower(),),
        )
        row = cursor.fetchone()

        if row:
            logger.info(
                f"Applying learned correction for '{text}' "
                f"(applied {row['times_applied']}x before)"
            )
            return {
                "intent": row["corrected_intent"],
                "params": json.loads(row["corrected_params"] or "{}"),
            }
        return None

    # ═══════════════════════════════════════════
    # ANALYTICS & INSIGHTS
    # ═══════════════════════════════════════════

    def get_stats(self) -> dict:
        """Get overall usage statistics."""
        cursor = self._conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM command_history")
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as ok FROM command_history WHERE success = 1"
        )
        successes = cursor.fetchone()["ok"]

        cursor.execute(
            "SELECT AVG(execution_time_ms) as avg_time FROM command_history"
        )
        avg_time = cursor.fetchone()["avg_time"] or 0

        cursor.execute(
            "SELECT COUNT(DISTINCT parsed_intent) as unique_intents FROM command_history"
        )
        unique_intents = cursor.fetchone()["unique_intents"]

        cursor.execute("SELECT COUNT(*) as corrections FROM corrections")
        corrections = cursor.fetchone()["corrections"]

        return {
            "total_commands": total,
            "successful_commands": successes,
            "success_rate": successes / total if total > 0 else 1.0,
            "avg_execution_time_ms": round(avg_time, 1),
            "unique_intents_used": unique_intents,
            "learned_corrections": corrections,
        }

    def get_top_apps(self, limit: int = 5) -> list[tuple[str, int]]:
        """Get the most frequently opened applications."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT parsed_params, COUNT(*) as cnt 
            FROM command_history 
            WHERE parsed_intent = 'open_application' AND success = 1
            GROUP BY parsed_params
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (limit,),
        )

        results = []
        for row in cursor.fetchall():
            try:
                params = json.loads(row["parsed_params"])
                app_name = params.get("app_name", "unknown")
                results.append((app_name, row["cnt"]))
            except (json.JSONDecodeError, KeyError):
                continue
        return results

    def get_top_intents(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get the most frequently used intents."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT parsed_intent, COUNT(*) as cnt 
            FROM command_history 
            GROUP BY parsed_intent
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [(row["parsed_intent"], row["cnt"]) for row in cursor.fetchall()]

    def get_failure_patterns(self, limit: int = 10) -> list[dict]:
        """Get commands that frequently fail — candidates for improvement."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT raw_text, parsed_intent, COUNT(*) as failure_count
            FROM command_history 
            WHERE success = 0
            GROUP BY raw_text
            ORDER BY failure_count DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_corrections(self, limit: int = 10) -> list[dict]:
        """Get recently learned corrections."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT * FROM corrections 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_high_confidence_preferences(
        self, min_confidence: float = 0.5
    ) -> list[dict]:
        """Get preferences with high confidence (well-established patterns)."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT * FROM preferences 
            WHERE confidence >= ?
            ORDER BY confidence DESC
            """,
            (min_confidence,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def generate_self_report(self) -> str:
        """
        Generate a self-analysis report — what Stewie has learned.

        Can be triggered by: "Hey Stewie, what have you learned?"
        """
        stats = self.get_stats()
        top_apps = self.get_top_apps()
        top_intents = self.get_top_intents()
        failures = self.get_failure_patterns(limit=5)
        corrections = self.get_recent_corrections(limit=5)

        report_lines = [
            "📊 Self-Analysis Report",
            f"Total commands processed: {stats['total_commands']}",
            f"Success rate: {stats['success_rate']:.1%}",
            f"Average response time: {stats['avg_execution_time_ms']:.0f}ms",
            f"Unique capabilities used: {stats['unique_intents_used']}",
            f"Learned corrections: {stats['learned_corrections']}",
            "",
        ]

        if top_apps:
            report_lines.append("Your favorite apps:")
            for app, count in top_apps:
                report_lines.append(f"  • {app}: opened {count} times")
            report_lines.append("")

        if top_intents:
            report_lines.append("Most used commands:")
            for intent, count in top_intents[:5]:
                report_lines.append(f"  • {intent}: {count} times")
            report_lines.append("")

        if failures:
            report_lines.append("Areas for improvement:")
            for fail in failures:
                report_lines.append(
                    f"  ⚠️ '{fail['raw_text']}' failed {fail['failure_count']} times"
                )
            report_lines.append("")

        if corrections:
            report_lines.append("Corrections I've internalized:")
            for corr in corrections:
                report_lines.append(
                    f"  ✅ '{corr['original_text']}' → {corr['corrected_intent']}"
                )

        return "\n".join(report_lines)

    # ═══════════════════════════════════════════
    # CLEANUP & MAINTENANCE
    # ═══════════════════════════════════════════

    def prune_old_records(self, days: int = 90) -> int:
        """Remove command records older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self._conn.cursor()
        cursor.execute(
            "DELETE FROM command_history WHERE timestamp < ?", (cutoff,)
        )
        deleted = cursor.rowcount
        self._conn.commit()

        if deleted > 0:
            logger.info(f"Pruned {deleted} records older than {days} days")
        return deleted

    def export_knowledge(self) -> dict:
        """Export all learned knowledge as a portable dict."""
        return {
            "stats": self.get_stats(),
            "top_apps": self.get_top_apps(),
            "top_intents": self.get_top_intents(),
            "preferences": self.get_high_confidence_preferences(0.0),
            "corrections": self.get_recent_corrections(limit=50),
            "exported_at": datetime.now().isoformat(),
        }

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            logger.debug("Learning engine database closed.")
