import asyncio  # noqa: F401
import csv  # noqa: F401
import io  # noqa: F401
import json as json_mod
import sys  # noqa: F401
from datetime import UTC, datetime, timezone  # noqa: F401
from typing import Any
from uuid import UUID, uuid4  # noqa: F401

import typer
from redis.asyncio import Redis  # noqa: F401
from sqlalchemy import text  # noqa: F401
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.auth import generate_api_key, hash_api_key  # noqa: F401
from src.core.config import Settings
from src.storage.database import create_session_factory
from src.storage.repository import SampleRepository  # noqa: F401

app = typer.Typer(name="opencadence", help="OpenCadence management CLI.")
keys_app = typer.Typer(help="Manage device API keys.")
dead_letters_app = typer.Typer(help="Manage dead letter queue.")

app.add_typer(keys_app, name="keys")
app.add_typer(dead_letters_app, name="dead-letters")

_json_output: bool = False


@app.callback()
def main(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """OpenCadence management CLI."""
    global _json_output
    _json_output = json_output


def _get_session_factory() -> async_sessionmaker:
    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception as exc:
        typer.echo(f"Error: failed to load settings: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    return create_session_factory(settings)


def _get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:
        typer.echo(f"Error: failed to load settings: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _error(msg: str) -> None:
    typer.echo(f"Error: {msg}")
    raise typer.Exit(code=1)


def _output(data: dict[str, Any] | list[dict[str, Any]], plain: str) -> None:
    if _json_output:
        typer.echo(json_mod.dumps(data, default=str))
    else:
        typer.echo(plain)


@keys_app.command("generate")
def keys_generate(
    name: str = typer.Argument(..., help="Device name"),
    source_type: str = typer.Option("healthkit", help="Source type: healthkit or health-connect"),
) -> None:
    """Create a new device and API key."""
    asyncio.run(_keys_generate(name, source_type))


async def _keys_generate(name: str, source_type: str) -> None:
    factory = _get_session_factory()
    device_id = uuid4()
    raw_key = generate_api_key(device_id)
    key_hash = hash_api_key(raw_key)

    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO devices (id, name, api_key_hash, source_type) "
                "VALUES (:id, :name, :hash, :source)"
            ),
            {"id": device_id, "name": name, "hash": key_hash, "source": source_type},
        )
        await session.commit()

    _output(
        {
            "device_id": str(device_id),
            "api_key": raw_key,
            "name": name,
            "source_type": source_type,
        },
        f"Device ID: {device_id}\nAPI Key:   {raw_key}\n"
        f"Name:      {name}\nSource:    {source_type}",
    )


@keys_app.command("rotate")
def keys_rotate(
    device_id: str = typer.Argument(..., help="Device UUID"),
) -> None:
    """Rotate a device's API key."""
    try:
        did = UUID(device_id)
    except ValueError:
        _error(f"invalid UUID: {device_id}")
    asyncio.run(_keys_rotate(did))


async def _keys_rotate(device_id: UUID) -> None:
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text("SELECT id, name, revoked_at FROM devices WHERE id = :id"),
            {"id": device_id},
        )
        row = result.first()
        if row is None:
            _error(f"device {device_id} not found")
        device = dict(row._mapping)
        if device["revoked_at"] is not None:
            _error(f"device {device_id} is revoked")

        raw_key = generate_api_key(device_id)
        key_hash = hash_api_key(raw_key)
        await session.execute(
            text("UPDATE devices SET api_key_hash = :hash WHERE id = :id"),
            {"hash": key_hash, "id": device_id},
        )
        await session.commit()

    _output(
        {"device_id": str(device_id), "api_key": raw_key},
        f"Device ID: {device_id}\nNew API Key: {raw_key}",
    )


@keys_app.command("revoke")
def keys_revoke(
    device_id: str = typer.Argument(..., help="Device UUID"),
) -> None:
    """Revoke a device's API key."""
    try:
        did = UUID(device_id)
    except ValueError:
        _error(f"invalid UUID: {device_id}")
    asyncio.run(_keys_revoke(did))


async def _keys_revoke(device_id: UUID) -> None:
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text("SELECT id, name, revoked_at FROM devices WHERE id = :id"),
            {"id": device_id},
        )
        row = result.first()
        if row is None:
            _error(f"device {device_id} not found")
        device = dict(row._mapping)
        if device["revoked_at"] is not None:
            _error(f"device {device_id} is already revoked")

        await session.execute(
            text("UPDATE devices SET revoked_at = :now WHERE id = :id"),
            {"now": datetime.now(UTC), "id": device_id},
        )
        await session.commit()

    _output(
        {"device_id": str(device_id), "status": "revoked"},
        f"Device {device_id} revoked.",
    )


