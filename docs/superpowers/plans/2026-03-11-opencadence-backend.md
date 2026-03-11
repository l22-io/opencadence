# OpenCadence Backend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hostable health data pipeline backend with FastAPI, TimescaleDB, and Docker Compose.

**Architecture:** Modular monolith with five internal modules (ingestion, processing, storage, API, FHIR) communicating via an in-process async event bus. Device-based identity model with API keys for ingest and JWT for queries.

**Tech Stack:** Python 3.12, FastAPI, TimescaleDB, Redis, Alembic, Docker Compose, pytest, ruff, mypy

**Spec:** `docs/superpowers/specs/2026-03-11-opencadence-design.md`

---

## Chunk 1: Project Scaffolding & Core Module

### Task 1: OSS Foundation Files

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `CODE_OF_CONDUCT.md`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/ISSUE_TEMPLATE/data_source_request.md`
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg
.venv/
venv/

# Environment
.env
*.local.*

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# AI assistants
.claude/
.cursor/
.aider*
.copilot/

# Docker volumes
data/
pgdata/

# Test / Coverage
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Alembic
backend/migrations/versions/__pycache__/
```

- [ ] **Step 2: Create LICENSE (Apache 2.0)**

Download the standard Apache 2.0 license text. Set copyright to `2026 Sebastian Varga`.

- [ ] **Step 3: Create CODE_OF_CONDUCT.md**

Use Contributor Covenant v2.1 (standard text from https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

- [ ] **Step 4: Create SECURITY.md**

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do not open a public issue.**

Instead, email **security@l22.io** with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to provide a fix within 7 days for critical issues.

## Scope

- Backend API and data pipeline
- Authentication and authorization mechanisms
- Data handling and storage
- Docker and Kubernetes configurations

## Out of Scope

- Denial of service attacks
- Social engineering
- Issues in third-party dependencies (report upstream)
```

- [ ] **Step 5: Create CONTRIBUTING.md**

```markdown
# Contributing to OpenCadence

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Make

### Getting Started

```bash
git clone https://github.com/your-org/opencadence.git
cd opencadence
cp deploy/docker/.env.example deploy/docker/.env
make dev
```

### Running Tests

```bash
make test        # Unit tests
make test-int    # Integration tests (requires Docker)
make lint        # Linting + type checks
```

## Code Style

- We use **ruff** for linting and formatting
- We use **mypy** for type checking (strict mode)
- All public functions must have type annotations
- Write tests first (TDD)

## Branch Strategy

- `main` — always deployable, tagged releases
- `develop` — integration branch
- `feat/<name>` — new features (branch from `develop`)
- `fix/<name>` — bug fixes (branch from `develop`)
- `docs/<name>` — documentation changes

## Pull Request Process

1. Branch from `develop`
2. Write tests for your changes
3. Ensure `make lint` and `make test` pass
4. Submit PR against `develop`
5. Fill out the PR template
6. Wait for review

## Adding a New Metric Type

One of the most common contributions. See `docs/contributing/adding-metrics.md`.

In short:
1. Create a YAML file in `backend/src/core/metrics/`
2. Optionally create a custom processor in `backend/src/processing/`
3. Add tests
4. Submit PR

## Commit Messages

Use conventional commits:
- `feat: add respiratory rate metric`
- `fix: handle timezone edge case in ingestion`
- `docs: update API usage guide`
- `test: add integration tests for FHIR export`
```

- [ ] **Step 6: Create CHANGELOG.md**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding
```

- [ ] **Step 7: Create issue templates and PR template**

Bug report template:
```markdown
---
name: Bug Report
about: Report a bug in OpenCadence
title: "[BUG] "
labels: bug
---

## Description
A clear description of the bug.

## Steps to Reproduce
1.
2.
3.

## Expected Behavior

## Actual Behavior

## Environment
- OpenCadence version:
- Deployment method: (Docker Compose / Kubernetes / other)
- OS:
```

Feature request template:
```markdown
---
name: Feature Request
about: Suggest a feature for OpenCadence
title: "[FEATURE] "
labels: enhancement
---

## Problem
What problem does this solve?

## Proposed Solution

## Alternatives Considered

## Additional Context
```

Data source request template:
```markdown
---
name: Data Source Request
about: Request support for a new wearable or health data source
title: "[DATA SOURCE] "
labels: metric-request
---

## Data Source
Name and type of the wearable/health data source.

## Metrics Available
What health metrics does this source provide?

## API/SDK Documentation
Link to the data source's API or SDK documentation.

## Additional Context
```

PR template:
```markdown
## Summary
Brief description of changes.

## Changes
-

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] `make lint` passes
- [ ] `make test` passes

## Breaking Changes
None / describe breaking changes.
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore LICENSE CODE_OF_CONDUCT.md SECURITY.md CONTRIBUTING.md CHANGELOG.md .github/
git commit -m "feat: add OSS foundation files

License, contributing guide, security policy, code of conduct,
issue templates, and PR template."
```

---

### Task 2: Python Project Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/__init__.py`
- Create: `backend/src/core/__init__.py`
- Create: `Makefile`
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "opencadence"
version = "0.1.0"
description = "Self-hostable health data pipeline for wearable devices"
readme = "README.md"
license = {text = "Apache-2.0"}
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "pyyaml>=6.0.0",
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.2.0",
    "redis>=5.2.0",
    "structlog>=24.4.0",
    "prometheus-client>=0.21.0",
    "httpx>=0.28.0",
    "typer>=0.15.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "testcontainers[postgres]>=4.9.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "pre-commit>=4.0.0",
    "types-PyYAML>=6.0.0",
    "types-redis>=4.6.0",
]

# CLI entry point - created in a follow-up task
# [project.scripts]
# opencadence = "src.core.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "S", "B", "A", "SIM", "TCH"]
ignore = ["S101"]  # allow assert in tests

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: marks tests requiring Docker services",
]
```

- [ ] **Step 2: Create package init files**

```bash
mkdir -p backend/src/core backend/tests
touch backend/src/__init__.py backend/src/core/__init__.py backend/tests/__init__.py
```

- [ ] **Step 3: Create Makefile**

```makefile
.PHONY: dev test test-int lint format install seed

install:
	cd backend && pip install -e ".[dev]"

dev:
	docker compose -f deploy/docker/docker-compose.yml up -d db redis
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest -v --ignore=tests/integration

test-int:
	cd backend && pytest -v -m integration

lint:
	cd backend && ruff check src tests
	cd backend && ruff format --check src tests
	cd backend && mypy src

format:
	cd backend && ruff check --fix src tests
	cd backend && ruff format src tests

seed:
	cd backend && python -m src.seed

up:
	docker compose -f deploy/docker/docker-compose.yml up -d

down:
	docker compose -f deploy/docker/docker-compose.yml down

migrate:
	cd backend && alembic upgrade head
```

- [ ] **Step 4: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.10.0
          - types-PyYAML>=6.0.0
        args: [--config-file=backend/pyproject.toml]
```

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/src/ backend/tests/ Makefile .pre-commit-config.yaml
git commit -m "feat: add Python project setup with tooling

pyproject.toml with dependencies, Makefile for common commands,
pre-commit hooks for ruff and mypy."
```

---

### Task 3: Configuration Module

**Files:**
- Create: `backend/src/core/config.py`
- Create: `backend/tests/core/__init__.py`
- Create: `backend/tests/core/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_config.py
from src.core.config import Settings


def test_default_settings() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/opencadence",
        redis_url="redis://localhost:6379/0",
        jwt_secret="test-secret-key-min-32-characters-long",
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
        jwt_secret="test-secret-key-min-32-characters-long",
        raw_retention_days=30,
        batch_size_limit=500,
        log_level="DEBUG",
    )
    assert settings.raw_retention_days == 30
    assert settings.batch_size_limit == 500
    assert settings.log_level == "DEBUG"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/core/test_config.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write implementation**

