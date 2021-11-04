import requests
import logging as log
import time

MAX_CONNECTION_ATTEMPTS = 10
WAIT_BEFORE_RETRY = 1

class TkeClient:
    def __init__(self, ke_url: str, kb_id: str, kb_name: str, kb_desc: str):
        self.ke_url = ke_url
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.kb_desc = kb_desc

        self.kis = dict()
    
    def register(self):
        attempts = 0
        success = False
        while not success:
            try:
                attempts += 1
                response = requests.post(
                    f'{self.ke_url}/sc',
                    json={
                        'knowledgeBaseId': self.kb_id,
                        'knowledgeBaseName': self.kb_name,
                        'knowledgeBaseDescription': self.kb_desc
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
            return self.add_answer_knowledge_interaction(ki)
        elif ki['type'] == 'react':
            return self.add_react_knowledge_interaction(ki)
        elif ki['type'] == 'ask':
            return self.add_ask_knowledge_interaction(ki)
        elif ki['type'] == 'post':
            return self.add_post_knowledge_interaction(ki)


    def get_ki(self, name=None, id=None):
        if name is not None and id is None:
            for ki in self.kis.values():
                if ki['name'] == name:
                    return ki
        if id is not None and name is None:
            if id in self.kis:
                return self.kis[id]

    
    def add_ask_knowledge_interaction(self, ki):
        body = {
            'knowledgeInteractionType': 'AskKnowledgeInteraction',
            'graphPattern': ki['pattern']
        }

        if 'prefixes' in ki:
            body['prefixes'] = ki['prefixes']

        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json=body,
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = ki
        ki['id'] = ki_id
        return ki_id


    def add_answer_knowledge_interaction(self, ki):
        body = {
            'knowledgeInteractionType': 'AnswerKnowledgeInteraction',
            'graphPattern': ki['pattern']
        }

        if 'prefixes' in ki:
            body['prefixes'] = ki['prefixes']

        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json=body,
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = ki
        ki['id'] = ki_id
        return ki_id


    def add_post_knowledge_interaction(self, ki):
        body = {
            'knowledgeInteractionType': 'PostKnowledgeInteraction',
            'argumentGraphPattern': ki['argument_pattern'],
            'resultGraphPattern': ki['result_pattern']
        }

        if 'prefixes' in ki:
            body['prefixes'] = ki['prefixes']

        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json=body,
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = ki
        ki['id'] = ki_id
        return ki_id


    def add_react_knowledge_interaction(self, ki):
        body = {
            'knowledgeInteractionType': 'ReactKnowledgeInteraction',
            'argumentGraphPattern': ki['argument_pattern'],
            'resultGraphPattern': ki['result_pattern']
        }

        if 'prefixes' in ki:
            body['prefixes'] = ki['prefixes']

        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json=body,
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = ki
        ki['id'] = ki_id
        return ki_id


    def ask(self, ki_id, bindings):
        response = requests.post(
            f'{self.ke_url}/sc/ask',
            json=bindings,
            headers={
                'Knowledge-Base-Id': self.kb_id,
                'Knowledge-Interaction-Id': ki_id,
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Asking to smart connector failed.')

        return response.json()


    def post(self, ki_id, bindings):
        response = requests.post(
            f'{self.ke_url}/sc/ask',
            json=bindings,
            headers={
                'Knowledge-Base-Id': self.kb_id,
                'Knowledge-Interaction-Id': ki_id,
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Posting to smart connector failed.')

        return response.json()


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
        else:
            log.warn(f'long_poll received unexpected status {response.status_code}')
            log.warn(response.text)
            log.warn('retrying anyway..')
            return "repoll", None


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
