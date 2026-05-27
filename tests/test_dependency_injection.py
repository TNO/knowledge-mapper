from typing import Annotated

import pytest

from src import Depends
from src.kb.knowledge_base import KnowledgeBase
from src.ke.models import BindingSet


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
