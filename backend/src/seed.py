"""Generate demo data for exploring the API."""
import asyncio
import math
import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import Settings


async def seed() -> None:
    settings = Settings()  # type: ignore[call-arg]
    engine = create_async_engine(settings.database_url)

    device_id = uuid4()
    api_key_hash = "$2b$12$demo_seed_hash_not_for_production"  # placeholder

    async with engine.begin() as conn:
        # Register a demo device
        await conn.execute(
            text("""
                INSERT INTO devices (id, name, api_key_hash, source_type, metadata)
                VALUES (:id, :name, :hash, :source, :meta::jsonb)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": device_id,
                "name": "Demo Apple Watch",
                "hash": api_key_hash,
                "source": "apple_watch",
                "meta": '{"model": "Series 9", "os": "watchOS 12"}',
            },
        )

        # Generate 24 hours of heart rate data (1 sample per minute)
        now = datetime.now(UTC)
        start = now - timedelta(hours=24)
        samples = []
        t = start
        while t < now:
            hour = t.hour
            # Simulate circadian rhythm
            base_hr = 60 + 10 * math.sin(2 * math.pi * (hour - 6) / 24)
            hr = base_hr + random.gauss(0, 5)
            samples.append({
                "time": t,
                "device_id": device_id,
                "metric": "heart_rate",
                "value": round(max(40, min(180, hr)), 1),
                "unit": "bpm",
                "source": "apple_watch_series_9",
            })
            t += timedelta(minutes=1)

        # Bulk insert
        await conn.execute(
            text("""
                INSERT INTO raw_samples (time, device_id, metric, value, unit, source)
                VALUES (:time, :device_id, :metric, :value, :unit, :source)
                ON CONFLICT DO NOTHING
            """),
            samples,
        )

    await engine.dispose()
    print(f"Seeded {len(samples)} samples for device {device_id}")
    print(f"Device ID: {device_id}")


if __name__ == "__main__":
    asyncio.run(seed())