```python
# backend/src/core/config.py
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

    model_config = {"env_prefix": "OC_", "env_file": ".env", "env_file_encoding": "utf-8"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/core/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/config.py backend/tests/core/
git commit -m "feat(core): add configuration module

Pydantic settings with env var support and sensible defaults."
```

---

### Task 4: Event Bus

**Files:**
- Create: `backend/src/core/events.py`
- Create: `backend/tests/core/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_events.py
import asyncio
from dataclasses import dataclass

import pytest

from src.core.events import Event, EventBus, InProcessEventBus


@dataclass(frozen=True)
class SampleEvent(Event):
    value: int


@pytest.fixture
def bus() -> InProcessEventBus:
    return InProcessEventBus(max_queue_depth=100)


async def test_publish_and_subscribe(bus: InProcessEventBus) -> None:
    received: list[SampleEvent] = []

    async def handler(event: SampleEvent) -> None:
        received.append(event)

    bus.subscribe(SampleEvent, handler)
    await bus.start()

    await bus.publish(SampleEvent(value=42))
    await asyncio.sleep(0.05)

    assert len(received) == 1
    assert received[0].value == 42

    await bus.stop()


async def test_multiple_subscribers(bus: InProcessEventBus) -> None:
    counts = {"a": 0, "b": 0}

    async def handler_a(event: SampleEvent) -> None:
        counts["a"] += 1

    async def handler_b(event: SampleEvent) -> None:
        counts["b"] += 1

    bus.subscribe(SampleEvent, handler_a)
    bus.subscribe(SampleEvent, handler_b)
    await bus.start()

    await bus.publish(SampleEvent(value=1))
    await asyncio.sleep(0.05)

    assert counts["a"] == 1
    assert counts["b"] == 1

    await bus.stop()


async def test_queue_depth_exceeded(bus: InProcessEventBus) -> None:
    """When queue is full, publish returns False."""
    small_bus = InProcessEventBus(max_queue_depth=2)

    async def slow_handler(event: SampleEvent) -> None:
        await asyncio.sleep(1)

    small_bus.subscribe(SampleEvent, slow_handler)
    await small_bus.start()

    # Fill the queue
    await small_bus.publish(SampleEvent(value=1))
    await small_bus.publish(SampleEvent(value=2))
    result = await small_bus.publish(SampleEvent(value=3))

    assert result is False

    await small_bus.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/core/test_events.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# backend/src/core/events.py
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    """Base class for all events."""
    pass


class EventHandler(Protocol):
    async def __call__(self, event: Any) -> None: ...


class EventBus(Protocol):
    """Protocol for event bus implementations."""

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None: ...
    async def publish(self, event: Event) -> bool: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class InProcessEventBus:
    """In-process async event bus with bounded queue."""

    def __init__(self, max_queue_depth: int = 10000) -> None:
        self._handlers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue_depth)
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> bool:
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Event bus queue full, dropping event: %s", type(event).__name__)
            return False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._process())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except (asyncio.TimeoutError, TimeoutError):
                continue

            handlers = self._handlers.get(type(event), [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:
                    logger.exception(
                        "Handler %s failed for event %s",
                        handler.__name__ if hasattr(handler, '__name__') else handler,
                        type(event).__name__,
                    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/core/test_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/events.py backend/tests/core/test_events.py
git commit -m "feat(core): add in-process async event bus

Protocol-based EventBus with bounded queue and fan-out to
multiple subscribers."
```

---

### Task 5: Metric Registry

**Files:**
- Create: `backend/src/core/registry.py`
- Create: `backend/src/core/metrics/heart_rate.yaml`
- Create: `backend/src/core/metrics/hrv.yaml`
- Create: `backend/src/core/metrics/spo2.yaml`
- Create: `backend/src/core/metrics/respiratory_rate.yaml`
- Create: `backend/src/core/metrics/skin_temperature.yaml`
- Create: `backend/tests/core/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_registry.py
from pathlib import Path

import pytest

from src.core.registry import MetricDefinition, MetricRegistry


@pytest.fixture
def registry(tmp_path: Path) -> MetricRegistry:
    """Create a registry with a test metric YAML."""
    metric_file = tmp_path / "test_metric.yaml"
    metric_file.write_text("""
name: test_metric
label: Test Metric
unit: units
valid_range:
  min: 0
  max: 100
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "12345-6"
  system: "http://loinc.org"
  display: "Test Metric"
""")
    return MetricRegistry.from_directory(tmp_path)


def test_registry_loads_metric(registry: MetricRegistry) -> None:
    metric = registry.get("test_metric")
    assert metric is not None
    assert metric.name == "test_metric"
    assert metric.label == "Test Metric"
    assert metric.unit == "units"
    assert metric.valid_range.min == 0
    assert metric.valid_range.max == 100


def test_registry_unknown_metric(registry: MetricRegistry) -> None:
    assert registry.get("nonexistent") is None


def test_registry_lists_all_metrics(registry: MetricRegistry) -> None:
    names = registry.list_metrics()
    assert "test_metric" in names


def test_registry_validates_value(registry: MetricRegistry) -> None:
    metric = registry.get("test_metric")
    assert metric is not None
    assert metric.is_in_range(50.0) is True
    assert metric.is_in_range(150.0) is False
    assert metric.is_in_range(-1.0) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/core/test_registry.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# backend/src/core/registry.py
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidRange:
    min: float
    max: float


@dataclass(frozen=True)
class FhirMapping:
    code: str
    system: str
    display: str


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    label: str
    unit: str
    valid_range: ValidRange
    aggregation: str
    processors: list[str]
    fhir: FhirMapping

    def is_in_range(self, value: float) -> bool:
        return self.valid_range.min <= value <= self.valid_range.max


class MetricRegistry:
    """Loads and provides access to metric definitions from YAML files."""

    def __init__(self, metrics: dict[str, MetricDefinition]) -> None:
        self._metrics = metrics

    @classmethod
    def from_directory(cls, path: Path) -> "MetricRegistry":
        metrics: dict[str, MetricDefinition] = {}
        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                definition = MetricDefinition(
                    name=data["name"],
                    label=data["label"],
                    unit=data["unit"],
                    valid_range=ValidRange(
                        min=data["valid_range"]["min"],
                        max=data["valid_range"]["max"],
                    ),
                    aggregation=data["aggregation"],
                    processors=data.get("processors", []),
                    fhir=FhirMapping(
                        code=data["fhir"]["code"],
                        system=data["fhir"]["system"],
                        display=data["fhir"]["display"],
                    ),
                )
                metrics[definition.name] = definition
                logger.info("Loaded metric: %s", definition.name)
            except (KeyError, TypeError) as e:
                logger.error("Invalid metric definition in %s: %s", yaml_file, e)
                raise ValueError(f"Invalid metric definition in {yaml_file}: {e}") from e
        return cls(metrics)

    def get(self, name: str) -> MetricDefinition | None:
        return self._metrics.get(name)

    def list_metrics(self) -> list[str]:
        return list(self._metrics.keys())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/core/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Create metric YAML files**

```yaml
# backend/src/core/metrics/heart_rate.yaml
name: heart_rate
label: Heart Rate
unit: bpm
valid_range:
  min: 20
  max: 300
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "8867-4"
  system: "http://loinc.org"
  display: "Heart rate"
