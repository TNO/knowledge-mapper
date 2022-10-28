import json
import os

from django.forms import model_to_dict
from django.http import HttpRequest, JsonResponse
from django.views import View

from km.models import KnowledgeBase

KE_ENDPOINT = os.environ["KE_ENDPOINT"]


class BadRequestResponse(JsonResponse):
    def __init__(self, reason: str, status=400, **kwargs):
        super().__init__({"error": reason}, status=status, **kwargs)


class KnowledgeBaseListView(View):
    async def get(self, request: HttpRequest):
        return JsonResponse(
            {
                "data": [model_to_dict(kb) async for kb in KnowledgeBase.objects.all()],
            }
        )

    async def post(self, request: HttpRequest):
        try:
            json_body = json.loads(request.body)
            kb_id = json_body["kb_id"]
            name = json_body["name"]
            description = json_body["description"]
        except KeyError:
            return BadRequestResponse("`kb_id`, `name` and `description` are required")
        except json.JSONDecodeError:
            return BadRequestResponse("should be valid JSON")

        kb = await KnowledgeBase.objects.acreate(
            kb_id=kb_id, name=name, description=description
        )
        return JsonResponse(model_to_dict(kb))


class KnowledgeBaseDetailView(View):
    async def get(self, request: HttpRequest, id: int = -1):
        if id == -1:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        try:
            kb = await KnowledgeBase.objects.aget(id=id)
        except KnowledgeBase.DoesNotExist:
            return BadRequestResponse("Knowledge Base not found.", status=404)

        return JsonResponse(model_to_dict(kb))
