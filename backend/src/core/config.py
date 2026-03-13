from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required
    database_url: str
    redis_url: str
    jwt_secret: str

    # Data retention
    raw_retention_days: int = 90

    # Ingestion limits
    batch_size_limit: int = 1000
    api_rate_limit: int = 100  # requests per minute per device key

    # Event bus
    event_bus_queue_depth: int = 10000

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Metrics
    metrics_token: str | None = None

    model_config = {"env_prefix": "OC_", "env_file": ".env", "env_file_encoding": "utf-8"}
