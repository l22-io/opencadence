from src.core.config import Settings


def test_default_settings() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/opencadence",
        redis_url="redis://localhost:6379/0",
        jwt_secret="test-secret-key-min-32-characters-long",  # noqa: S106
    )
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/opencadence"
    assert settings.raw_retention_days == 90
    assert settings.batch_size_limit == 1000
    assert settings.event_bus_queue_depth == 10000
    assert settings.api_rate_limit == 100
    assert settings.log_level == "INFO"


def test_settings_override() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/test",
        redis_url="redis://localhost:6379/1",
        jwt_secret="test-secret-key-min-32-characters-long",  # noqa: S106
        raw_retention_days=30,
        batch_size_limit=500,
        log_level="DEBUG",
    )
    assert settings.raw_retention_days == 30
    assert settings.batch_size_limit == 500
    assert settings.log_level == "DEBUG"