```

```yaml
# backend/src/core/metrics/hrv.yaml
name: hrv
label: Heart Rate Variability
unit: ms
valid_range:
  min: 0
  max: 500
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "80404-7"
  system: "http://loinc.org"
  display: "R-R interval.standard deviation (Heart rate variability)"
```

```yaml
# backend/src/core/metrics/spo2.yaml
name: spo2
label: Blood Oxygen Saturation
unit: "%"
valid_range:
  min: 50
  max: 100
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "2708-6"
  system: "http://loinc.org"
  display: "Oxygen saturation in Arterial blood"
```

```yaml
# backend/src/core/metrics/respiratory_rate.yaml
name: respiratory_rate
label: Respiratory Rate
unit: breaths/min
valid_range:
  min: 4
  max: 60
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "9279-1"
  system: "http://loinc.org"
  display: "Respiratory rate"
```

```yaml
# backend/src/core/metrics/skin_temperature.yaml
name: skin_temperature
label: Skin Temperature
unit: "°C"
valid_range:
  min: 25.0
  max: 42.0
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "39106-0"
  system: "http://loinc.org"
  display: "Temperature of Skin"
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/core/registry.py backend/src/core/metrics/ backend/tests/core/test_registry.py
git commit -m "feat(core): add metric registry with YAML definitions

Loads metric definitions from YAML files at startup. Ships with
5 vitals metrics: heart rate, HRV, SpO2, respiratory rate,
skin temperature. Each metric defines valid range, aggregation
method, processor chain, and FHIR mapping."
```

---

### Task 6: Structured Logging

**Files:**
- Create: `backend/src/core/logging.py`
- Create: `backend/tests/core/test_logging.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_logging.py
import json
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/core/test_logging.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# backend/src/core/logging.py
import logging
import sys

import structlog


def setup_logging(level: str = "INFO", testing: bool = False) -> None:
    """Configure structured JSON logging via structlog."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if testing:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/core/test_logging.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/logging.py backend/tests/core/test_logging.py
git commit -m "feat(core): add structured JSON logging

Structlog-based logging with JSON output in production,
console output in dev/test. Supports correlation IDs
via contextvars."
```

---

### Task 7: Shared Pydantic Models

**Files:**
- Create: `backend/src/core/models.py`
- Create: `backend/tests/core/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_models.py
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.core.models import IngestPayload, Sample


def test_valid_sample() -> None:
    sample = Sample(
        metric="heart_rate",
        value=72.0,
        unit="bpm",
        timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
        source="apple_watch_series_9",
    )
    assert sample.metric == "heart_rate"
    assert sample.value == 72.0


def test_valid_ingest_payload() -> None:
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
                source="apple_watch_series_9",
            )
        ],
    )
    assert len(payload.batch) == 1


def test_empty_batch_rejected() -> None:
    with pytest.raises(ValidationError):
        IngestPayload(device_id=uuid4(), batch=[])


def test_batch_over_limit_rejected() -> None:
    samples = [
        Sample(
            metric="heart_rate",
            value=72.0,
            unit="bpm",
            timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
            source="test",
        )
        for _ in range(1001)
    ]
    with pytest.raises(ValidationError):
        IngestPayload(device_id=uuid4(), batch=samples)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/core/test_models.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# backend/src/core/models.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Sample(BaseModel):
    """A single health data sample from a wearable device."""

    metric: str
    value: float
    unit: str
    timestamp: datetime
    source: str


class IngestPayload(BaseModel):
    """Batch payload for health data ingestion."""

    device_id: UUID
    batch: list[Sample] = Field(min_length=1, max_length=1000)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/core/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/models.py backend/tests/core/test_models.py
git commit -m "feat(core): add shared Pydantic models

IngestPayload and Sample models with batch size validation
(1-1000 samples per request)."
```

---

## Chunk 2: Database, Auth & Docker

### Task 8: SQLAlchemy Models & Alembic Setup

**Files:**
- Create: `backend/src/storage/__init__.py`
- Create: `backend/src/storage/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/001_initial_schema.py`

- [ ] **Step 1: Create SQLAlchemy models**

```python
# backend/src/storage/models.py
import uuid
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawSample(Base):
    """Time-series table for raw health data samples."""

    __tablename__ = "raw_samples"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    metric: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[float] = mapped_column(Double)
    unit: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_raw_samples_device_metric", "device_id", "metric"),
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text)
    api_key_hash: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    metric: Mapped[str] = mapped_column(Text)
    value: Mapped[float] = mapped_column(Double)
    reason: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class DeadLetter(Base):
    __tablename__ = "dead_letter"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    error: Mapped[str] = mapped_column(Text)
    module: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    replayed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 2: Create alembic.ini**

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://opencadence:opencadence@localhost:5432/opencadence

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create migration env.py**

```python
# backend/migrations/env.py
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.storage.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override URL from environment if set
db_url = os.environ.get("OC_DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create initial migration**

```python
# backend/migrations/versions/001_initial_schema.py
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
```

- [ ] **Step 5: Create script.py.mako template**

```mako
# backend/migrations/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/storage/ backend/alembic.ini backend/migrations/
git commit -m "feat(storage): add SQLAlchemy models and Alembic migrations

TimescaleDB hypertable for raw_samples, continuous aggregates
for 1min and 1hr rollups, devices, anomalies, and dead_letter
tables."
```

---

### Task 9: Database Session & Repository

**Files:**
- Create: `backend/src/storage/database.py`
- Create: `backend/src/storage/repository.py`
- Create: `backend/tests/storage/__init__.py`
- Create: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write database session management**

```python
# backend/src/storage/database.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Settings


def create_engine(settings: Settings):  # type: ignore[no-untyped-def]
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
```

- [ ] **Step 2: Write the failing repository tests**

```python
# backend/tests/storage/test_repository.py
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.storage.repository import SampleRepository


@pytest.fixture
def repo() -> SampleRepository:
    """Unit test with mock - integration tests go in tests/integration/."""
    return SampleRepository()


def test_samples_to_insert_params() -> None:
    """Test that payload is converted to insert-ready dicts."""
    device_id = uuid4()
    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
                source="apple_watch",
            ),
        ],
    )
    rows = SampleRepository.payload_to_rows(payload)
    assert len(rows) == 1
    assert rows[0]["device_id"] == device_id
    assert rows[0]["metric"] == "heart_rate"
    assert rows[0]["value"] == 72.0
```

- [ ] **Step 3: Write implementation**

```python
# backend/src/storage/repository.py
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import IngestPayload


class SampleRepository:
    """Data access for raw samples and aggregates."""

    @staticmethod
    def payload_to_rows(payload: IngestPayload) -> list[dict[str, Any]]:
        return [
            {
                "time": sample.timestamp,
                "device_id": payload.device_id,
                "metric": sample.metric,
                "value": sample.value,
                "unit": sample.unit,
                "source": sample.source,
            }
            for sample in payload.batch
        ]

    async def insert_samples(
        self, session: AsyncSession, payload: IngestPayload
    ) -> int:
        rows = self.payload_to_rows(payload)
        stmt = text("""
            INSERT INTO raw_samples (time, device_id, metric, value, unit, source)
            VALUES (:time, :device_id, :metric, :value, :unit, :source)
            ON CONFLICT (time, device_id, metric, source) DO NOTHING
        """)
        result = await session.execute(stmt, rows)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]

    async def query_raw(
        self,
        session: AsyncSession,
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT time, value, unit, source
            FROM raw_samples
            WHERE device_id = :device_id AND metric = :metric
              AND time >= :start AND time < :end
            ORDER BY time
            LIMIT :limit
        """)
        result = await session.execute(
            stmt,
            {"device_id": device_id, "metric": metric, "start": start, "end": end, "limit": limit},
        )
        return [dict(row._mapping) for row in result]

    async def query_aggregates(
        self,
        session: AsyncSession,
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        resolution: str,
    ) -> list[dict[str, Any]]:
        allowed_views = {"1min": "aggregates_1min", "1hr": "aggregates_1hr"}
        view = allowed_views.get(resolution)
        if view is None:
            raise ValueError(f"Invalid resolution: {resolution}")
        stmt = text(f"""
            SELECT bucket AS time, min_value, max_value, mean_value,
                   stddev_value, sample_count
            FROM {view}
            WHERE device_id = :device_id AND metric = :metric
              AND bucket >= :start AND bucket < :end
            ORDER BY bucket
        """)
        result = await session.execute(
            stmt,
            {"device_id": device_id, "metric": metric, "start": start, "end": end},
        )
        return [dict(row._mapping) for row in result]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/storage/test_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/storage/database.py backend/src/storage/repository.py backend/tests/storage/
