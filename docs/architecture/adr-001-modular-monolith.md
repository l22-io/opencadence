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
