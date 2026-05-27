"""Tests for SPARQL handler factory and helper functions."""

from unittest.mock import patch

import pytest

from knowledge_mapper.ke.models import (
    AskAnswerInteractionInfo,
    KiTypes,
)
from knowledge_mapper.sparql.handler import (
    _apply_variable_mapping,
    _filter_bindings,
    _sparql_binding_to_n3,
    make_sparql_handler,
)

# --- _sparql_binding_to_n3 ---


class TestSparqlBindingToN3:
    def test_uri(self):
        result = _sparql_binding_to_n3(
            {"type": "uri", "value": "http://example.org/tree1"}
        )
        assert result == "<http://example.org/tree1>"

    def test_plain_literal(self):
        result = _sparql_binding_to_n3({"type": "literal", "value": "hello"})
        assert result == '"hello"'

    def test_typed_literal(self):
        result = _sparql_binding_to_n3(
            {
                "type": "literal",
                "value": "42",
                "datatype": "http://www.w3.org/2001/XMLSchema#integer",
            }
        )
        assert result == '"42"^^<http://www.w3.org/2001/XMLSchema#integer>'

    def test_typed_literal_alt_type(self):
        result = _sparql_binding_to_n3(
            {
                "type": "typed-literal",
                "value": "3.14",
                "datatype": "http://www.w3.org/2001/XMLSchema#decimal",
            }
        )
        assert result == '"3.14"^^<http://www.w3.org/2001/XMLSchema#decimal>'

    def test_language_tagged_literal(self):
        result = _sparql_binding_to_n3(
            {"type": "literal", "value": "hello", "xml:lang": "en"}
        )
        assert result == '"hello"@en'

    def test_bnode(self):
        result = _sparql_binding_to_n3({"type": "bnode", "value": "b0"})
        assert result == "_:b0"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown SPARQL result binding type"):
            _sparql_binding_to_n3({"type": "unknown", "value": "x"})


# --- _apply_variable_mapping ---


class TestApplyVariableMapping:
    def test_renames_variables(self):
        bindings = [{"sparql_tree": "<http://ex/t1>", "h": '"10"'}]
        mapping = {"tree": "sparql_tree", "height": "h"}
        result = _apply_variable_mapping(bindings, mapping)
        assert result == [{"tree": "<http://ex/t1>", "height": '"10"'}]

    def test_unmapped_variables_kept(self):
        bindings = [{"x": "<http://ex/x>", "extra": '"val"'}]
        mapping = {"renamed_x": "x"}
        result = _apply_variable_mapping(bindings, mapping)
        assert result == [{"renamed_x": "<http://ex/x>", "extra": '"val"'}]

    def test_empty_bindings(self):
        result = _apply_variable_mapping([], {"a": "b"})
        assert result == []


# --- _filter_bindings ---


class TestFilterBindings:
    def test_no_incoming_returns_all(self):
        bindings = [{"x": "<http://ex/1>"}, {"x": "<http://ex/2>"}]
        result = _filter_bindings(bindings, [])
        assert result == bindings

    def test_empty_incoming_dicts_returns_all(self):
        bindings = [{"x": "<http://ex/1>"}]
        result = _filter_bindings(bindings, [{}])
        assert result == bindings

    def test_filters_by_matching_variable(self):
        bindings = [
            {"name": '"Oak"', "height": '"10"'},
            {"name": '"Pine"', "height": '"20"'},
        ]
        incoming = [{"name": '"Oak"'}]
        result = _filter_bindings(bindings, incoming)
        assert result == [{"name": '"Oak"', "height": '"10"'}]

    def test_multiple_incoming_bindings(self):
        bindings = [
            {"name": '"Oak"', "height": '"10"'},
            {"name": '"Pine"', "height": '"20"'},
            {"name": '"Birch"', "height": '"15"'},
        ]
        incoming = [{"name": '"Oak"'}, {"name": '"Birch"'}]
        result = _filter_bindings(bindings, incoming)
        assert len(result) == 2
        assert {"name": '"Oak"', "height": '"10"'} in result
        assert {"name": '"Birch"', "height": '"15"'} in result

    def test_no_match_returns_empty(self):
        bindings = [{"name": '"Oak"'}]
        incoming = [{"name": '"NonExistent"'}]
        result = _filter_bindings(bindings, incoming)
        assert result == []


