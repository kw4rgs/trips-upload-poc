# Specification: POC Carga y Procesamiento de Viajes

**Task ID:** trips-upload-poc  
**Created:** 2026-05-22  
**Status:** Ready for Planning  
**Version:** 1.0  
**Governance:** `constitution.md` (immutable)

---

## 1. Problem Statement

- **The Problem:** La app móvil genera archivos grandes (GPS, IMU, BT, metadata) al finalizar un viaje. Enviarlos por API backend es costoso, lento y no escala.
- **Current Situation:** Datos generados localmente; una única carga al terminar el viaje.
- **Desired Outcome:** Carga directa a Blob con SAS temporal, validación de integridad en backend, metadata persistida, evento publicado en Event Hub para procesamiento asíncrono downstream.

## 2. User Personas

### Primary User: App móvil
- **Who:** Cliente que finaliza un viaje y sube datos
- **Goals:** Subir archivos de forma segura sin pasar por API; confirmar carga exitosa
- **Pain points:** Timeouts, payloads grandes, reintentos sin idempotencia

### Secondary User: Operador / plataforma
- **Who:** Equipo que monitorea el POC
- **Goals:** Trazabilidad por viaje, logs estructurados, métricas en App Insights
- **Pain points:** Falta de correlation_id, imposibilidad de reconstruir flujos

### Downstream: Workers (GPS / IMU / BT)
- **Who:** Consumidores Event Hub por consumer group
- **Goals:** Recibir evento con metadata y referencias a blobs — no payloads binarios
- **Pain points:** Eventos sin `trip_storage_root` o `trip_file_prefix`

## 3. Functional Requirements

### FR-1: Autenticación JWT
**Description:** Validar identidad en endpoints de upload.

**User Story:**
> As a mobile app, I want to authenticate with JWT so that only authorized users can request upload sessions.

**Acceptance Criteria:**
- [ ] Given request without Bearer token, when calling upload endpoints, then 401
- [ ] Given valid JWT mock (POC), when calling endpoints, then user_id extracted from token
- [ ] JWT mock configurable; evolución futura a Auth0 / Entra / Firebase

**Priority:** Must Have

### FR-2: Crear sesión de upload
**Description:** `POST /api/upload/session` genera SAS y metadata de sesión.

**User Story:**
> As a mobile app, I want temporary write-only SAS URLs so that I can upload files directly to Blob Storage.

**Acceptance Criteria:**
- [ ] Given valid JWT and `route_id`, when POST session, then 201 with `upload_session_id`, `correlation_id`, `expires_at`
- [ ] Response includes SAS per source: gps, imu, bt, metadata
- [ ] SAS: write-only, 15 min TTL, paths definidas por API (cliente no construye rutas)
- [ ] Blob naming: `{timestampZulu}_{userId}_{routeId}_{source}.{ext}`
- [ ] Path structure: `landing/source={source}/year=/month=/day=/`

**Priority:** Must Have

### FR-3: Carga directa a Blob
**Description:** App sube archivos usando SAS — sin transitar Function App.

**User Story:**
> As a mobile app, I want to upload imu.bin, gps.json, bt.json, metadata.json directly to storage.

**Acceptance Criteria:**
- [ ] Files uploaded via SAS URLs returned in FR-2
- [ ] No large payloads pass through Upload Service API

**Priority:** Must Have

### FR-4: Confirmar carga completada
**Description:** `POST /api/upload/complete` valida integridad.

**User Story:**
> As a mobile app, I want to notify upload completion so that the backend validates and triggers processing.

**Acceptance Criteria:**
- [ ] Given uploaded blobs, when POST complete with files[{name, size, checksum}], then validate existence, size, checksum
- [ ] Result: VALIDATED or FAILED with per-file detail
- [ ] Idempotent: reintentos no duplican evento si ya PUBLISHED

**Priority:** Must Have

### FR-5: Persistencia trip_ingestion_log
**Description:** Metadata operacional en Cosmos DB.

**User Story:**
> As platform, I want trip state persisted separately from blob files for traceability.

**Acceptance Criteria:**
- [ ] Collection: `trip_ingestion_log`, partition key: `/route_id`
- [ ] Fields: route_id, correlation_id, upload_session_id, status, validation_status, gps/imu/bt exists, timestamps
- [ ] States: RECEIVED → VALIDATING → VALIDATED → PUBLISHED → (downstream: PROCESSING, SUCCESS, PARTIALLY_PROCESSED, FAILED)

**Priority:** Must Have

### FR-6: Publicación Event Hub
**Description:** Tras validación exitosa, publicar evento con metadata.

**User Story:**
> As platform, I want an event published so downstream workers can process by data type.

**Acceptance Criteria:**
- [ ] Event published to `trip-processing-eventhub` after VALIDATED
- [ ] Schema per FR-7 — metadata only, no binary payloads
- [ ] POC scope ends here — worker execution out of scope

