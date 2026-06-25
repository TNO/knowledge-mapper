# Knowledge Mapper — Codebase Context

> This file is the authoritative context document for AI coding assistants and developers working on this repository. Keep it up to date as the project evolves.

---

## What Is This Project?

**`knowledge-mapper`** is a Python SDK for connecting Python applications to the [TNO Knowledge Engine (TKE)](https://docs.knowledge-engine.eu/) network. It provides:

1. **A Python SDK** — write Python code, use decorators, implement your own handlers.
2. **A settings/config-driven approach** (work in progress) — for simple cases where no custom handler logic is needed, a config file (YAML/JSON) plus a CLI should suffice.

Both approaches are planned and partially implemented. The SDK path is fully functional, and the `knowledge-mapper run path/to/file.py:kb` CLI starts an SDK-defined KB (issue #10). A future config-driven CLI (loading a `KnowledgeBase` from a YAML/JSON settings file) is tracked separately.

---

## TKE Ecosystem Glossary

| Term | Abbreviation | Meaning |
|------|-------------|---------|
| Knowledge Engine | KE | The distributed network/platform that enables knowledge exchange between applications |
| Knowledge Directory | KD | Central service that matches and routes knowledge interactions between Smart Connectors |
| Smart Connector | SC | Central service where participants register and that participants query for other participants in the network |
| Knowledge Base | KB | A user's application that holds or requests knowledge; connects to the KE network via a Smart Connector |
| Knowledge Interaction | KI | A declared intent to exchange knowledge — either to provide it (ANSWER/REACT) or request it (ASK/POST) |
| Binding Set | BS | A list of dictionaries mapping SPARQL variable names to RDF N3-encoded values |
| Graph Pattern | GP | A SPARQL-like triple pattern string that describes the "shape" of a knowledge interaction |

### Knowledge Interaction Types

| Type | Direction | Role |
|------|-----------|------|
| **ASK** | Outgoing | The KB queries the KE network for knowledge matching the graph pattern |
| **ANSWER** | Incoming | The KB responds to queries from the KE network with its knowledge |
| **POST** | Outgoing | The KB pushes data into the KE network (argument + optional result pattern) |
| **REACT** | Incoming | The KB handles incoming POST calls from the KE network |

---

## Architecture

```
User's Python app (this library)
        │
        │  instantiates
        ▼
  KnowledgeBase (src/kb/knowledge_base.py)
        │
        │  REST API calls (requests)
        ▼
  Smart Connector (SC) ← Java process, usually in Docker
        │
        │  KE network protocol
        ▼
  Knowledge Directory (KD)
        │
        │  routes to other SCs/KBs
        ▼
  Other KBs in the network
```

**Key runtime model**: The `KnowledgeBase` registers itself and its KIs with the SC, then enters a **concurrent long-polling loop** (`start_handling_loop()`). The loop runs multiple poll-dispatch cycles concurrently, bounded by a semaphore (`max_concurrent_handlers`, default 10). Each cycle acquires the semaphore, polls the SC, and on HANDLE spawns an `asyncio.Task` that runs the handler, posts the response, and releases the semaphore. Handler exceptions are caught — an empty binding set is posted back so the SC doesn't hang. On EXIT, the loop stops polling and awaits all in-flight handler tasks. For outgoing interactions (`ask()` / `post()`), the KB sends a request to the SC which fans out through the network.

---

## Repository Layout

```
src/
  __init__.py                  # Public API exports: KnowledgeBase, KnowledgeBaseBuilder, KnowledgeBaseSettings, Depends
  depends.py                   # Depends — DI marker for handler parameter annotations
  di.py                        # resolve_dependencies — resolves Depends-annotated params at call time
  knowledge_base.py            # KnowledgeBase class — the main user-facing class
  knowledge_base_builder.py    # KnowledgeBaseBuilder — settings-aware builder that wraps KnowledgeBase
  knowledge_interaction.py     # KnowledgeInteractionContext, Handler type, status enum
  settings.py                  # KnowledgeBaseSettings (Pydantic BaseSettings subclass)
  ke/
    __init__.py
    client.py                  # Client (real HTTP) + ClientProtocol (interface) + PollResult
    models.py                  # All Pydantic models: BindingModel, Uri, Literal, KiTypes, etc.
    errors.py                  # Custom exceptions
    testing/
      fake_client.py           # TestClient — in-memory fake SC for unit tests

examples/
  basic.py                     # Simplest possible KB with an ANSWER KI
  binding_models.py            # Typed BindingModels vs raw BindingSet usage
  ask_interaction.py           # ASK KI with a typed BindingModel
  post_measurement.py          # POST KI with argument and result BindingModels
  custom-settings/
    custom_settings.py         # KnowledgeBaseSettings subclass + ki_from_settings pattern
    settings.yaml              # Example YAML config for all four KI types
  shared.py                    # Example logging helper
  compose.yaml                 # Docker Compose for running two SC instances for examples/testing

tests/
  test_ask_and_post.py
  test_bindings.py
  test_client.py
  test_handlers.py
  test_kb_lifespan.py
  test_ki_registration.py
  configuration/               # Config files used by tests
```

---

## Public API

### `KnowledgeBase`

```python
from src import KnowledgeBase

kb = KnowledgeBase(
    id="http://example.org/my-kb",        # URI identifying this KB in the network
    name="my-kb",
    description="...",
    ke_url="http://localhost:8280/rest",   # URL of the Smart Connector REST API
)

# Alternatively, build from settings — returns a KnowledgeBaseBuilder:
builder = KnowledgeBase.from_settings(settings)  # settings: KnowledgeBaseSettings
```

#### Lifecycle
```python
await kb.connect()      # Verify SC is reachable (raises KnowledgeEngineNotAvailableError if not)
await kb.register()     # Register KB + sync all KIs with the SC (re-registers if already registered)
await kb.unregister()   # Unregister KB from SC (KIs automatically unregistered)
await kb.close()        # Close the underlying HTTP client and release resources
```

#### Registering KIs (decorator pattern)

```python
# ANSWER KI — handler called when another KB asks for this pattern
@kb.answer_ki(name="...", graph_pattern="...", prefixes={...})
def my_handler(binding_set, info):
    ...
    return binding_set

# REACT KI — handler called when another KB posts matching data
@kb.react_ki(name="...", argument_graph_pattern="...", result_graph_pattern="...", prefixes={...})
def my_react_handler(binding_set, info):
    ...
    return result_binding_set
```

#### Registering KIs (non-decorator)

```python
# ASK KI — no handler; call kb.ask() to query the network
kb.ask_ki(name="...", graph_pattern="...", binding_model=MyModel, prefixes={...})

# POST KI — no handler; call kb.post() to push data to the network
kb.post_ki(name="...", argument_graph_pattern="...", result_graph_pattern="...", prefixes={...})
```

#### Outgoing interactions

```python
result = await kb.ask(binding_set, ki_name="...")    # Returns BindingSet or list[BindingModel]
result = await kb.post(binding_set, ki_name="...")   # Returns result BindingSet or list[BindingModel]
```

#### Handling loop

```python
await kb.start_handling_loop()                          # Concurrent dispatch, up to 10 in-flight
await kb.start_handling_loop(max_concurrent_handlers=5) # Limit to 5 concurrent handlers
await kb.start_handling_loop(loops=10)                  # Runs exactly 10 poll cycles (useful for testing)
```

---

### `Depends` — Dependency injection

Handlers can declare dependencies (database connections, HTTP clients, config, etc.) using
`Depends()` in `Annotated` type hints.  The framework resolves them at call time.

```python
from typing import Annotated
from src import Depends

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

**Behaviour:**
- The framework inspects handler signatures at registration time and resolves `Depends` params at call time.
- Dependency factories can be **sync (`def`) or async (`async def`)** — async factories are detected via `asyncio.iscoroutinefunction()` and awaited automatically; sync factories are called directly.
- Factories can themselves declare `Depends` parameters — nested/transitive resolution is supported, including mixed sync/async chains.
- `cache=True` (default): factory called once per KI-call invocation; result shared across all uses.
- `cache=False`: factory called fresh every time it is needed.

---

### `KnowledgeBaseBuilder`

Returned by `KnowledgeBase.from_settings()`. Wraps a `KnowledgeBase` internally and exposes
settings-based KI registration. Call `build()` when all handlers are attached to get the
finished KB.

ASK and POST KIs are registered automatically from settings — no explicit call needed.
Attach handlers for ANSWER and REACT KIs via `handler()` before calling `build()`.

```python
from src import KnowledgeBase, KnowledgeBaseSettings

settings = KnowledgeBaseSettings(...)
builder = KnowledgeBase.from_settings(settings)

# For ANSWER/REACT — attach a handler; KI info comes from settings
builder.handler("my-answer-ki", my_handler_func)

# For ASK/POST — no call needed; they are auto-registered from settings

kb = builder.build()   # Returns the configured KnowledgeBase; raises ValueError if any
                       # ANSWER/REACT KI has no handler
kb.connect()
kb.register()
kb.start_handling_loop()
```

---

## BindingModel — Typed Bindings

`BindingModel` (Pydantic `BaseModel` subclass) maps Python types to RDF N3 encoding automatically. Use it to avoid manual N3 string construction.

```python
from src.ke.models import BindingModel, Uri, Literal
from rdflib import URIRef

class PersonBinding(BindingModel):
    person: Uri              # maps to/from URIRef, serialized as <...>
    name: Literal[str]       # maps to/from Python str, serialized as "..."^^xsd:string
    age: Literal[int]        # maps to/from Python int, serialized as "..."^^xsd:integer
```

- **`Uri`**: Accepts `URIRef` or N3-encoded string (`<...>`), serializes to N3 `<...>`.
- **`Literal[T]`**: Accepts Python native types or N3 literals, serializes to N3 `"value"^^type`.
- All fields default to `None` — use `dump_result_binding()` to validate all fields are set before returning, or `dump_partial_binding()` for partial/query bindings.

**When to use typed BindingModels vs raw `BindingSet` (list of dicts)**:
- Use `BindingModel` when you want type safety, validation, and automatic N3 serialization.
- Use raw `BindingSet = Sequence[dict[str, str]]` when working with passthrough data or when you need the raw N3 strings.

Handler type annotation controls automatic (de)serialization:

```python
# Typed — framework validates incoming bindings and serializes outgoing ones
def my_handler(binding_set: list[PersonBinding], info) -> list[PersonBinding]: ...

# Raw — no automatic conversion, you get/return raw N3 strings
def my_handler(binding_set: BindingSet, info) -> BindingSet: ...
```

---

## Settings System (`KnowledgeBaseSettings`)

Pydantic `BaseSettings` subclass. Supports config from (highest priority first):
1. Keyword arguments
2. Environment variables (delimiter `__` for nested, e.g. `KNOWLEDGE_BASE__ID`)
3. YAML config file (default `config.yaml`)
4. JSON config file (default `config.json`)
5. Field defaults

Subclass to add application-specific settings:

```python
from src import KnowledgeBaseSettings
from pydantic_settings import SettingsConfigDict, CliSettingsSource

class AppSettings(KnowledgeBaseSettings):
    model_config = SettingsConfigDict(yaml_file="config.yaml", cli_parse_args=True)
    db_url: str = "sqlite:///./app.db"

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        return (CliSettingsSource(settings_cls, cli_parse_args=True),
                *super().settings_customise_sources(settings_cls, **kwargs))
```

YAML config structure:

```yaml
knowledge_base:
  id: "http://example.org/my-kb"
  name: "my-kb"
  description: "..."
knowledge_engine_endpoint: "http://localhost:8280/rest"
knowledge_interactions:
  - name: my-answer-ki
    type: AnswerKnowledgeInteraction
    prefixes:
      ex: "http://example.org/"
    graph_pattern: "?s ?p ?o ."
```

#### Registering KIs from settings

```python
builder = KnowledgeBase.from_settings(settings)

# For ANSWER/REACT — attach a handler function
builder.handler("my-answer-ki", my_handler_func)

# For ASK/POST — auto-registered; no explicit call needed

kb = builder.build()
```

---

## Testing

Tests use `TestClient` — an in-memory fake Smart Connector satisfying `ClientProtocol`. No live KE runtime needed.

```python
from src.ke.testing import TestClient

client = TestClient(fake_url="http://fake-ke")
kb = KnowledgeBase(id="...", name="...", description="...", ke_url="http://fake-ke")
kb.client = client   # inject fake client
kb.register()

# Mock a result for an ASK or POST KI
client.mock_result_binding_set(ki_name="my-ask-ki", binding_set=[...])

# Simulate an incoming KI call (ANSWER/REACT) — queued for the handling loop to consume
client.enqueue_handle_request(ki_name="my-answer-ki", binding_set=[...])
client.enqueue_exit()  # signal the handling loop to stop after draining the queue
kb.start_handling_loop()

# Assert the handler result was posted back to the (fake) SC
assert client.last_handle_response == [...]
```

### `dependency_overrides` — Overriding Dependencies in Tests

`KnowledgeBase.dependency_overrides` is a `dict[Callable, Callable]` that lets you replace dependency factories at test time, mirroring FastAPI's `app.dependency_overrides`.

```python
def get_db() -> RealDatabase:
    return RealDatabase(url="postgresql://...")

# In production — handler receives RealDatabase
@kb.answer_ki(name="my-ki", graph_pattern="...")
def handler(
    binding_set, info,
    db: Annotated[RealDatabase, Depends(get_db)],
): ...

# In tests — swap the factory
kb.dependency_overrides[get_db] = lambda: FakeDatabase()

# Clear when done
kb.dependency_overrides.clear()
```

**Behaviour:**
- Overrides are **transitive**: overriding a leaf factory (e.g. `get_config`) propagates to all factories that depend on it.
- Override factories **inherit the `cache` setting** from the original `Depends()` declaration.
- Overrides apply to all KI handlers on the KB (not per-KI).

Run tests with:

```bash
uv run pytest
```

For integration tests requiring a live SC, use the Docker Compose in `examples/compose.yaml`:

```bash
docker compose -f examples/compose.yaml up -d
uv run pytest
```

---

## Development Environment

- **Python**: ≥ 3.13
- **Package manager**: `uv` (see `uv.lock`)
- **Linter/formatter**: `ruff` (configured in `pyproject.toml`)
- **Build system**: `setuptools`

```bash
uv sync              # install dependencies
uv run pytest        # run tests
uv run ruff check .  # lint
uv run ruff format . # format
```

---

## Legacy Code

The pre-overhaul, config-file-driven mapper implementation has been removed from the repository. The `mapper-legacy` git tag marks the last legacy release and preserves the full history.

---

## Open Issues (GitHub)

| # | Title | Notes |
|---|-------|-------|
| [#5](https://github.com/TNO/knowledge-mapper/issues/5) | Make `result_pattern` optional for POST interactions | `PostReactInteractionInfo.result_graph_pattern` is currently required; should be optional |
| [#6](https://github.com/TNO/knowledge-mapper/issues/6) | Allow domain knowledge loading via KE client | Extend `Client`/`ClientProtocol` with methods to load domain knowledge into the SC (supported since KE 1.3.1) |
| [#10](https://github.com/TNO/knowledge-mapper/issues/10) | Create simple CLI for starting KM | ✅ Done — `knowledge-mapper run path/to/file.py:kb` (typer-based, see `src/knowledge_mapper/cli.py`) |
| [#11](https://github.com/TNO/knowledge-mapper/issues/11) | Add dependency injection system | Allow handlers to declare dependencies (e.g. DB connections) that are injected at call time |
| [#15](https://github.com/TNO/knowledge-mapper/issues/15) | Create default handlers for POST and ASK interactions | ASK/POST KIs are now auto-registered from settings via `builder.build()` with no handler; outgoing-only KIs need no handler |
| [#23](https://github.com/TNO/knowledge-mapper/issues/23) | Extract settings-based KI registration out of KnowledgeBase | ✅ Done — moved to `KnowledgeBaseBuilder` in `src/knowledge_base_builder.py` |
| [#20](https://github.com/TNO/knowledge-mapper/issues/20) | Deepen KnowledgeInteractionContext: move binding dispatch into the context | Binding model apply-logic is duplicated across `call()`, `ask()`, `post()` |
| [#21](https://github.com/TNO/knowledge-mapper/issues/21) | Bug: handling loop dispatches by KI ID but registry is keyed by name; handle response never sent | Latent bug masked by TestClient always returning REPOLL |
| [#22](https://github.com/TNO/knowledge-mapper/issues/22) | TestClient: support enqueueing incoming KI calls to make the handling loop unit-testable | `poll_ki_call` hardwired to REPOLL; HANDLE/EXIT paths untestable |
| [#23](https://github.com/TNO/knowledge-mapper/issues/23) | Extract settings-based KI registration out of KnowledgeBase | Move to `KnowledgeBaseBuilder` in `src/kb/builder.py` |

---

## Key Design Decisions

- **`KnowledgeBase` ≠ Smart Connector**: The SC is a separate Java process (usually containerized). `KnowledgeBase` is the Python representation of a KB that registers with the SC over REST.
- **Pydantic throughout**: Models, settings, and binding validation all use Pydantic v2. `BindingModel` uses `alias_generator=to_camel` to match the TKE REST API's camelCase fields.
- **`ClientProtocol`**: The `Client` (real HTTP) and `TestClient` (fake) both satisfy this Protocol. Injecting a fake client is the standard testing pattern. `ClientProtocol` includes `post_handle_response` — the method that sends a handler's result back to the SC after an incoming KI call.
- **Deferred KI registration**: By default, `answer_ki`/`react_ki` etc. use `defer_ke_registration=True`, meaning KIs are registered locally but not sent to the SC until `kb.register()` or `kb.sync_knowledge_interactions()` is called.
- **KI registry indexed by ID after registration**: `KnowledgeBase` maintains a secondary index (`_ki_registry_by_id`) populated once a KI is registered with the SC and assigned an ID. The handling loop dispatches by ID using this index.
- **Handler introspection**: `KnowledgeInteractionContext.__post_init__` inspects handler signatures to auto-detect binding models, enabling transparent (de)serialization without manual type dispatch. Dispatch logic (validate → call → serialize for ANSWER/REACT; prepare_outgoing + parse_result for ASK/POST) lives in `KnowledgeInteractionContext`, not in `KnowledgeBase`.
- **`KnowledgeBaseBuilder` wraps `KnowledgeBase`**: Settings-based KI registration belongs to `KnowledgeBaseBuilder`, not to `KnowledgeBase`. `KnowledgeBase.from_settings()` returns a builder; `builder.build()` returns the finished `KnowledgeBase`. `KnowledgeBase` itself has no knowledge of settings. ASK/POST KIs are auto-registered at `build()` time; ANSWER/REACT KIs require a handler attached via `builder.handler(name, func)` before `build()` is called.
- **Dependency injection via `Depends`**: `KnowledgeInteractionContext.dispatch()` calls `resolve_dependencies(handler)` before invoking the handler, passing resolved values as kwargs.  The resolver (`src/dependency_injection.py`) uses `get_type_hints(include_extras=True)` to find `Annotated[T, Depends(factory)]` params, recursively resolves factory deps (transitive), and caches results per invocation when `cache=True`.  Factories can be sync (`def`) or async (`async def`) — async factories are detected via `asyncio.iscoroutinefunction()` and awaited; sync factories are called directly.  `@wraps` on the decorator wrapper preserves `__annotations__`, so the resolver sees the original handler's hints.
- **`dependency_overrides`**: `KnowledgeBase.dependency_overrides` is a `dict[Callable, Callable]` (à la FastAPI) that substitutes dependency factories at resolution time.  Overrides are checked transitively at every level and inherit the original `Depends(cache=...)` setting.  The dict is passed explicitly from `KnowledgeBase.call()` → `dispatch()` → `resolve_dependencies()` to keep `KnowledgeInteractionContext` decoupled from `KnowledgeBase`.
