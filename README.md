# Knowledge Mapper

The Knowledge Mapper makes it easier to share your data in a knowledge base to the TNO Knowledge Engine (TKE) network. 
It maps SQL, SPARQL, and Python classes to the format used by Smart Connectors in a TKE network.
This allows your knowledge base to be connected to the network using only a single configuration file.

The mapper also helps if you use other programming and query languages.
It provides functions that allow you to easily share data to a TKE network.
The mapper takes care of connecting to the TKE network and helps in registering your knowledge base and knowledge interactions.

## Where does it operate?

Given the configuration of your mappings, it talks to the knowledge engine's REST API to register the relevant knowledge interactions.

When there is an incoming request from the knowledge network (through the REST API), the mapper uses the configuration to retrieve the knowledge from the knowledge base.

The following diagram shows where the Knowledge Mapper operates within the Knowledge Engine ecosystem. As an example, it shows how a SPARQL data source can be connected with a simple configuration file and a single command:

![architecture diagram](./docs/img/architecture.png)

## How do I use it?

1. Install `knowledge_mapper` in a Python environment with `pip`:

```bash
pip install knowledge_mapper
```

2. Make a configuration file (e.g. `config.json`) that defines the knowledge interactions and mappings from your data source. (See [the examples linked here](./examples/README.md).)

3. Start your Knowledge Mapper:

```bash
python -m knowledge_mapper config.json
```

## Configuration

The minimal configuration looks like this:
```jsonc
{
  // The endpoint where a knowledge engine is available.
  "knowledge_engine_endpoint": "http://localhost:8280/rest",
  "knowledge_base": {
    // An URL representing the identity of this knowledge base
    "id": "https://example.org/a-knowledge-base",
    // A name for this knowledge base
    "name": "Some knowledge base",
    // A description for this knowledge base
    "description": "This is just an example."
  },

  "knowledge_interactions": [
    // Several knowledge interaction definitions can be placed here.
  ]
}
```

In the `knowledge_interaction` property, you can add the definitions of your knowledge interactions, including their graph patterns.

Let's add a knowledge interaction that expresses that we have knowledge available about trees:

```jsonc
{
  // ...
  "knowledge_interactions": [
    {
      // The type of this knowledge interaction. If we have knowledge
      // available that is requestable, the type should be "answer".
      "type": "answer",
      // The graph pattern that expresses the 'shape' of our knowledge.
      "pattern": "?tree <https://example.org/hasHeight> ?height . ?tree <https://example.org/hasName> ?name .",
      // A list of variables used in the pattern above. (This is redundant and will be removed in a future version.)
      "vars": ["tree", "height", "name"]
    },
  ]
}
```

However, at this point the knowledge mapper will not know where to get this knowledge! So let's add this to the configuration too. Let's assume we have the data about the trees in a SQL database.

```jsonc
{
  // ...

  // Connection details for the SQL database
  "sql_host": "sql-db",
  "sql_port": 3306,
  "sql_database": "treedb",
  "sql_user": "user",
  "sql_password": "password",

  "knowledge_interactions": [
    {
      // ...

      // SQL query to query data to be used to fill bindings for the graph pattern.
      // Note that the column names in the result set "tree" and "height" must 
      // correspond with the variable names in the graph pattern.
      "sql_query": "SELECT id AS tree, height, name FROM trees"
    },
  ]
}
```

Notice the similarity between this SQL-query and the graph pattern defined in the knowledge interaction above.
The knowledge mapper maps the variables in the SQL results to graph pattern variables in the knowledge interaction.
For example, SQL variable **height** becomes **?height** in the graph pattern (i.e., objects for predicate <https://example.org/hasHeight>).

With this configuration (see [here](examples/sql-mapper/config.json) for the entire file) we can start the Knowledge Mapper:

```
python -m knowledge_mapper examples/sql-mapper/config.json
```

The Knowledge Mapper will now continuously listen for incoming knowledge requests, and answer them by using the given SQL query and mapping them to bindings for the graph pattern.

### Authorization with deny-unless-permit policy

In order for another knowledge base to request a knowledge interaction, authorization can be set using the boolean configuration property `authorization_enabled`. This is an optional setting which means that if the property is absent no authorization is being applied and all knowledge interactions are permitted.

If the property is set to `true`, a deny-unless-permit policy is being applied. Then, for every knowledge interaction, a `permitted` list can be added that indicates which knowledge bases are permitted to request that knowledge interaction.

There are some special cases for the values of this `permitted` list:
- If this list is absent or empty, NO knowledge bases are permitted.
- If the list equals `*`, ALL knowledge bases are permitted.

For all other cases, the `permitted` list contains the ids of the knowledge bases that are permitted.

The configuration file below gives an example of authorization enabled and a knowledge interaction with a permitted list with a single other knowledge base. 

## Configuration

### SQL

See [the example config for SQL data sources](examples/sql-mapper/config.json).

### SPARQL

See [the example config for SPARQL data sources](examples/sparql-mapper/config.json).

### Custom data source

See [the example config for a custom data source](custom-conf/config.json).

# Development instructions

## Testing

There's unit tests in the Python package that require a TKE runtime to be running at port 8082:
```bash
# Start the TKE runtime
docker run -d --rm -p 8280:8280 --name tke-runtime ci.tno.nl/tke/knowledge-engine/smart-connector-rest-dist:1.1.0
# Perform the unit tests
pytest

# Stop the TKE runtime
docker stop tke-runtime
```

There's also an example setup that acts like an integration test. See [examples/README.md](examples/README.md).


# Developer instructions

These are instructions for developers that work on the Knowledge Mapper project.

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