git commit -m "feat(storage): add database session management and repository

Async SQLAlchemy session factory, SampleRepository with raw
insert (ON CONFLICT dedup), raw query, and aggregate query."
```

---

### Task 10: Authentication Module

**Files:**
- Create: `backend/src/core/auth.py`
- Create: `backend/tests/core/test_auth.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_auth.py
from uuid import uuid4

import pytest

from src.core.auth import (
    create_jwt_token,
    decode_jwt_token,
    hash_api_key,
    verify_api_key,
)


def test_hash_and_verify_api_key() -> None:
    raw_key = "oc_test_key_abc123"
    hashed = hash_api_key(raw_key)
    assert verify_api_key(raw_key, hashed) is True
    assert verify_api_key("wrong_key", hashed) is False


def test_create_and_decode_jwt() -> None:
    device_ids = [uuid4(), uuid4()]
    secret = "test-secret-key-min-32-characters-long"
    token = create_jwt_token(
        device_ids=device_ids,
        secret=secret,
        algorithm="HS256",
        expiry_hours=24,
    )
    payload = decode_jwt_token(token, secret=secret, algorithm="HS256")
    assert payload is not None
    decoded_ids = [str(d) for d in device_ids]
    assert payload["device_ids"] == decoded_ids


def test_decode_invalid_jwt() -> None:
    secret = "test-secret-key-min-32-characters-long"
    payload = decode_jwt_token("invalid.token.here", secret=secret, algorithm="HS256")
    assert payload is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/core/test_auth.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# backend/src/core/auth.py
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()


def verify_api_key(raw_key: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw_key.encode(), hashed.encode())


def create_jwt_token(
    device_ids: list[UUID],
    secret: str,
    algorithm: str = "HS256",
    expiry_hours: int = 24,
) -> str:
    payload = {
        "device_ids": [str(d) for d in device_ids],
        "exp": datetime.now(UTC) + timedelta(hours=expiry_hours),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_jwt_token(
    token: str,
    secret: str,
    algorithm: str = "HS256",
) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        logger.warning("Invalid JWT token")
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/core/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/auth.py backend/tests/core/test_auth.py
git commit -m "feat(core): add authentication module

API key hashing (bcrypt) and JWT token create/decode for
device-scoped bearer tokens."
```

---

### Task 11: Docker Compose & Environment

**Files:**
- Create: `deploy/docker/docker-compose.yml`
- Create: `deploy/docker/Dockerfile`
- Create: `deploy/docker/.env.example`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
# deploy/docker/docker-compose.yml
services:
  backend:
    build:
      context: ../../
      dockerfile: deploy/docker/Dockerfile
    ports:
      - "${OC_PORT:-8000}:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: opencadence
      POSTGRES_USER: opencadence
      POSTGRES_PASSWORD: opencadence
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/home/postgres/pgdata/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U opencadence"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
# deploy/docker/Dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml .
COPY backend/src/ src/
COPY backend/alembic.ini .
COPY backend/migrations/ migrations/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 3: Create .env.example**

```bash
# deploy/docker/.env.example

# Database
OC_DATABASE_URL=postgresql+asyncpg://opencadence:opencadence@db:5432/opencadence

# Redis
OC_REDIS_URL=redis://redis:6379/0

# Authentication - CHANGE THIS
OC_JWT_SECRET=change-me-to-a-random-string-at-least-32-chars

# Server
OC_HOST=0.0.0.0
OC_PORT=8000
OC_LOG_LEVEL=INFO

# Data retention
OC_RAW_RETENTION_DAYS=90

# Rate limiting
OC_API_RATE_LIMIT=100

# Event bus
OC_EVENT_BUS_QUEUE_DEPTH=10000
```

- [ ] **Step 4: Commit**

```bash
git add deploy/
git commit -m "feat: add Docker Compose setup with TimescaleDB and Redis

Three-service stack: backend, TimescaleDB, Redis. Includes
Dockerfile, env example, and health checks."
```

---

## Chunk 3: Ingestion, Processing & Storage Services

### Task 12: Ingestion Module

**Files:**
- Create: `backend/src/ingestion/__init__.py`
- Create: `backend/src/ingestion/router.py`
- Create: `backend/src/ingestion/service.py`
- Create: `backend/tests/ingestion/__init__.py`
- Create: `backend/tests/ingestion/test_service.py`
- Create: `backend/tests/ingestion/test_router.py`

- [ ] **Step 1: Write the failing service test**

```python
# backend/tests/ingestion/test_service.py
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
from src.ingestion.service import IngestionService, ValidationError


@pytest.fixture
def registry(tmp_path: Path) -> MetricRegistry:
    metric_file = tmp_path / "heart_rate.yaml"
    metric_file.write_text("""
name: heart_rate
label: Heart Rate
unit: bpm
valid_range:
  min: 20
  max: 300
aggregation: mean
processors: []
fhir:
  code: "8867-4"
  system: "http://loinc.org"
  display: "Heart rate"
""")
    return MetricRegistry.from_directory(tmp_path)


@pytest.fixture
def service(registry: MetricRegistry) -> IngestionService:
    return IngestionService(registry=registry)


def test_validate_valid_payload(service: IngestionService) -> None:
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=datetime.now(UTC),
                source="test",
            )
        ],
    )
    errors = service.validate(payload)
    assert errors == []


def test_validate_unknown_metric(service: IngestionService) -> None:
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="unknown_metric",
                value=42.0,
                unit="units",
                timestamp=datetime.now(UTC),
                source="test",
            )
        ],
    )
    errors = service.validate(payload)
    assert len(errors) == 1
    assert "unknown_metric" in errors[0]


def test_validate_future_timestamp(service: IngestionService) -> None:
    future = datetime.now(UTC) + timedelta(hours=1)
    payload = IngestPayload(
        device_id=uuid4(),
        batch=[
            Sample(
                metric="heart_rate",
                value=72.0,
                unit="bpm",
                timestamp=future,
                source="test",
            )
        ],
    )
    errors = service.validate(payload)
    assert len(errors) == 1
    assert "future" in errors[0].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/ingestion/test_service.py -v`
Expected: FAIL

- [ ] **Step 3: Write service implementation**

```python
# backend/src/ingestion/service.py
from datetime import UTC, datetime, timedelta

from src.core.models import IngestPayload
from src.core.registry import MetricRegistry


class ValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class IngestionService:
    """Validates and normalizes incoming health data."""

    # Allow timestamps up to 5 minutes in the future (clock skew)
    MAX_FUTURE_OFFSET = timedelta(minutes=5)

    def __init__(self, registry: MetricRegistry) -> None:
        self._registry = registry

    def validate(self, payload: IngestPayload) -> list[str]:
        errors: list[str] = []
        now = datetime.now(UTC)

        for i, sample in enumerate(payload.batch):
            metric_def = self._registry.get(sample.metric)
            if metric_def is None:
                errors.append(
                    f"Sample {i}: unknown metric '{sample.metric}'"
                )
                continue

            if sample.timestamp > now + self.MAX_FUTURE_OFFSET:
                errors.append(
                    f"Sample {i}: future timestamp {sample.timestamp.isoformat()}"
                )

        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/ingestion/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing router test**

