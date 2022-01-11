import requests
import logging as log
import time

import knowledge_mapper.knowledge_base as knowledge_base

from knowledge_mapper.tke_exceptions import UnexpectedHttpResponseError

MAX_CONNECTION_ATTEMPTS = 10
WAIT_BEFORE_RETRY = 1

class TkeClient:
    def __init__(self, ke_url: str):
        self.ke_url = ke_url


    def connect(self):
        attempts = 0
        success = False
        while not success:
            try:
                attempts += 1
                self.get_knowledge_bases()
                success = True
            except requests.exceptions.ConnectionError:
                log.warning(f'Connecting to {self.ke_url} failed.')

            if not success and attempts < MAX_CONNECTION_ATTEMPTS:
                log.warning(f'Request to {self.ke_url} failed. Retrying in {WAIT_BEFORE_RETRY} s.')
                time.sleep(WAIT_BEFORE_RETRY)
            elif not success:
                raise Exception(f'Request to {self.ke_url} failed. Gave up after {attempts} attempts.')
        log.info(f'Succesfully connected to {self.ke_url}.')


    def get_knowledge_bases(self) -> list[knowledge_base.KnowledgeBase]:
        response = requests.get(f'{self.ke_url}/sc')

        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        return [knowledge_base.KnowledgeBase.from_json(kb_data) for kb_data in response.json()]

    def get_knowledge_base(self, kb_id: str) -> knowledge_base.KnowledgeBase | None:
        response = requests.get(
            f'{self.ke_url}/sc',
            headers={
                'Knowledge-Base-Id': kb_id
            }
        )

        if response.status_code == 404:
            return None
        elif not response.ok:
            raise UnexpectedHttpResponseError(response)

        return [knowledge_base.KnowledgeBase.from_json(kb_data) for kb_data in response.json()]


    def register(self, req: knowledge_base.KnowledgeBaseRegistrationRequest, reregister=False) -> knowledge_base.KnowledgeBase:
        if reregister:
            already_existing = self.get_knowledge_base(req.id)
            if already_existing is not None:
                already_existing.unregister()
        response = requests.post(
            f'{self.ke_url}/sc',
            json={
                'knowledgeBaseId': req.id,
                'knowledgeBaseName': req.name,
                'knowledgeBaseDescription': req.description
            }
        )
        if not response.ok:
            raise UnexpectedHttpResponseError(response)

        return knowledge_base.KnowledgeBase(req, ke_url=self.ke_url)


class CleanUpFailedError(RuntimeError):
    pass
