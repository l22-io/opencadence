from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.metrics.instruments import WS_CONNECTIONS_ACTIVE, WS_MESSAGES_SENT

if TYPE_CHECKING:
    from uuid import UUID

    from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionFilter:
    """Per-client subscription state: which devices/metrics to receive."""

    _subscriptions: dict[UUID, set[str] | None] = field(default_factory=dict)

    def add(self, device_id: UUID, metrics: set[str] | None) -> None:
        if metrics is None:
            self._subscriptions[device_id] = None
        else:
            existing = self._subscriptions.get(device_id)
            if existing is None and device_id in self._subscriptions:
                return  # already subscribed to all
            if existing is None:
                self._subscriptions[device_id] = set(metrics)
            else:
                existing.update(metrics)

    def remove(self, device_id: UUID, metrics: set[str] | None) -> None:
        if metrics is None:
            self._subscriptions.pop(device_id, None)
        else:
            existing = self._subscriptions.get(device_id)
            if existing is None:
                return
            existing -= metrics
            if not existing:
                del self._subscriptions[device_id]

    def matches(self, device_id: UUID, metric: str) -> bool:
        allowed = self._subscriptions.get(device_id)
        if allowed is None and device_id not in self._subscriptions:
            return False
        if allowed is None:
            return True
        return metric in allowed

    @property
    def device_ids(self) -> list[UUID]:
        return list(self._subscriptions.keys())

    def metrics_for(self, device_id: UUID) -> set[str] | None:
        return self._subscriptions.get(device_id)


SEND_TIMEOUT = 5.0


class WebSocketBroadcaster:
    """Manages WebSocket clients and broadcasts DataReceived events."""

    def __init__(self) -> None:
        self._clients: dict[WebSocket, SubscriptionFilter] = {}

    @property
    def connection_count(self) -> int:
        return len(self._clients)

    def register(self, ws: WebSocket, filter_: SubscriptionFilter) -> None:
        self._clients[ws] = filter_
        WS_CONNECTIONS_ACTIVE.inc()

    def unregister(self, ws: WebSocket) -> None:
        if ws in self._clients:
            del self._clients[ws]
            WS_CONNECTIONS_ACTIVE.dec()

    def get_filter(self, ws: WebSocket) -> SubscriptionFilter | None:
        return self._clients.get(ws)

    async def broadcast(
        self,
        device_id: UUID,
        metric: str,
        data: dict,
    ) -> None:
        disconnected: list[WebSocket] = []
        for ws, filter_ in list(self._clients.items()):
            if not filter_.matches(device_id, metric):
                continue
            try:
                await asyncio.wait_for(
                    ws.send_json({"type": "sample", "data": data}),
                    timeout=SEND_TIMEOUT,
                )
                WS_MESSAGES_SENT.inc()
            except Exception:
                logger.warning("Disconnecting slow/broken WebSocket client")
                disconnected.append(ws)

        for ws in disconnected:
            self.unregister(ws)
            with contextlib.suppress(Exception):
                await ws.close(code=1008, reason="Send timeout")

    async def handle_data_received(self, event: Any) -> None:
        """Event bus handler for DataReceived events."""
        payload = event.payload
        device_id = payload.device_id
        for sample in payload.batch:
            data = {
                "device_id": str(device_id),
                "metric": sample.metric,
                "time": sample.timestamp.isoformat(),
                "value": sample.value,
                "unit": sample.unit,
                "source": sample.source,
            }
            await self.broadcast(device_id, sample.metric, data)

    async def stop(self) -> None:
        for ws in list(self._clients):
            with contextlib.suppress(Exception):
                await ws.close(code=1001, reason="Server shutting down")
        self._clients.clear()
        WS_CONNECTIONS_ACTIVE.set(0)
