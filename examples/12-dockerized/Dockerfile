# syntax=docker/dockerfile:1.7
#
# Packages the example knowledge base app as a Docker image. Build context is
# this folder:
#
#   docker build -t km-dockerized-example .

# ---------- Builder: install dependencies into /opt/venv with uv

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

# Only the dependency manifests, so this layer stays cached until they change.
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- Runtime: slim Python image with the venv, the app and a non-root user

FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system app && useradd --system --gid app --home-dir /app --create-home app

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY app.py asker.py ./

USER app

# The KB is a client of its Smart Connector, so no port is exposed. Exec form
# keeps the CLI as PID 1, so it receives SIGTERM and unregisters cleanly.
CMD ["knowledge-mapper", "run", "app.py:kb"]
