import logging
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# --- HTTP metrics (set by ASGI middleware) ---

HTTP_REQUESTS_TOTAL = Counter(
    "oc_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "oc_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

HTTP_IN_FLIGHT = Gauge(
    "oc_http_requests_in_flight",
    "Currently active HTTP requests",
)

# --- Domain metrics (set by services) ---

SAMPLES_INGESTED = Counter(
    "oc_samples_ingested_total",
    "Samples accepted at the API boundary",
    ["metric_type"],
)

ANOMALIES_FLAGGED = Counter(
    "oc_anomalies_flagged_total",
    "Anomalies detected by processors",
    ["metric_type", "validator"],
)

RATE_LIMIT_REJECTIONS = Counter(
    "oc_rate_limit_rejections_total",
    "Requests rejected by rate limiter",
)

DEAD_LETTERS_TOTAL = Counter(
    "oc_dead_letters_total",
    "Events persisted to dead letter queue",
)

# --- WebSocket metrics (set by streaming broadcaster) ---

WS_CONNECTIONS_ACTIVE = Gauge(
    "oc_ws_connections_active",
    "Currently active WebSocket connections",
)

WS_MESSAGES_SENT = Counter(
    "oc_ws_messages_sent_total",
    "Messages pushed to WebSocket clients",
)

# --- Infrastructure metrics (set on scrape) ---

EVENT_BUS_QUEUE_DEPTH = Gauge(
    "oc_event_bus_queue_depth",
    "Current event bus queue size",
)

DB_POOL_SIZE = Gauge(
    "oc_db_pool_size",
    "SQLAlchemy connection pool size",
)

DB_POOL_CHECKED_OUT = Gauge(
    "oc_db_pool_checked_out",
    "Active database connections",
)

REDIS_CONNECTED = Gauge(
    "oc_redis_connected",
    "Redis reachability (1=up, 0=down)",
)


async def collect_infra_metrics(engine: Any, redis: Any, event_bus: Any) -> None:
    """Collect infrastructure metrics on demand (called per scrape)."""
    # DB pool
    pool = engine.pool
    DB_POOL_SIZE.set(pool.size())
    DB_POOL_CHECKED_OUT.set(pool.checkedout())

    # Redis
    try:
        await redis.ping()
        REDIS_CONNECTED.set(1)
    except Exception:
        REDIS_CONNECTED.set(0)

    # Event bus
    EVENT_BUS_QUEUE_DEPTH.set(event_bus.queue_depth)