```python
# backend/tests/ingestion/test_router.py
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.core.config import Settings
from src.core.events import InProcessEventBus
from src.core.registry import MetricRegistry
from src.ingestion.router import create_ingest_router
from src.ingestion.service import IngestionService


@pytest.fixture
def registry(tmp_path: Path) -> MetricRegistry:
    metric_file = tmp_path / "heart_rate.yaml"
    metric_file.write_text("""
name: heart_rate
label: Heart Rate
unit: bpm
valid_range:
  min: 20
  max: 300
aggregation: mean
processors: []
fhir:
  code: "8867-4"
  system: "http://loinc.org"
  display: "Heart rate"
""")
    return MetricRegistry.from_directory(tmp_path)


@pytest.fixture
def client(registry: MetricRegistry) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    bus = InProcessEventBus(max_queue_depth=100)
    service = IngestionService(registry=registry)
    app.include_router(create_ingest_router(service=service, event_bus=bus))
    return TestClient(app)


def test_ingest_valid_payload(client: TestClient) -> None:
    device_id = str(uuid4())
    response = client.post(
        "/api/v1/ingest",
        json={
            "device_id": device_id,
            "batch": [
                {
                    "metric": "heart_rate",
                    "value": 72.0,
                    "unit": "bpm",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "source": "test",
                }
            ],
        },
    )
    assert response.status_code == 202
    assert response.json()["accepted"] == 1


def test_ingest_unknown_metric(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ingest",
        json={
            "device_id": str(uuid4()),
            "batch": [
                {
                    "metric": "unknown",
                    "value": 42.0,
                    "unit": "x",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "source": "test",
                }
            ],
        },
    )
    assert response.status_code == 422
    assert "errors" in response.json()
```

- [ ] **Step 6: Write router implementation**

```python
# backend/src/ingestion/router.py
import logging
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.events import EventBus, Event
from src.core.models import IngestPayload
from src.ingestion.service import IngestionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataReceived(Event):
    """Emitted when validated data is ready for processing."""
    payload: IngestPayload


class IngestResponse(BaseModel):
    accepted: int


def create_ingest_router(service: IngestionService, event_bus: EventBus) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["ingestion"])

    @router.post("/ingest", response_model=IngestResponse, status_code=202)
    async def ingest(payload: IngestPayload) -> IngestResponse:
        errors = service.validate(payload)
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

        published = await event_bus.publish(DataReceived(payload=payload))
        if not published:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        logger.info(
            "Accepted %d samples from device %s",
            len(payload.batch),
            payload.device_id,
        )
        return IngestResponse(accepted=len(payload.batch))

    return router
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/ingestion/ -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/src/ingestion/ backend/tests/ingestion/
git commit -m "feat(ingestion): add ingestion module with validation

IngestionService validates metrics against registry and rejects
future timestamps. Router accepts batches and publishes
DataReceived events to the event bus."
```

---

### Task 13: Processing Module

**Files:**
- Create: `backend/src/processing/__init__.py`
- Create: `backend/src/processing/base.py`
- Create: `backend/src/processing/validators.py`
- Create: `backend/src/processing/service.py`
- Create: `backend/tests/processing/__init__.py`
- Create: `backend/tests/processing/test_validators.py`
- Create: `backend/tests/processing/test_service.py`

- [ ] **Step 1: Write the failing validator test**

```python
# backend/tests/processing/test_validators.py
from datetime import UTC, datetime
from uuid import uuid4

from src.core.models import Sample
from src.core.registry import MetricDefinition, ValidRange, FhirMapping
from src.processing.base import ProcessingContext, AnomalyFlag
from src.processing.validators import RangeValidator


def _make_metric() -> MetricDefinition:
    return MetricDefinition(
        name="heart_rate",
        label="Heart Rate",
        unit="bpm",
        valid_range=ValidRange(min=20, max=300),
        aggregation="mean",
        processors=["validators.RangeValidator"],
        fhir=FhirMapping(code="8867-4", system="http://loinc.org", display="Heart rate"),
    )


def test_range_validator_passes_valid() -> None:
    validator = RangeValidator()
    sample = Sample(
        metric="heart_rate", value=72.0, unit="bpm",
        timestamp=datetime.now(UTC), source="test",
    )
    ctx = ProcessingContext(
        device_id=uuid4(), metric_def=_make_metric(), anomalies=[]
    )
    result = validator.process(sample, ctx)
    assert result == sample
    assert len(ctx.anomalies) == 0


def test_range_validator_flags_out_of_range() -> None:
    validator = RangeValidator()
    sample = Sample(
        metric="heart_rate", value=350.0, unit="bpm",
        timestamp=datetime.now(UTC), source="test",
    )
    ctx = ProcessingContext(
        device_id=uuid4(), metric_def=_make_metric(), anomalies=[]
    )
    result = validator.process(sample, ctx)
    assert result == sample  # sample passes through, but anomaly is flagged
    assert len(ctx.anomalies) == 1
    assert ctx.anomalies[0].reason == "out_of_range"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/processing/test_validators.py -v`
Expected: FAIL

- [ ] **Step 3: Write base processor and validator**

```python
# backend/src/processing/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from src.core.models import Sample
from src.core.registry import MetricDefinition


@dataclass
class AnomalyFlag:
    reason: str
    severity: str
    context: dict


@dataclass
class ProcessingContext:
    device_id: UUID
    metric_def: MetricDefinition
    anomalies: list[AnomalyFlag] = field(default_factory=list)


class BaseProcessor(ABC):
    @abstractmethod
    def process(self, sample: Sample, ctx: ProcessingContext) -> Sample:
        """Process a sample and return it (possibly modified).
        May add anomaly flags to ctx.anomalies."""
        ...
```

```python
# backend/src/processing/validators.py
from src.core.models import Sample
from src.processing.base import AnomalyFlag, BaseProcessor, ProcessingContext


class RangeValidator(BaseProcessor):
    """Flags samples outside the metric's valid range."""

    def process(self, sample: Sample, ctx: ProcessingContext) -> Sample:
        if not ctx.metric_def.is_in_range(sample.value):
            ctx.anomalies.append(
                AnomalyFlag(
                    reason="out_of_range",
                    severity="warning",
                    context={
                        "value": sample.value,
                        "min": ctx.metric_def.valid_range.min,
                        "max": ctx.metric_def.valid_range.max,
                    },
                )
            )
        return sample
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/processing/test_validators.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing service test**

```python
# backend/tests/processing/test_service.py
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
from src.processing.service import ProcessingService


@pytest.fixture
def registry(tmp_path: Path) -> MetricRegistry:
    metric_file = tmp_path / "heart_rate.yaml"
    metric_file.write_text("""
name: heart_rate
label: Heart Rate
unit: bpm
valid_range:
  min: 20
  max: 300
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "8867-4"
  system: "http://loinc.org"
  display: "Heart rate"
""")
    return MetricRegistry.from_directory(tmp_path)


@pytest.fixture
def service(registry: MetricRegistry) -> ProcessingService:
    return ProcessingService(registry=registry)


def test_process_valid_samples(service: ProcessingService) -> None:
    device_id = uuid4()
    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate", value=72.0, unit="bpm",
                timestamp=datetime.now(UTC), source="test",
            ),
        ],
    )
    result = service.process(device_id, payload.batch)
    assert len(result.processed_samples) == 1
    assert len(result.anomalies) == 0


