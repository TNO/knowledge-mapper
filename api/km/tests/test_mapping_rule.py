from django.forms import model_to_dict
import pytest
from km.models import MappingRule


@pytest.fixture(autouse=True)
def use_dummy_cache_backend(settings):
    settings.DATABASES["default"]["NAME"] = ":memory:"


@pytest.mark.django_db
def test_serialize_mapping_rule():
    mr = MappingRule(type="StaticTable", data=[{"a": "<some-value>"}])
    mr.save()
    assert mr.id != None
    mr_recalled = MappingRule.objects.get(id=mr.id)
    assert model_to_dict(mr_recalled) == model_to_dict(mr)
