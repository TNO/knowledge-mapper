import json
import os

from django.forms import model_to_dict
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from km.models import MAPPING_TYPES, MappingRule

from km.models import KnowledgeBase, DataSource, KI_TYPES
from knowledge_mapper.tke_client import TkeClient
from knowledge_mapper.knowledge_base import KnowledgeBaseRegistrationRequest
from knowledge_mapper.knowledge_interaction import (
    AskKnowledgeInteractionRegistrationRequest,
    AnswerKnowledgeInteractionRegistrationRequest,
    PostKnowledgeInteractionRegistrationRequest,
    ReactKnowledgeInteractionRegistrationRequest,
)


KE_ENDPOINT = os.environ["KE_ENDPOINT"]


class BadRequestResponse(JsonResponse):
    def __init__(self, reason: str, status=400, **kwargs):
        super().__init__({"error": reason}, status=status, **kwargs)


class KnowledgeBaseListView(View):
    def get(self, request: HttpRequest):
        return JsonResponse(
            {
                "data": [model_to_dict(kb) for kb in KnowledgeBase.objects.all()],
            }
        )

    def post(self, request: HttpRequest):
        try:
            json_body = json.loads(request.body)
            id_url = json_body["id_url"]
            name = json_body["name"]
            description = json_body["description"]
        except KeyError:
            return BadRequestResponse(
                "`id_url`, `name`, and `description` are required."
            )
        except json.JSONDecodeError:
            return BadRequestResponse("Request body should be valid JSON.")

        if KnowledgeBase.objects.filter(id_url=id_url).exists():
            return BadRequestResponse("`id_url` must be unique.")

        tke_client = TkeClient(KE_ENDPOINT)
        tke_client.connect()
        _kb = tke_client.register(
            KnowledgeBaseRegistrationRequest(
                id=id_url, name=name, description=description
            )
        )

        kb_instance = KnowledgeBase.objects.create(
            id_url=id_url, name=name, description=description
        )
        return JsonResponse(model_to_dict(kb_instance))


class KnowledgeBaseDetailView(View):
    def get(self, request: HttpRequest, id: int = -1):
        if id == -1:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        try:
            kb = KnowledgeBase.objects.get(id=id)
        except KnowledgeBase.DoesNotExist:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        return JsonResponse(model_to_dict(kb))

    def delete(self, request: HttpRequest, id: int = -1):
        if id == -1:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        try:
            kb_instance = KnowledgeBase.objects.get(id=id)
        except KnowledgeBase.DoesNotExist:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        tke_client = TkeClient(KE_ENDPOINT)
        tke_client.connect()
        kb = tke_client.get_knowledge_base(kb_instance.id_url)
        kb.unregister()

        kb_instance.delete()

        return HttpResponse(status=200)


class DataSourceListView(View):
    def get(self, request: HttpRequest, kb_id: int = -1):
        if kb_id == -1:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        try:
            kb_instance = KnowledgeBase.objects.get(id=kb_id)
        except KnowledgeBase.DoesNotExist:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        qs = DataSource.objects.filter(kb_id=kb_instance.id)

        if "knowledgeInteractionId" in request.GET:
            qs = qs.filter(ki_id=request.GET["knowledgeInteractionId"])

        if "includeMapping" in request.GET:
            data_sources = []
            for ki in qs:
                data_source = model_to_dict(ki)
                data_source["mapping_rule"] = model_to_dict(ki.mapping_rule)
                data_sources += [data_source]
        else:
            data_sources = [model_to_dict(ki) for ki in qs]

        return JsonResponse(
            {
                "data": data_sources,
            }
        )

    def post(self, request: HttpRequest, kb_id: int = -1):
        if kb_id == -1:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        try:
            kb_instance = KnowledgeBase.objects.get(id=kb_id)
        except KnowledgeBase.DoesNotExist:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        try:
            json_body = json.loads(request.body)
            try:
                name = json_body["name"]
            except KeyError:
                name = None

            type = json_body["type"]
            if type not in [choice[0] for choice in KI_TYPES]:
                return BadRequestResponse(
                    f"`type`, should be in {[choice[0] for choice in KI_TYPES]}"
                )

            pattern_1 = json_body["pattern_1"]
            try:
                pattern_2 = json_body["pattern_2"]
            except KeyError:
                pattern_2 = None

            try:
                prefixes = json_body["prefixes"]
            except KeyError:
                prefixes = dict()

            try:
                mapping = json_body["mapping"]
                mapping_type = mapping["type"]
                mapping_data = mapping["data"]
                if mapping_type not in [choice[0] for choice in MAPPING_TYPES]:
                    return BadRequestResponse(
                        f"`mapping.type`, should be in {[choice[0] for choice in MAPPING_TYPES]}."
                    )
                if mapping_type == "StaticTable" and not isinstance(mapping_data, list):
                    return BadRequestResponse(
                        f'`mapping.data`, should be a list if mapping.type is "StaticTable".'
                    )
            except KeyError:
                return BadRequestResponse(
                    "`mapping` with `typ` and `data` is required."
                )
        except KeyError:
            return BadRequestResponse("`type`, and `pattern_1` are required.")
        except json.JSONDecodeError:
            return BadRequestResponse("Request body should be valid JSON.")

        tke_client = TkeClient(KE_ENDPOINT)
        tke_client.connect()
        kb = tke_client.get_knowledge_base(kb_instance.id_url)
        if type == "ASK":
            ki = kb.register_knowledge_interaction(
                AskKnowledgeInteractionRegistrationRequest(
                    prefixes=prefixes,
                    pattern=pattern_1,
                ),
                name=name,
            )
        elif type == "ANSWER":
            ki = kb.register_knowledge_interaction(
                AnswerKnowledgeInteractionRegistrationRequest(
                    prefixes=prefixes,
                    pattern=pattern_1,
                    handler=None,
                ),
                name=name,
            )
        elif type == "POST":
            ki = kb.register_knowledge_interaction(
                PostKnowledgeInteractionRegistrationRequest(
                    prefixes=prefixes,
                    argument_pattern=pattern_1,
                    result_pattern=pattern_2,
                ),
                name=name,
            )
        elif type == "REACT":
            ki = kb.register_knowledge_interaction(
                ReactKnowledgeInteractionRegistrationRequest(
                    prefixes=prefixes,
                    argument_pattern=pattern_1,
                    result_pattern=pattern_2,
                    handler=None,
                ),
                name=name,
            )

        # TODO: catch exceptions in the above registrations

        mapping_rule = MappingRule.objects.create(
            type=mapping["type"], data=mapping["data"]
        )

        ki_instance = DataSource.objects.create(
            ki_id=ki.id,
            kb=kb_instance,
            ki_type=type,
            name=name,
            prefixes=prefixes,
            pattern_1=pattern_1,
            pattern_2=pattern_2,
            mapping_rule=mapping_rule,
        )

        return JsonResponse(
            model_to_dict(ki_instance),
        )
