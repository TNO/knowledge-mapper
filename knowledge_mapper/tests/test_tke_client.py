import requests
from ..tke_client import TkeClient
import pytest
import asyncio

@pytest.mark.asyncio
async def test_ask_answer():

    kb1 = 'http://example.org/kb1'
    kb2 = 'http://example.org/kb2'

    answer_ki_registered = asyncio.Event()

    async def task_1():
        client_1 = TkeClient('http://localhost:8280/rest', kb1, 'KB 1', 'Knowledge Base 1')
        client_1.register()
        ask_ki = client_1.add_ask_knowledge_interaction({
            'pattern': '?a ex:likes ?b',
            'prefixes': {
                'ex': 'http://example.org/'
            },
        })
        print('waiting for answer KI to finish registering')
        await answer_ki_registered.wait()
        print('asking for likes...')
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, client_1.ask, ask_ki, [])
        bindings = result['bindingSet']
        assert len(bindings) == 1
        assert bindings[0]['a'] == '<han>'
        assert bindings[0]['b'] == '"coffee"'

    async def task_2():
        client_2 = TkeClient('http://localhost:8280/rest', kb2, 'KB 2', 'Knowledge Base 2')
        client_2.register()
        answer_ki = client_2.add_answer_knowledge_interaction({
            'pattern': '?a ex:likes ?b',
            'prefixes': {
                'ex': 'http://example.org/'
            },
        })
        answer_ki_registered.set()
        loop = asyncio.get_event_loop()
        status, handle_request = await loop.run_in_executor(None, client_2.long_poll)
        assert status == 'handle'
        assert len(handle_request['bindingSet']) == 0
        assert handle_request['requestingKnowledgeBaseId'] == kb1
        await loop.run_in_executor(None, client_2.post_handle_response, answer_ki, handle_request['handleRequestId'], [{'a': '<han>', 'b': '"coffee"'}])


    await asyncio.gather(task_1(), task_2())
