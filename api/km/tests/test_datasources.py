from django.forms import model_to_dict
from django.core import serializers
import pytest

from km.models import DataSource, KnowledgeBase, MappingRule


@pytest.mark.django_db
def test_serialize_mapping_rule():
    ki_id1 = "http://example.org/kb/ki1"
    ki_id2 = "http://example.org/kb/ki2"
    kb_id = "http://example.org/kb"
    kb = KnowledgeBase(id_url=kb_id, name="bla", description="bla")
    mr = MappingRule(type="StaticTable", data=[{"a": "<some-value>"}])
    ds1 = DataSource(
        name="bla",
        kb=kb,
        ki_id=ki_id1,
        ki_type="ANSWER",
        mapping_rule=mr,
        pattern_1="?a <bla> ?b .",
        prefixes={},
    )

    ds2 = DataSource(
        name="bla2",
        kb=kb,
        ki_id=ki_id2,
        ki_type="ANSWER",
        mapping_rule=mr,
        pattern_1="?a <bla> ?b .",
        prefixes={},
    )
    mr.save()
    kb.save()
    ds1.save()
    ds2.save()

    qs1 = DataSource.objects.filter(kb_id=99999)
    assert len(qs1) == 0
    qs2 = DataSource.objects.filter(kb_id=kb.id)
    assert len(qs2) == 2
    qs3 = qs2.filter(ki_id=ki_id1)
    assert len(qs3) == 1
    qs4 = qs2.filter(ki_id=ki_id1)
    assert len(qs4) == 1

    print(serializers.serialize("json", qs2))
    print([model_to_dict(ki) for ki in qs2])
