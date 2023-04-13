from functools import partial
import logging as log
from knowledge_mapper.auth.base_auth import BaseAuth
from knowledge_mapper.utils import extract_variables
from knowledge_mapper.knowledge_base import (
    KnowledgeBaseRegistrationRequest,
)
from knowledge_mapper.knowledge_interaction import (
    AnswerKnowledgeInteractionRegistrationRequest,
    AskKnowledgeInteractionRegistrationRequest,
    PostKnowledgeInteractionRegistrationRequest,
    ReactKnowledgeInteractionRegistrationRequest,
)

from .data_source import DataSource
from .tke_client import TkeClient

WAIT_BEFORE_RETRY = 1


class KnowledgeMapper:
    def __init__(
        self,
        data_source: DataSource,
        authorization: BaseAuth,
        ke_url: str,
        kb_id: str,
        kb_name: str,
        kb_desc: str,
    ):
        self.data_source = data_source
        self.ke_url = ke_url
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.kb_desc = kb_desc
        self.kis = dict()

        self.tke_client = TkeClient(ke_url)
        self.tke_client.connect()

        self.kb = self.tke_client.register(
            KnowledgeBaseRegistrationRequest(
                id=kb_id, name=kb_name, description=kb_desc
            )
        )
        self.data_source.set_knowledge_base(self.kb)

        self.authorization = authorization

    def start(self):
        self.kb.start_handle_loop()

    def clean_up(self):
        self.kb.unregister()

    def reregister(self):
        self.kb = self.tke_client.register(
            KnowledgeBaseRegistrationRequest(
                id=self.kb_id, name=self.kb_name, description=self.kb_desc
            )
        )

    def handle(self, ki, bindings: list[dict], requesting_kb: str):
        # For this implementation we assume that the knowledge mapper is responsible for authorisation
        # Check whether the requesting knowledge base is permitted to request the knowledge interaction
        if self.authorization is not None:
            permission = self.authorization.has_permission(requesting_kb, ki)
        else:  # no authorization is defined so, have the data source handle the request.
            permission = True

        # if permitted, then handle the request
        if permission:
            try:
                result = self.data_source.handle(ki, bindings, requesting_kb)
            except Exception:
                log.exception(
                    "an exception occurred while the data source was handling a knowledge request"
                )
                result = []
        else:
            result = []
        return result

    def add_knowledge_interaction(self, ki):
        if "prefixes" in ki:
            prefixes = ki["prefixes"]
        else:
            prefixes = dict()

        if ki["type"] == "ask":
            req = AskKnowledgeInteractionRegistrationRequest(pattern=ki["pattern"])
            if "vars" not in ki:
                ki["vars"] = extract_variables(ki["pattern"], prefixes=prefixes)
        elif ki["type"] == "answer":
            req = AnswerKnowledgeInteractionRegistrationRequest(
                pattern=ki["pattern"], handler=partial(self.handle, ki)
            )
            if "vars" not in ki:
                ki["vars"] = extract_variables(ki["pattern"], prefixes=prefixes)
        elif ki["type"] == "post":
            req = PostKnowledgeInteractionRegistrationRequest(
                argument_pattern=ki["argument_pattern"],
                result_pattern=ki["result_pattern"],
            )
            if "vars" not in ki:
                ki["vars"] = extract_variables(
                    ki["argument_pattern"], prefixes=prefixes
                )
        elif ki["type"] == "react":
            req = ReactKnowledgeInteractionRegistrationRequest(
                argument_pattern=ki["argument_pattern"],
                result_pattern=ki["result_pattern"],
                handler=partial(self.handle, ki),
            )
            if "vars" not in ki:
                ki["vars"] = extract_variables(
                    ki["argument_pattern"], prefixes=prefixes
                )
        else:
            raise Exception(f"Invalid KI type: {ki['type']}")

        req.prefixes = prefixes

        if "name" not in ki:
            ki["name"] = None
        name = ki["name"]

        registered_ki = self.kb.register_knowledge_interaction(req, name=name)
        ki["id"] = registered_ki.id

        # The authorization object needs to be made aware of the new knowledge
        # interaction
        if self.authorization is not None:
            self.authorization.add_knowledge_interaction(ki)
