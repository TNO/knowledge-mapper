import requests
import logging as log
import os
from urllib.parse import quote
from requests.auth import HTTPBasicAuth

class KnowledgeMapper:


    def __init__(self, sparql_url: str, ke_url: str, kb_id: str, kb_name: str, kb_desc: str):
        self.ke_url = ke_url
        self.sparql_url = sparql_url
        self.kb_id = kb_id
        self.kis = dict()

        response = requests.post(
            f'{self.ke_url}/sc',
            json={
                'knowledgeBaseId': kb_id,
                'knowledgeBaseName': kb_name,
                'knowledgeBaseDescription': kb_desc
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge base failed.')


    def add_knowledge_interaction(self, type: str, pattern: str, vars: list):
        response = requests.post(
            f'{self.ke_url}/sc/ki',
            json={
                'knowledgeInteractionType': 'AnswerKnowledgeInteraction',
                'graphPattern': pattern
            },
            headers={
                'Knowledge-Base-Id': self.kb_id
            }
        )
        if not response.ok:
            log.error('%s', response.text)
            raise Exception('Registering knowledge interaction failed.')

        ki_id = response.text
        self.kis[ki_id] = {
            'type': type,
            'pattern': pattern,
            'vars': vars,
        }


    def start(self):
        while True:
            status, handle_request = self.long_poll()

            if status == "repoll":
                continue
            elif status == "exit":
                break
            elif status == "handle":
                log.info('Handling handle request %d', handle_request['handleRequestId'])
                answer = self.query_sparql(handle_request['knowledgeInteractionId'], handle_request['bindingSet'])
                self.post_handle_response(handle_request['knowledgeInteractionId'], handle_request['handleRequestId'], answer)
            else:
                raise Exception("Invalid internal status from KnowledgeMapper.long_poll!")

        self.clean_up()


    def long_poll(self):
        log.info('Waiting for response to long poll...')
        response = requests.get(f'{self.ke_url}/sc/handle', headers = {'Knowledge-Base-Id': self.kb_id})
        if response.status_code == 202:
            log.info('Received 202.')
            return "repoll", None
        elif response.status_code == 500:
            log.error(response.text)
            log.error('TKE had an internal server error. Reinitiating long poll.')
            return "repoll", None
        elif response.status_code == 410:
            log.info('Received 410! Exiting.')
            return "exit", None
        elif response.status_code == 200:
            log.info('Received 200')
            return "handle", response.json()


    def post_handle_response(self, ki_id, handle_id, bindings):
        log.info(f'Posting response to %d', handle_id)
        response = requests.post(f'{self.ke_url}/sc/handle',
            json={
                'handleRequestId': handle_id,
                'bindingSet': bindings,
            },
            headers={
                'Knowledge-Base-Id': self.kb_id,
                'Knowledge-Interaction-Id': ki_id,
            }
        )
        if not response.ok:
            log.warn(response.text)
            log.warn('Posting a handle response failed. Ignoring it.')


    def clean_up(self):
        response = requests.delete(f'{self.ke_url}/sc', headers={'Knowledge-Base-Id': self.kb_id})
        if not response.ok:
            log.error(response.text)
            log.error('Deletion of knowledge base failed.')
        else:
            log.info('Knowledge base successfully deleted.')


    def query_sparql(self, ki_id: str, incoming_bindings):
        ki = self.kis[ki_id]

        # For all partial bindings that are actually partial, we set the
        # variables that ARE in the graph pattern, but NOT in the binding to
        # UNDEF, so that they match anything.
        for var in ki['vars']:
            for incoming_binding in incoming_bindings:
                if var not in incoming_binding:
                    incoming_binding[var] = 'UNDEF'

        query = '''
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

        args = {
            'headers': {
                'Accept': 'application/json'
            }
        }

        if os.environ['SPARQL_USERNAME'] and os.environ['SPARQL_PASSWORD']:
            args['auth'] = HTTPBasicAuth(os.environ['SPARQL_USERNAME'], os.environ['SPARQL_PASSWORD'])

        log.info('Sending query to SPARQL endpoint: %s', query)
        response = requests.get(
            f'{self.sparql_url}?query={quote(query)}',
            **args
        )

        if not response.ok:
            log.error(response)
            log.error(response.text)

        result_bindings = response.json()['results']['bindings']

        for binding in result_bindings:
            for key, value in binding.items():

                if value['type'] == 'uri':
                    binding[key] = f'<{value["value"]}>'
                elif binding[key]['type'] == 'literal':
                    if 'datatype' in value:
                        binding[key] = f'"{value["value"]}"^^<{value["datatype"]}>'
                    else:
                        binding[key] = f'"{value["value"]}"'

        return result_bindings
