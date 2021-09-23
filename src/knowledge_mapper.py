import requests
import logging as log
import time

from data_source import DataSource
from tke_client import TkeClient

MAX_CONNECTION_ATTEMPTS = 10
WAIT_BEFORE_RETRY = 1

class KnowledgeMapper:
    def __init__(self, data_source: DataSource, ke_url: str, kb_id: str, kb_name: str, kb_desc: str):
        self.data_source = data_source
        self.ke_url = ke_url
        self.kb_id = kb_id
        self.kis = dict()

        self.tke_client = TkeClient(ke_url, kb_id, kb_name, kb_desc)

        self.tke_client.register()


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

                # Have the data source handle the incoming bindings, and
                # retrieve the resulting bindings.
                result = self.data_source.handle(ki, handle_request['bindingSet'])

                # Post the bindings to the SC, with the correct KI ID and handle
                # request ID.
                self.tke_client.post_handle_response(handle_request['knowledgeInteractionId'], handle_request['handleRequestId'], result)
            else:
                raise Exception("Invalid internal status from KnowledgeMapper.long_poll!")

    def add_knowledge_interaction(self, ki):
        self.tke_client.add_knowledge_interaction(ki)
