"""
Stewie Event Bus — Lightweight publish/subscribe system for decoupled module communication.

Allows modules to communicate without direct references to each other.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

from loguru import logger


# Type alias for event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """
    Asynchronous event bus for inter-module communication.

    Usage:
        bus = EventBus()
        bus.subscribe("wake_detected", my_handler)
        await bus.emit("wake_detected", timestamp=time.time())
    """

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._event_history: list[dict] = []
        self._max_history = 100

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler for an event."""
        self._subscribers[event_name].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to '{event_name}'")

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a handler from an event."""
        if handler in self._subscribers[event_name]:
            self._subscribers[event_name].remove(handler)
            logger.debug(f"Unsubscribed {handler.__name__} from '{event_name}'")

    async def emit(self, event_name: str, **kwargs) -> None:
        """
        Fire an event, calling all registered handlers concurrently.

        Args:
            event_name: The event identifier.
            **kwargs: Data payload passed to all handlers.
        """
        handlers = self._subscribers.get(event_name, [])
        if not handlers:
            logger.trace(f"Event '{event_name}' emitted with no subscribers")
            return

        logger.debug(
            f"Emitting '{event_name}' to {len(handlers)} handler(s)"
        )

        # Record event in history
        self._event_history.append(
            {"event": event_name, "data": kwargs, "handlers": len(handlers)}
        )
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Execute all handlers concurrently
        tasks = [
            asyncio.create_task(self._safe_call(handler, event_name, **kwargs))
            for handler in handlers
        ]
        await asyncio.gather(*tasks)

    async def _safe_call(
        self, handler: EventHandler, event_name: str, **kwargs
    ) -> None:
        """Call a handler with error protection."""
        try:
            await handler(**kwargs)
        except Exception as e:
            logger.error(
                f"Error in handler '{handler.__name__}' for event "
                f"'{event_name}': {e}"
            )

    @property
    def history(self) -> list[dict]:
        """Get recent event history."""
        return list(self._event_history)

    def clear(self) -> None:
        """Remove all subscriptions and history."""
        self._subscribers.clear()
        self._event_history.clear()
