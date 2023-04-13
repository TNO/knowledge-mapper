from rdflib import Graph, URIRef, Variable


def match_bindings(query: list[dict], source: list[dict]) -> list:
    matches = []
    for s in source:
        for q in query:
            q_matches = True
            for k, v in q.items():
                if not (k in s and s[k] == v):
                    q_matches = False
                    break
            if q_matches:
                matches.append(s.copy())
                break
    return matches


def extract_variables(graph_pattern, prefixes=dict()):
    """Given a graph pattern, returns a set with the variables (strings) that
    are used in the graph pattern"""
    g = Graph()
    # Wrap the graph pattern in a SELECT query
    query = f"SELECT * WHERE {{ {graph_pattern} }}"
    # Parse the query into an RDFLib query object
    q = g.query(query, initNs=prefixes)
    # Extract the variables from the query
    variables = set()
    for var in q.vars:
        if isinstance(var, Variable):
            variables.add(var.n3()[1:])
    return variables
