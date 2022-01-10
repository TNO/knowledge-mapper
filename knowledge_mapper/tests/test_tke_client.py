from ..tke_client import TkeClient
import pytest
import asyncio

from uuid import uuid4


ke_runtime_url = 'http://localhost:8280/rest'


def generate_kb_id_and_name(prefix='https://example.org/'):
    random_characters = uuid4().hex
    return (f'{prefix}{random_characters}', random_characters)


@pytest.mark.asyncio
async def test_ask_answer():

    kb1_id, kb1_name = generate_kb_id_and_name()
    kb2_id, kb2_name = generate_kb_id_and_name()

    answer_ki_registered = asyncio.Event()

    # Next up are two coroutines that have to run asynchronously, because they
    # interact with eachother via the KE.

    async def kb1_task():
        client_1 = TkeClient(ke_runtime_url, kb1_id, kb1_name, 'KB 1')
        client_1.register()
        ask_ki = client_1.add_ask_knowledge_interaction({
            'pattern': '?a ex:likes ?b',
            'prefixes': {
                'ex': 'http://example.org/'
            },
        })

        # Wait for the other KI to tell us that it has been registered.
        await answer_ki_registered.wait()

        # Trigger the knowledge interaction on the default executor.
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client_1.ask(ask_ki, [])
        )

        # Assert some things
        bindings = result['bindingSet']
        assert len(bindings) == 1
        assert bindings[0]['a'] == '<han>'
        assert bindings[0]['b'] == '"coffee"'

        client_1.clean_up()

    async def kb2_task():
        client_2 = TkeClient(ke_runtime_url, kb2_id, kb2_name, 'KB 2')
        client_2.register()
        answer_ki = client_2.add_answer_knowledge_interaction({
            'pattern': '?c ex:likes ?d',
            'prefixes': {
                'ex': 'http://example.org/'
            },
        })

        # Signal that the ANSWER KI has been registered to the other task in
        # this test.
        answer_ki_registered.set()

        # Make this knowledge base's client listen long poll for incoming
        # knowledge requests.
        status, handle_request = await asyncio.get_event_loop()\
            .run_in_executor(None, lambda: client_2.long_poll())

        # Assert some things about the incoming request.
        assert status == 'handle'
        assert len(handle_request['bindingSet']) == 0
        assert handle_request['requestingKnowledgeBaseId'] == kb1_id

        # Send the response to the knowledge request
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client_2.post_handle_response(
                answer_ki,
                handle_request['handleRequestId'],
                [{'c': '<han>', 'd': '"coffee"'}]
            )
        )

        client_2.clean_up()

    # Wait for both tasks to complete. (They are scheduled not sequentially, but
    # asynchronously.)
    await asyncio.gather(kb1_task(), kb2_task())
