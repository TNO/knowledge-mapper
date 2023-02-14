import logging
import time
import os
import requests

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
        logger.debug(kbs)
        if kbs:
            kb = kbs[0]
        else:
            logger.info(f"waiting for user to register knowledge base")
            time.sleep(2)
    logger.info(f"found knowledge base with ID {kb['id_url']}")