def test_process_flags_anomalies(service: ProcessingService) -> None:
    device_id = uuid4()
    payload = IngestPayload(
        device_id=device_id,
        batch=[
            Sample(
                metric="heart_rate", value=350.0, unit="bpm",
                timestamp=datetime.now(UTC), source="test",
            ),
        ],
    )
    result = service.process(device_id, payload.batch)
    assert len(result.processed_samples) == 1
    assert len(result.anomalies) == 1
```

- [ ] **Step 6: Write processing service**

```python
# backend/src/processing/service.py
import logging
from dataclasses import dataclass
from uuid import UUID

from src.core.models import Sample
from src.core.registry import MetricRegistry
from src.processing.base import AnomalyFlag, BaseProcessor, ProcessingContext
from src.processing.validators import RangeValidator

logger = logging.getLogger(__name__)

# Processor class lookup
PROCESSOR_MAP: dict[str, type[BaseProcessor]] = {
    "validators.RangeValidator": RangeValidator,
}


@dataclass
class ProcessingResult:
    processed_samples: list[Sample]
    anomalies: list[tuple[Sample, AnomalyFlag]]


class ProcessingService:
    """Runs processor chains on incoming samples."""

    def __init__(self, registry: MetricRegistry) -> None:
        self._registry = registry

    def _get_processors(self, processor_names: list[str]) -> list[BaseProcessor]:
        processors: list[BaseProcessor] = []
        for name in processor_names:
            cls = PROCESSOR_MAP.get(name)
            if cls:
                processors.append(cls())
            else:
                logger.warning("Unknown processor: %s", name)
        return processors

    def process(
        self, device_id: UUID, samples: list[Sample]
    ) -> ProcessingResult:
        processed: list[Sample] = []
        all_anomalies: list[tuple[Sample, AnomalyFlag]] = []

        for sample in samples:
            metric_def = self._registry.get(sample.metric)
            if metric_def is None:
                logger.warning("Skipping unknown metric: %s", sample.metric)
                continue

            ctx = ProcessingContext(
                device_id=device_id, metric_def=metric_def
            )
            processors = self._get_processors(metric_def.processors)

            current = sample
            for proc in processors:
                current = proc.process(current, ctx)

            processed.append(current)
            for anomaly in ctx.anomalies:
                all_anomalies.append((sample, anomaly))

        return ProcessingResult(
            processed_samples=processed, anomalies=all_anomalies
        )
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/processing/ -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/src/processing/ backend/tests/processing/
git commit -m "feat(processing): add processing module with pluggable chain

BaseProcessor ABC, RangeValidator, and ProcessingService that
runs processor chains per metric definition. Flags anomalies
without dropping samples."
```

---

### Task 14: Storage Service (Event Subscriber)

**Files:**
- Create: `backend/src/storage/service.py`
- Create: `backend/tests/storage/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/storage/test_service.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.events import InProcessEventBus
from src.core.models import IngestPayload, Sample
from src.core.registry import MetricRegistry
from src.ingestion.router import DataReceived
from src.processing.base import AnomalyFlag
from src.storage.service import StorageService


@pytest.fixture
def mock_session_factory() -> AsyncMock:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=session)
    return factory


def test_storage_service_creates_without_error(mock_session_factory: AsyncMock) -> None:
    """Basic construction test - integration tests cover actual DB writes."""
    registry_mock = MagicMock(spec=MetricRegistry)
    service = StorageService(
        session_factory=mock_session_factory,
        registry=registry_mock,
    )
    assert service is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/storage/test_service.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# backend/src/storage/service.py
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.models import IngestPayload
from src.core.registry import MetricRegistry
from src.processing.base import AnomalyFlag
from src.processing.service import ProcessingResult, ProcessingService
from src.storage.repository import SampleRepository

logger = logging.getLogger(__name__)


