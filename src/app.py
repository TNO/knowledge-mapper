import argparse
import logging as log
import json
from data_sources import SparqlSource, SqlSource
import sys

from knowledge_mapper import KnowledgeMapper

log.basicConfig(level=log.INFO)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Expose a SPARQL endpoint to a knowledge network.')
    parser.add_argument('config')
    args = parser.parse_args()
    with open(args.config) as config_file:
        config = json.load(config_file)

        if 'sparql_endpoint' in config:
            data_source = SparqlSource(config['sparql_endpoint'])
        elif 'sql_host' in config:
            data_source = SqlSource(config['sql_host'], config['sql_port'])
        else:
            log.error('Invalid config.')
            sys.exit(1)

        data_source.test()

        client = KnowledgeMapper(data_source, config['knowledge_engine_endpoint'], config['knowledge_base']['id'], config['knowledge_base']['name'], config['knowledge_base']['description'])
        for ki in config['knowledge_interactions']:
            client.add_knowledge_interaction(ki['type'], ki['pattern'], ki['vars'])

        exit_code = 0
        try:
            client.start()
        except KeyboardInterrupt:
            log.info('Shutting down...')
        except Exception as e:
            log.error(e)
            exit_code = 1
        finally:
            client.clean_up()

        log.info('Goodbye.')
        exit(exit_code)
