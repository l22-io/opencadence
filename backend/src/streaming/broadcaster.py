from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

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