class StorageService:
    """Subscribes to events and persists data to TimescaleDB."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: MetricRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._repo = SampleRepository()
        self._processing = ProcessingService(registry=registry)

    async def handle_data_received(self, payload: IngestPayload) -> None:
        """Process and store incoming data."""
        try:
            result = self._processing.process(payload.device_id, payload.batch)

            async with self._session_factory() as session:
                # Store raw samples
                if result.processed_samples:
                    insert_payload = IngestPayload(
                        device_id=payload.device_id,
                        batch=result.processed_samples,
                    )
                    count = await self._repo.insert_samples(session, insert_payload)
                    logger.info("Stored %d samples for device %s", count, payload.device_id)

                # Store anomalies
                for sample, anomaly in result.anomalies:
                    await session.execute(
                        text("""
                            INSERT INTO anomalies (time, device_id, metric, value, reason, severity, context)
                            VALUES (:time, :device_id, :metric, :value, :reason, :severity, :context::jsonb)
                        """),
                        {
                            "time": sample.timestamp,
                            "device_id": payload.device_id,
                            "metric": sample.metric,
                            "value": sample.value,
                            "reason": anomaly.reason,
                            "severity": anomaly.severity,
                            "context": json.dumps(anomaly.context),
                        },
                    )
                if result.anomalies:
                    await session.commit()
                    logger.info(
                        "Flagged %d anomalies for device %s",
                        len(result.anomalies),
                        payload.device_id,
                    )
        except Exception:
            logger.exception("Failed to process data for device %s", payload.device_id)
            # Dead letter handling would go here in production
            raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/storage/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/storage/service.py backend/tests/storage/test_service.py
git commit -m "feat(storage): add storage service event handler

Processes incoming data through the processing pipeline and
persists raw samples and anomalies to TimescaleDB."
```

---

## Chunk 4: API, FHIR, CLI & App Entrypoint

### Task 15: API Query Endpoints

**Files:**
- Create: `backend/src/api/__init__.py`
- Create: `backend/src/api/router.py`
- Create: `backend/src/api/schemas.py`
- Create: `backend/tests/api/__init__.py`
- Create: `backend/tests/api/test_router.py`

- [ ] **Step 1: Write API schemas**

```python
# backend/src/api/schemas.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AggregatedSample(BaseModel):
    time: datetime
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    stddev: float | None = None
    count: int | None = None


class RawSample(BaseModel):
    time: datetime
    value: float
    unit: str
    source: str


class DataQueryResponse(BaseModel):
    device_id: UUID
    metric: str
    resolution: str
    samples: list[AggregatedSample] | list[RawSample]


class DeviceResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    created_at: datetime
    active: bool


class AnomalyResponse(BaseModel):
    time: datetime
    device_id: UUID
    metric: str
    value: float
    reason: str
    severity: str
    context: dict | None = None
```

- [ ] **Step 2: Write the failing router test**

```python
# backend/tests/api/test_router.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.router import create_api_router
from src.storage.repository import SampleRepository


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock(spec=SampleRepository)
    repo.query_raw.return_value = [
        {"time": datetime(2026, 3, 11, 10, 0, tzinfo=UTC), "value": 72.0, "unit": "bpm", "source": "test"}
    ]
    repo.query_aggregates.return_value = [
        {
            "time": datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
            "min_value": 60.0, "max_value": 85.0,
            "mean_value": 72.0, "stddev_value": 5.0, "sample_count": 12,
        }
    ]
    return repo


@pytest.fixture
def client(mock_repo: AsyncMock) -> TestClient:
    app = FastAPI()
    mock_session_factory = AsyncMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = session
    app.include_router(
        create_api_router(session_factory=mock_session_factory, repo=mock_repo)
    )
    return TestClient(app)


def test_query_raw_data(client: TestClient, mock_repo: AsyncMock) -> None:
    device_id = str(uuid4())
    response = client.get(
        f"/api/v1/data?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=raw"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "heart_rate"
    assert data["resolution"] == "raw"
    assert len(data["samples"]) == 1


def test_query_aggregate_data(client: TestClient, mock_repo: AsyncMock) -> None:
    device_id = str(uuid4())
    response = client.get(
        f"/api/v1/data?device_id={device_id}&metric=heart_rate"
        f"&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=1min"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resolution"] == "1min"
```

- [ ] **Step 3: Write router implementation**

```python
# backend/src/api/router.py
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.schemas import (
    AggregatedSample,
    AnomalyResponse,
    DataQueryResponse,
    RawSample,
)
from src.storage.repository import SampleRepository


def create_api_router(
    session_factory: async_sessionmaker[AsyncSession],
    repo: SampleRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["query"])

    @router.get("/data", response_model=DataQueryResponse)
    async def query_data(
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        resolution: str = Query(default="raw", pattern="^(raw|1min|1hr)$"),
    ) -> DataQueryResponse:
        async with session_factory() as session:
            if resolution == "raw":
                rows = await repo.query_raw(session, device_id, metric, start, end)
                samples = [
                    RawSample(
                        time=r["time"], value=r["value"],
                        unit=r["unit"], source=r["source"],
                    )
                    for r in rows
                ]
            else:
                rows = await repo.query_aggregates(
                    session, device_id, metric, start, end, resolution
                )
                samples = [
                    AggregatedSample(
                        time=r["time"],
                        min=r["min_value"],
                        max=r["max_value"],
                        mean=r["mean_value"],
                        stddev=r["stddev_value"],
                        count=r["sample_count"],
                    )
                    for r in rows
                ]

        return DataQueryResponse(
            device_id=device_id,
            metric=metric,
            resolution=resolution,
            samples=samples,
        )

    return router
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/api/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/ backend/tests/api/
git commit -m "feat(api): add query endpoints for data and aggregates

GET /api/v1/data with device_id, metric, time range, and
resolution (raw, 1min, 1hr) parameters."
```

---

### Task 16: FHIR Export Module

**Files:**
- Create: `backend/src/fhir/__init__.py`
- Create: `backend/src/fhir/mapper.py`
- Create: `backend/src/fhir/router.py`
- Create: `backend/tests/fhir/__init__.py`
- Create: `backend/tests/fhir/test_mapper.py`

- [ ] **Step 1: Write the failing mapper test**

```python
# backend/tests/fhir/test_mapper.py
from datetime import UTC, datetime
from uuid import uuid4

from src.core.registry import FhirMapping, MetricDefinition, ValidRange
from src.fhir.mapper import to_fhir_observation


def test_map_to_fhir_observation() -> None:
    device_id = uuid4()
    metric_def = MetricDefinition(
        name="heart_rate",
        label="Heart Rate",
        unit="bpm",
        valid_range=ValidRange(min=20, max=300),
        aggregation="mean",
        processors=[],
        fhir=FhirMapping(
            code="8867-4",
            system="http://loinc.org",
            display="Heart rate",
        ),
    )

    obs = to_fhir_observation(
        device_id=device_id,
        metric_def=metric_def,
        value=72.0,
        unit="bpm",
        timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
    )

    assert obs["resourceType"] == "Observation"
    assert obs["status"] == "final"
    assert obs["code"]["coding"][0]["code"] == "8867-4"
    assert obs["valueQuantity"]["value"] == 72.0
    assert obs["valueQuantity"]["unit"] == "bpm"
    assert obs["device"]["reference"] == f"Device/{device_id}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/fhir/test_mapper.py -v`
Expected: FAIL

- [ ] **Step 3: Write mapper**

```python
# backend/src/fhir/mapper.py
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.registry import MetricDefinition


def to_fhir_observation(
    device_id: UUID,
    metric_def: MetricDefinition,
    value: float,
    unit: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Map a raw sample to a FHIR R4 Observation resource."""
    return {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": metric_def.fhir.system,
                    "code": metric_def.fhir.code,
                    "display": metric_def.fhir.display,
                }
            ],
            "text": metric_def.label,
        },
        "device": {"reference": f"Device/{device_id}"},
        "effectiveDateTime": timestamp.isoformat(),
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/fhir/test_mapper.py -v`
Expected: PASS

- [ ] **Step 5: Write FHIR router**

```python
# backend/src/fhir/router.py
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.registry import MetricRegistry
from src.fhir.mapper import to_fhir_observation
from src.storage.repository import SampleRepository


def create_fhir_router(
    session_factory: async_sessionmaker[AsyncSession],
    repo: SampleRepository,
    registry: MetricRegistry,
) -> APIRouter:
    router = APIRouter(prefix="/fhir", tags=["fhir"])

    @router.get("/Observation")
    async def get_observations(
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        _count: int = Query(default=100, alias="_count", le=1000),
    ) -> dict[str, Any]:
        metric_def = registry.get(metric)
        if metric_def is None:
            return {"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []}

        async with session_factory() as session:
            rows = await repo.query_raw(
                session, device_id, metric, start, end, limit=_count
            )

        entries = [
            {
                "resource": to_fhir_observation(
                    device_id=device_id,
                    metric_def=metric_def,
                    value=row["value"],
                    unit=row["unit"],
                    timestamp=row["time"],
                ),
            }
            for row in rows
        ]

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(entries),
            "entry": entries,
        }

    return router
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/fhir/ backend/tests/fhir/
git commit -m "feat(fhir): add FHIR R4 Observation export

Maps internal samples to FHIR R4 Observation resources.
GET /fhir/Observation returns a FHIR Bundle."
```

---

### Task 17: FastAPI Application Entrypoint

**Files:**
- Create: `backend/src/main.py`

- [ ] **Step 1: Write the app factory**

```python
# backend/src/main.py
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI

