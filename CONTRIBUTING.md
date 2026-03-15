# Contributing to OpenCadence

Thank you for your interest in contributing to OpenCadence! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Make

### Getting Started

```bash
git clone https://github.com/l22-io/opencadence.git
cd opencadence
make install      # Install dependencies
make test         # Run tests
make lint         # Run linters
```

## How to Contribute

### Reporting Issues

- Use the **Bug Report** template for bugs
- Use the **Feature Request** template for new ideas
- Use the **New Data Source** template to propose new metric types

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main` (`git checkout -b feature/your-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`make test`)
5. Ensure linting passes (`make lint`)
6. Commit with clear, descriptive messages
7. Open a Pull Request against `main`

### Branch Naming

- `feature/description` -- new functionality
- `fix/description` -- bug fixes
- `docs/description` -- documentation only

### Code Style

- We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Type hints are required for all public functions
- Run `make lint` before committing

### AI / LLM Tools

Contributors are welcome to use AI coding assistants. The `.gitignore` excludes config files for common tools (Copilot, Cursor, etc.) so they don't end up in the repo. Please review any generated code before submitting -- you're responsible for understanding and testing what you commit.

### Adding a New Metric Type

OpenCadence uses a YAML-based metric registry. To add a new metric:

1. Add the metric definition to `backend/src/core/metrics/definitions/`
2. Include: metric key, display name, unit, valid range, FHIR mapping
3. Add processors if the metric requires custom validation
4. Write tests covering the new metric's validation and processing
5. Update the metrics table in the README

### Testing

- Unit tests: `make test`
- Integration tests require Docker: `make test-integration`
- All PRs must include tests for new functionality
- Aim for meaningful test coverage, not just line coverage

## Pull Request Process

1. Fill out the PR template completely
2. Ensure CI passes
3. Request review from a maintainer
4. Address review feedback
5. PRs require at least one approval before merge

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
