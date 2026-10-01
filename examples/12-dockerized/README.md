# 12 — Dockerized knowledge base

Shows how to package a knowledge base (KB) application as a Docker image and run it
next to a Smart Connector (SC) and a Knowledge Directory (KD) using Docker Compose.
The KB logic is kept minimal; the focus is on the Docker workflow. You can apply this
pattern to any of the other examples.

## Files

| File | Purpose |
|------|---------|
| `app.py` | ANSWER KB that answers greeting requests. Started with `knowledge-mapper run app.py:kb`. |
| `asker.py` | One-shot ASK KB that queries `app.py` once to show the interaction works, then exits. |
| `pyproject.toml` / `uv.lock` | The app's dependencies (`knowledge-mapper` pinned to a release from PyPI). |
| `Dockerfile` | Multi-stage build: uv installs the locked dependencies into a venv; a slim runtime image runs the app as a non-root user. |
| `.dockerignore` | Keeps the build context limited to the files the image needs. |
| `compose.yaml` | Starts the KD, the SC, the answering KB and the asker. |

## Run it

From this folder:

```bash
docker compose up --build
```

After a few seconds, the asker logs the answers it received from the dockerized KB
and exits:

```text
asker-1      | ... [dockerized-asker] Received answer: {'greeting': '<http://example.org/knowledge-mapper/dockerized#hello>', 'text': '"Hello from a container!"'}
asker-1      | ... [dockerized-asker] Received answer: {'greeting': '<http://example.org/knowledge-mapper/dockerized#goedemorgen>', ...}
asker-1 exited with code 0
```

The answering KB keeps running. Press `Ctrl+C`, or run `docker compose down` to stop
everything. On `SIGTERM`, the `knowledge-mapper` CLI unregisters the KB from the SC
before it exits.

To run the asker again while the rest is up:

```bash
docker compose run --rm asker
```

## How it works

### Configuration through environment variables

The image contains no configuration. Both scripts build their KB with
`KnowledgeBase.from_settings(KnowledgeBaseSettings())`. That reads the KB identity and
the SC endpoint from environment variables, with `__` as the separator for nested
fields:

| Variable | Example |
|----------|---------|
| `KNOWLEDGE_BASE__ID` | `http://example.org/knowledge-mapper/dockerized#answer-kb` |
| `KNOWLEDGE_BASE__NAME` | `dockerized-answer-kb` |
| `KNOWLEDGE_BASE__DESCRIPTION` | `A dockerized KB that answers greeting requests.` |
| `KNOWLEDGE_ENGINE_ENDPOINT` | `http://smart-connector:8280/rest` |

This lets you deploy the same image to different environments. The knowledge
interactions themselves are defined in code.

### Networking

All services share the default compose network and reach each other by service
name:

- The KBs call the SC's REST API at `http://smart-connector:8280/rest`.
- The SC registers with the KD at `http://knowledge-directory:8282`. It announces
  `KE_RUNTIME_EXPOSED_URL` (`http://smart-connector:8081`) as the address where other
  SCs can reach it.

A KB only makes outgoing requests (it long-polls its SC for incoming requests), so the
KB containers expose no ports. The SC's REST API is not published to the host either.
Add `ports: ["8280:8280"]` to the `smart-connector` service if you want to reach it
from the host, for example to run the other examples against it.

### Startup order

`depends_on` only waits for a container to start, not for the SC to be ready. If the
SC is not up yet, `knowledge-mapper run` exits with an error, and
`restart: unless-stopped` starts the KB again until registration succeeds. The asker
retries in code instead, both for connecting and until the answering KB responds.

### Using a different `knowledge-mapper` version

The version is pinned in `pyproject.toml`. To change it, edit the dependency and run
`uv lock` in this folder, then rebuild with `docker compose up --build`.
