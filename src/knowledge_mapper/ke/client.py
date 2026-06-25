import logging
from enum import StrEnum
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .errors import SmartConnectorNotFoundError, UnexpectedHttpResponseError
from .models import (
    AskAnswerInteractionInfo,
    AskResult,
    BindingSet,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
    PostResult,
    SmartConnectorLease,
)

logger = logging.getLogger(__name__)


class PollResult(StrEnum):
    HANDLE = "handle"
    REPOLL = "repoll"
    EXIT = "exit"


class HandleRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, extra="allow", frozen=True, populate_by_name=True
    )

    knowledge_interaction_id: str
    handle_request_id: int
    binding_set: list[dict[str, str]]
    requesting_knowledge_base_id: str


class ClientProtocol(Protocol):
    """Interface for communicating with a Knowledge Engine runtime."""

    async def ke_is_available(self) -> bool:
        """Return ``True`` if the KE runtime is reachable, ``False`` otherwise."""
        ...

    async def ke_version(self) -> str:
        """Return the version string of the KE runtime.

        Raises:
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def get_knowledge_base(self, id: str) -> KnowledgeBaseInfo | None:
        """Return the KB with the given ID, or ``None`` if it does not exist.

        Raises:
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def get_all_knowledge_bases(self) -> list[KnowledgeBaseInfo]:
        """Return all KBs registered at the KE runtime.

        Raises:
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def register_kb(
        self, info: KnowledgeBaseInfo, reregister: bool = True
    ) -> None:
        """Register a KB at the KE runtime, optionally re-registering if it already
        exists.

        Raises:
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def unregister_kb(self, id: str) -> None:
        """Unregister the KB with the given ID from the KE runtime.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def get_all_knowledge_interactions(
        self, kb_id: str
    ) -> list[KnowledgeInteractionInfo]:
        """Return all knowledge interactions registered for the given KB.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def register_ki(
        self, kb_id: str, ki: KnowledgeInteractionInfo
    ) -> KnowledgeInteractionInfo:
        """Register a knowledge interaction for the given KB and return it with its
        assigned ID set in the info.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def unregister_ki(self, kb_id: str, ki_id: str) -> None:
        """Unregister a single knowledge interaction with the given ID from the KB
        with the given ID.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID, or no knowledge interaction with the given ID exists for that KB.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def renew_lease(self, kb_id: str) -> SmartConnectorLease:
        """Renew the lease of the smart connector for the given KB and return the
        new lease.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID, or it does not have a lease.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def load_domain_knowledge(self, kb_id: str, knowledge: str) -> None:
        """Load domain knowledge (Apache Jena facts/rules) into the smart connector
        for the given KB. Replaces any previously loaded domain knowledge.

        Args:
            kb_id: The ID of the KB whose smart connector should be loaded with the
                given domain knowledge.
            knowledge: The domain knowledge (both facts and rules) as plain text in
                the Apache Jena Rules syntax.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def poll_ki_call(self, kb_id: str) -> tuple[PollResult, HandleRequest | None]:
        """Poll the KE runtime for an incoming KI call for the given KB.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def post_handle_response(
        self, kb_id: str, ki_id: str, handle_request_id: int, binding_set: BindingSet
    ) -> None:
        """Post the response to a KI call that was received via ``poll_ki_call``.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def ask(
        self,
        kb_id: str,
        ki_id: str,
        binding_set: BindingSet,
        recipient_ids: list[str] | None = None,
    ) -> AskResult:
        """Execute an ASK interaction by sending the given binding set as the
        response to the KI call and returning the resulting binding set from the KE.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def post(
        self,
        kb_id: str,
        ki_id: str,
        binding_set: BindingSet,
        recipient_ids: list[str] | None = None,
    ) -> PostResult:
        """Execute a POST interaction by sending the given binding set as the
        response to the KI call.

        Raises:
            SmartConnectorNotFoundError: If no smart connector exists for the given KB
            ID.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        ...

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        ...

    @property
    def ke_url(self) -> str:
        """Return the base URL of the KE runtime this client is communicating with."""
        ...