from src.core.config import Settings
from src.core.events import InProcessEventBus
from src.core.logging import setup_logging
from src.core.registry import MetricRegistry
from src.ingestion.router import DataReceived, create_ingest_router
from src.ingestion.service import IngestionService
from src.api.router import create_api_router
from src.fhir.router import create_fhir_router
from src.storage.database import create_session_factory
from src.storage.repository import SampleRepository
from src.storage.service import StorageService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    setup_logging(level=settings.log_level)

    # Core components
    metrics_path = Path(__file__).parent / "core" / "metrics"
    registry = MetricRegistry.from_directory(metrics_path)
    event_bus = InProcessEventBus(max_queue_depth=settings.event_bus_queue_depth)

    # Database
    session_factory = create_session_factory(settings)
    repo = SampleRepository()

    # Services
    ingestion_service = IngestionService(registry=registry)
    storage_service = StorageService(
        session_factory=session_factory, registry=registry
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Wire event handlers
        async def on_data_received(event: DataReceived) -> None:
            await storage_service.handle_data_received(event.payload)

        event_bus.subscribe(DataReceived, on_data_received)
        await event_bus.start()
        logger.info("OpenCadence started with %d metrics", len(registry.list_metrics()))
        yield
        await event_bus.stop()
        logger.info("OpenCadence stopped")

    app = FastAPI(
        title="OpenCadence",
        description="Self-hostable health data pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Mount routers
    app.include_router(create_ingest_router(service=ingestion_service, event_bus=event_bus))
    app.include_router(create_api_router(session_factory=session_factory, repo=repo))
    app.include_router(create_fhir_router(session_factory=session_factory, repo=repo, registry=registry))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def get_app() -> FastAPI:
    """Module-level app instance for uvicorn. Only called at server startup."""
    return create_app()


app = get_app()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/main.py
git commit -m "feat: add FastAPI application entrypoint

App factory wiring all modules: ingestion, processing, storage,
API queries, FHIR export. Lifespan manages event bus lifecycle."
```

---

### Task 18: Seed Data Script

**Files:**
- Create: `backend/src/seed.py`

- [ ] **Step 1: Write seed script**

```python
# backend/src/seed.py
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/seed.py
git commit -m "feat: add demo seed data script

Generates 24h of simulated heart rate data with circadian
rhythm pattern for API exploration."
```

---

### Task 19: CI/CD Workflows

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: cd backend && pip install -e ".[dev]"
      - name: Ruff check
        run: cd backend && ruff check src tests
      - name: Ruff format check
        run: cd backend && ruff format --check src tests
      - name: Mypy
        run: cd backend && mypy src

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg16
        env:
          POSTGRES_DB: opencadence_test
          POSTGRES_USER: opencadence
          POSTGRES_PASSWORD: opencadence
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U opencadence"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: cd backend && pip install -e ".[dev]"
      - name: Run tests
        env:
          OC_DATABASE_URL: postgresql+asyncpg://opencadence:opencadence@localhost:5432/opencadence_test
          OC_REDIS_URL: redis://localhost:6379/0
          OC_JWT_SECRET: ci-test-secret-key-at-least-32-chars
        run: cd backend && pytest -v --cov=src --cov-report=term-missing
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI workflow

Lint (ruff + mypy) and test jobs with TimescaleDB and Redis
service containers."
```

---

### Task 20: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# OpenCadence

Self-hostable health data pipeline for wearable devices.

Collect vitals from your Apple Watch, Pixel Watch, or any wearable — own your data, query it via API, export it as FHIR R4.

## Architecture

```mermaid
graph LR
    subgraph Mobile
        iOS[iOS App<br/>HealthKit]
        Android[Android App<br/>Health Connect]
    end

    subgraph Backend
        Ingest[Ingestion] --> Bus[Event Bus]
        Bus --> Process[Processing]
        Process --> Store[Storage]
        Store --> DB[(TimescaleDB)]
        API[Query API] --> DB
        FHIR[FHIR Export] --> DB
    end

    iOS -->|POST /api/v1/ingest| Ingest
    Android -->|POST /api/v1/ingest| Ingest
```

## Quick Start

```bash
git clone https://github.com/your-org/opencadence.git
cd opencadence
cp deploy/docker/.env.example deploy/docker/.env
# Edit .env to set OC_JWT_SECRET
docker compose -f deploy/docker/docker-compose.yml up -d
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Seed Demo Data

```bash
make seed
```

## API Overview

### Ingest Data

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "your-device-uuid",
    "batch": [{
      "metric": "heart_rate",
      "value": 72.0,
      "unit": "bpm",
      "timestamp": "2026-03-11T10:30:00Z",
      "source": "apple_watch_series_9"
    }]
  }'
```

### Query Data

```bash
# Raw samples
curl "http://localhost:8000/api/v1/data?device_id=UUID&metric=heart_rate&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=raw"

# 1-minute aggregates
curl "http://localhost:8000/api/v1/data?device_id=UUID&metric=heart_rate&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z&resolution=1min"
```

### FHIR Export

```bash
curl "http://localhost:8000/fhir/Observation?device_id=UUID&metric=heart_rate&start=2026-03-11T00:00:00Z&end=2026-03-12T00:00:00Z"
```

## Supported Metrics

| Metric | Unit | LOINC Code |
|--------|------|------------|
| Heart Rate | bpm | 8867-4 |
| HRV | ms | 80404-7 |
| SpO2 | % | 2708-6 |
| Respiratory Rate | breaths/min | 9279-1 |
| Skin Temperature | C | 39106-0 |

## Adding a New Metric

Create a YAML file in `backend/src/core/metrics/`:

```yaml
name: my_metric
label: My Metric
unit: units
valid_range:
  min: 0
  max: 100
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "12345-6"
  system: "http://loinc.org"
  display: "My Metric"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Development

```bash
make install    # Install dependencies
make dev        # Start dev server with hot reload
make test       # Run unit tests
make lint       # Run linter and type checker
```

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with architecture diagram and quick start

Mermaid architecture diagram, Docker quick start, API examples,
supported metrics table, and development guide."
```

---

### Task 21: ADR Documents

**Files:**
- Create: `docs/architecture/adr-001-modular-monolith.md`
- Create: `docs/architecture/adr-002-timescaledb.md`
- Create: `docs/architecture/adr-003-fhir-compatibility.md`

- [ ] **Step 1: Write ADR-001**

```markdown
# ADR-001: Modular Monolith Architecture

## Status
Accepted

## Context
OpenCadence needs an architecture that is simple to self-host (single `docker compose up`) while maintaining clean module boundaries for independent evolution and testability.

## Decision
Single deployable FastAPI application with five internal modules (ingestion, processing, storage, API, FHIR) communicating through an in-process async event bus. Each module has a clear interface and could be extracted into a separate service if needed.

## Consequences
- Simple deployment and operation
- Low latency (in-process communication)
- Contributors work in a single codebase
- Requires discipline to maintain module boundaries
- Cannot independently scale modules (acceptable for the target use case)
```

- [ ] **Step 2: Write ADR-002**

```markdown
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
```

- [ ] **Step 3: Write ADR-003**

```markdown
# ADR-003: FHIR R4 Compatibility Layer

## Status
Accepted

## Context
Healthcare interoperability standards (HL7 FHIR) enable data exchange with clinical systems. However, FHIR's data model is optimized for clinical workflows, not time-series storage and querying.

## Decision
Keep the internal data model optimized for time-series operations. Provide a read-only FHIR R4 export layer that maps internal samples to FHIR Observation resources on-the-fly. No FHIR write path.

## Alternatives Considered
- **FHIR-native storage**: Store all data as FHIR resources. High interoperability but poor query performance for time-series use cases and unnecessary complexity for self-hosters.
- **No FHIR support**: Simpler, but closes the door to clinical system integration.

## Consequences
- Internal queries remain fast (native time-series model)
- FHIR export available for systems that need it
- Mapping maintained per metric type in YAML registry
- No SMART on FHIR scopes for MVP (standard JWT auth)
```

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/
git commit -m "docs: add Architecture Decision Records

ADR-001 (modular monolith), ADR-002 (TimescaleDB),
ADR-003 (FHIR compatibility layer)."
```

---

## Follow-up Tasks (Not in This Plan)

The following spec requirements are deferred to subsequent plans to keep this plan focused on a working, testable core:

1. **Authentication middleware** - Wire API key auth on `/api/v1/ingest`, JWT auth on query/FHIR endpoints as FastAPI dependencies
2. **Rate limiting** - Redis-based rate limiter middleware per device key (HTTP 429)
3. **WebSocket streaming** - `/api/v1/stream` with subscription filters and JWT auth
4. **Prometheus `/metrics` endpoint** - Wire `prometheus_client` into FastAPI
5. **Dead letter queue writes** - Catch processing failures and insert into `dead_letter` table
6. **CLI tools** - `opencadence device register` and `opencadence replay-dlq` (Typer)
7. **`GET /api/v1/devices`** and **`GET /api/v1/anomalies`** endpoints
8. **FHIR router tests** - Endpoint-level tests for `GET /fhir/Observation`
9. **K8s readiness/liveness probes** - `/ready` (checks DB) and `/live` (always 200)
10. **`release.yml`** and **`security.yml`** GitHub Actions workflows
11. **Seed data for all 5 metrics** - Expand seed script beyond heart rate
12. **iOS companion app** (separate plan)
13. **Android companion app** (separate plan)
