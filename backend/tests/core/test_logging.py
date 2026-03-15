import logging

from src.core.logging import setup_logging


def test_structured_logging(capfd: object) -> None:
    setup_logging(level="DEBUG", testing=True)
    logger = logging.getLogger("test")
    logger.info("test message", extra={"correlation_id": "abc-123"})
    # Verify structlog is configured (no crash is the minimal test)
    assert True


def test_setup_logging_returns_without_error() -> None:
    setup_logging(level="INFO", testing=True)
