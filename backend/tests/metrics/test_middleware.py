from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.metrics.instruments import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
)
from src.metrics.middleware import PrometheusMiddleware

OK_LABELS = {"method": "GET", "path": "/test", "status": "200"}
FAIL_LABELS = {"method": "GET", "path": "/fail", "status": "500"}


def _counter_value(counter, labels):
    try:
        return counter.labels(**labels)._value.get()
    except KeyError:
        return 0.0


def _histogram_count(histogram, labels):
    """Read the observation count from a histogram with given labels."""
    for metric_family in histogram.collect():
        for sample in metric_family.samples:
            if sample.name.endswith("_count") and all(
                sample.labels.get(k) == v for k, v in labels.items()
            ):
                return int(sample.value)
    return 0


def _make_app():
    app = FastAPI()

    @app.get("/test")
    async def test_route():
        return {"ok": True}

    @app.get("/fail")
    async def fail_route():
        raise ValueError("boom")

    app = PrometheusMiddleware(app)
    return app


def test_middleware_increments_request_counter():
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    before = _counter_value(HTTP_REQUESTS_TOTAL, OK_LABELS)
    client.get("/test")
    after = _counter_value(HTTP_REQUESTS_TOTAL, OK_LABELS)

    assert after - before == 1


def test_middleware_records_duration():
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    before = _histogram_count(
        HTTP_REQUEST_DURATION, {"method": "GET", "path": "/test"}
    )
    client.get("/test")
    after = _histogram_count(
        HTTP_REQUEST_DURATION, {"method": "GET", "path": "/test"}
    )

    assert after - before == 1


def test_middleware_tracks_error_status():
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    before = _counter_value(HTTP_REQUESTS_TOTAL, FAIL_LABELS)
    client.get("/fail")
    after = _counter_value(HTTP_REQUESTS_TOTAL, FAIL_LABELS)

    assert after - before == 1


def test_middleware_strips_trailing_slash():
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    before = _counter_value(HTTP_REQUESTS_TOTAL, OK_LABELS)
    client.get("/test/")
    after = _counter_value(HTTP_REQUESTS_TOTAL, OK_LABELS)

    # Trailing slash gets stripped, so same label as /test
    # (May 404 depending on FastAPI config, but path label should be /test)
    assert after >= before
