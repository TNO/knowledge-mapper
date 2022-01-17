from functools import partial
import logging as log

from knowledge_mapper.knowledge_base import KnowledgeBaseRegistrationRequest
from knowledge_mapper.knowledge_interaction import AnswerKnowledgeInteractionRegistrationRequest, AskKnowledgeInteractionRegistrationRequest, PostKnowledgeInteractionRegistrationRequest, ReactKnowledgeInteractionRegistrationRequest

from .data_source import DataSource
from .tke_client import TkeClient

WAIT_BEFORE_RETRY = 1

class KnowledgeMapper:
    def __init__(self, data_source: DataSource, auth_enabled: bool, ke_url: str, kb_id: str, kb_name: str, kb_desc: str):
        self.data_source = data_source
        self.ke_url = ke_url
        self.kb_id = kb_id
        self.kis = dict()
        self.auth_enabled = auth_enabled

        self.tke_client = TkeClient(ke_url)
        self.tke_client.connect()

        self.kb = self.tke_client.register(KnowledgeBaseRegistrationRequest(id=kb_id, name=kb_name, description=kb_desc))
        self.data_source.set_knowledge_base(self.kb)


    def start(self):
        self.kb.start_handle_loop()
    
    def clean_up(self):
        self.kb.unregister()

    def handle(self, ki, bindings: list[dict], requesting_kb: str):
        # For this implementation we assume that the knowledge mapper is responsible for authorisation
        # Check whether the requesting knowledge base is permitted to request the knowledge interaction
        permission = False
        if self.auth_enabled:
            if 'permitted' in ki:
                if ki['permitted'] != "*":
                    # check whether the requesting kb is in the permitted list                      
                    if requesting_kb in ki['permitted']:
                        permission = True
                    else:
                        log.info('Knowledge base %s is not permitted to do this request!', requesting_kb)
                else: # permission is set to *, so every one is permitted
                    permission = True
            else: # no permission is set, so deny
                log.info('No permission is set at all for this knowledge interaction %s, so deny!', ki)
        else: # no authorization is defined so, have the data source handle the request.
            permission = True
            
        # if permitted, then handle the request
        if permission:
            result = self.data_source.handle(ki, bindings)
        else:
            result = []
        return result

    def add_knowledge_interaction(self, ki):
        if ki['type'] == 'ask':
            req = AskKnowledgeInteractionRegistrationRequest(pattern=ki['pattern'])
        elif ki['type'] == 'answer':
            req = AnswerKnowledgeInteractionRegistrationRequest(pattern=ki['pattern'], handler=partial(self.handle, ki))
        elif ki['type'] == 'post':
            req = PostKnowledgeInteractionRegistrationRequest(argument_pattern=ki['argument_pattern'], result_pattern=ki['result_pattern'])
        elif ki['type'] == 'react':
            req = ReactKnowledgeInteractionRegistrationRequest(argument_pattern=ki['argument_pattern'], result_pattern=ki['result_pattern'], handler=partial(self.handle, ki))
        else:
            raise Exception(f"Invalid KI type: {ki['type']}")

        if 'prefixes' in ki:
            req.prefixes = ki['prefixes']

        if 'name' in ki:
            name = ki['name']
        else:
            name = None

        self.kb.register_knowledge_interaction(req, name=name)
