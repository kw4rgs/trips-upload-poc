# trips-upload-poc

Azure Functions upload gateway — Blob SAS, Cosmos metadata, Event Hub publish.

## Structure

```
trips_upload/
├── function_app.py          # Entrypoint — registers api/v1 blueprints
├── api/v1/                  # HTTP blueprints (health, upload/session, upload/complete)
├── services/                # blob_storage, cosmos_db, event_hub, auth
├── models/                  # Pydantic schemas
├── config.py                # Settings
├── shared/                  # logging, correlation
├── tests/
└── docs/                    # constitution, architecture, implementation plan
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.json.example local.settings.json
func start
curl http://localhost:7071/api/health
```

## Docs

| File | Description |
|------|-------------|
| [docs/constitution.md](docs/constitution.md) | Immutable project rules |
| [docs/poc-architecture.md](docs/poc-architecture.md) | Architecture & requirements |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Tasks T01–T18 |
| [docs/azure-portal-checklist.md](docs/azure-portal-checklist.md) | Azure Portal setup |
| [docs/technical-plan.md](docs/technical-plan.md) | Technical design detail |
