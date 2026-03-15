import asyncio
import contextlib
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    """Base class for all events."""

    pass


class EventHandler(Protocol):
    async def __call__(self, event: Any) -> None: ...


class EventBus(Protocol):
    """Protocol for event bus implementations."""

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None: ...
    async def publish(self, event: Event) -> bool: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class InProcessEventBus:
    """In-process async event bus with bounded queue."""

    def __init__(self, max_queue_depth: int = 10000) -> None:
        self._handlers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue_depth)
        self._task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> bool:
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Event bus queue full, dropping event: %s", type(event).__name__)
            return False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._process())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _process(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except TimeoutError:
                continue

            handlers = self._handlers.get(type(event), [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:
                    logger.exception(
                        "Handler %s failed for event %s",
                        handler.__name__ if hasattr(handler, "__name__") else handler,
                        type(event).__name__,
                    )
