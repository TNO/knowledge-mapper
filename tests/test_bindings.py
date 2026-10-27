from datetime import datetime
from typing import Annotated

import pytest
from pydantic import ValidationError
from rdflib import XSD, URIRef
from rdflib import Literal as RDFLiteral

from knowledge_mapper.ke.models import (
    UNDEFINED,
    UNDEFINED_LITERAL,
    BindingModel,
    Datatype,
    Literal,
    RdfLiteral,
    Uri,
    serialize_literal,
    serialize_uri,
    validate_literal,
    validate_uri,
)

CELSIUS = URIRef("http://example.org/units#celsius")


def test_validate_str_to_uriref():
    uri = "<http://example.com/uri>"
    validated = validate_uri(uri)
    assert isinstance(validated, URIRef)
    assert validated.toPython() == "http://example.com/uri"


def test_validate_str_to_literal():
    literal = '"foo"@de'
    validated = validate_literal(literal)
    assert isinstance(validated, str)
    assert validated == "foo"

    literal = '"4"^^xsd:integer'
    validated = validate_literal(literal)
    assert isinstance(validated, int)
    assert validated == 4


def test_validate_none():
    assert validate_literal(None) is None


def test_validate_uriref():
    assert isinstance(validate_uri(URIRef("<URI>")), URIRef)


def test_validate_literal():
    assert isinstance(validate_literal(RDFLiteral("literal")), str)


def test_serialize_none():
    assert serialize_literal(None) is None


def test_serialize_uriref():
    assert serialize_uri(URIRef("uri")) == "<uri>"


def test_serialize_literal():
    assert serialize_literal(RDFLiteral("literal")) == '"literal"'


def test_serialize_binding():
    class TestBinding(BindingModel):
        sensor: Uri = None
        year_of_manufacture: Literal[int] = None
        manufacturer_name: Literal[str] = None

    binding = TestBinding(
        sensor=URIRef("http://example.org/test#sensor"),
        year_of_manufacture=2020,
        manufacturer_name="Manufacturer Inc.",
    )

    assert binding.dump_result_binding() == {
        "sensor": "<http://example.org/test#sensor>",
        "yearOfManufacture": '"2020"^^<http://www.w3.org/2001/XMLSchema#integer>',
        "manufacturerName": '"Manufacturer Inc."',
    }


def test_validate_binding():
    class TestBinding(BindingModel):
        sensor: Uri = None
        year_of_manufacture: Literal[int] = None
        manufacturer_name: Literal[str] = None

    binding = TestBinding.model_validate(
        {
            "sensor": "<http://example.org/test#sensor>",
            "yearOfManufacture": '"2020"^^<http://www.w3.org/2001/XMLSchema#integer>',
            "manufacturerName": '"Manufacturer Inc."',
        }
    )

    assert binding.sensor == URIRef("http://example.org/test#sensor")
    assert binding.year_of_manufacture == 2020
    assert binding.manufacturer_name == "Manufacturer Inc."


def test_assigned_datetime_string_dumps_with_datetime_datatype():
    class TestBinding(BindingModel):
        timestamp: Literal[datetime] = None

    binding = TestBinding()
    binding.timestamp = "2026-07-14T20:30:00+0200"

    assert binding.dump_result_binding() == {
        "timestamp": '"2026-07-14T20:30:00+02:00"'
        "^^<http://www.w3.org/2001/XMLSchema#dateTime>",
    }


def test_assigned_datetime_dumps_with_datetime_datatype():
    class TestBinding(BindingModel):
        timestamp: Literal[datetime] = None

    binding = TestBinding()
    binding.timestamp = datetime.fromisoformat("2026-07-14T20:30:00+02:00")

    assert binding.dump_result_binding() == {
        "timestamp": '"2026-07-14T20:30:00+02:00"'
        "^^<http://www.w3.org/2001/XMLSchema#dateTime>",
    }


def test_assigning_invalid_value_to_typed_literal_raises():
    class TestBinding(BindingModel):
        timestamp: Literal[datetime] = None

    binding = TestBinding()

    with pytest.raises(ValidationError):
        binding.timestamp = "not a datetime"


# ---------- RdfLiteral


class RdfLiteralBinding(BindingModel):
    value: RdfLiteral = None


@pytest.mark.parametrize(
    "n3",
    [
        '"12.5"^^<http://example.org/units#celsius>',
        '"4"^^<http://www.w3.org/2001/XMLSchema#integer>',
        '"foo"@de',
        '"plain"',
    ],
)
def test_rdf_literal_round_trip(n3):
    binding = RdfLiteralBinding.model_validate({"value": n3})

    assert isinstance(binding.value, RDFLiteral)
    assert binding.dump_result_binding() == {"value": n3}


