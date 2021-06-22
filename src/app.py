import argparse
import logging as log
import json

from knowledge_mapper import KnowledgeMapper

log.basicConfig(level=log.INFO)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Expose a SPARQL endpoint to a knowledge network.')
    parser.add_argument('config')
    args = parser.parse_args()
    with open(args.config) as config_file:
        config = json.load(config_file)
        client = KnowledgeMapper(config['sparql_endpoint'], config['knowledge_engine_endpoint'], config['knowledge_base']['id'], config['knowledge_base']['name'], config['knowledge_base']['description'])
        for ki in config['knowledge_interactions']:
            client.add_knowledge_interaction(ki['type'], ki['pattern'], ki['vars'])

        exit_code = 0
        try:
            client.test_sparql_endpoint()
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
