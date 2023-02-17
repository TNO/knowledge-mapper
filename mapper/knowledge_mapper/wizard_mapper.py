import logging
import time
import os
import requests

from knowledge_mapper.knowledge_base import (
    KnowledgeBaseUnregistered,
    KnowledgeEngineTerminated,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def start():
    time.sleep(5)
    km_api = os.environ.get("KM_API")
    if km_api is None:
        logger.error("environment variable KM_API is required when using --wizard")
        exit(1)
    else:
        logger.info(f"using KM_API {km_api}")

    have_kb = False
    kb = None
    while kb is None:
        resp = requests.get(f"{km_api}/knowledge-bases")
        assert resp.ok
        kbs = resp.json()["data"]
        assert len(kbs) <= 2
        if kbs:
            kb = kbs[0]
        else:
            logger.info(f"waiting for user to register knowledge base")
            time.sleep(2)
    logger.info(f"found knowledge base with ID {kb['id_url']}")

    while True:
        k_req = wait_for_knowledge_request(kb["id_url"])

    # TODO wait for a KI to be registered, and open a long poll loop


def wait_for_knowledge_request(kb_id):
    ke_api = os.environ.get("KE_API")

    while True:
        response = requests.get(
            f"{ke_api}/sc/handle", headers={"Knowledge-Base-Id": kb_id}
        )
        if response.status_code == 202:
            logger.debug("repolling...")
            continue
        elif response.status_code == 500:
            logger.error(response.text)
            logger.error("TKE had an internal server error. Reinitiating long poll.")
            continue
        elif response.status_code == 410:
            logger.warning("The Knowledge Engine REST server terminated!")
            raise KnowledgeEngineTerminated()
        elif response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning("Our Knowledge Base has been unregistered!")
            raise KnowledgeBaseUnregistered()
        else:
            logger.warning(
                f"long_poll received unexpected status {response.status_code}"
            )
            logger.warning(response.text)
            logger.warning("repolling anyway..")
            continue
