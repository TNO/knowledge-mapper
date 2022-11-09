import json
import os

from django.forms import model_to_dict
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from km.models import KnowledgeBase
from knowledge_mapper.tke_client import TkeClient
from knowledge_mapper.knowledge_base import KnowledgeBaseRegistrationRequest


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
            kb_id = json_body["kb_id"]
            name = json_body["name"]
            description = json_body["description"]
        except KeyError:
            return BadRequestResponse(
                "`kb_id`, `name`, and `description` are required."
            )
        except json.JSONDecodeError:
            return BadRequestResponse("Request body should be valid JSON.")

        if KnowledgeBase.objects.filter(kb_id=kb_id).exists():
            return BadRequestResponse("`kb_id` must be unique.")

        tke_client = TkeClient(KE_ENDPOINT)
        tke_client.connect()
        _kb = tke_client.register(
            KnowledgeBaseRegistrationRequest(
                id=kb_id, name=name, description=description
            )
        )

        kb_instance = KnowledgeBase.objects.create(
            kb_id=kb_id, name=name, description=description
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
        kb = tke_client.get_knowledge_base(kb_instance.kb_id)
        kb.unregister()

        kb_instance.delete()

        return HttpResponse(status=200)