@app.command("export")
def export_cmd(
    device_id: str = typer.Argument(..., help="Device UUID"),
    metric: str = typer.Option(..., help="Metric name (e.g. heart_rate)"),
    start: str = typer.Option(..., help="Start date (ISO format, e.g. 2026-03-01)"),
    end: str = typer.Option(..., help="End date (ISO format, exclusive)"),
    format: str = typer.Option("csv", help="Output format: csv or json"),  # noqa: A002
) -> None:
    """Export raw sample data to stdout."""
    try:
        did = UUID(device_id)
    except ValueError:
        _error(f"invalid UUID: {device_id}")
    try:
        start_dt = datetime.fromisoformat(start).replace(tzinfo=UTC)
        end_dt = datetime.fromisoformat(end).replace(tzinfo=UTC)
    except ValueError:
        _error("invalid date format: use ISO format like 2026-03-01")
    asyncio.run(_export(did, metric, start_dt, end_dt, format))


async def _export(device_id: UUID, metric: str, start: datetime, end: datetime, fmt: str) -> None:
    factory = _get_session_factory()
    repo = SampleRepository()
    async with factory() as session:
        rows = await repo.query_raw(session, device_id, metric, start, end)

    use_json = _json_output or fmt == "json"
    if use_json:
        typer.echo(json_mod.dumps(rows, default=str))
    else:
        if not rows:
            return
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["time", "value", "unit", "source"])
        writer.writeheader()
        writer.writerows(rows)
        typer.echo(output.getvalue().rstrip())


@dead_letters_app.command("replay")
def dl_replay(
    dl_id: int = typer.Argument(..., help="Dead letter ID"),
) -> None:
    """Mark a dead letter as replayed."""
    asyncio.run(_dl_replay(dl_id))


async def _dl_replay(dl_id: int) -> None:
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text("SELECT id, replayed_at FROM dead_letter WHERE id = :id"),
            {"id": dl_id},
        )
        row = result.first()
        if row is None:
            _error(f"dead letter {dl_id} not found")
        dl = dict(row._mapping)
        if dl["replayed_at"] is not None:
            _error(f"dead letter {dl_id} already replayed")

        await session.execute(
            text("UPDATE dead_letter SET replayed_at = :now WHERE id = :id"),
            {"now": datetime.now(UTC), "id": dl_id},
        )
        await session.commit()

    _output(
        {"id": dl_id, "status": "replayed"},
        f"Dead letter {dl_id} marked as replayed.",
    )


@dead_letters_app.command("list")
def dl_list(
    status: str = typer.Option("pending", help="Filter: pending, replayed, or all"),
    limit: int = typer.Option(50, min=1, max=200, help="Max entries to return"),
) -> None:
    """List dead letter entries."""
    asyncio.run(_dl_list(status, limit))


async def _dl_list(status: str, limit: int) -> None:
    factory = _get_session_factory()
    where = "1=1"
    if status == "pending":
        where = "replayed_at IS NULL"
    elif status == "replayed":
        where = "replayed_at IS NOT NULL"

    async with factory() as session:
        result = await session.execute(
            text(
                f"SELECT id, event_type, error, module, created_at, replayed_at "  # noqa: S608
                f"FROM dead_letter WHERE {where} "
                f"ORDER BY created_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        )
        rows = [dict(row._mapping) for row in result]

    if _json_output:
        typer.echo(json_mod.dumps(rows, default=str))
    else:
        if not rows:
            typer.echo("No dead letters found.")
            return
        typer.echo(f"{'ID':<6}{'Event Type':<18}{'Error':<30}{'Created At':<28}{'Status'}")
        for row in rows:
            dl_status = "replayed" if row["replayed_at"] else "pending"
            error_short = str(row["error"])[:28]
            typer.echo(
                f"{row['id']:<6}{row['event_type']:<18}{error_short:<30}"
                f"{str(row['created_at']):<28}{dl_status}"
            )


@app.command("health")
def health() -> None:
    """Check connectivity to backend services."""
    asyncio.run(_health())


async def _health() -> None:
    settings = _get_settings()
    statuses: dict[str, str] = {}

    # DB check
    try:
        factory = _get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        statuses["db"] = "ok"
    except Exception as exc:
        statuses["db"] = f"error: {exc}"

    # Redis check
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
        statuses["redis"] = "ok"
    except Exception as exc:
        statuses["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in statuses.values())

    if _json_output:
        typer.echo(json_mod.dumps(statuses))
    else:
        typer.echo(f"DB:    {statuses['db']}")
        typer.echo(f"Redis: {statuses['redis']}")

    if not all_ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
