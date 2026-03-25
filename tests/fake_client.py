"""In-memory FakeClient that satisfies ClientProtocol for use in tests."""

from src.ke.client import PollResult
from src.ke.models import KnowledgeBaseInfo, KnowledgeInteractionInfo


class FakeClient:
    """A lightweight in-memory stand-in for Client. Always succeeds."""

    def __init__(self, fake_url) -> None:
        self._knowledge_bases: dict[str, KnowledgeBaseInfo] = {}
        # Maps kb_id -> list of registered KIs
        self._knowledge_interactions: dict[str, list[KnowledgeInteractionInfo]] = {}
        self._next_ki_id: int = 1
        self.ke_url = fake_url

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

    def get_knowledge_interactions(self, kb_id: str) -> list[KnowledgeInteractionInfo]:
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
