import logging
from typing import Protocol

import requests

from .errors import SmartConnectorNotFoundError, UnexpectedHttpResponseError
from .models import (
    AskAnswerInteractionInfo,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
)

logger = logging.getLogger(__name__)


class ClientProtocol(Protocol):
    def ke_is_available(self) -> bool: ...
    def ke_version(self) -> str: ...
    def get_knowledge_base(self, id: str) -> KnowledgeBaseInfo | None: ...
    def get_all_knowledge_bases(self) -> list[KnowledgeBaseInfo]: ...
    def register_kb(self, info: KnowledgeBaseInfo, reregister: bool = True) -> None: ...
    def unregister_kb(self, id: str) -> None: ...
    def get_knowledge_interactions(
        self, kb_id: str
    ) -> list[KnowledgeInteractionInfo]: ...
    def register_ki(
        self, kb_id: str, ki: KnowledgeInteractionInfo
    ) -> KnowledgeInteractionInfo: ...


class Client:
    def __init__(self, ke_url: str):
        self.ke_url = ke_url

    def ke_is_available(self) -> bool:
        try:
            _ = requests.get(f"{self.ke_url}/version")
            return True
        except requests.exceptions.RequestException:
            return False

    def ke_version(self) -> str:
        response = requests.get(f"{self.ke_url}/version")
        return response.json()["version"]

    def get_knowledge_base(self, id: str) -> KnowledgeBaseInfo | None:
        response = requests.get(f"{self.ke_url}/sc", headers={"Knowledge-Base-Id": id})
        if response.status_code == 404:
            return None
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        # KE returns a list with only one element here.
        return KnowledgeBaseInfo.model_validate(response.json()[0])

    def get_all_knowledge_bases(self) -> list[KnowledgeBaseInfo]:
        response = requests.get(f"{self.ke_url}/sc")
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        return [
            KnowledgeBaseInfo.model_validate(kb_json) for kb_json in response.json()
        ]

    def register_kb(self, info: KnowledgeBaseInfo, reregister: bool = True) -> None:
        if self.get_knowledge_base(info.id) is not None:
            if reregister:
                self.unregister_kb(info.id)
            else:
                return

        logger.debug("Registering knowledge base '%s' at %s.", info.id, self.ke_url)
        response = requests.post(
            f"{self.ke_url}/sc",
            json=info.model_dump(by_alias=True),
        )
        if not response.ok:
            raise UnexpectedHttpResponseError(response)
        return

    def unregister_kb(self, id: str) -> None:
        logger.debug("Unregistering knowledge base '%s' at %s.", id, self.ke_url)
        response = requests.delete(
            f"{self.ke_url}/sc", headers={"Knowledge-Base-Id": id}
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(id, self.ke_url)
        if not response.ok:
            raise UnexpectedHttpResponseError(response)
        return

    def get_knowledge_interactions(self, kb_id: str) -> list[KnowledgeInteractionInfo]:
        response = requests.get(
            f"{self.ke_url}/sc/ki",
            headers={"Knowledge-Base-Id": kb_id},
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        kis = []
        for kb_info in response.json():
            match kb_info["knowledgeInteractionType"]:
                case KiTypes.ASK | KiTypes.ANSWER:
                    kis.append(AskAnswerInteractionInfo.model_validate(kb_info))
                case KiTypes.POST | KiTypes.REACT:
                    kis.append(PostReactInteractionInfo.model_validate(kb_info))
        return kis

    def register_ki(
        self, kb_id: str, ki: KnowledgeInteractionInfo
    ) -> KnowledgeInteractionInfo:
        logger.debug(
            "Registering knowledge interaction '%s' for KB '%s' at %s.",
            ki.name,
            kb_id,
            self.ke_url,
        )
        response = requests.post(
            f"{self.ke_url}/sc/ki",
            json=ki.model_dump(by_alias=True),
            headers={"Knowledge-Base-Id": kb_id},
        )
        if response.status_code == 404:
            raise SmartConnectorNotFoundError(kb_id, self.ke_url)
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        registered_ki = ki.model_copy(
            update={"id": response.json()["knowledgeInteractionId"]}
        )
        return registered_ki
