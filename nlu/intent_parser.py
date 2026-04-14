"""
Stewie Intent Parser — LLM-powered natural language understanding.

Uses OpenAI's function-calling API to convert free-form voice/text
commands into structured action plans that the orchestrator can execute.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from loguru import logger
from openai import AsyncOpenAI

from core.context import ConversationContext
from nlu.function_schemas import STEWIE_FUNCTION_SCHEMAS


SYSTEM_PROMPT = """You are Stewie, a sophisticated AI assistant inspired by JARVIS from Iron Man. 
You serve as the voice-controlled command interface for a Windows laptop.

Your job is to parse the user's spoken command and determine the correct action(s) to take.

RULES:
1. If the user's command involves MULTIPLE sequential steps, call multiple functions in order.
2. If a command is ambiguous, choose the most likely interpretation.
3. For "search" commands, use the web_search function.
4. For "research" commands (implying deeper investigation), use research_topic.
5. If the user wants to create a document with research results, use research_topic first, 
   then create_document — the document content will be populated from research results.
6. For brightness/volume: "increase" = positive delta, "decrease" = negative delta.
   "set to X" = absolute level. If they say a percentage, use the set function.
7. For commands you cannot understand, respond with a brief clarification question.

CONVERSATION CONTEXT:
{context}

LEARNED USER PATTERNS:
{learned_context}

Parse the user's command and call the appropriate function(s)."""


class IntentParser:
    """
    LLM-based intent parser using OpenAI function calling.

    Converts natural language commands into structured action plans
    with intents, entities, and execution parameters.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
        context: Optional[ConversationContext] = None,
        learning_engine=None,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.context = context
        self.learning_engine = learning_engine

    async def parse(self, text: str) -> dict[str, Any]:
        """
        Parse a natural language command into structured intent(s).

        Args:
            text: The transcribed voice command or Telegram message.

        Returns:
            A dict with 'action'/'steps', 'params', 'intent', etc.
            ready for the Orchestrator.
        """
        logger.debug(f"Parsing: \"{text}\"")

        # Check for learned corrections first (skip LLM if we already know)
        if self.learning_engine:
            correction = self.learning_engine.check_correction(text)
            if correction:
                logger.info(f"Using learned correction for: '{text}'")
                return {
                    "intent": correction["intent"],
                    "action": correction["intent"],
                    "params": correction["params"],
                    "original_text": text,
                    "source": "voice",
                    "confidence": 0.98,
                    "from_learning": True,
                }

        # Build context strings for the system prompt
        context_str = ""
        if self.context:
            context_str = self.context.get_context_for_llm()

        learned_context = ""
        if self.learning_engine:
            learned_context = self.learning_engine.get_learned_context()

        system_prompt = SYSTEM_PROMPT.format(
            context=context_str or "No previous interactions.",
            learned_context=learned_context or "No learned patterns yet.",
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                tools=STEWIE_FUNCTION_SCHEMAS,
                tool_choice="auto",
                temperature=0.1,  # Low temp for deterministic parsing
            )

            return self._process_response(response, text)

        except Exception as e:
            error_str = str(e)
            if "failed_generation" in error_str:
                import re
                # e.g., <function=web_search{"query": "weather today"}</function>
                match = re.search(r"<function=(\w+)(.*?)></function>|<function=(\w+)(.*?)</function>", error_str)
                if match:
                    action = match.group(1) or match.group(3)
                    params_str = match.group(2) or match.group(4)
                    try:
                        import json
                        params = json.loads(params_str)
                        logger.info(f"Recovered hallucinated tool call: {action}")
                        return {
                            "intent": action,
                            "action": action,
                            "params": params,
                            "original_text": text,
                            "source": "voice",
                            "confidence": 0.8,
                        }
                    except json.JSONDecodeError:
                        pass
            
            logger.error(f"LLM intent parsing failed: {e}")
            # Fall back to basic parsing
            return self._fallback_parse(text)

    def _process_response(self, response, original_text: str) -> dict:
        """Process the OpenAI response into our internal format."""
        message = response.choices[0].message

        # Check if the model called any functions
        if message.tool_calls:
            steps = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                try:
                    params = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    params = {}

                steps.append(
                    {"action": function_name, "params": params}
                )

            if len(steps) == 1:
                # Single action
                result = {
                    "intent": steps[0]["action"],
                    "action": steps[0]["action"],
                    "params": steps[0]["params"],
                    "original_text": original_text,
                    "source": "voice",
                    "confidence": 0.95,
                }
            else:
                # Multi-step plan
                result = {
                    "intent": "multi_step_task",
                    "steps": steps,
                    "original_text": original_text,
                    "source": "voice",
                    "abort_on_failure": True,
                    "confidence": 0.90,
                }

            logger.info(
                f"Parsed intent: {result.get('intent')} "
                f"({len(steps)} step(s))"
            )
            return result

        # No function calls — the model responded with text
        # This usually means it needs clarification
        response_text = message.content or "I'm not sure what you'd like me to do."
        logger.info(f"NLU returned text response (no action): {response_text}")

        return {
            "intent": "clarification",
            "action": "respond",
            "params": {"message": response_text},
            "original_text": original_text,
            "source": "voice",
            "confidence": 0.5,
        }

    def _fallback_parse(self, text: str) -> dict:
        """
        Basic keyword-based fallback when LLM is unavailable.

        This is intentionally simple — just enough to handle
        critical commands offline.
        """
        from nlu.fallback_parser import FallbackParser

        return FallbackParser.parse(text)
