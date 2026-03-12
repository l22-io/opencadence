"""Initial schema with TimescaleDB hypertable.

Revision ID: 001
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # Devices table
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("api_key_hash", sa.Text, nullable=False),
        sa.Column("source_type", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Raw samples hypertable
    op.create_table(
        "raw_samples",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.Uuid, nullable=False),
        sa.Column("metric", sa.Text, nullable=False),
        sa.Column("value", sa.Double, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("time", "device_id", "metric", "source"),
    )
    op.create_index("ix_raw_samples_device_metric", "raw_samples", ["device_id", "metric"])

    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('raw_samples', by_range('time'))"
    )

    # Continuous aggregates
    op.execute("""
        CREATE MATERIALIZED VIEW aggregates_1min
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 minute', time) AS bucket,
            device_id,
            metric,
            min(value) AS min_value,
            max(value) AS max_value,
            avg(value) AS mean_value,
            stddev(value) AS stddev_value,
            count(*) AS sample_count
        FROM raw_samples
        GROUP BY bucket, device_id, metric
        WITH NO DATA
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW aggregates_1hr
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', time) AS bucket,
            device_id,
            metric,
            min(value) AS min_value,
            max(value) AS max_value,
            avg(value) AS mean_value,
            stddev(value) AS stddev_value,
            count(*) AS sample_count
        FROM raw_samples
        GROUP BY bucket, device_id, metric
        WITH NO DATA
    """)

    # Refresh policies for continuous aggregates
    op.execute("""
        SELECT add_continuous_aggregate_policy('aggregates_1min',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 minute',
            schedule_interval => INTERVAL '1 minute')
    """)

    op.execute("""
        SELECT add_continuous_aggregate_policy('aggregates_1hr',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour')
    """)

    # Anomalies table
    op.create_table(
        "anomalies",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.Uuid, nullable=False),
        sa.Column("metric", sa.Text, nullable=False),
        sa.Column("value", sa.Double, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("context", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Dead letter table
    op.create_table(
        "dead_letter",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("error", sa.Text, nullable=False),
        sa.Column("module", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS aggregates_1hr CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS aggregates_1min CASCADE")
    op.drop_table("dead_letter")
    op.drop_table("anomalies")
    op.drop_table("raw_samples")
    op.drop_table("devices")
