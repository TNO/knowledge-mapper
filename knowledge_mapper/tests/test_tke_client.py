import knowledge_mapper.knowledge_base as tke_kb
import knowledge_mapper.knowledge_interaction as tke_ki
import knowledge_mapper.tke_client as tke
import pytest
import asyncio
import requests
from os import environ

from uuid import uuid4

if 'KE_RUNTIME_URL' in environ:
    ke_runtime_url = environ['KE_RUNTIME_URL']
else:
    ke_runtime_url = 'http://localhost:8280/rest'

print(f'Using KE runtime at {ke_runtime_url} for tests.')

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
        client_1 = tke.TkeClient(ke_runtime_url)
        client_1.connect()
        kb1 = client_1.register(tke_kb.KnowledgeBaseRegistrationRequest(id=kb1_id, name=kb1_name, description="KB 1"))

        ki_name = 'things-that-like-other-things'
        ask_ki: tke_ki.AskKnowledgeInteraction = kb1.register_knowledge_interaction(tke_ki.AskKnowledgeInteractionRegistrationRequest(prefixes={'ex': 'http://example.org/'}, pattern='?a ex:likes ?b'), ki_name)

        # Make sure that the KIs name is in the KI's ID.
        assert(kb1.id + '/interaction/' + ki_name in requests.get(
            ke_runtime_url + '/sc/ki',
            headers = {
                'Knowledge-Base-Id': kb1.id
            }
        ).text)

        # Wait for the other KI to tell us that it has been registered.
        await answer_ki_registered.wait()

        # Trigger the knowledge interaction on the default executor.
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ask_ki.ask([])
        )

        # Assert some things
        bindings = result['bindingSet']
        assert len(bindings) == 1
        assert bindings[0]['a'] == '<han>'
        assert bindings[0]['b'] == '"coffee"'

        kb1.unregister()

    async def kb2_task():
        client_2 = tke.TkeClient(ke_runtime_url)
        client_2.connect()
        kb2 = client_2.register(tke_kb.KnowledgeBaseRegistrationRequest(id=kb2_id, name=kb2_name, description="KB 2"))

        def handler(bindings: dict, requesting_kb_id: str) -> dict:
            assert len(bindings) == 0
            assert requesting_kb_id == kb1_id
            return [{'c': '<han>', 'd': '"coffee"'}]

        kb2.register_knowledge_interaction(
            tke_ki.AnswerKnowledgeInteractionRegistrationRequest(
                prefixes={'ex': 'http://example.org/'},
                pattern='?c ex:likes ?d',
                handler=handler
            ),
        )

        # Signal that the ANSWER KI has been registered to the other task in
        # this test.
        answer_ki_registered.set()

        # Make this knowledge base's client long poll for 1 incoming knowledge
        # request.
        await asyncio.get_event_loop()\
            .run_in_executor(None, lambda: kb2.start_handle_loop(1))

        kb2.unregister()

    # Wait for both tasks to complete. (They are scheduled not sequentially, but
    # asynchronously.)
    await asyncio.gather(kb1_task(), kb2_task())

def test_reregister():
    kb_id, kb_name = generate_kb_id_and_name()
    client = tke.TkeClient(ke_runtime_url)
    client.connect()

    kb1 = client.register(tke_kb.KnowledgeBaseRegistrationRequest(id=kb_id, name=kb_name, description="KB that will be reregistered"))
    assert kb1 is not None

    # Try to register with the same id, and the reregister flag turned OFF
    kb2 = client.register(tke_kb.KnowledgeBaseRegistrationRequest(id=kb_id, name=kb_name, description="KB that will be reregistered"), reregister=False)
    assert kb2 is None

    # Try to register with the same id, and the reregister flag turned ON
    kb3 = client.register(tke_kb.KnowledgeBaseRegistrationRequest(id=kb_id, name=kb_name, description="KB that will be reregistered"), reregister=True)
    assert kb3 is not None

    # We only have to clean up the final one since it uses the same ID
    kb3.unregister()
