from typing import Annotated

import pytest

from knowledge_mapper import Depends
from knowledge_mapper.kb.knowledge_base import KnowledgeBase
from knowledge_mapper.ke.models import BindingSet


@pytest.fixture
def kb():
    return KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )


# ---------------------------------------------------------------------------
# Tracer bullet: basic injection
# ---------------------------------------------------------------------------


def test_handler_receives_injected_dependency(kb: KnowledgeBase):
    """Handler with a Depends-annotated param receives the factory's return value."""

    class FakeDb:
        def query(self):
            return "db-result"

    def get_db() -> FakeDb:
        return FakeDb()

    @kb.answer_ki(name="test-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        db: Annotated[FakeDb, Depends(get_db)],
    ) -> BindingSet:
        return [{"result": db.query()}]

    result = kb.call([], "test-ki")
    assert result == [{"result": "db-result"}]


# ---------------------------------------------------------------------------
# cache=True: factory called once per KI call even when used by multiple deps
# ---------------------------------------------------------------------------


def test_cached_dependency_factory_called_once(kb: KnowledgeBase):
    """With cache=True (default), a shared factory is called only once per KI call."""
    call_count = 0

    def get_db():
        nonlocal call_count
        call_count += 1
        return object()

    def get_service(db: Annotated[object, Depends(get_db)]):
        return db  # just passes it through

    @kb.answer_ki(name="cache-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        db: Annotated[object, Depends(get_db)],
        svc: Annotated[object, Depends(get_service)],
    ) -> BindingSet:
        # both db and svc.db should be the SAME object
        assert db is svc
        return []

    kb.call([], "cache-ki")
    assert call_count == 1


# ---------------------------------------------------------------------------
# cache=False: factory called fresh every time
# ---------------------------------------------------------------------------


def test_uncached_dependency_factory_called_each_time(kb: KnowledgeBase):
    """With cache=False, the factory is called fresh for every dependent param."""
    call_count = 0

    def get_value():
        nonlocal call_count
        call_count += 1
        return call_count  # returns a unique value each call

    @kb.answer_ki(name="nocache-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        a: Annotated[int, Depends(get_value, cache=False)],
        b: Annotated[int, Depends(get_value, cache=False)],
    ) -> BindingSet:
        assert a != b  # different values: factory called twice
        return []

    kb.call([], "nocache-ki")
    assert call_count == 2


# ---------------------------------------------------------------------------
# Transitive: dep factory itself has Depends params
# ---------------------------------------------------------------------------


def test_transitive_dependency_resolution(kb: KnowledgeBase):
    """A factory that declares its own Depends params is resolved transitively."""

    class Config:
        url = "sqlite://:memory:"

    class Db:
        def __init__(self, config: Config):
            self.url = config.url

    def get_config() -> Config:
        return Config()

    def get_db(config: Annotated[Config, Depends(get_config)]) -> Db:
        return Db(config)

    @kb.answer_ki(name="transitive-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        db: Annotated[Db, Depends(get_db)],
    ) -> BindingSet:
        return [{"url": db.url}]

    result = kb.call([], "transitive-ki")
    assert result == [{"url": "sqlite://:memory:"}]


# ---------------------------------------------------------------------------
# dependency_overrides: FastAPI-style override mechanism
# ---------------------------------------------------------------------------


def test_dependency_override_replaces_factory(kb: KnowledgeBase):
    """A factory listed in dependency_overrides is replaced at resolution time."""

    class RealDb:
        name = "real"

    class FakeDb:
        name = "fake"

    def get_db() -> RealDb:
        return RealDb()

    @kb.answer_ki(name="override-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        db: Annotated[RealDb, Depends(get_db)],
    ) -> BindingSet:
        return [{"db": db.name}]

    # Without override — uses real factory
    assert kb.call([], "override-ki") == [{"db": "real"}]

    # With override — uses fake factory
    kb.dependency_overrides[get_db] = lambda: FakeDb()
    assert kb.call([], "override-ki") == [{"db": "fake"}]

    # Clear override — back to real
    kb.dependency_overrides.clear()
    assert kb.call([], "override-ki") == [{"db": "real"}]


def test_dependency_override_transitive(kb: KnowledgeBase):
    """Overriding a transitive (nested) factory propagates through the chain."""

    class Config:
        url = "prod://db"

    class TestConfig:
        url = "test://db"

    class Db:
        def __init__(self, config):
            self.url = config.url

    def get_config() -> Config:
        return Config()

    def get_db(config: Annotated[Config, Depends(get_config)]) -> Db:
        return Db(config)

    @kb.answer_ki(name="transitive-override-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        db: Annotated[Db, Depends(get_db)],
    ) -> BindingSet:
        return [{"url": db.url}]

    # Override the leaf dependency — get_db still runs but receives TestConfig
    kb.dependency_overrides[get_config] = lambda: TestConfig()
    assert kb.call([], "transitive-override-ki") == [{"url": "test://db"}]


def test_dependency_override_respects_cache(kb: KnowledgeBase):
    """Override factory inherits the cache=True setting from the Depends declaration."""
    call_count = 0

    def get_value():
        return "real"

    def fake_get_value():
        nonlocal call_count
        call_count += 1
        return "fake"

    def get_service(val: Annotated[str, Depends(get_value)]):
        return val

    @kb.answer_ki(name="cache-override-ki", graph_pattern="?s ?p ?o .")
    def handler(
        binding_set: BindingSet,
        info,
        val: Annotated[str, Depends(get_value)],
        svc: Annotated[str, Depends(get_service)],
    ) -> BindingSet:
        assert val is svc  # same cached instance
        return [{"val": val}]

    kb.dependency_overrides[get_value] = fake_get_value
    kb.call([], "cache-override-ki")
    # fake_get_value should be called only once due to cache=True
    assert call_count == 1
