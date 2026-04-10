from rdflib import Literal as RDFLiteral
from rdflib import URIRef

from src.ke.models import (
    BindingModel,
    Literal,
    Uri,
    serialize_literal,
    serialize_uri,
    validate_literal,
    validate_uri,
)


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
        sensor: Uri
        year_of_manufacture: Literal[int]
        manufacturer_name: Literal[str]

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
        sensor: Uri
        year_of_manufacture: Literal[int]
        manufacturer_name: Literal[str]

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
