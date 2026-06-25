# Contributing to Knowledge Mapper

Thank you for your interest in contributing to the Knowledge Mapper! This guide covers setting up a development environment, running tests, building distributions, and code style.

## Development Environment

**Requirements:**

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (for integration tests)

**Setup:**

```bash
# Clone the repository
git clone https://github.com/TNO/knowledge-mapper.git
cd knowledge-mapper

# Install all dependencies (including dev)
uv sync
```

## Running Tests

### Unit Tests

Unit tests use `TestClient`, an in-memory fake Smart Connector. No external services needed.

```bash
uv run pytest
```

### Integration Tests

Integration tests require a live Knowledge Engine runtime. Use the Docker Compose file in `examples/`:

```bash
# Start the Knowledge Engine
docker compose -f examples/compose.yaml up -d

# Run tests
uv run pytest

# Stop the Knowledge Engine
docker compose -f examples/compose.yaml down
```

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting, configured in `pyproject.toml`.

```bash
# Check for lint errors
uv run ruff check .

# Auto-fix lint errors
uv run ruff check . --fix

# Format code
uv run ruff format .
```

Key style settings:

- Line length: 88 characters
- Target Python version: 3.13
- Enabled rule sets: pycodestyle (E), Pyflakes (F), pyupgrade (UP), flake8-bugbear (B), flake8-simplify (SIM), isort (I)

## Building a Distribution

The project uses `setuptools` as its build backend, configured in `pyproject.toml`.

```bash
# Build source and wheel distributions
uv build
```

The built distributions will be in the `dist/` directory.

## Publishing a Release

Releases are published to PyPI. Make sure the version number in `src/knowledge_mapper/__init__.py` and `pyproject.toml` are updated before publishing.

```bash
# Build the distribution
uv build

# Publish to PyPI (requires credentials)
uv publish
```

## Project Structure

- `src/knowledge_mapper/` — main package source
- `tests/` — unit and integration tests
- `examples/` — runnable examples demonstrating features
- `docs/` — documentation assets (architecture diagrams)