class Client(ClientProtocol):
    """HTTP client for the Knowledge Engine REST API."""

    def __init__(self, ke_url: str):
        self._ke_url = ke_url
        # The KE pattern (long-poll, dispatch, collate) can legitimately take
        # well over httpx's 5 s default, especially under concurrent load.
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    async def ke_is_available(self) -> bool:
        try:
            _ = await self._http.get(f"{self.ke_url}/version")
            return True
        except httpx.HTTPError:
            return False

    async def ke_version(self) -> str:
        response = await self._http.get(f"{self.ke_url}/version")
        return response.json()["version"]

    async def get_knowledge_base(self, id: str) -> KnowledgeBaseInfo | None:
        response = await self._http.get(
            f"{self.ke_url}/sc", headers={"Knowledge-Base-Id": id}
        )
        if response.status_code == 404:
            return None
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        # KE returns a list with only one element here.
        return KnowledgeBaseInfo.model_validate(response.json()[0])

    async def get_all_knowledge_bases(self) -> list[KnowledgeBaseInfo]:
        response = await self._http.get(f"{self.ke_url}/sc")
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        return [
            KnowledgeBaseInfo.model_validate(kb_json) for kb_json in response.json()
        ]

    async def register_kb(
        self, info: KnowledgeBaseInfo, reregister: bool = True
    ) -> None:
        if await self.get_knowledge_base(info.id) is not None:
            if reregister:
                await self.unregister_kb(info.id)
            else:
                return

        logger.debug("Registering knowledge base '%s' at %s.", info.id, self.ke_url)
        response = await self._http.post(
            f"{self.ke_url}/sc",
            json=info.model_dump(by_alias=True, exclude_none=True),
        )
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)
        return

    async def unregister_kb(self, id: str) -> None:
        logger.debug("Unregistering knowledge base '%s' at %s.", id, self.ke_url)
        response = await self._http.delete(
            f"{self.ke_url}/sc", headers={"Knowledge-Base-Id": id}
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(id, self.ke_url)
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)
        return

    async def get_all_knowledge_interactions(
        self, kb_id: str
    ) -> list[KnowledgeInteractionInfo]:
        response = await self._http.get(
            f"{self.ke_url}/sc/ki",
            headers={"Knowledge-Base-Id": kb_id},
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        kis = []
        for kb_info in response.json():
            match kb_info["knowledgeInteractionType"]:
                case KiTypes.ASK | KiTypes.ANSWER:
                    kis.append(AskAnswerInteractionInfo.model_validate(kb_info))
                case KiTypes.POST | KiTypes.REACT:
                    kis.append(PostReactInteractionInfo.model_validate(kb_info))
        return kis

    async def register_ki(
        self, kb_id: str, ki: KnowledgeInteractionInfo
    ) -> KnowledgeInteractionInfo:
        logger.debug(
            "Registering knowledge interaction '%s' for KB '%s' at %s.",
            ki.name,
            kb_id,
            self.ke_url,
        )
        response = await self._http.post(
            f"{self.ke_url}/sc/ki",
            json=ki.model_dump(by_alias=True),
            headers={"Knowledge-Base-Id": kb_id},
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        registered_ki = ki.model_copy(
            update={"id": response.json()["knowledgeInteractionId"]}
        )
        return registered_ki

    async def unregister_ki(self, kb_id: str, ki_id: str) -> None:
        logger.debug(
            "Unregistering knowledge interaction '%s' for KB '%s' at %s.",
            ki_id,
            kb_id,
            self.ke_url,
        )
        response = await self._http.delete(
            f"{self.ke_url}/sc/ki",
            headers={
                "Knowledge-Base-Id": kb_id,
                "Knowledge-Interaction-Id": ki_id,
            },
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

    async def renew_lease(self, kb_id: str) -> SmartConnectorLease:
        logger.debug("Renewing lease for KB '%s' at %s.", kb_id, self.ke_url)
        response = await self._http.put(
            f"{self.ke_url}/sc/lease/renew",
            headers={"Knowledge-Base-Id": kb_id},
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        return SmartConnectorLease.model_validate(response.json())

    async def load_domain_knowledge(self, kb_id: str, knowledge: str) -> None:
        logger.debug("Loading domain knowledge for KB '%s' at %s.", kb_id, self.ke_url)
        response = await self._http.post(
            f"{self.ke_url}/sc/knowledge",
            content=knowledge.encode("utf-8"),
            headers={
                "Knowledge-Base-Id": kb_id,
                "Content-Type": "text/plain; charset=UTF-8",
            },
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

    async def poll_ki_call(self, kb_id: str) -> tuple[PollResult, HandleRequest | None]:
        logger.debug("Polling for KI calls...")
        response = await self._http.get(
            f"{self.ke_url}/sc/handle",
            headers={"Knowledge-Base-Id": kb_id},
            # Set a longer timeout for this request due to the KE 30 second long-polling
            timeout=httpx.Timeout(35.0, connect=5.0),
        )

        if response.status_code == 200:
            logger.debug("Received 200 response, handling KI call.")
            return PollResult.HANDLE, HandleRequest.model_validate(response.json())
        elif response.status_code == 202:
            logger.debug("Received 202 response, no handling.")
            return PollResult.REPOLL, None
        elif response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        elif response.status_code == 410:
            logger.debug("Received 410 response, need to stop polling.")
            return PollResult.EXIT, None
        elif response.status_code == 500:
            logger.error(
                "Received 500 response from KE, indicating an internal server error. "
                "Will re-poll."
            )
            return PollResult.REPOLL, None
        else:
            raise UnexpectedHttpResponseError(response)

    async def post_handle_response(
        self, kb_id: str, ki_id: str, handle_request_id: int, binding_set: BindingSet
    ) -> None:
        logger.debug("Posting handle response for KI call.")
        response = await self._http.post(
            f"{self.ke_url}/sc/handle",
            json={
                "handleRequestId": handle_request_id,
                "bindingSet": binding_set,
            },
            headers={
                "Knowledge-Base-Id": kb_id,
                "Knowledge-Interaction-Id": ki_id,
            },
        )

        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

    async def post(
        self,
        kb_id: str,
        ki_id: str,
        binding_set: BindingSet,
        recipient_ids: list[str] | None = None,
    ) -> PostResult:
        if recipient_ids is not None:
            payload = {
                "bindingSet": binding_set,
                "recipientSelector": {
                    "knowledgeBases": recipient_ids,
                },
            }
        else:
            payload = binding_set

        response = await self._http.post(
            f"{self.ke_url}/sc/post",
            json=payload,
            headers={
                "Knowledge-Base-Id": kb_id,
                "Knowledge-Interaction-Id": ki_id,
            },
        )

        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        return PostResult.model_validate(response.json())

    async def ask(
        self,
        kb_id: str,
        ki_id: str,
        binding_set: BindingSet,
        recipient_ids: list[str] | None = None,
    ) -> AskResult:
        if recipient_ids is not None:
            payload = {
                "bindingSet": binding_set,
                "recipientSelector": {
                    "knowledgeBases": recipient_ids,
                },
            }
        else:
            payload = binding_set

        response = await self._http.post(
            f"{self.ke_url}/sc/ask",
            json=payload,
            headers={
                "Knowledge-Base-Id": kb_id,
                "Knowledge-Interaction-Id": ki_id,
            },
        )

        if not response.is_success:
            raise UnexpectedHttpResponseError(response)

        return AskResult.model_validate(response.json())

    async def close(self) -> None:
        await self._http.aclose()

    @property
    def ke_url(self) -> str:
        return self._ke_url
