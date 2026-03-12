# ADR-002: TimescaleDB for Time-Series Storage

## Status
Accepted

## Context
Health data from wearables is inherently time-series: high-frequency samples (heart rate every few seconds) that need efficient storage, retention policies, and pre-computed aggregates across time windows.

## Decision
Use TimescaleDB (PostgreSQL extension) as the primary database. Leverage hypertables for automatic time-based partitioning, continuous aggregates for 1-minute and 1-hour rollups, and retention policies for raw data lifecycle.

## Alternatives Considered
- **InfluxDB**: Purpose-built time-series DB, but adds a separate query language (Flux/InfluxQL) and loses PostgreSQL ecosystem (tooling, ORMs, managed hosting).
- **Plain PostgreSQL with partitioning**: Manual partitioning management, no built-in continuous aggregates. More operational burden.

## Consequences
- Native time-series optimizations (chunked storage, compression)
- Continuous aggregates computed automatically in the background
- Full PostgreSQL compatibility (SQLAlchemy, Alembic, pg_dump)
- Requires TimescaleDB extension (available in Docker, most managed Postgres providers)
