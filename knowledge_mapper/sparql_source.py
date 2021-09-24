import requests
from requests.auth import HTTPBasicAuth
import os
import logging as log
from urllib.parse import quote

from .data_source import DataSource

class SparqlSource(DataSource):
    def __init__(self, endpoint: str):
        self.endpoint = endpoint


    def test(self):
        log.info('Testing SPARQL endpoint.')
        self.do_sparql_select('SELECT * WHERE { ?s ?p ?o . } LIMIT 0')
        log.info('Succes!')


    def handle(self, ki, binding_set):
        if ki['type'] == 'answer':
            return self.handle_answer(ki, binding_set)
        elif ki['type'] == 'react':
            return self.handle_react(ki, binding_set)


    def handle_answer(self, ki, binding_set):
        # Generate the SPARQL query based on the incoming bindings and the knowledge interaction's graph pattern.
        query = generate_sparql_select(ki, binding_set)
        # Fire the SPARQL query.
        result = self.do_sparql_select(query)
        # Restructure the bindings into TKE bindings and return it
        return restructure_bindings(result)


    def handle_react(self, ki, binding_set):
        # Generate the SPARQL query based on the incoming bindings and the knowledge interaction's graph pattern.
        query = generate_sparql_insert(ki, binding_set)
        # Fire the SPARQL query.
        self.do_sparql_insert(query)
        # Restructure the bindings into TKE bindings and return it
        return []


    def do_sparql_select(self, query):
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


    def do_sparql_insert(self, query):
        args = {
            'headers': {
                'Accept': 'application/json',
                'Content-Type': 'application/sparql-update'
            }
        }

        if 'SPARQL_USERNAME' in os.environ and 'SPARQL_PASSWORD' in os.environ:
            args['auth'] = HTTPBasicAuth(os.environ['SPARQL_USERNAME'], os.environ['SPARQL_PASSWORD'])

        response = requests.post(
            f'{self.endpoint}',
            data=query,
            **args
        )

        if response.status_code == 401:
            raise UnauthorizedError("Provide BasicAuth with system environment variables SPARQL_USERNAME and SPARQL_PASSWORD.")
        elif not response.ok:
            raise RuntimeError("Invalid response from SPARQL endpoint.  (status: {}, body: {})".format(response.status_code, response.text))

        return


def generate_sparql_select(ki, incoming_bindings):
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


def generate_sparql_insert(ki, bindings):
    variables = ki['vars']
    return f'''
        INSERT {{
            {ki['argument_pattern']}
        }} WHERE {{ VALUES ({' '.join([f'?{variable}' for variable in variables])}) {{
            {os.linesep.join(f'({" ".join([str(binding[variable]) for variable in variables])})' for binding in bindings)}
        }} }}
    '''


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
