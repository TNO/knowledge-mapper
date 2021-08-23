import requests
import logging as log
import os
from urllib.parse import quote
from requests.auth import HTTPBasicAuth
import mariadb

class DataSource:
    def test(self):
        raise NotImplementedError("Please implement this abstract method.")
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
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.conn = mariadb.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database)


    def test(self):
        log.info('Testing SQL connection.')
        self.conn.ping()
        log.info('Succes!')


    def handle(self, ki, binding_set):
        if ki['type'] == 'answer':
            return self.handle_answer(ki, binding_set)
        elif ki['type'] == 'react':
            return self.handle_react(ki, binding_set)


    def handle_answer(self, ki, binding_set):
        sql_bindings = ()
        if binding_set:
            binding_constraints = '0 '

            # Add constraint clause with a disjunct for every binding, and in
            # each disjunct a conjunction with a conjunct for every binding
            # entry.
            for binding in binding_set:
                binding_constraints += 'OR 1 '
                for key, value in binding.items():
                    binding_constraints += f'AND {key} = ? '
                    prefix = ""
                    if key in ki['column_prefixes']:
                        prefix = ki['column_prefixes'][key]
                    # If prefixed, remove the <>'s and the prefix, otherwise,
                    # use `value` as is.
                    if prefix:
                        unprefixed = value[len(prefix) + 1:-1]
                    else:
                        unprefixed = value
                    sql_bindings += (unprefixed,)

            # HAVING is used because WHERE is evaluated before aggregations, and
            # so aliases defined in the query are unavailable.
            query = f"{ki['sql_query']} HAVING {binding_constraints}"
        else:
            query = ki['sql_query']

        # Create a cursor and execute the query.
        cursor = self.conn.cursor(named_tuple=True)
        cursor.execute(query, sql_bindings)

        result_binding_set = []
        for row in cursor:
            binding = dict()
            for variable in ki['vars']:
                # Get the value of the current variable from the current row.
                value = getattr(row, variable)

                # Check the type of the value and set the datatype accordingly.
                # TODO: Support more data types?
                if variable in ki['column_prefixes']:
                    prefix = ki['column_prefixes'][variable]
                    typed_value = f"<{prefix}{value}>"
                elif isinstance(value, int):
                    typed_value = f"\"{value}\"^^<http://www.w3.org/2001/XMLSchema#integer>"
                else:
                    # Fall back to a string literal.
                    typed_value = f"\"{value}\""

                binding[variable] = typed_value

            result_binding_set.append(binding)

        return result_binding_set


    def handle_react(self, ki, binding_set):
        if binding_set:
            for binding in binding_set:
                for statement in ki['sql_query']:
                    variables = statement['bindings']
                    sql_binding = ()
                    for variable in variables:
                        value = binding[variable]
                        # If prefixed, remove the <>'s and the prefix, otherwise,
                        # use `value` as is.
                        if variable in ki['column_prefixes']:
                            prefix = ki['column_prefixes'][variable]
                            sql_binding += (value[len(prefix) + 1:-1],)
                        elif value[0] == '"' and value[-1] == '"':
                            # This is a string literal. We want to use the
                            # string INSIDE the quotes for the SQL binding.
                            sql_binding += (value[1:-1],)
                        else:
                            # TODO: Handle other datatypes correctly if they're
                            # given with "value"^^:datatype syntax.
                            sql_binding += (value,)

                    # Create a cursor and execute the query.
                    try:
                        cursor = self.conn.cursor()
                        cursor.execute(statement['statement'], sql_binding)
                    except mariadb.Error as e:
                        log.warn(e)
                        self.conn.rollback()
                        continue
                # Only commit after a complete query (with multiple statements)
                # is executed.
                self.conn.commit()
            return []


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
