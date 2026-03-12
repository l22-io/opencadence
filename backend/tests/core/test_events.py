import asyncio
from dataclasses import dataclass

import pytest

from src.core.events import Event, EventBus, InProcessEventBus


@dataclass(frozen=True)
class SampleEvent(Event):
    value: int


@pytest.fixture
def bus() -> InProcessEventBus:
    return InProcessEventBus(max_queue_depth=100)


async def test_publish_and_subscribe(bus: InProcessEventBus) -> None:
    received: list[SampleEvent] = []

    async def handler(event: SampleEvent) -> None:
        received.append(event)

    bus.subscribe(SampleEvent, handler)
    await bus.start()

    await bus.publish(SampleEvent(value=42))
    await asyncio.sleep(0.05)

    assert len(received) == 1
    assert received[0].value == 42

    await bus.stop()


async def test_multiple_subscribers(bus: InProcessEventBus) -> None:
    counts = {"a": 0, "b": 0}

    async def handler_a(event: SampleEvent) -> None:
        counts["a"] += 1

    async def handler_b(event: SampleEvent) -> None:
        counts["b"] += 1

    bus.subscribe(SampleEvent, handler_a)
    bus.subscribe(SampleEvent, handler_b)
    await bus.start()

    await bus.publish(SampleEvent(value=1))
    await asyncio.sleep(0.05)

    assert counts["a"] == 1
    assert counts["b"] == 1

    await bus.stop()


async def test_queue_depth_exceeded(bus: InProcessEventBus) -> None:
    """When queue is full, publish returns False."""
    small_bus = InProcessEventBus(max_queue_depth=2)

    async def slow_handler(event: SampleEvent) -> None:
        await asyncio.sleep(1)

    small_bus.subscribe(SampleEvent, slow_handler)
    await small_bus.start()

    # Fill the queue
    await small_bus.publish(SampleEvent(value=1))
    await small_bus.publish(SampleEvent(value=2))
    result = await small_bus.publish(SampleEvent(value=3))

    assert result is False

    await small_bus.stop()
