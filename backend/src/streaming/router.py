import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.auth import decode_jwt_token
from src.core.registry import MetricRegistry
from src.storage.repository import SampleRepository
from src.streaming.broadcaster import SubscriptionFilter, WebSocketBroadcaster

logger = logging.getLogger(__name__)


def create_stream_router(
    broadcaster: WebSocketBroadcaster,
    session_factory: async_sessionmaker[AsyncSession] | None,
    repo: SampleRepository,
    registry: MetricRegistry,
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["streaming"])

    @router.websocket("/stream")
    async def stream(ws: WebSocket) -> None:
        # --- Auth ---
        token = ws.query_params.get("token")
        if not token:
            await ws.close(code=4001, reason="Missing token")
            return

        claims = decode_jwt_token(token, secret=jwt_secret, algorithm=jwt_algorithm)
        if claims is None:
            await ws.close(code=4001, reason="Invalid token")
            return

        allowed_device_ids = {UUID(d) for d in claims.get("device_ids", [])}
        await ws.accept()

        filter_ = SubscriptionFilter()
        broadcaster.register(ws, filter_)

        try:
            while True:
                msg = await ws.receive_json()
                action = msg.get("action")

                if action == "subscribe":
                    await _handle_subscribe(
                        ws,
                        msg,
                        filter_,
                        allowed_device_ids,
                        registry,
                    )
                elif action == "unsubscribe":
                    _handle_unsubscribe(ws, msg, filter_, allowed_device_ids)
                    await ws.send_json(
                        {
                            "type": "unsubscribed",
                            "device_ids": msg.get("device_ids", []),
                        }
                    )
                else:
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown action: {action}",
                        }
                    )
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WebSocket error")
        finally:
            broadcaster.unregister(ws)

    async def _handle_subscribe(
        ws: WebSocket,
        msg: dict[str, Any],
        filter_: SubscriptionFilter,
        allowed_device_ids: set[UUID],
        registry: MetricRegistry,
    ) -> None:
        raw_ids = msg.get("device_ids", [])
        metrics_list = msg.get("metrics")
        since_str = msg.get("since")

        # Validate device IDs
        device_ids: list[UUID] = []
        for raw_id in raw_ids:
            try:
                did = UUID(raw_id)
            except ValueError:
                await ws.send_json({"type": "error", "message": f"Invalid device ID: {raw_id}"})
                return
            if did not in allowed_device_ids:
                await ws.send_json(
                    {
                        "type": "error",
                        "message": f"Device {raw_id} not authorized for this token",
                    }
                )
                return
            device_ids.append(did)

        # Validate metrics
        metrics: set[str] | None = None
        if metrics_list is not None:
            for m in metrics_list:
                if registry.get(m) is None:
                    await ws.send_json({"type": "error", "message": f"Unknown metric: {m}"})
                    return
            metrics = set(metrics_list)

        # Apply subscription
        for did in device_ids:
            filter_.add(did, metrics)

        # Backfill if since provided
        if since_str and session_factory is not None:
            since = datetime.fromisoformat(since_str)
            now = datetime.now(UTC)
            query_metrics = list(metrics) if metrics else registry.list_metrics()

            async with session_factory() as session:
                for did in device_ids:
                    for metric_name in query_metrics:
                        rows = await repo.query_raw(
                            session,
                            did,
                            metric_name,
                            start=since,
                            end=now,
                            limit=1000,
                        )
                        for row in rows:
                            await ws.send_json(
                                {
                                    "type": "backfill",
                                    "data": {
                                        "device_id": str(did),
                                        "metric": metric_name,
                                        "time": row["time"].isoformat(),
                                        "value": row["value"],
                                        "unit": row["unit"],
                                        "source": row["source"],
                                    },
                                }
                            )

            await ws.send_json({"type": "backfill_complete"})

        await ws.send_json(
            {
                "type": "subscribed",
                "device_ids": [str(d) for d in device_ids],
                "metrics": list(metrics) if metrics else None,
            }
        )

    def _handle_unsubscribe(
        ws: WebSocket,
        msg: dict[str, Any],
        filter_: SubscriptionFilter,
        allowed_device_ids: set[UUID],
    ) -> None:
        raw_ids = msg.get("device_ids", [])
        metrics_list = msg.get("metrics")
        metrics = set(metrics_list) if metrics_list else None

        for raw_id in raw_ids:
            try:
                did = UUID(raw_id)
            except ValueError:
                continue
            filter_.remove(did, metrics)

    return router
