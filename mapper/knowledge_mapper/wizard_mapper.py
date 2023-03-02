import logging
import time
import os
import requests

from knowledge_mapper.knowledge_base import (
    KnowledgeEngineTerminated,
)
from knowledge_mapper.utils import match_bindings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class KnowledgeBaseNotFoundInApi(Exception):
    pass


class ApiNotReachable(Exception):
    pass


def start():
    ke_endpoint = os.environ.get("KE_ENDPOINT")
    time.sleep(5)
    km_api = os.environ.get("KM_API")
    if km_api is None:
        logger.error("environment variable KM_API is required when using --wizard")
        exit(1)
    else:
        logger.info(f"using KM_API {km_api}")

    have_kb = False
    kb = None
    while True:
        while kb is None:
            try:
                resp = requests.get(f"{km_api}/knowledge-bases")
            except:
                logger.warning(f"KM API cannot be reached. Retrying in 2 seconds.")
                time.sleep(2)
                continue
            assert resp.ok
            kbs = resp.json()["data"]
            assert len(kbs) <= 2
            if kbs:
                kb = kbs[0]
            else:
                logger.info(f"waiting for user to register knowledge base")
                time.sleep(2)
        logger.info(f"found knowledge base with ID {kb['id']}")

        kb_disappeared_from_api = False
        while not kb_disappeared_from_api:
            k_req = wait_for_knowledge_request(kb["id_url"])
            logger.debug(f"received knowledge request: {k_req}")
            ki_id = k_req["knowledgeInteractionId"]
            handle_id = k_req["handleRequestId"]
            binding_set = k_req["bindingSet"]
            requesting_kb_id = k_req["requestingKnowledgeBaseId"]

            try:
                result_binding_set = map_knowledge_request(
                    kb["id"], ki_id, binding_set, requesting_kb_id
                )
            except KnowledgeBaseNotFoundInApi:
                result_binding_set = []
                kb_disappeared_from_api = True
            except:
                logger.exception("something went wrong while mapping knowledge request")
                result_binding_set = []

            post_response(kb["id_url"], ki_id, handle_id, result_binding_set)

        if kb_disappeared_from_api:
            response = requests.delete(
                f"{ke_endpoint}/sc", headers={"Knowledge-Base-Id": kb["id_url"]}
            )
            assert response.ok
            kb = None


def wait_for_knowledge_request(kb_id):
    ke_endpoint = os.environ.get("KE_ENDPOINT")

    while True:
        response = requests.get(
            f"{ke_endpoint}/sc/handle", headers={"Knowledge-Base-Id": kb_id}
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            logger.debug("repolling...")
            continue
        elif response.status_code == 404:
            logger.warning("Our Knowledge Base has been unregistered!")
            raise KnowledgeBaseNotFoundInApi()
        elif response.status_code == 410:
            logger.warning("The Knowledge Engine REST server terminated!")
            raise KnowledgeEngineTerminated()
        elif response.status_code == 500:
            logger.error(response.text)
            logger.error("TKE had an internal server error. Reinitiating long poll.")
            continue
        else:
            logger.warning(
                f"long_poll received unexpected status {response.status_code}"
            )
            logger.warning(response.text)
            logger.warning("repolling anyway..")
            continue


def post_response(kb_id, ki_id, handle_request_id, binding_set):
    ke_endpoint = os.environ.get("KE_ENDPOINT")
    response = requests.post(
        f"{ke_endpoint}/sc/handle",
        headers={"Knowledge-Base-Id": kb_id, "Knowledge-Interaction-Id": ki_id},
        json={"handleRequestId": handle_request_id, "bindingSet": binding_set},
    )
    if not response.ok:
        logger.error("Failed to post a response to knowledge request!")


def map_knowledge_request(my_kb_id, ki_id, binding_set, requesting_kb_id):
    mapping_rule = get_mapping_rule(my_kb_id, ki_id)
    return map(mapping_rule, binding_set)


def get_mapping_rule(my_kb_id, ki_id):
    km_api = os.environ.get("KM_API")
    try:
        response = requests.get(
            f"{km_api}/knowledge-bases/{my_kb_id}/data-sources/",
            params={"knowledgeInteractionId": ki_id, "includeMapping": True},
        )
    except:
        raise ApiNotReachable()
    if not response.ok:
        if response.status_code == 404:
            raise KnowledgeBaseNotFoundInApi()
        logger.error(response.status_code)
        logger.error(response.text)
        raise Exception("Request failed!")
    body = response.json()
    if len(body["data"]) != 1:
        raise Exception(
            f"Expected 1 data source, but found {len(body['data'])}: {body['data']}"
        )
    data_source = body["data"][0]
    return data_source["mapping_rule"]


def map(mapping_rule, binding_set):
    if mapping_rule["type"] != "StaticTable":
        raise Exception(f"Unsupported mapping rule type {mapping_rule['type']}!")
    source_bindings = mapping_rule["data"]
    if len(binding_set) == 0:
        binding_set = [dict()]
    return match_bindings(binding_set, source_bindings)
