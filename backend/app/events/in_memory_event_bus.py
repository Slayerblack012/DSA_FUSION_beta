"""
DSA AutoGrader - In-Memory Event Bus.

Simple event bus for development and testing.
For production, use RabbitMQEventBus or KafkaEventBus.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from app.core.models import Event, EventType

logger = logging.getLogger("dsa.events")


class InMemoryEventBus:
    """
    In-memory event bus implementation.

    Suitable for:
    - Development
    - Testing
    - Single-instance deployments

    For production with multiple instances, use RabbitMQ or Kafka.
    """

    def __init__(self):
        self._handlers = defaultdict(list)
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to event bus (no-op for in-memory)."""
        self._connected = True
        logger.info("In-memory event bus connected")

    async def disconnect(self) -> None:
        """Disconnect from event bus (no-op for in-memory)."""
        self._connected = False
        logger.info("In-memory event bus disconnected")

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: Event to publish
        """
        if not self._connected:
            logger.warning("Event bus not connected, event dropped")
            return

        handlers = self._handlers.get(event.type, [])

        if not handlers:
            logger.debug("No handlers for event: %s", event.type)
            return

        # Fire all handlers concurrently
        tasks = [self._safe_handle(handler, event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug("Event %s published to %d handlers", event.type, len(handlers))

    async def _safe_handle(self, handler, event: Event) -> None:
        """
        Safely call handler with error handling.

        Args:
            handler: Event handler
            event: Event to handle
        """
        try:
            await handler.handle(event)
        except Exception as e:
            logger.error(
                f"Handler {handler.__class__.__name__} failed for event {event.type}: {e}",
                exc_info=True,
            )

    def subscribe(self, event_type: EventType, handler) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: Type of event
            handler: Handler instance
        """
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(
                "Handler %s subscribed to %s", handler.__class__.__name__, event_type
            )

    def unsubscribe(self, event_type: EventType, handler) -> None:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: Type of event
            handler: Handler instance
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(
                "Handler %s unsubscribed from %s",
                handler.__class__.__name__,
                event_type,
            )

    async def publish_batch(self, events: List[Event]) -> None:
        """
        Publish multiple events in batch.

        Args:
            events: List of events
        """
        # Group events by type for efficiency
        by_type: Dict[EventType, List[Event]] = defaultdict(list)
        for event in events:
            by_type[event.type].append(event)

        # Publish each type
        tasks = [self.publish(event) for event in events]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_handler_count(self, event_type: EventType) -> int:
        """
        Get number of handlers for an event type.

        Args:
            event_type: Event type

        Returns:
            Number of handlers
        """
        return len(self._handlers.get(event_type, []))

    async def health_check(self) -> bool:
        """
        Check if event bus is healthy.

        Returns:
            True if healthy
        """
        return self._connected

    def clear_handlers(self) -> None:
        """Clear all handlers (for testing)."""
        self._handlers.clear()

    def get_stats(self) -> Dict[str, int]:
        """
        Get event bus statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_event_types": len(self._handlers),
            "total_handlers": sum(len(h) for h in self._handlers.values()),
            "connected": self._connected,
        }
