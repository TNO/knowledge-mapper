# Knowledge Mapper

This mapper makes it easier to disclose data from knowledge bases that use SPARQL and (future work) other protocols to a knowledge network.

## Where does it operate?

Given the configuration of your mappings, it talks to the knowledge engine's REST API to register the relevant knowledge interactions.

When there is an incoming request from the knowledge network (through the REST API), the mapper uses the configuration to retrieve the knowledge from the knowledge base.

## How to use it?

We publish releases of the knowledge mapper as Docker images.
Configuration goes into a file `/usr/src/app/conf/config.json` in that image.
You can mount a Docker volume at `/usr/src/app/conf`, and put your own `config.json` there, or overwrite `/usr/src/app/conf/config.json` in your own image.

## Authorization with deny-unless-permit policy

In order for another knowledge base to request a knowledge interaction, authorization can be set using the boolean configuration property `authorization_enabled`. This is an optional setting which means that if the property is absent no authorization is being applied and all knowledge interactions are permitted.

If the property is set to `true`, a deny-unless-permit policy is being applied. Then, for every knowledge interaction, a `permitted` list can be added that indicates which knowledge bases are permitted to request that knowledge interaction.

There are some special cases for the values of this `permitted` list:
- If this list is absent or empty, NO knowledge bases are permitted.
- If the list equals `*`, ALL knowledge bases are permitted.

For all other cases, the `permitted` list contains the ids of the knowledge bases that are permitted.

The configuration file below gives an example of authorization enabled and a knowledge interaction with a permitted list with a single other knowledge base. 

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

  "authorization_enabled": true,

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
      "permitted" : ["https://example.org/another-knowledge-base"],
      "sql_query": "SELECT id AS tree, height FROM trees"
    }
  ]
}
```