**Priority:** Must Have

### FR-7: Esquema de evento
**Description:** Contrato tipado del evento Event Hub.

```json
{
  "event_id": "evt_98765",
  "correlation_id": "corr_abc123",
  "trip_id": "98765",
  "route_id": "aaa-4567",
  "user_id": "123",
  "upload_session_id": "sess_9f2a1c",
  "trip_date": "2026-05-19",
  "uploaded_at": "2026-05-19T10:30:00Z",
  "available_sources": ["gps", "imu", "bt"],
  "trip_storage_root": "landing/year=2026/month=05/day=05/",
  "trip_file_prefix": "20260505T121314Z_123_aaa-4567"
}
```

**Priority:** Must Have

### FR-8: Observabilidad
**Description:** Application Insights + structured logging.

**Acceptance Criteria:**
- [ ] Logs include route_id, correlation_id, operation, status
- [ ] App Insights: errors, dependencies, duration, throughput
- [ ] No `print()` — constitution §6

**Priority:** Must Have

### FR-9: Estrategia de reintentos (documentada)
**Description:** App móvil y backend — app fuera de implementación backend POC.

**App móvil (referencia):** 1→0s, 2→2s, 3→4s, 4→8s, 5→30s; persistencia SQLite cifrada.

**Backend:** Event Hub checkpoint/replay; workers idempotentes; error-storage tras límite.

**Priority:** Should Have (documentación)

## 4. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | session/complete < 2s p95 POC |
| Security | SAS write-only 15min; MI default; no permanent credentials exposed |
| Scalability | Direct-to-blob; async via Event Hub |
| Observability | correlation_id propagation end-to-end |
| Contracts | Pydantic models mandatory |
| Stack | Python, Azure Functions, Blob, Cosmos DB, Event Hub, App Insights, Functions Core Tools local |

## 5. Azure Resources (from SDD)

| Resource | Name | Notes |
|----------|------|-------|
| Resource Group | `rg-g2k-suite-labs` | |
| Storage Account | `satripsuploadpoc` | Container `landing` |
| Event Hub | `backendnodeeventhub` / `trip-processing-eventhub` | Existente |
| Consumer Groups | gps-consumer, imu-consumer, bt-consumer | Pre-existentes |
| Application Insights | `ai-trips-upload-poc` | |
| Function App | Upload Service | 2 HTTP triggers |

## 6. Out of Scope

- ❌ **Workers GPS/IMU/BT implementation** — solo contrato de evento; POC termina en publicación Event Hub
- ❌ **Producción multi-región, CI/CD, ML, Databricks**
- ❌ **Seguridad avanzada, alta disponibilidad**
- ❌ **Terraform** — infra manual Portal/CLI
- ❌ **Login/JWT issuer production** — POC usa JWT mock
- ❌ **Procesamiento post-Event Hub**

## 7. Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Blob no existe en complete | FAILED; detalle por archivo; log con correlation_id |
| Size mismatch | FAILED validation for that file |
| Checksum mismatch | FAILED validation |
| SAS expirado | Cliente debe solicitar nueva sesión |
| Duplicate complete (idempotent) | 200; no re-publicar evento |
| Cosmos unavailable | 503; log error; no partial publish |
| Event Hub publish fails | Rollback status; retryable error |

| Error | HTTP | System Action |
|-------|------|---------------|
| Invalid JWT | 401 | Reject; log attempt |
| Invalid route_id / body | 400 | Pydantic validation error |
| Session not found | 404 | |
| Already published | 409 or 200 idempotent | Skip re-publish |

## 8. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| E2E POC demo | Complete flow works | Login mock → session → blob upload → complete → Cosmos → Event Hub |
| Acceptance criteria SDD §12 | 100% verifiable | Checklist manual / E2E test |
| No large files via API | Zero | Architecture review |
| Logs traceable | Every operation has correlation_id | App Insights query |

## 9. Architecture Context (reference)

```
Usuario → Login → JWT → Upload Service → SAS → App → Blob
→ upload/complete → validación → trip_ingestion_log (Cosmos)
→ Event Hub → [GPS | IMU | BT Workers — out of scope POC]
```

## 10. Open Questions

- [x] Persistencia metadata → **Cosmos DB** `trip_ingestion_log`, PK `/route_id`
- [x] Auth POC → **JWT mock**
- [ ] Algoritmo checksum exacto mobile ↔ backend (default: SHA256 hex)

## 11. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-22 | Initial specification |

## Next Steps

1. Review spec with stakeholders
2. Run `/plan trips-upload-poc` — **done:** see `plan.md`
3. Run `/tasks trips-upload-poc` — **done:** see `tasks.md`

*Specification created with SDD 5.1*
