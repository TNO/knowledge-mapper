"""In-memory FakeClient that satisfies ClientProtocol for use in tests."""

from datetime import UTC, datetime

from src.knowledge_mapper.ke.client import ClientProtocol, PollResult
from src.knowledge_mapper.ke.models import (
    AskResult,
    BindingSet,
    ExchangeInfo,
    Initiator,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostResult,
)


class TestClient(ClientProtocol):
    """A lightweight in-memory stand-in for Client. Always succeeds."""

    def __init__(self, fake_url) -> None:
        self._knowledge_bases: dict[str, KnowledgeBaseInfo] = {}
        # Maps kb_id -> list of registered KIs
        self._knowledge_interactions: dict[str, list[KnowledgeInteractionInfo]] = {}
        self._next_ki_id: int = 1
        self._ke_url = fake_url
        # Maps ki_name -> BindingSet to return from execute_post_interaction
        self._mock_interaction_results: dict[str, BindingSet] = {}

    def ke_is_available(self) -> bool:
        return True

    def ke_version(self) -> str:
        return "0.0.0-fake"

    def get_knowledge_base(self, id: str) -> KnowledgeBaseInfo | None:
        return self._knowledge_bases.get(id)

    def get_all_knowledge_bases(self) -> list[KnowledgeBaseInfo]:
        return list(self._knowledge_bases.values())

    def register_kb(self, info: KnowledgeBaseInfo, reregister: bool = True) -> None:
        if info.id in self._knowledge_bases:
            if reregister:
                self.unregister_kb(info.id)
            else:
                return
        self._knowledge_bases[info.id] = info
        self._knowledge_interactions[info.id] = []

    def unregister_kb(self, id: str) -> None:
        self._knowledge_bases.pop(id)
        self._knowledge_interactions.pop(id, None)

    def get_all_knowledge_interactions(
        self, kb_id: str
    ) -> list[KnowledgeInteractionInfo]:
        return list(self._knowledge_interactions.get(kb_id, []))

    def register_ki(
        self, kb_id: str, ki: KnowledgeInteractionInfo
    ) -> KnowledgeInteractionInfo:
        registered = ki.model_copy(update={"id": f"fake-ki-{self._next_ki_id}"})
        self._next_ki_id += 1
        self._knowledge_interactions.setdefault(kb_id, []).append(registered)
        return registered

    def poll_ki_call(self, kb_id: str) -> tuple[PollResult, None]:
        # This fake client never returns any KI calls to handle, but always asks to
        # repoll.
        return (PollResult.REPOLL, None)

    def mock_result_binding_set(self, ki_name: str, binding_set: BindingSet) -> None:
        """Store a result binding set to be returned when execute_post_interaction
        is called for the KI with the given name."""
        self._mock_interaction_results[ki_name] = binding_set

    def ask(
        self,
        kb_id: str,
        ki_id: str,
        binding_set: BindingSet,
        recipient_ids: list[str] | None = None,
    ) -> AskResult:
        # Look up KI by ID to find its name, then check for a mocked result.
        ki = next(
            (
                ki
                for kis in self._knowledge_interactions.values()
                for ki in kis
                if ki.id == ki_id
            ),
            None,
        )
        ki_name = ki.name if ki is not None else None
        binding_set = (
            self._mock_interaction_results[ki_name]
            if ki_name is not None and ki_name in self._mock_interaction_results
            else []
        )
        now = datetime.now(tz=UTC)
        return AskResult(
            binding_set=binding_set,
            exchange_info=[
                ExchangeInfo(
                    initiator=Initiator.KNOWLEDGE_BASE,
                    knowledge_base_id=kb_id,
                    knowledge_interaction_id=ki_id,
                    exchange_start=now,
                    exchange_end=now,
                    status="OK",
                )
            ],
        )

    def post(
        self,
        kb_id: str,
        ki_id: str,
        binding_set: BindingSet,
        recipient_ids: list[str] | None = None,
    ) -> PostResult:
        # Look up KI by ID to find its name, then check for a mocked result.
        ki = next(
            (
                ki
                for kis in self._knowledge_interactions.values()
                for ki in kis
                if ki.id == ki_id
            ),
            None,
        )
        ki_name = ki.name if ki is not None else None
        result_binding_set = (
            self._mock_interaction_results[ki_name]
            if ki_name is not None and ki_name in self._mock_interaction_results
            else []
        )
        now = datetime.now(tz=UTC)
        return PostResult(
            result_binding_set=result_binding_set,
            exchange_info=[
                ExchangeInfo(
                    initiator=Initiator.KNOWLEDGE_BASE,
                    knowledge_base_id=kb_id,
                    knowledge_interaction_id=ki_id,
                    exchange_start=now,
                    exchange_end=now,
                    status="OK",
                )
            ],
        )

    @property
    def ke_url(self) -> str:
        return self._ke_url
