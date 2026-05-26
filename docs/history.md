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
| `c4b8da5` | 2026-05-22 | FX-01–05 | Security & correctness fixes: JWT ownership, atomic publish, Cosmos etag, health probe, 503 sanitization |
| `d1b52f6` | 2026-05-22 | — | History metadata for FX-01–05 |
| `3a8d68f` | 2026-05-22 | v1.1.0 | Local stack abstraction — Kafka + docker-compose |
| `dc7467e` | 2026-05-22 | — | Cosmos emulator amd64 for Apple Silicon (Rosetta) |
| `4fbd118` | 2026-05-22 | — | Cosmos emulator vnext-preview (ARM64 native) |
| `d8fc77f` | 2026-05-22 | — | Cosmos vnext HTTP on 8081 (no TLS) |
| `db9804b` | 2026-05-22 | — | Revert Cosmos to GA emulator + Explorer UI |
| `8940c3e` | 2026-05-22 | — | Bitnami Kafka KRaft + kafka-ui (ARM64) |
| `7674cd1` | 2026-05-22 | — | Switch to apache/kafka official image (KRaft) |
| `bf7ed3a` | 2026-05-22 | — | Kafka internal/external listeners for kafka-ui |
| `2b18a18` | 2026-05-22 | — | cosmos-ui nginx redirect for Docker Desktop |
| `fadbc36` | 2026-05-22 | — | Remove unused Cosmos gateway port 8900 |
| `292b1fc` | 2026-05-22 | — | README local Docker stack, env routing, UIs |
| `1917b16` | 2026-05-26 | — | Local predefined token auth (`JWT_LOCAL_TOKEN`) |
| `f8b1ca0` | 2026-05-26 | — | Sample trip uploads (May/June 2026) + manifests |

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
