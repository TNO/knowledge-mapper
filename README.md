# Knowledge Mapper

## Demoing

```
docker compose up --build --force-recreate --scale data-source-1=0
```

Note the `--scale data-source-1=0` to exclude the test data source, because we want to add it via the wizard.

And then visit `http://localhost` in your browser.

Use the following graph pattern:

```
?a <http://example.org/predicate-1> ?b .
```

And the following json data in a file (see example_bindings.json above):

```
[
  {"a": "<http://example.org/subject-from-mapper-1>", "b": "<http://example.org/object-from-mapper-1>"},
  {"a": "<http://example.org/subject-from-mapper-2>", "b": "<http://example.org/object-from-mapper-2>"},
  {"a": "<http://example.org/subject-from-mapper-3>", "b": "<http://example.org/object-from-mapper-3>"},
  {"a": "<http://example.org/subject-from-mapper-4>", "b": "<http://example.org/object-from-mapper-4>"}
]
```

## Development

Start the development environment (Knowledge Engine and two other knowledge bases):
```bash
docker compose up --build --force-recreate -d knowledge-engine data-sink-1 data-source-1
```

Start the Knowledge Mapper configuration API:
```bash
cd ./api
python manage.py migrate
KE_ENDPOINT=http://localhost:8280/rest python manage.py runserver
```

Start the Knowledge Mapper in "wizard" mode:
```bash
cd ./mapper
KM_API=http://localhost:8000/km KE_ENDPOINT=http://localhost:8280/rest python -m knowledge_mapper ignored --wizard
```

Start the frontend that configures the Knowledge Mapper through the configuration API:
```bash
cd ./web
npm run dev
```
