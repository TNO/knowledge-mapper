from time import sleep
from knowledge_mapper.knowledge_interaction import AskKnowledgeInteraction, AskKnowledgeInteractionRegistrationRequest
from knowledge_mapper.tke_client import TkeClient
from knowledge_mapper.knowledge_base import KnowledgeBaseRegistrationRequest

def print_tree(tree):
    print(f'\t - Tree {tree["name"]} has height {tree["height"]}', flush=True)

if __name__ == '__main__':
    client = TkeClient('http://tke-runtime:8280/rest')
    client.connect()

    kb = client.register(KnowledgeBaseRegistrationRequest(id='https://example.org/tree-printer', name='Tree Printer', description="This knowledge base prints trees."))

    ki: AskKnowledgeInteraction = kb.register_knowledge_interaction(AskKnowledgeInteractionRegistrationRequest(pattern='?tree <https://example.org/hasHeight> ?height . ?tree <https://example.org/hasName> ?name .'))

    while True:
        print('Asking for all trees...', flush=True)
        trees = ki.ask([])['bindingSet']

        print(f'There are {len(trees)} trees:')
        for tree in trees:
            print_tree(tree)

        if len(trees) < 5:
            print(f'Haven\'t found all trees yet. Retrying in 5 seconds...', flush=True)
            if (len(trees) == 4):
                print(f'(do you still need to give access at http://localhost:8080/?server=auth-db&username=user&db=knowledge_mapper_db&select=policies ?)', flush=True)
            sleep(5)
            continue
        else:
            print(f'Found all {len(trees)} trees! Bye.')
            break

    kb.unregister()
