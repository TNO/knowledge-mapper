"""Auto-generated SPARQL-backed handlers for ANSWER and REACT KIs."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import requests

from ..ke.models import BindingSet, KnowledgeInteractionInfo

logger = logging.getLogger(__name__)


def _sparql_binding_to_n3(binding: dict[str, str]) -> str:
    """Convert a single SPARQL JSON result binding value to N3 notation.

    SPARQL JSON result bindings have this shape::

        {"type": "uri", "value": "http://example.org/x"}
        {"type": "literal", "value": "hello", "datatype": "http://..."}
        {"type": "literal", "value": "hello", "xml:lang": "en"}
        {"type": "bnode", "value": "b0"}
    """
    rdf_type = binding["type"]
    value = binding["value"]

    if rdf_type == "uri":
        return f"<{value}>"
    elif rdf_type == "literal" or rdf_type == "typed-literal":
        if "xml:lang" in binding:
            return f'"{value}"@{binding["xml:lang"]}'
        elif "datatype" in binding:
            return f'"{value}"^^<{binding["datatype"]}>'
        else:
            return f'"{value}"'
    elif rdf_type == "bnode":
        return f"_:{value}"
    else:
        raise ValueError(f"Unknown SPARQL result binding type: {rdf_type}")


def _execute_sparql_query(endpoint: str, query: str) -> list[dict[str, str]]:
    """Execute a SPARQL SELECT query and return a list of N3-encoded bindings.

    Each item in the returned list is a ``dict[str, str]`` mapping variable
    names (without ``?``) to N3-encoded values.
    """
    response = requests.post(
        endpoint,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    bindings: list[dict[str, str]] = []
    for row in result["results"]["bindings"]:
        binding: dict[str, str] = {}
        for var, val in row.items():
            binding[var] = _sparql_binding_to_n3(val)
        bindings.append(binding)

    return bindings


def _apply_variable_mapping(
    bindings: list[dict[str, str]],
    variable_mapping: dict[str, str],
) -> list[dict[str, str]]:
    """Rename SPARQL result variables to graph-pattern variable names.

    ``variable_mapping`` maps graph-pattern variable names (keys) to SPARQL
    result variable names (values).  The returned bindings use graph-pattern
    variable names as keys.
    """
    reverse_mapping = {v: k for k, v in variable_mapping.items()}
    mapped: list[dict[str, str]] = []
    for binding in bindings:
        row: dict[str, str] = {}
        for sparql_var, n3_value in binding.items():
            gp_var = reverse_mapping.get(sparql_var, sparql_var)
            row[gp_var] = n3_value
        mapped.append(row)
    return mapped


def _filter_bindings(
    bindings: list[dict[str, str]],
    incoming: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    """Post-filter SPARQL results against incoming (partial) bindings.

    If the incoming binding set is empty or contains only empty dicts, all
    results are returned.  Otherwise, a result row is kept only if it matches
    at least one incoming binding (i.e. all pre-filled variables in the
    incoming binding equal the result row's values for those variables).
    """
    filled = [b for b in incoming if b]
    if not filled:
        return bindings

    matched: list[dict[str, str]] = []
    for row in bindings:
        for inc in filled:
            if all(row.get(k) == v for k, v in inc.items()):
                matched.append(row)
                break
    return matched


def make_sparql_handler(
    sparql_endpoint: str,
    sparql_query: str,
    variable_mapping: dict[str, str] | None = None,
):
    """Return a handler that executes a SPARQL SELECT and maps results.

    The returned handler satisfies the ``Handler`` signature used by
    ``KnowledgeBaseBuilder.handler()``.

    Args:
        sparql_endpoint: URL of the SPARQL endpoint.
        sparql_query: The SPARQL SELECT query to execute.
        variable_mapping: Optional mapping from graph-pattern variable names
            to SPARQL result variable names.  When ``None``, a 1:1 name
            mapping is assumed.
    """

    def handler(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        logger.debug(
            "Executing SPARQL query for KI '%s' against %s",
            info.name,
            sparql_endpoint,
        )

        results = _execute_sparql_query(sparql_endpoint, sparql_query)

        if variable_mapping:
            results = _apply_variable_mapping(results, variable_mapping)

        results = _filter_bindings(results, binding_set)

        logger.debug(
            "SPARQL query returned %d result(s) for KI '%s'.",
            len(results),
            info.name,
        )
        return results

    return handler
