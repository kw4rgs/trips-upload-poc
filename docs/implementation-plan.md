# Implementation Tasks: trips-upload-poc

**Task ID:** trips-upload-poc  
**Created:** 2026-05-22  
**Status:** Ready for Implementation  
**Based on:** plan.md, spec.md, constitution.md  
**Implementation mode:** Superpowers TDD

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 22 |
| Epics | 7 (from implementation-plan) |
| Phases | 7 |
| POC boundary | Event Hub publish — workers out of scope |

---

## Phase 1: Infraestructura Azure (Épica 1)

### T01 — Resource Group y Storage
- [ ] Crear/usar RG `rg-g2k-suite-labs`
- [ ] Storage Account `satripsuploadpoc`, container `landing`
- [ ] Configurar Managed Identity en Function App (cuando exista)
- **Effort:** 2h | **Deps:** none
- **AC:** Container accesible; MI con Blob Data Contributor

### T02 — Cosmos DB
- [ ] Crear Cosmos DB account + database
- [ ] Colección `trip_ingestion_log`, partition key `/route_id`
- **Effort:** 1.5h | **Deps:** T01
- **AC:** CRUD manual de prueba OK

### T03 — Event Hub + App Insights
- [ ] Verificar namespace `backendnodeeventhub`, hub `trip-processing-eventhub`
- [ ] Consumer groups: gps-consumer, imu-consumer, bt-consumer
- [ ] Application Insights `ai-trips-upload-poc`
- [ ] Function App creada
- **Effort:** 2h | **Deps:** T01
- **AC:** Todos los recursos disponibles (DoD §9 impl plan)

---

## Phase 2: Scaffold repositorio

### T04 — Estructura repo
- [x] Crear árbol `api/v1/`, `services/`, `models/`, `shared/`, `tests/`, `docs/`
- [x] `requirements.txt`, `host.json`, `local.settings.json.example`, `config.py`
- [x] `function_app.py` + blueprints en `api/v1/`
- **Effort:** 2h | **Deps:** none
- **AC:** `func start` sin errores de import ✅

### T05 — Config y logging
- [x] Completar `config.py` (Pydantic Settings)
- [x] `shared/logging.py` + `shared/correlation.py`
- **Effort:** 1.5h | **Deps:** T04
- **AC:** Settings carga env; log format constitution-compliant

### T06 — Test harness
- [x] `tests/conftest.py`, pytest config
- **Effort:** 1h | **Deps:** T04
- **AC:** `pytest` baseline green

---

## Phase 3: Modelos Pydantic (Épica 2 prep)

### T07 — Models layer
- [x] `models/session.py` — UploadSessionResponse, UploadTarget
- [x] `models/complete.py` — UploadCompleteRequest, FileDescriptor, CompleteResponse
- [x] `models/trip_log.py` — TripLog
- [x] `models/trip_event.py` — TripEvent
- **Effort:** 2h | **Deps:** T06
- **AC:** Unit tests validación Pydantic; no dicts sueltos

---

## Phase 4: Servicios core (Épicas 3–5)

### T08 — AuthService (JWT mock)
- [x] `services/auth.py` — validate_jwt, extract user_id
- **Effort:** 1.5h | **Deps:** T05, T07
- **AC:** Unit tests: valid/invalid/expired mock token

### T09 — BlobStorageService (Épica 3)
- [ ] `generate_sas()`, `blob_exists()`, `get_blob_properties()`, `download_blob()`, `upload_blob()`
- [ ] User Delegation SAS; Azurite local
- **Effort:** 4h | **Deps:** T05
- **AC:** Integration test SAS + exists contra Azurite

### T10 — CosmosService (Épica 4)
- [ ] `create_trip_log()`, `update_trip_log()`, `get_trip_log()`, `trip_exists()`
- **Effort:** 3h | **Deps:** T07
- **AC:** Integration test CRUD (emulator o mock)

### T11 — EventHubService (Épica 5)
- [ ] `publish_trip_event()` con TripEvent schema
- **Effort:** 2h | **Deps:** T07
- **AC:** Unit test serialización; integration opcional

---

## Phase 5: Upload Service endpoints (Épica 2)

### T12 — upload_session function
- [ ] `functions/upload_session/` — POST /api/upload/session
- [ ] Wire: auth → blob paths → SAS → cosmos create
- **Effort:** 3h | **Deps:** T08, T09, T10
- **AC:** curl local 201 con SAS URLs; correlation_id en log

### T13 — upload_complete function
- [ ] `functions/upload_complete/` — POST /api/upload/complete
- [ ] Validación existencia/tamaño/checksum
- [ ] Cosmos update + EventHub publish
- [ ] Idempotencia si ya PUBLISHED
- **Effort:** 4h | **Deps:** T08, T09, T10, T11
- **AC:** Unit + integration tests all validation paths

---

## Phase 6: Observabilidad (Épica 6)

### T14 — Application Insights integration
- [ ] OpenTelemetry / azure-monitor-opentelemetry
- [ ] Dependency tracking Blob, Cosmos, Event Hub
- [ ] Custom dimensions: route_id, correlation_id, upload_session_id
- **Effort:** 2h | **Deps:** T12, T13
- **AC:** Traces visibles en App Insights lab

### T15 — Error handling HTTP
- [ ] Map errors → 400/401/404/409/503
- [ ] Structured error responses
- **Effort:** 1.5h | **Deps:** T12, T13
- **AC:** Tests por error type

---

## Phase 7: Pruebas E2E y docs (Épica 7)

### T16 — Integration tests
- [ ] Upload Service + Blob
- [ ] Upload Service + Cosmos
- [ ] Upload Service + Event Hub
- **Effort:** 3h | **Deps:** T13
- **AC:** pytest integration suite green (or skip if no Azure)

### T17 — E2E test script
- [ ] Flujo: mock JWT → session → upload blobs → complete → verify Cosmos → verify event
- **Effort:** 3h | **Deps:** T16
- **AC:** DoD implementation-plan §8 E2E diagram passes

### T18 — README y runbook
- [ ] Setup local, env vars, demo curl, Azure manual steps
- [ ] Referencias a `docs/`
- **Effort:** 1.5h | **Deps:** T17
- **AC:** Dev nuevo puede reproducir POC

---

## Dependency Graph

```
T01 → T02, T03
T04 → T05, T06
T06 → T07 → T08, T10, T11
T05 → T08, T09
T08 + T09 + T10 → T12
T08 + T09 + T10 + T11 → T13
T12 + T13 → T14, T15
T13 → T16 → T17 → T18
```

## Implementation Order

```
T01-T03  Infra Azure
    ↓
T04-T07  Repo + models
    ↓
T08-T11  Services (Blob, Cosmos, EventHub, Auth)
    ↓
T12-T13  Upload endpoints
    ↓
T14-T15  Observability + errors
    ↓
T16-T18  Tests E2E + docs
```

## Definition of Done

**Per task:** TDD red/green; constitution compliance (Pydantic, structured logs, no secrets in code)

**Feature complete:** All items in plan.md §13 Definition of Done

## Governance

- **constitution.md** is immutable — reject changes that violate it
- **spec.md** is source of truth for requirements
- **docs/** is the single documentation source for this project

---

**Next:** `Implementá T04 con Superpowers TDD` or `/implement trips-upload-poc`

*Tasks created with SDD 5.1*
