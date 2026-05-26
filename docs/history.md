# Historial de commits — trips-upload-poc

Registro cronológico de cambios del repositorio desde el inicio del POC.

| Commit | Fecha | Task | Descripción |
|--------|-------|------|-------------|
| `bc179d3` | inicio | — | Primer commit del repositorio |
| `e4ff7a7` | — | T04 | Scaffold inicial: Function App, health, specs |
| `9918ad0` | — | T04 | Reestructura: `api/v1/`, services, models, docs |
| `8ab033e` | — | — | README completo |
| `4a95cd7` | — | — | Upgrade Python 3.13 |
| `7645992` | — | T05 | Settings, logging JSON, correlation ID |
| `b2c1894` | — | T06 | Pytest harness + baseline tests |
| `cebb808` | — | T07 | Modelos Pydantic |
| `7b4348e` | — | T08 | JWT mock auth |
| `4a5d38d` | — | T09 | BlobStorageService + Azurite |
| `5eefff7` | — | T10 | CosmosService CRUD |
| `17df9ec` | — | T11 | EventHubService |
| `9f8f272` | 2026-05-22 | T12 | POST /api/upload/session |
| `c91c746` | 2026-05-22 | T13 | POST /api/upload/complete |
| `c2ab492` | 2026-05-22 | — | History metadata |
| `9b8becb` | 2026-05-22 | — | History self-entry |
| `d74cb47` | 2026-05-22 | T14 | App Insights OpenTelemetry |
| `ebf3399` | 2026-05-22 | T15 | Structured HTTP errors |
| `d4a34eb` | 2026-05-22 | T16–T18 | E2E test, runbook, README final |
| `055be20` | 2026-05-22 | FX-01–05 | Security & correctness fixes: JWT ownership, atomic publish, Cosmos etag, health probe, 503 sanitization |
| `19648e7` | 2026-05-22 | — | History metadata for FX-01–05 |
| `ee4ffff` | 2026-05-22 | v1.1.0 | Local stack abstraction — Kafka + docker-compose |
| `74bf113` | 2026-05-22 | — | Cosmos emulator amd64 for Apple Silicon (Rosetta) |
| `170cedc` | 2026-05-22 | — | Cosmos emulator vnext-preview (ARM64 native) |
| `fa66156` | 2026-05-22 | — | Cosmos vnext HTTP on 8081 (no TLS) |
| `d869ab3` | 2026-05-22 | — | Revert Cosmos to GA emulator + Explorer UI |
| `ca218e3` | 2026-05-22 | — | Bitnami Kafka KRaft + kafka-ui (ARM64) |
| `2cb3b0a` | 2026-05-22 | — | Switch to apache/kafka official image (KRaft) |
| `731b631` | 2026-05-22 | — | Kafka internal/external listeners for kafka-ui |
| `d1918e4` | 2026-05-22 | — | cosmos-ui nginx redirect for Docker Desktop |
| `934167a` | 2026-05-22 | — | Remove unused Cosmos gateway port 8900 |
| `364e1be` | 2026-05-22 | — | README local Docker stack, env routing, UIs |
| `8c65654` | 2026-05-26 | — | Local predefined token auth (`JWT_LOCAL_TOKEN`) |
| `4b8bb18` | 2026-05-26 | — | Sample trip uploads (May/June 2026) + manifests |
| `03df94d` | 2026-05-26 | — | Presentation source + README local testing guide; history catch-up |
| `090d255` | 2026-05-26 | — | History entry for presentation and README commit |

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