def test_rdf_literal_preserves_datatype_and_language():
    custom = RdfLiteralBinding.model_validate(
        {"value": '"12.5"^^<http://example.org/units#celsius>'}
    )
    tagged = RdfLiteralBinding.model_validate({"value": '"foo"@de'})

    assert custom.value.datatype == CELSIUS
    assert str(custom.value) == "12.5"
    assert tagged.value.language == "de"


def test_rdf_literal_from_rdflib_literal():
    binding = RdfLiteralBinding(value=RDFLiteral("12.5", datatype=CELSIUS))

    assert binding.dump_result_binding() == {
        "value": '"12.5"^^<http://example.org/units#celsius>'
    }


def test_rdf_literal_keeps_xsd_literal_unconverted():
    binding = RdfLiteralBinding(value=RDFLiteral(4))

    assert isinstance(binding.value, RDFLiteral)
    assert binding.value.datatype == XSD.integer


def test_rdf_literal_none():
    binding = RdfLiteralBinding()

    assert binding.value is None
    assert binding.dump_partial_binding() == {}


@pytest.mark.parametrize("value", ["<http://example.org/not-a-literal>", "bare", 4])
def test_rdf_literal_rejects_non_literals(value):
    with pytest.raises(ValidationError):
        RdfLiteralBinding.model_validate({"value": value})


def test_plain_literal_still_coerces_custom_datatype():
    class FloatBinding(BindingModel):
        value: Literal[float] = None

    binding = FloatBinding.model_validate(
        {"value": '"12.5"^^<http://example.org/units#celsius>'}
    )

    assert binding.value == 12.5


# ---------- Datatype


class CelsiusBinding(BindingModel):
    temperature: Annotated[Literal[float], Datatype(CELSIUS)] = None


def test_datatype_validates_custom_literal():
    binding = CelsiusBinding.model_validate(
        {"temperature": '"12.5"^^<http://example.org/units#celsius>'}
    )

    assert binding.temperature == 12.5


def test_datatype_serializes_with_custom_datatype():
    binding = CelsiusBinding(temperature=12.5)

    assert binding.dump_result_binding() == {
        "temperature": '"12.5"^^<http://example.org/units#celsius>'
    }


def test_datatype_accepts_rdflib_literal():
    binding = CelsiusBinding(temperature=RDFLiteral("12.5", datatype=CELSIUS))

    assert binding.temperature == 12.5


@pytest.mark.parametrize(
    "value",
    [
        '"12.5"^^<http://example.org/units#fahrenheit>',
        '"12.5"^^<http://www.w3.org/2001/XMLSchema#double>',
        '"12.5"',
        RDFLiteral(12.5),
    ],
)
def test_datatype_mismatch_raises(value):
    with pytest.raises(ValidationError, match="datatype"):
        CelsiusBinding.model_validate({"temperature": value})


def test_datatype_none():
    binding = CelsiusBinding()

    assert binding.temperature is None
    assert binding.dump_partial_binding() == {}


def test_datatype_with_str_and_datetime():
    timestamp_type = URIRef("http://example.org/types#timestamp")
    code_type = URIRef("http://example.org/types#code")

    class Binding(BindingModel):
        timestamp: Annotated[Literal[datetime], Datatype(timestamp_type)] = None
        code: Annotated[Literal[str], Datatype(code_type)] = None

    n3 = {
        "timestamp": '"2020-01-02T03:04:05"^^<http://example.org/types#timestamp>',
        "code": '"\\"quoted\\""^^<http://example.org/types#code>',
    }
    binding = Binding.model_validate(n3)

    assert binding.timestamp == datetime(2020, 1, 2, 3, 4, 5)
    assert binding.code == '"quoted"'
    assert binding.dump_result_binding() == n3


def test_datatype_accepts_string_iri():
    class Binding(BindingModel):
        temperature: Annotated[Literal[float], Datatype(str(CELSIUS))]

    assert Binding(temperature=1.5).dump_result_binding() == {
        "temperature": '"1.5"^^<http://example.org/units#celsius>'
    }


def test_datatype_and_rdf_literal_validate_on_assignment():
    class Binding(BindingModel):
        temperature: Annotated[Literal[float], Datatype(CELSIUS)] = None
        remark: RdfLiteral = None

    binding = Binding()
    binding.temperature = '"12.5"^^<http://example.org/units#celsius>'
    binding.remark = '"foo"@de'

    assert binding.temperature == 12.5
    assert binding.remark == RDFLiteral("foo", lang="de")
    with pytest.raises(ValidationError, match="datatype"):
        binding.temperature = '"12.5"^^<http://example.org/units#fahrenheit>'


# ---------- Explicit None defaults


