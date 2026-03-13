import time
from collections.abc import Callable
from typing import Any

from src.metrics.instruments import (
    HTTP_IN_FLIGHT,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
)

Scope = dict[str, Any]
Receive = Callable[..., Any]
Send = Callable[..., Any]
ASGIApp = Callable[..., Any]


class PrometheusMiddleware:
    """ASGI middleware that records HTTP request metrics."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope["method"]
        path = scope["path"].rstrip("/") or "/"
        status_code = 500  # default if response never completes

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        HTTP_IN_FLIGHT.inc()
        start = time.monotonic()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.monotonic() - start
            HTTP_IN_FLIGHT.dec()
            HTTP_REQUESTS_TOTAL.labels(
                method=method, path=path, status=str(status_code)
            ).inc()
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration)
