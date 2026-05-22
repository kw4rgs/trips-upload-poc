# Historial de commits — trips-upload-poc

Registro cronológico de cambios del repositorio desde el inicio del POC.

| Commit | Fecha | Task | Descripción |
|--------|-------|------|-------------|
| `bc179d3` | inicio | — | Primer commit del repositorio |
| `e4ff7a7` | — | T04 | Scaffold inicial: Function App, health, specs |
| `9918ad0` | — | T04 | Reestructura: `api/v1/`, services, models, docs |
| `8ab033e` | — | — | README completo |
| `3996fa7` | — | — | Upgrade Python 3.13 |
| `86e9615` | — | T05 | Settings, logging JSON, correlation ID |
| `3684ee4` | — | T06 | Pytest harness + baseline tests |
| `5370a25` | — | T07 | Modelos Pydantic |
| `6c7c768` | — | T08 | JWT mock auth |
| `0dcd94f` | — | T09 | BlobStorageService + Azurite |
| `73716ae` | — | T10 | CosmosService CRUD |
| `e52dfc9` | — | T11 | EventHubService |
| `2e2cdda` | 2026-05-22 | T12 | POST /api/upload/session |
| `261e21b` | 2026-05-22 | T13 | POST /api/upload/complete |
| `69d315e` | 2026-05-22 | — | History metadata |
| `ac80885` | 2026-05-22 | — | History self-entry |
| `d5c9064` | 2026-05-22 | T14 | App Insights OpenTelemetry |
| `1038e9c` | 2026-05-22 | T15 | Structured HTTP errors |
| `c598e50` | 2026-05-22 | T16–T18 | E2E test, runbook, README final |

---

## Leyenda de fases

| Fase | Tasks | Estado |
|------|-------|--------|
| 1 — Infra Azure | T01–T03 | Pendiente (Portal) |
| 2 — Scaffold | T04–T06 | ✅ |
| 3 — Modelos | T07 | ✅ |
| 4 — Servicios core | T08–T11 | ✅ |
| 5 — Endpoints HTTP | T12–T13 | ✅ |
| 6 — Observabilidad | T14–T15 | ✅ |
| 7 — E2E + docs | T16–T18 | ✅ |

---

*Actualizar este archivo al cierre de cada task con commit y push.*
