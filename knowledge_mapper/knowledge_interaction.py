from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

import requests

from knowledge_mapper.tke_exceptions import UnexpectedHttpResponseError

ASK = 'AskKnowledgeInteraction'
ANSWER = 'AnswerKnowledgeInteraction'
POST = 'PostKnowledgeInteraction'
REACT = 'ReactKnowledgeInteraction'

@dataclass(kw_only=True)
class KnowledgeInteractionRegistrationRequest:
    prefixes: dict = field(default_factory=dict)
    type: str = None # This is defined in the concrete child classes.

@dataclass(kw_only=True)
class AskKnowledgeInteractionRegistrationRequest(KnowledgeInteractionRegistrationRequest):
    pattern: str
    type: str = ASK

@dataclass(kw_only=True)
class AnswerKnowledgeInteractionRegistrationRequest(KnowledgeInteractionRegistrationRequest):
    pattern: str
    type: str = ANSWER
    handler: Callable[[list[dict], str], list[dict]]

@dataclass(kw_only=True)
class PostKnowledgeInteractionRegistrationRequest(KnowledgeInteractionRegistrationRequest):
    argument_pattern: str
    result_pattern: str
    type: str = POST

@dataclass(kw_only=True)
class ReactKnowledgeInteractionRegistrationRequest(KnowledgeInteractionRegistrationRequest):
    argument_pattern: str
    result_pattern: str
    type: str = REACT
    handler: Callable[[list[dict], str], list[dict]]

class KnowledgeInteraction:
    def __init__(self, id: str, type: str, kb):
        self.id = id
        self.type = type
        self.kb = kb

    def from_req(req: KnowledgeInteractionRegistrationRequest, id: str, kb) -> KnowledgeInteraction:
        if isinstance(req, AskKnowledgeInteractionRegistrationRequest):
            return AskKnowledgeInteraction(req, id, kb)
        elif isinstance(req, AnswerKnowledgeInteractionRegistrationRequest):
            return AnswerKnowledgeInteraction(req, id, kb)
        elif isinstance(req, PostKnowledgeInteractionRegistrationRequest):
            return PostKnowledgeInteraction(req, id, kb)
        elif isinstance(req, ReactKnowledgeInteractionRegistrationRequest):
            return ReactKnowledgeInteraction(req, id, kb)
        else:
            raise Exception('`req` must be a concrete knowledge interaction object')


class AskKnowledgeInteraction(KnowledgeInteraction):
    def __init__(self, req: AskKnowledgeInteractionRegistrationRequest, id: str, kb):
        super().__init__(id, req.type, kb)
        self.pattern = req.pattern
        self.prefixes = req.prefixes

    def ask(self, bindings: dict) -> dict:
        response = requests.post(
            f'{self.kb.ke_url}/sc/ask',
            json=bindings,
            headers={
                'Knowledge-Base-Id': self.kb.id,
                'Knowledge-Interaction-Id': self.id,
            }
        )
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        return response.json()


class AnswerKnowledgeInteraction(KnowledgeInteraction):
    def __init__(self, req: AnswerKnowledgeInteractionRegistrationRequest, id: str, kb):
        super().__init__(id, req.type, kb)
        self.pattern = req.pattern
        self.prefixes = req.prefixes
        self.handler = req.handler

    def answer(self, bindings: list[dict], requesting_kb_id: str) -> list[dict]:
        return self.handler(bindings, requesting_kb_id)


class PostKnowledgeInteraction(KnowledgeInteraction):
    def __init__(self, req: PostKnowledgeInteractionRegistrationRequest, id: str, kb):
        super().__init__(id, req.type, kb)
        self.argument_pattern = req.argument_pattern
        self.result_pattern = req.result_pattern
        self.prefixes = req.prefixes

    def post(self, bindings: list[dict]) -> list[dict]:
        response = requests.post(
            f'{self.kb.ke_url}/sc/post',
            json=bindings,
            headers={
                'Knowledge-Base-Id': self.kb.id,
                'Knowledge-Interaction-Id': self.id,
            }
        )
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        return response.json()


class ReactKnowledgeInteraction(KnowledgeInteraction):
    def __init__(self, req: ReactKnowledgeInteractionRegistrationRequest, id: str, kb):
        super().__init__(id, req.type, kb)
        self.argument_pattern = req.argument_pattern
        self.result_pattern = req.result_pattern
        self.prefixes = req.prefixes
        self.handler = req.handler

    def react(self, bindings: list[dict], requesting_kb_id: str) -> list[dict]:
        return self.handler(bindings, requesting_kb_id)
