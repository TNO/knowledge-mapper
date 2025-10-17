# Knowledge Mapper examples

This is a docker-compose project that demonstrates 3 ways in which you can configure a Knowledge Mapper:

- __`sql-mapper`__: This service maps data from the database running in the `mariadb` service. The `mariadb` service has a table with trees, containing their heights and names. The Knowledge Mapper's [configuration](./sql-mapper/config.jsonc) specifies how the data can be queried (with SQL) from the table and translated into terms of an example ontology.
- __`sparql-mapper`__: This service maps data from the triple store in the `fuseki` service.
 The `fuseki` service contains RDF data about trees. The Knowledge Mapper's [configuration](./sparql-mapper/config.jsonc) specifies how to connect to the triple store (with SPARQL) and what data is in there.
- __`custom-mapper`__: This service shows that it is also possible to plug in your own code if you need more flexibility in your Knowledge Mapper. You might want to use this if you want to disclose data from a web API. In this case, it simply returns knowledge about a maple tree.

Apart from these three knowledge mappers, the project also contains the following data sources (mentioned above):

- `sql-db`: An SQL database that contains data about trees. See [this file](./sql-db/seed_data/0-schema.sql) for the schema and [this file](./sql-db/seed_data/1-data.sql) for the seed data.
- `fuseki`: A triple store that is approachable with SPARQL. The data content is in [this file](./fuseki/data/data.ttl)

Then there is a service `tree-printer`, which registers itself as a knowledge base and asks for knowledge about the trees. When receiving this, it prints it.

Last but not least is the __`tke-runtime`__ service, which takes care of all interoperability.

## Running the example

To run the example, do the following:

```bash
# Make sure older containers (if any) are removed, so we start fresh.
docker-compose down

# Start all services.
docker-compose up -d 

# Look at the logs of tree-printer so we can see the trees.
docker-compose logs -f tree-printer

# Shut everything down again.
docker-compose down
```

You will see that the `tree-printer` receives knowledge about trees coming from the 3 different Knowledge Mappers.
This shows that Knowledge Mappers can be used with relative ease to disclose different data sources into a unified model.

Note: to receive all 5 expected trees you need to give the `tree-printer` access to the data from `dynamic-auth`. You can use `adminer` to add the knowledge base id `https://example.org/tree-printer` and knowledge interaction id `https://example.org/a-custom-knowledge-base-with-dyn-auth/interaction/answer-trees-with-heights-and-names` to the database by going to the following URL: `http://localhost:8080/?server=auth-db&username=user&db=knowledge_mapper_db&edit=policies`.
