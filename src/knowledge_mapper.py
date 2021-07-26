import requests
import logging as log
import time

from data_sources import DataSource

MAX_CONNECTION_ATTEMPTS = 10
WAIT_BEFORE_RETRY = 1

class KnowledgeMapper:
    def __init__(self, data_source: DataSource, ke_url: str, kb_id: str, kb_name: str, kb_desc: str):
        self.data_source = data_source
        self.ke_url = ke_url
        self.kb_id = kb_id
        self.kis = dict()

        attempts = 0
        success = False
        while not success:
            try:
                attempts += 1
                response = requests.post(
                    f'{self.ke_url}/sc',
                    json={
                        'knowledgeBaseId': kb_id,
                        'knowledgeBaseName': kb_name,
                        'knowledgeBaseDescription': kb_desc
                    }
                )
                if response.ok:
                    success = True
                else:
                    log.error('%s', response.text)
            except requests.exceptions.ConnectionError:
                log.warning(f'Connecting to {self.ke_url} failed.')

            if not success and attempts < MAX_CONNECTION_ATTEMPTS:
                log.warning(f'Request to {self.ke_url} failed. Retrying in {WAIT_BEFORE_RETRY} s.')
                time.sleep(WAIT_BEFORE_RETRY)
            elif not success:
                raise Exception(f'Request to {self.ke_url} failed. Gave up after {attempts} attempts.')
        log.info(f'Successfully registered knowledge base {self.kb_id}')


    def add_knowledge_interaction(self, ki):
        if ki['type'] == 'answer':
            self.add_answer_knowledge_interaction(ki)
        elif ki['type'] == 'react':
            self.add_react_knowledge_interaction(ki)


    def add_answer_knowledge_interaction(self, ki):
        pattern = ki['pattern']
        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json={
                'knowledgeInteractionType': 'AnswerKnowledgeInteraction',
                'graphPattern': pattern
            },
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = ki


    def add_react_knowledge_interaction(self, ki):
        argument_pattern = ki['argument_pattern']
        result_pattern = ki['result_pattern']

        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json={
                'knowledgeInteractionType': 'ReactKnowledgeInteraction',
                'argumentGraphPattern': argument_pattern,
                'resultGraphPattern': result_pattern
            },
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = ki


    def start(self):
        while True:
            status, handle_request = self.long_poll()

            if status == "repoll":
                continue
            elif status == "exit":
                break
            elif status == "handle":
                log.info('Handling handle request %d', handle_request['handleRequestId'])

                ki = self.kis[handle_request['knowledgeInteractionId']]

                # Have the data source handle the incoming bindings, and
                # retrieve the resulting bindings.
                result = self.data_source.handle(ki, handle_request['bindingSet'])

                # Post the bindings to the SC, with the correct KI ID and handle
                # request ID.
                self.post_handle_response(handle_request['knowledgeInteractionId'], handle_request['handleRequestId'], result)
            else:
                raise Exception("Invalid internal status from KnowledgeMapper.long_poll!")


    def long_poll(self):
        log.info('Waiting for response to long poll...')
        response = requests.get(f'{self.ke_url}/sc/handle', headers = {'Knowledge-Base-Id': self.kb_id})
        if response.status_code == 202:
            log.info('Received 202.')
            return "repoll", None
        elif response.status_code == 500:
            log.error(response.text)
            log.error('TKE had an internal server error. Reinitiating long poll.')
            return "repoll", None
        elif response.status_code == 410:
            log.info('Received 410! Exiting.')
            return "exit", None
        elif response.status_code == 200:
            log.info('Received 200')
            return "handle", response.json()


    def post_handle_response(self, ki_id, handle_id, bindings):
        log.info(f'Posting response to %d', handle_id)
        response = requests.post(f'{self.ke_url}/sc/handle',
            json={
                'handleRequestId': handle_id,
                'bindingSet': bindings,
            },
            headers={
                'Knowledge-Base-Id': self.kb_id,
                'Knowledge-Interaction-Id': ki_id,
            }
        )
        if not response.ok:
            log.warn(response.text)
            log.warn('Posting a handle response failed. Ignoring it.')


    def clean_up(self):
        response = requests.delete(f'{self.ke_url}/sc', headers={'Knowledge-Base-Id': self.kb_id})
        if not response.ok:
            raise CleanUpFailedError('Deletion of knowledge base failed: {}'.format(response.text))
        else:
            log.info('Knowledge base successfully deleted.')


class CleanUpFailedError(RuntimeError):
    pass
