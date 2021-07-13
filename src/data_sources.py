import requests
import logging as log
import os
from urllib.parse import quote
from requests.auth import HTTPBasicAuth


class DataSource:
    def handle(self, ki, binding_set):
        raise NotImplementedError("Please implement this abstract method.")


class SparqlSource(DataSource):
    def __init__(self, endpoint: str):
        self.endpoint = endpoint


    def test(self):
        log.info('Testing SPARQL endpoint.')
        self.do_sparql('SELECT * WHERE { ?s ?p ?o . } LIMIT 0')
        log.info('Succes!')


    def handle(self, ki, binding_set):
        # Generate the SPARQL query based on the incoming bindings and the knowledge interaction's graph pattern.
        query = generate_sparql(ki, binding_set)
        # Fire the SPARQL query.
        result = self.do_sparql(query)
        # Restructure the bindings into TKE bindings and return it
        return restructure_bindings(result)


    def do_sparql(self, query):
        args = {
            'headers': {
                'Accept': 'application/json'
            }
        }

        if 'SPARQL_USERNAME' in os.environ and 'SPARQL_PASSWORD' in os.environ:
            args['auth'] = HTTPBasicAuth(os.environ['SPARQL_USERNAME'], os.environ['SPARQL_PASSWORD'])

        response = requests.get(
            f'{self.endpoint}?query={quote(query)}',
            **args
        )

        if response.status_code == 401:
            raise UnauthorizedError("Provide BasicAuth with system environment variables SPARQL_USERNAME and SPARQL_PASSWORD.")
        elif not response.ok:
            raise RuntimeError("Invalid response from SPARQL endpoint.  (status: {}, body: {})".format(response.status_code, response.text))

        return response.json()


class SqlSource(DataSource):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port


def generate_sparql(ki, incoming_bindings):
    # For all partial bindings that are actually partial, we set the
    # variables that ARE in the graph pattern, but NOT in the binding to
    # UNDEF, so that they match anything.
    for var in ki['vars']:
        for incoming_binding in incoming_bindings:
            if var not in incoming_binding:
                incoming_binding[var] = 'UNDEF'

    return '''
        SELECT {{variables}} WHERE {{{{
            {triple_pattern}
            {values_clause}
        }}}}
    '''.format(
            triple_pattern=ki['pattern'],
            values_clause='''
                VALUES ({{variables}}) {{{{
                    {bindings}
                }}}}
            '''.format(
                bindings='\n'.join([
                    f'({" ".join([binding[var] for var in ki["vars"]])})' for binding in incoming_bindings
                ])
            ) if incoming_bindings else '',
        ).format(
            variables=' '.join([f'?{var}' for var in ki['vars']]),
        )


def restructure_bindings(sparql_results):
    restructured_binding_set = []
    for binding in sparql_results['results']['bindings']:
        restructured_binding = dict()
        for key, value in binding.items():
            if value['type'] == 'uri':
                restructured_value = f'<{value["value"]}>'
            elif binding[key]['type'] == 'literal':
                if 'datatype' in value:
                    restructured_value = f'"{value["value"]}"^^<{value["datatype"]}>'
                else:
                    restructured_value = f'"{value["value"]}"'
            restructured_binding[key] = restructured_value

        restructured_binding_set.append(restructured_binding)

    return restructured_binding_set


class UnauthorizedError(RuntimeError):
   pass
