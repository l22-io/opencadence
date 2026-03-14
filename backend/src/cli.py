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


if __name__ == "__main__":
    app()