def test_explicit_none_defaults_behave_like_implicit_ones():
    """`= None` is the recommended pattern for type checkers (issue #77)."""

    class Binding(BindingModel):
        person: Uri = None
        age: Literal[int] = None
        remark: RdfLiteral = None
        temperature: Annotated[Literal[float], Datatype(CELSIUS)] = None

    partial = Binding(person=URIRef("http://example.org/a"))
    validated = Binding.model_validate(
        {
            "age": '"3"^^<http://www.w3.org/2001/XMLSchema#integer>',
            "remark": '"foo"@de',
            "temperature": '"12.5"^^<http://example.org/units#celsius>',
        }
    )

    assert partial.dump_partial_binding() == {"person": "<http://example.org/a>"}
    assert validated.age == 3
    assert validated.dump_partial_binding() == {
        "age": '"3"^^<http://www.w3.org/2001/XMLSchema#integer>',
        "remark": '"foo"@de',
        "temperature": '"12.5"^^<http://example.org/units#celsius>',
    }
# ---------- UNDEFINED sentinels

UNDEFINED_N3 = "<http://www.knowledge-engine.eu/mapper/undefined>"


class OptionalValuesBinding(BindingModel):
    uri: Uri
    count: Literal[int]
    name: Literal[str]
    timestamp: Literal[datetime]
    temperature: Annotated[Literal[float], Datatype(CELSIUS)]
    remark: RdfLiteral


LITERAL_FIELDS = ["count", "name", "timestamp", "temperature", "remark"]
ALL_UNDEFINED = {"uri": UNDEFINED} | dict.fromkeys(LITERAL_FIELDS, UNDEFINED_LITERAL)


def make_defined_binding() -> OptionalValuesBinding:
    return OptionalValuesBinding(
        uri=URIRef("http://example.org/a"),
        count=1,
        name="a",
        timestamp=datetime(2020, 1, 1),
        temperature=1.5,
        remark=RDFLiteral("a"),
    )


def test_undefined_sentinels_share_the_mapper_uri():
    assert URIRef("http://www.knowledge-engine.eu/mapper/undefined") == UNDEFINED
    assert UNDEFINED.n3() == UNDEFINED_N3
    assert UNDEFINED_LITERAL.n3() == UNDEFINED_N3


def test_undefined_sentinels_serialize_to_the_mapper_uri():
    binding = OptionalValuesBinding(**ALL_UNDEFINED)

    assert binding.dump_result_binding() == dict.fromkeys(ALL_UNDEFINED, UNDEFINED_N3)


def test_mapper_uri_deserializes_to_the_sentinel_matching_the_field_type():
    binding = OptionalValuesBinding.model_validate(
        dict.fromkeys(ALL_UNDEFINED, UNDEFINED_N3)
    )

    for field, sentinel in ALL_UNDEFINED.items():
        assert getattr(binding, field) is sentinel


@pytest.mark.parametrize("field", list(ALL_UNDEFINED))
def test_undefined_sentinel_can_be_assigned_and_replaced(field):
    binding = make_defined_binding()
    original = getattr(binding, field)

    setattr(binding, field, ALL_UNDEFINED[field])
    assert getattr(binding, field) is ALL_UNDEFINED[field]
    assert binding.dump_result_binding()[field] == UNDEFINED_N3

    setattr(binding, field, original)
    assert getattr(binding, field) == original


@pytest.mark.parametrize("field", LITERAL_FIELDS)
def test_uri_sentinel_is_rejected_for_literal_fields(field):
    with pytest.raises(ValidationError, match="UNDEFINED_LITERAL"):
        OptionalValuesBinding(**{field: UNDEFINED})


def test_literal_sentinel_is_rejected_for_uri_fields():
    with pytest.raises(ValidationError, match="UNDEFINED instead"):
        OptionalValuesBinding(uri=UNDEFINED_LITERAL)


@pytest.mark.parametrize("field", ["count", "temperature", "remark"])
def test_bare_mapper_uri_string_is_not_a_sentinel(field):
    with pytest.raises(ValidationError):
        OptionalValuesBinding(**{field: str(UNDEFINED)})


def test_undefined_sentinels_are_concrete_values_in_partial_bindings():
    binding = OptionalValuesBinding(uri=UNDEFINED, count=UNDEFINED_LITERAL)

    assert binding.dump_partial_binding() == {
        "uri": UNDEFINED_N3,
        "count": UNDEFINED_N3,
    }
    assert binding.matches_with(uri=UNDEFINED_N3, count=UNDEFINED_N3)
    assert not binding.matches_with(count='"1"^^xsd:integer')


def test_other_uris_are_still_rejected_for_literal_fields():
    with pytest.raises(ValidationError):
        OptionalValuesBinding(count="<http://example.org/other>")
    with pytest.raises(ValidationError):
        OptionalValuesBinding(temperature=URIRef("http://example.org/other"))
