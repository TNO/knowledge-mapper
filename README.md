# Knowledge Mapper

## Demoing

```
docker compose up --build --force-recreate
```

And then visit `http://localhost` in your browser.

## Development

Start the development environment (Knowledge Engine and two other knowledge bases):
```bash
docker compose up --build --force-recreate -d knowledge-engine data-sink-1 data-source-1
```

Start the Knowledge Mapper configuration API:
```bash
cd ./api
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
