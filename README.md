# Knowledge Mapper

The Knowledge Mapper is a Python SDK for connecting your applications to the [TNO Knowledge Engine (TKE)](https://docs.knowledge-engine.eu/) network. Define knowledge interactions with decorators, use typed binding models, and let the SDK handle registration, polling, and data exchange with the network.

The best way to learn to work with the Knowledge Mapper is to check out the [examples](/examples/). Users that are familiar with Python's [FastAPI](https://fastapi.tiangolo.com/) will recognize many concepts from that package.

## Quick Start

```bash
pip install knowledge_mapper
```

```python
import asyncio
from knowledge_mapper import KnowledgeBase

kb = KnowledgeBase(
    id="http://example.org/my-kb",
    name="my-kb",
    description="A simple example KB.",
    ke_url="http://localhost:8280/rest",
)

@kb.answer_ki(
    name="greeting",
    graph_pattern='?s <http://example.org/says> ?message .',
)
def handle(binding_set, info):
    return binding_set

async def main():
    await kb.connect()
    await kb.register()
    await kb.start_handling_loop()

asyncio.run(main())
```

## Installation

Install from PyPI:

```bash
pip install knowledge_mapper
```

For local development (from the repository root):

```bash
pip install -e .
```

## CLI

Installing the package also provides a `knowledge-mapper` command. Use `run` to start a `KnowledgeBase` defined in a Python file, replacing the `asyncio.run(...)` boilerplate:

```bash
knowledge-mapper run my_app.py:kb
```

Where `my_app.py` is the Python file and `kb` is the name of the `KnowledgeBase` variable. The command connects to the Knowledge Engine, registers the KB, runs the handling loop, and on `SIGINT` or `SIGTERM` unregisters and closes cleanly.

## Examples

The [`examples/`](./examples/) directory contains runnable examples covering all major features. Each example has inline comments explaining the code.

| Example | Description |
|---------|-------------|
| [01-basic.py](./examples/01-basic.py) | Minimal knowledge base with a simple ANSWER knowledge interaction |
| [02-binding_models.py](./examples/02-binding_models.py) | Pydantic-style binding models for type-safe bindings |
| [03-ask_interaction.py](./examples/03-ask_interaction.py) | Outgoing ASK knowledge interactions with typed binding models |
| [04-post_measurement.py](./examples/04-post_measurement.py) | POST interactions for pushing measurements or data to the network |
| [05-custom-settings/](./examples/05-custom-settings/) | Custom settings subclass with YAML configuration |
| [06-dependency_injection.py](./examples/06-dependency_injection.py) | Dependency injection for handlers (database connections, configs, etc.) |
| [07-testing/](./examples/07-testing/) | Writing tests with the in-memory `TestClient` |
| [08-async_handlers.py](./examples/08-async_handlers.py) | Async and sync REACT handlers side by side |
| [09-sparql-store/](./examples/09-sparql-store/) | Connecting a SPARQL store as a knowledge base |
| [10-cli.py](./examples/10-cli.py) | Start a KB via the `knowledge-mapper run` CLI |

See the [examples README](./examples/README.md) for prerequisites and setup instructions.

## API Reference

### `KnowledgeBase`

The main entry point. Create one, register knowledge interactions with decorators, then connect and start handling.

```python
from knowledge_mapper import KnowledgeBase

kb = KnowledgeBase(
    id="http://example.org/my-kb",
    name="my-kb",
    description="...",
    ke_url="http://localhost:8280/rest",
)
```

**Lifecycle:**

```python
await kb.connect()                # Verify the Smart Connector is reachable
await kb.register()               # Register KB and all KIs with the Smart Connector
await kb.start_handling_loop()    # Start concurrent long-polling for incoming requests
await kb.unregister()             # Unregister from the Smart Connector
await kb.close()                  # Close the HTTP client
```

**Registering Knowledge Interactions (decorators):**

```python
# ANSWER — respond to incoming queries
@kb.answer_ki(name="...", graph_pattern="...", prefixes={...})
def my_handler(binding_set, info):
    return binding_set

# REACT — handle incoming POST data
@kb.react_ki(name="...", argument_graph_pattern="...", result_graph_pattern="...", prefixes={...})
def my_react_handler(binding_set, info):
    return result_binding_set
```

**Registering Knowledge Interactions (non-decorator):**

```python
# ASK — query the network (no handler needed)
kb.ask_ki(name="...", graph_pattern="...", binding_model=MyModel, prefixes={...})

# POST — push data to the network (no handler needed)
kb.post_ki(name="...", argument_graph_pattern="...", result_graph_pattern="...", prefixes={...})
```

**Outgoing interactions:**

```python
result = await kb.ask(binding_set, ki_name="...")
result = await kb.post(binding_set, ki_name="...")
```

### `BindingModel`

A Pydantic `BaseModel` subclass that maps Python types to RDF N3 encoding automatically.

```python
from knowledge_mapper import BindingModel, Uri, Literal

class PersonBinding(BindingModel):
    person: Uri              # URIRef, serialized as <...>
    name: Literal[str]       # Python str, serialized as "..."^^xsd:string
    age: Literal[int]        # Python int, serialized as "..."^^xsd:integer
```

Use `BindingModel` for type safety and automatic serialization. Use raw `BindingSet` (`Sequence[dict[str, str]]`) for passthrough data.

### `Depends` — Dependency Injection

Handlers can declare dependencies using `Depends()` in `Annotated` type hints. The framework resolves them at call time.

```python
from typing import Annotated
from knowledge_mapper import Depends

def get_db() -> MyDatabase:
    return MyDatabase(url="...")

@kb.answer_ki(name="...", graph_pattern="...")
def handler(
    binding_set: list[PersonBinding],
    info: KnowledgeInteractionInfo,
    db: Annotated[MyDatabase, Depends(get_db)],
) -> list[PersonBinding]:
    return db.query(binding_set)
```

Dependencies can be sync or async, support nesting, and are cached per invocation by default (`cache=True`).

### `KnowledgeBaseBuilder`

Build a `KnowledgeBase` from settings. Returned by `KnowledgeBase.from_settings()`.

```python
from knowledge_mapper import KnowledgeBase, KnowledgeBaseSettings

settings = KnowledgeBaseSettings(...)
builder = KnowledgeBase.from_settings(settings)

# Attach handlers for ANSWER/REACT KIs defined in settings
builder.handler("my-answer-ki", my_handler_func)

# ASK/POST KIs are auto-registered from settings
kb = builder.build()
```

## Configuration

`KnowledgeBaseSettings` is a Pydantic `BaseSettings` subclass that supports configuration from (highest priority first):

1. Keyword arguments
2. Environment variables (delimiter `__`, e.g. `KNOWLEDGE_BASE__ID`)
3. YAML config file
4. JSON config file
5. Field defaults

Example YAML configuration:

```yaml
knowledge_base:
  id: "http://example.org/my-kb"
  name: "my-kb"
  description: "My knowledge base"
knowledge_engine_endpoint: "http://localhost:8280/rest"
knowledge_interactions:
  - name: my-answer-ki
    type: AnswerKnowledgeInteraction
    prefixes:
      ex: "http://example.org/"
    graph_pattern: "?s ?p ?o ."
```

Subclass `KnowledgeBaseSettings` to add application-specific settings:

```python
from knowledge_mapper import KnowledgeBaseSettings

class AppSettings(KnowledgeBaseSettings):
    db_url: str = "sqlite:///./app.db"
```

## Development

```bash
uv sync              # Install dependencies
uv run pytest        # Run tests
uv run ruff check .  # Lint
uv run ruff format . # Format
```

Tests use `TestClient`, an in-memory fake Smart Connector — no live KE runtime needed for unit tests. For integration tests, start a KE runtime with Docker:

```bash
docker compose -f examples/compose.yaml up -d
uv run pytest
docker compose -f examples/compose.yaml down
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed development and contribution guidelines.
