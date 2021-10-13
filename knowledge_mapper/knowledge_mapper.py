import requests
import logging as log
import time

from .data_source import DataSource
from .tke_client import TkeClient
from _ast import If

MAX_CONNECTION_ATTEMPTS = 10
WAIT_BEFORE_RETRY = 1

class KnowledgeMapper:
    def __init__(self, data_source: DataSource, auth_enabled: bool, ke_url: str, kb_id: str, kb_name: str, kb_desc: str):
        self.data_source = data_source
        self.ke_url = ke_url
        self.kb_id = kb_id
        self.kis = dict()
        self.auth_enabled = auth_enabled

        self.tke_client = TkeClient(ke_url, kb_id, kb_name, kb_desc)

        self.tke_client.register()
        self.data_source.set_tke_client(self.tke_client)


    def start(self):
        while True:
            status, handle_request = self.tke_client.long_poll()

            if status == "repoll":
                continue
            elif status == "exit":
                break
            elif status == "handle":
                log.info('Handling handle request %d', handle_request['handleRequestId'])

                ki = self.tke_client.kis[handle_request['knowledgeInteractionId']]
                
                # For this implementation we assume that the knowledge mapper is responsible for authorisation
                # Check whether the requesting knowledge base is permitted to request the knowledge interaction
                permission = False
                if self.auth_enabled:
                    if 'permitted' in ki:
                        if ki['permitted'] != "*":
                            # check whether the requesting kb is in the permitted list
                            requesting_kb = handle_request['requestingKnowledgeBaseId']                        
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
                    result = self.data_source.handle(ki, handle_request['bindingSet'])
                else:
                    result = []
                                    
                # Post the bindings to the SC, with the correct KI ID and handle request ID.
                self.tke_client.post_handle_response(handle_request['knowledgeInteractionId'], handle_request['handleRequestId'], result)
            else:
                raise Exception("Invalid internal status from KnowledgeMapper.long_poll!")

    def add_knowledge_interaction(self, ki):
        self.tke_client.add_knowledge_interaction(ki)
