# Historial de commits — trips-upload-poc

Registro cronológico de cambios del repositorio desde el inicio del POC.

| Commit | Fecha* | Task | Descripción |
|--------|--------|------|-------------|
| `bc179d3` | inicio | — | Primer commit del repositorio |
| `e4ff7a7` | — | T04 | Scaffold inicial: Function App, health endpoint, `.gitignore`, `host.json`, specs |
| `9918ad0` | — | T04 | Reestructura: blueprints `api/v1/`, servicios, models, `docs/`, `config.py` |
| `8ab033e` | — | — | README completo con arquitectura, flujo, API y roadmap |
| `3996fa7` | — | — | Upgrade a Python 3.13 + `.python-version` |
| `86e9615` | — | T05 | Settings Pydantic, logging JSON estructurado, correlation ID |
| `3684ee4` | — | T06 | Pytest harness, fixtures, 10 unit tests baseline |
| `5370a25` | — | T07 | Modelos Pydantic: session, complete, trip_log, trip_event |
| `6c7c768` | — | T08 | Auth JWT mock con PyJWT |
| `0dcd94f` | — | T09 | BlobStorageService: SAS, paths, Azurite |
| `73716ae` | — | T10 | CosmosService: CRUD trip_ingestion_log |
| `e52dfc9` | — | T11 | EventHubService: publish TripEvent |
| `2e2cdda` | 2026-05-22 | T12 | Endpoint POST /api/upload/session + UploadSessionService + docs/history.md |
| `261e21b` | 2026-05-22 | T13 | Endpoint POST /api/upload/complete + validación + Event Hub publish |

\* Fechas no incluidas en commits tempranos; ver `git log` para timestamps exactos.

---

## Leyenda de fases

| Fase | Tasks | Estado |
|------|-------|--------|
| 1 — Infra Azure | T01–T03 | Pendiente (Portal) |
| 2 — Scaffold | T04–T06 | ✅ |
| 3 — Modelos | T07 | ✅ |
| 4 — Servicios core | T08–T11 | ✅ |
| 5 — Endpoints HTTP | T12–T13 | ✅ |
| 6 — Observabilidad | T14–T15 | Pendiente |
| 7 — E2E + docs | T16–T18 | Pendiente |

---

*Actualizar este archivo al cierre de cada task con commit y push.*
