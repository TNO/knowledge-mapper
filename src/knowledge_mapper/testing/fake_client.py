"""In-memory FakeClient that satisfies ClientProtocol for use in tests."""

import asyncio
from datetime import UTC, datetime, timedelta

from knowledge_mapper.ke.client import ClientProtocol, HandleRequest, PollResult
from knowledge_mapper.ke.errors import SmartConnectorNotFoundError
from knowledge_mapper.ke.models import (
    AskResult,
    BindingSet,
    ExchangeInfo,
    Initiator,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostResult,
    SmartConnectorLease,
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
        self._handle_responses: list[tuple[str, str, int, BindingSet]] = []
        self._incoming_calls: asyncio.Queue[tuple[PollResult, HandleRequest | None]] = (
            asyncio.Queue()
        )
        self._next_handle_request_id: int = 1
        # Maps kb_id -> the most recently loaded domain knowledge string.
        self._domain_knowledge: dict[str, str] = {}
        # Maps kb_id -> number of times its lease has been renewed.
        self._lease_renewals: dict[str, int] = {}

    async def ke_is_available(self) -> bool:
        return True

    async def ke_version(self) -> str:
        return "0.0.0-fake"

    async def get_knowledge_base(self, id: str) -> KnowledgeBaseInfo | None:
        return self._knowledge_bases.get(id)

    async def get_all_knowledge_bases(self) -> list[KnowledgeBaseInfo]:
        return list(self._knowledge_bases.values())

    async def register_kb(
        self, info: KnowledgeBaseInfo, reregister: bool = True
    ) -> None:
        if info.id in self._knowledge_bases:
            if reregister:
                await self.unregister_kb(info.id)
            else:
                return
        self._knowledge_bases[info.id] = info
        self._knowledge_interactions[info.id] = []

    async def unregister_kb(self, id: str) -> None:
        self._knowledge_bases.pop(id)
        self._knowledge_interactions.pop(id, None)

    async def get_all_knowledge_interactions(
        self, kb_id: str
    ) -> list[KnowledgeInteractionInfo]:
        return list(self._knowledge_interactions.get(kb_id, []))

    async def register_ki(
        self, kb_id: str, ki: KnowledgeInteractionInfo
    ) -> KnowledgeInteractionInfo:
        registered = ki.model_copy(update={"id": f"fake-ki-{self._next_ki_id}"})
        self._next_ki_id += 1
        self._knowledge_interactions.setdefault(kb_id, []).append(registered)
        return registered

    async def unregister_ki(self, kb_id: str, ki_id: str) -> None:
        if kb_id not in self._knowledge_bases:
            raise SmartConnectorNotFoundError(kb_id, self._ke_url)
        kis = self._knowledge_interactions.get(kb_id, [])
        for i, ki in enumerate(kis):
            if ki.id == ki_id:
                kis.pop(i)
                return
        raise SmartConnectorNotFoundError(kb_id, self._ke_url)

    async def renew_lease(self, kb_id: str) -> SmartConnectorLease:
        if kb_id not in self._knowledge_bases:
            raise SmartConnectorNotFoundError(kb_id, self._ke_url)
        self._lease_renewals[kb_id] = self._lease_renewals.get(kb_id, 0) + 1
        info = self._knowledge_bases[kb_id]
        # Default to 60 seconds if leaseRenewalTime is unset.
        renewal_seconds = info.lease_renewal_time or 60
        return SmartConnectorLease(
            knowledge_base_id=kb_id,
            expires=datetime.now(tz=UTC) + timedelta(seconds=renewal_seconds),
        )

    async def load_domain_knowledge(self, kb_id: str, knowledge: str) -> None:
        if kb_id not in self._knowledge_bases:
            raise SmartConnectorNotFoundError(kb_id, self._ke_url)
        self._domain_knowledge[kb_id] = knowledge

    @property
    def loaded_domain_knowledge(self) -> dict[str, str]:
        """Return the most-recently-loaded domain knowledge per KB id (for tests)."""
        return dict(self._domain_knowledge)

    @property
    def lease_renewals(self) -> dict[str, int]:
        """Return the number of lease renewals per KB id (for tests)."""
        return dict(self._lease_renewals)

    async def poll_ki_call(self, kb_id: str) -> tuple[PollResult, HandleRequest | None]:
        return await self._incoming_calls.get()

    async def post_handle_response(
        self, kb_id: str, ki_id: str, handle_request_id: int, binding_set: BindingSet
    ) -> None:
        self._handle_responses.append((kb_id, ki_id, handle_request_id, binding_set))

    @property
    def last_handle_response(self) -> BindingSet | None:
        """Return the binding set from the most recent handle response, or ``None``."""
        if not self._handle_responses:
            return None
        return self._handle_responses[-1][3]

    def mock_result_binding_set(self, ki_name: str, binding_set: BindingSet) -> None:
        """Store a result binding set to be returned when execute_post_interaction
        is called for the KI with the given name."""
        self._mock_interaction_results[ki_name] = binding_set

    def enqueue_handle_request(
        self,
        ki_name: str,
        binding_set: BindingSet,
        requesting_kb_id: str = "http://example.org/requesting-kb",
    ) -> None:
        """Queue an incoming KI call so ``poll_ki_call`` returns HANDLE for it.

        Args:
            ki_name: Name of a KI that has already been registered via
                ``register_ki``.
            binding_set: The incoming binding set to pass to the handler.
            requesting_kb_id: The ID of the requesting knowledge base
                (defaults to a test sentinel).

        Raises:
            KeyError: If no registered KI with *ki_name* exists.
        """
        ki = next(
            (
                ki
                for kis in self._knowledge_interactions.values()
                for ki in kis
                if ki.name == ki_name
            ),
            None,
        )
        if ki is None or ki.id is None:
            raise KeyError(
                f"No registered KI named '{ki_name}' found in TestClient. "
                "Register the KI before enqueueing a handle request."
            )

        handle_request = HandleRequest(
            knowledge_interaction_id=ki.id,
            handle_request_id=self._next_handle_request_id,
            binding_set=binding_set,
            requesting_knowledge_base_id=requesting_kb_id,
        )
        self._next_handle_request_id += 1
        self._incoming_calls.put_nowait((PollResult.HANDLE, handle_request))

    def enqueue_exit(self) -> None:
        """Queue an EXIT signal so ``poll_ki_call`` terminates the handling loop."""
        self._incoming_calls.put_nowait((PollResult.EXIT, None))

    async def ask(
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

    async def post(
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

    async def close(self) -> None:
        pass

    @property
    def ke_url(self) -> str:
        return self._ke_url
