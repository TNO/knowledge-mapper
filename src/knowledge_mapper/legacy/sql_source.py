import logging as log
import mysql.connector

from .data_source import DataSource

class SqlSource(DataSource):
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def test(self):
        log.info('Testing SQL connection.')
        self.conn = mysql.connector.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database)
        self.conn.ping()
        log.info('Succes!')


    def handle(self, ki, binding_set, requesting_kb):
        if ki['type'] == 'answer':
            return self.handle_answer(ki, binding_set, requesting_kb)
        elif ki['type'] == 'react':
            return self.handle_react(ki, binding_set, requesting_kb)


    def handle_answer(self, ki, binding_set, requesting_kb):
        sql_bindings = ()
        if binding_set:
            binding_constraints = '0 '

            # Add constraint clause with a disjunct for every binding, and in
            # each disjunct a conjunction with a conjunct for every binding
            # entry.
            for binding in binding_set:
                binding_constraints += 'OR 1 '
                for key, value in binding.items():
                    binding_constraints += f'AND {key} = %s '
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

        cursor.close()

        # The connection caches query results if not committed and this resulted in 
        # subsequent queries not containing the latest changes to the tables.
        self.conn.commit()


        return result_binding_set


    def handle_react(self, ki, binding_set, requesting_kb):
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
                    except mysql.connector.Error as e:
                        log.warn(e)
                        self.conn.rollback()
                        continue
                # Only commit after a complete query (with multiple statements)
                # is executed.
                self.conn.commit()
            return []
