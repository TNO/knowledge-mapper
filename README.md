# Knowledge Mapper

This mapper makes it easier to disclose data from knowledge bases that use SPARQL and other protocols to a knowledge network.

## Where does it operate?

Given the configuration of your mappings, it talks to the knowledge engine's REST API to register the relevant knowledge interactions.

When there is an incoming request from the knowledge network (through the REST API), the mapper uses the configuration to retrieve the knowledge from the knowledge base.

## How to use it?

Two options: cloning the repo, or installing via `pip`

### Clone the repo

```
git clone git@ci.tno.nl:tke/knowledge-mapper.git
```

Then run it with, for example,

```
python -m knowledge_mapper conf/sql-config.json
```

### Install via `pip`

```bash
pip install knowledge_mapper
```

Then run it with:

```bash
python -m knowledge_mapper config.json
```
(make sure you have a valid config in `config.json`)

## Authorization with deny-unless-permit policy

In order for another knowledge base to request a knowledge interaction, authorization can be set using the boolean configuration property `authorization_enabled`. This is an optional setting which means that if the property is absent no authorization is being applied and all knowledge interactions are permitted.

If the property is set to `true`, a deny-unless-permit policy is being applied. Then, for every knowledge interaction, a `permitted` list can be added that indicates which knowledge bases are permitted to request that knowledge interaction.

There are some special cases for the values of this `permitted` list:
- If this list is absent or empty, NO knowledge bases are permitted.
- If the list equals `*`, ALL knowledge bases are permitted.

For all other cases, the `permitted` list contains the ids of the knowledge bases that are permitted.

The configuration file below gives an example of authorization enabled and a knowledge interaction with a permitted list with a single other knowledge base. 

## Configuration

### SPARQL

```jsonc
{
  "knowledge_engine_endpoint": "http://localhost:8280/rest",
  "knowledge_base": {
    "id": "https://example.org/a-sparql-knowledge-base",
    "name": "Some SPARQL knowledge base",
    "description": "This is just an example."
  },

  "sparql": {
    "endpoint": "http://localhost:3031/example",
    "username_environment_var": "SPARQL_USERNAME",
    "password_environment_var": "SPARQL_PASSWORD"
  },
  
  "authorization_enabled": true,

  "knowledge_interactions": [
    {
      "type": "answer",
      "vars": ["a", "b"],
      "pattern": "?a <https://example.org/isRelatedTo> ?b .",
      "permitted": ["https://example.org/another-knowledge-base"]
    },
    {
      "type": "react",
      "vars": ["a", "b"],
      "argument_pattern": "?a <https://example.org/isRelatedTo> ?b .",
      "result_pattern": null,
      "permitted": ["https://example.org/another-knowledge-base"]
    }
  ]
}
```


### SQL

(remove the comments, otherwise it doesn't parse correctly)

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

# Development instructions

## Testing

There's unit tests in the Python package that require a TKE runtime to be running at port 8082:
```bash
# Start the TKE runtime and store the container ID in a variable (in bash)
TKE_CONTAINER_ID=$(docker run -d --rm -p 8280:8280 ci.tno.nl/tke/knowledge-engine/smart-connector-rest-dist:1.0.2)

# Perform the unit tests
pytest

# Stop the TKE runtime
docker stop $TKE_CONTAINER_ID
```

There's also integration tests that require the testbed defined in `docker-compose.yml`:
```bash
# Start the testbed
docker-compose up -d
```

SPARQL KB:
```bash
python -m knowledge_mapper conf/sparql-kb-config.json
# exit with EXIT signal (Ctrl+C). It should clean up gracefully so you can reuse
# the testbed
```

SPARQL KB with authentication and authorization:
```bash
SPARQL_USERNAME=admin SPARQL_PASSWORD=pw python -m knowledge_mapper conf/sparql-kb-with-authentication-and-authorization-config.json
# exit with EXIT signal (Ctrl+C). It should clean up gracefully so you can reuse
# the testbed
```

SQL KB (credentials in JSON, but see #16):
```bash
python -m knowledge_mapper conf/sql-config.json
# exit with EXIT signal (Ctrl+C). It should clean up gracefully so you can reuse
# the testbed
```

Custom plugin (Python class):
```bash
python -m knowledge_mapper conf/plugin-config.json
# exit with EXIT signal (Ctrl+C). It should clean up gracefully so you can reuse
# the testbed
```

## Building a new distribution

- Make sure the `./dist` directory is empty or non-existing.
- Make sure you use a Python environment with the packages `distutils` and `wheel`  installed.
- Make sure the version number is correct in `setup.py` *AND* `knowledge_mapper/__init__.py`.
- Build the project:

```bash
# this creates a source distribution (`sdist`) and a built distribution (`bdist_wheel`).
python setup.py sdist bdist_wheel
```
- There should now be 2 files under the `./dist` directory.

## Releasing a new distribution

- Make sure you just built a new distribution with a *NEW* version number and have it in `./dist`
- Use `twine` to upload your new distribution to PyPI:

```
twine upload dist/*
```

- Enter your PyPI credentials in the prompt
- Make sure the new version is working as intended (attempt to upgrade project that use it)
