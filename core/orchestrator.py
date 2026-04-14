"""
Stewie Command Orchestrator — The brain that coordinates all execution.

Receives parsed intents from the NLU engine, builds execution plans,
dispatches tasks to the appropriate modules, and compiles results.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from loguru import logger

from core.context import ConversationContext
from core.event_bus import EventBus
from core.exceptions import CommandExecutionError


class TaskStatus(Enum):
    """Status of a task execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """Result of a single task or multi-step execution."""

    status: TaskStatus
    data: Any = None
    error: str | None = None
    summary: str = ""


@dataclass
class ExecutionPlan:
    """A sequence of steps to execute for a complex command."""

    steps: list[dict] = field(default_factory=list)
    abort_on_failure: bool = True
    source: str = "voice"


# Type for action handler functions
ActionHandler = Callable[..., Coroutine[Any, Any, Any]]


class Orchestrator:
    """
    Central command dispatcher — transforms NLU output into action.

    Maintains a registry of action handlers (mapped to execution modules)
    and coordinates multi-step task execution with result chaining.
    """

    def __init__(
        self,
        event_bus: EventBus,
        context: ConversationContext,
    ):
        self.event_bus = event_bus
        self.context = context
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, action_name: str, handler: ActionHandler) -> None:
        """Register an action handler."""
        self._handlers[action_name] = handler
        logger.debug(f"Registered action handler: '{action_name}'")

    def register_many(self, handlers: dict[str, ActionHandler]) -> None:
        """Register multiple action handlers at once."""
        for name, handler in handlers.items():
            self.register(name, handler)

    async def execute(self, parsed_intent: dict) -> TaskResult:
        """
        Execute a parsed intent, potentially with multiple steps.

        Args:
            parsed_intent: NLU output containing 'action' or 'steps'.

        Returns:
            TaskResult with compiled outcome.
        """
        # Determine if single action or multi-step plan
        steps = parsed_intent.get("steps")
        if steps is None:
            # Single action — wrap in a step
            steps = [
                {
                    "action": parsed_intent.get("action", "unknown"),
                    "params": parsed_intent.get("params", {}),
                }
            ]

        abort_on_failure = parsed_intent.get("abort_on_failure", True)
        source = parsed_intent.get("source", "voice")

        plan = ExecutionPlan(
            steps=steps,
            abort_on_failure=abort_on_failure,
            source=source,
        )

        logger.info(
            f"Executing plan with {len(plan.steps)} step(s) "
            f"[source={plan.source}]"
        )

        results = await self._execute_plan(plan)
        compiled = self._compile_results(results)

        # Record in conversation context
        command_text = parsed_intent.get("original_text", "")
        intent_name = parsed_intent.get("intent", "unknown")
        self.context.add_interaction(
            command=command_text,
            intent=intent_name,
            result_status=compiled.status.value,
            result_summary=compiled.summary,
            source=source,
        )

        # Emit completion event
        await self.event_bus.emit(
            "command_complete",
            result=compiled,
            source=source,
        )

        return compiled

    async def _execute_plan(self, plan: ExecutionPlan) -> list[TaskResult]:
        """Execute each step in sequence, with result chaining."""
        results: list[TaskResult] = []

        for i, step in enumerate(plan.steps):
            action = step.get("action", "unknown")
            params = step.get("params", {})

            logger.info(
                f"Step {i + 1}/{len(plan.steps)}: {action} "
                f"with params={params}"
            )

            # Resolve references to previous step results
            params = self._resolve_references(params, results)

            # Find the handler
            handler = self._handlers.get(action)
            if handler is None:
                error_msg = f"No handler registered for action: '{action}'"
                logger.warning(error_msg)
                results.append(
                    TaskResult(
                        status=TaskStatus.FAILED,
                        error=error_msg,
                        summary=f"Unknown action: {action}",
                    )
                )
                if plan.abort_on_failure:
                    break
                continue

            # Execute the handler
            try:
                await self.event_bus.emit(
                    "task_started", action=action, step=i + 1
                )

                result_data = await handler(**params)

                task_result = TaskResult(
                    status=TaskStatus.COMPLETED,
                    data=result_data,
                    summary=f"Completed: {action}",
                )
                results.append(task_result)

                await self.event_bus.emit(
                    "task_completed",
                    action=action,
                    step=i + 1,
                    result=task_result,
                )

                logger.info(f"Step {i + 1} completed: {action}")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Step {i + 1} failed: {action} — {error_msg}")

                task_result = TaskResult(
                    status=TaskStatus.FAILED,
                    error=error_msg,
                    summary=f"Failed: {action} — {error_msg}",
                )
                results.append(task_result)

                await self.event_bus.emit(
                    "task_failed",
                    action=action,
                    step=i + 1,
                    error=error_msg,
                )

                if plan.abort_on_failure:
                    logger.warning(
                        "Aborting remaining steps due to failure."
                    )
                    break

        return results

    def _resolve_references(
        self, params: dict, previous_results: list[TaskResult]
    ) -> dict:
        """
        Replace placeholder references with actual data from previous steps.

        Supports: "$result.N" where N is the step index (0-based).
        Example: {"content": "$result.2"} → uses data from step 3.
        """
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$result."):
                try:
                    idx = int(value.split(".")[1])
                    if idx < len(previous_results):
                        resolved[key] = previous_results[idx].data
                    else:
                        logger.warning(
                            f"Reference {value} out of range "
                            f"(only {len(previous_results)} results available)"
                        )
                        resolved[key] = value
                except (ValueError, IndexError):
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    def _compile_results(self, results: list[TaskResult]) -> TaskResult:
        """Merge all step results into a single comprehensive response."""
        if not results:
            return TaskResult(
                status=TaskStatus.COMPLETED,
                summary="No tasks to execute.",
            )

        all_ok = all(r.status == TaskStatus.COMPLETED for r in results)
        summaries = [r.summary for r in results if r.summary]
        combined_summary = " → ".join(summaries)

        errors = [r.error for r in results if r.error]

        return TaskResult(
            status=TaskStatus.COMPLETED if all_ok else TaskStatus.FAILED,
            data=[r.data for r in results],
            error="; ".join(errors) if errors else None,
            summary=combined_summary,
        )

    @property
    def available_actions(self) -> list[str]:
        """List all registered action names."""
        return list(self._handlers.keys())
