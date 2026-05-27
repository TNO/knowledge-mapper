"""Tests for the ``knowledge-mapper sparql`` CLI subcommand."""

import textwrap
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from knowledge_mapper.cli import app

runner = CliRunner()


def _write_sparql_config(tmp_path: Path, **overrides) -> Path:
    """Write a minimal SPARQL config YAML and return the path."""
    config = {
        "sparql_endpoint": "http://localhost:7200/repositories/test",
        "knowledge_base": {
            "id": "http://example.org/sparql-test#kb",
            "name": "sparql-test-kb",
            "description": "A SPARQL-backed KB for testing.",
        },
        "knowledge_engine_endpoint": "http://localhost:8280/rest",
        "knowledge_interactions": [
            {
                "name": "tree-answer-ki",
                "type": "AnswerKnowledgeInteraction",
                "prefixes": {"ex": "http://example.org/"},
                "graph_pattern": "?tree ex:hasHeight ?height .",
                "sparql_query": (
                    "SELECT ?tree ?height"
                    " WHERE { ?tree ex:hasHeight ?height . }"
                ),
            }
        ],
    }
    config.update(overrides)

    import yaml

    config_file = tmp_path / "sparql-config.yaml"
    config_file.write_text(yaml.dump(config, default_flow_style=False))
    return config_file


def _write_sparql_config_raw(tmp_path: Path, content: str) -> Path:
    """Write raw YAML content to a config file."""
    config_file = tmp_path / "sparql-config.yaml"
    config_file.write_text(textwrap.dedent(content))
    return config_file


def test_sparql_happy_path(tmp_path: Path):
    config_file = _write_sparql_config_raw(
        tmp_path,
        """\
        sparql_endpoint: "http://localhost:7200/repositories/test"
        knowledge_base:
          id: "http://example.org/sparql-test#kb"
          name: "sparql-test-kb"
          description: "A SPARQL-backed KB for testing."
        knowledge_engine_endpoint: "http://localhost:8280/rest"
        knowledge_interactions:
          - name: tree-answer-ki
            type: AnswerKnowledgeInteraction
            prefixes:
              ex: "http://example.org/"
            graph_pattern: "?tree ex:hasHeight ?height ."
            sparql_query: "SELECT ?tree ?height WHERE { ?tree ex:hasHeight ?height . }"
        """,
    )

    with (
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.register"),
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.start_handling_loop"),
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.unregister"),
    ):
        result = runner.invoke(app, ["sparql", str(config_file)])

    assert result.exit_code == 0


def test_sparql_with_variable_mapping(tmp_path: Path):
    config_file = _write_sparql_config_raw(
        tmp_path,
        """\
        sparql_endpoint: "http://localhost:7200/repositories/test"
        knowledge_base:
          id: "http://example.org/sparql-test#kb"
          name: "sparql-test-kb"
          description: "A SPARQL-backed KB for testing."
        knowledge_engine_endpoint: "http://localhost:8280/rest"
        knowledge_interactions:
          - name: tree-answer-ki
            type: AnswerKnowledgeInteraction
            prefixes:
              ex: "http://example.org/"
            graph_pattern: "?tree ex:hasHeight ?height ."
            sparql_query: "SELECT ?t ?h WHERE { ?t ex:hasHeight ?h . }"
            variable_mapping:
              tree: t
              height: h
        """,
    )

    with (
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.register"),
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.start_handling_loop"),
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.unregister"),
    ):
        result = runner.invoke(app, ["sparql", str(config_file)])

    assert result.exit_code == 0


def test_sparql_react_ki(tmp_path: Path):
    config_file = _write_sparql_config_raw(
        tmp_path,
        """\
        sparql_endpoint: "http://localhost:7200/repositories/test"
        knowledge_base:
          id: "http://example.org/sparql-test#kb"
          name: "sparql-test-kb"
          description: "A SPARQL-backed KB for testing."
        knowledge_engine_endpoint: "http://localhost:8280/rest"
        knowledge_interactions:
          - name: my-react-ki
            type: ReactKnowledgeInteraction
            prefixes:
              ex: "http://example.org/"
            argument_graph_pattern: "?s ex:hasProp ?val ."
            result_graph_pattern: "?s ex:hasResult ?res ."
            sparql_query: "SELECT ?s ?res WHERE { ?s ex:hasResult ?res . }"
        """,
    )

    with (
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.register"),
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.start_handling_loop"),
        patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.unregister"),
    ):
        result = runner.invoke(app, ["sparql", str(config_file)])

    assert result.exit_code == 0


def test_sparql_file_not_found():
    result = runner.invoke(app, ["sparql", "nonexistent.yaml"])

    assert result.exit_code != 0


def test_sparql_no_answer_or_react_ki(tmp_path: Path):
    config_file = _write_sparql_config_raw(
        tmp_path,
        """\
        sparql_endpoint: "http://localhost:7200/repositories/test"
        knowledge_base:
          id: "http://example.org/sparql-test#kb"
          name: "sparql-test-kb"
          description: "A SPARQL-backed KB for testing."
        knowledge_engine_endpoint: "http://localhost:8280/rest"
        knowledge_interactions:
          - name: ask-ki
            type: AskKnowledgeInteraction
            prefixes:
              ex: "http://example.org/"
            graph_pattern: "?s ?p ?o ."
            sparql_query: "SELECT ?s ?p ?o WHERE { ?s ?p ?o . }"
        """,
    )

    result = runner.invoke(app, ["sparql", str(config_file)])

    assert result.exit_code != 0
    assert "No ANSWER or REACT" in (result.output + (result.stderr or ""))


def test_sparql_missing_sparql_endpoint(tmp_path: Path):
    config_file = _write_sparql_config_raw(
        tmp_path,
        """\
        knowledge_base:
          id: "http://example.org/sparql-test#kb"
          name: "sparql-test-kb"
          description: "A SPARQL-backed KB for testing."
        knowledge_engine_endpoint: "http://localhost:8280/rest"
        knowledge_interactions:
          - name: tree-answer-ki
            type: AnswerKnowledgeInteraction
            prefixes:
              ex: "http://example.org/"
            graph_pattern: "?tree ex:hasHeight ?height ."
            sparql_query: "SELECT ?tree ?height WHERE { ?tree ex:hasHeight ?height . }"
        """,
    )

    result = runner.invoke(app, ["sparql", str(config_file)])

    assert result.exit_code != 0
