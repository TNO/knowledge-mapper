from time import sleep
import os
import json
from knowledge_mapper.knowledge_interaction import (
    AskKnowledgeInteraction,
    AskKnowledgeInteractionRegistrationRequest,
)
from knowledge_mapper.tke_client import TkeClient
from knowledge_mapper.knowledge_base import KnowledgeBaseRegistrationRequest


def print_tree(tree):
    print(f'\t - Tree {tree["name"]} has height {tree["height"]}', flush=True)


KE_API = os.environ.get("KE_API")
KB_ID = os.environ.get("KB_ID")
KB_NAME = os.environ.get("KB_NAME")
KB_DESCRIPTION = os.environ.get("KB_DESCRIPTION")
GRAPH_PATTERN = os.environ.get("GRAPH_PATTERN")
GRAPH_PATTERN_PREFIXES = os.environ.get("GRAPH_PATTERN_PREFIXES")

if __name__ == "__main__":
    client = TkeClient(KE_API)
    client.connect()

    kb = client.register(
        KnowledgeBaseRegistrationRequest(
            id=KB_ID,
            name=KB_NAME,
            description=KB_DESCRIPTION,
        )
    )

    ki: AskKnowledgeInteraction = kb.register_knowledge_interaction(
        AskKnowledgeInteractionRegistrationRequest(
            pattern=GRAPH_PATTERN, prefixes=json.loads(GRAPH_PATTERN_PREFIXES)
        )
    )

    while True:
        print("Asking for all data...", flush=True)
        bindings = ki.ask([])["bindingSet"]

        print(f"There are {len(bindings)} trees:")
        for tree in bindings:
            print_tree(tree)
        sleep(4)

    kb.unregister()
