# Knowledge Mapper

This mapper makes it easier to disclose data from knowledge bases that use SPARQL and (future work) other protocols to a knowledge network.

## Where does it operate?

Given the configuration of your mappings, it talks to the knowledge engine's REST API to register the relevant knowledge interactions.

When there is an incoming request from the knowledge network (through the REST API), the mapper uses the configuration to retrieve the knowledge from the knowledge base.

## How to use it?

We publish releases of the knowledge mapper as Docker images.
Configuration goes into a file `/usr/src/app/conf/config.json` in that image.
You can mount a Docker volume at `/usr/src/app/conf`, and put your own `config.json` there, or overwrite `/usr/src/app/conf/config.json` in your own image.

## Authorization

In order for another knowledge base to request a knowledge interaction, authorization needs to be set as shown in the configuration file below.

## Configuration

### SQL

```jsonc
{
  "knowledge_engine_endpoint": "http://localhost:8280/rest",
  "knowledge_base": {
    "id": "https://example.org/a-sql-knowledge-base",
    "name": "Some SQL knowledge base",
    "description": "This is just an example."
  },
  
  // DB connection and credentials
  "sql_host": "127.0.0.1",
  "sql_port": 3306,
  "sql_database": "treedb",
  "sql_user": "user",
  "sql_password": "pw",

  "knowledge_interactions": [
    {
      // This map makes ensures that the value is prefixed for the variables in the keys.
      "column_prefixes": {
        // When a row (from DB) is retrieved with value 42 for the 'tree'
        // column, it is mapped to <http://example.org/trees/42> in the binding.
        "tree": "http://example.org/trees/"
      },
      "type": "answer",
      "vars": ["tree", "height"],
      "pattern": "?tree <https://example.org/hasHeight> ?height .",
      "authorized" : ["https://example.org/another-knowledge-base"].
      "sql_query": "SELECT id AS tree, height FROM trees"
    }
  ]
}
```