# --- make_sparql_handler ---


class TestMakeSparqlHandler:
    SPARQL_RESPONSE = {
        "results": {
            "bindings": [
                {
                    "tree": {"type": "uri", "value": "http://example.org/tree1"},
                    "height": {
                        "type": "literal",
                        "value": "10",
                        "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                    },
                    "name": {"type": "literal", "value": "Oak"},
                },
                {
                    "tree": {"type": "uri", "value": "http://example.org/tree2"},
                    "height": {
                        "type": "literal",
                        "value": "20",
                        "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                    },
                    "name": {"type": "literal", "value": "Pine"},
                },
            ]
        }
    }

    KI_INFO = AskAnswerInteractionInfo(
        name="test-ki", type=KiTypes.ANSWER, graph_pattern="?tree ?height ?name ."
    )

    @patch("knowledge_mapper.sparql.handler.requests.post")
    def test_handler_returns_binding_set(self, mock_post):
        mock_post.return_value.json.return_value = self.SPARQL_RESPONSE
        mock_post.return_value.raise_for_status = lambda: None

        handler = make_sparql_handler(
            sparql_endpoint="http://sparql:7200/repo",
            sparql_query="SELECT ?tree ?height ?name WHERE { ... }",
        )
        result = handler([{}], self.KI_INFO)

        assert len(result) == 2
        assert result[0]["tree"] == "<http://example.org/tree1>"
        assert (
            result[0]["height"]
            == '"10"^^<http://www.w3.org/2001/XMLSchema#integer>'
        )
        assert result[0]["name"] == '"Oak"'

    @patch("knowledge_mapper.sparql.handler.requests.post")
    def test_handler_with_variable_mapping(self, mock_post):
        mock_post.return_value.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "t": {"type": "uri", "value": "http://example.org/tree1"},
                        "h": {
                            "type": "literal",
                            "value": "10",
                            "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                        },
                    }
                ]
            }
        }
        mock_post.return_value.raise_for_status = lambda: None

        handler = make_sparql_handler(
            sparql_endpoint="http://sparql:7200/repo",
            sparql_query="SELECT ?t ?h WHERE { ... }",
            variable_mapping={"tree": "t", "height": "h"},
        )
        result = handler([{}], self.KI_INFO)

        assert len(result) == 1
        assert result[0]["tree"] == "<http://example.org/tree1>"
        assert (
            result[0]["height"]
            == '"10"^^<http://www.w3.org/2001/XMLSchema#integer>'
        )

    @patch("knowledge_mapper.sparql.handler.requests.post")
    def test_handler_filters_with_incoming_bindings(self, mock_post):
        mock_post.return_value.json.return_value = self.SPARQL_RESPONSE
        mock_post.return_value.raise_for_status = lambda: None

        handler = make_sparql_handler(
            sparql_endpoint="http://sparql:7200/repo",
            sparql_query="SELECT ?tree ?height ?name WHERE { ... }",
        )
        incoming = [{"name": '"Oak"'}]
        result = handler(incoming, self.KI_INFO)

        assert len(result) == 1
        assert result[0]["name"] == '"Oak"'

    @patch("knowledge_mapper.sparql.handler.requests.post")
    def test_handler_sends_correct_request(self, mock_post):
        mock_post.return_value.json.return_value = {"results": {"bindings": []}}
        mock_post.return_value.raise_for_status = lambda: None

        query = "SELECT ?x WHERE { ?x a <http://ex/T> . }"
        handler = make_sparql_handler(
            sparql_endpoint="http://sparql:7200/repo",
            sparql_query=query,
        )
        handler([{}], self.KI_INFO)

        mock_post.assert_called_once_with(
            "http://sparql:7200/repo",
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30,
        )
