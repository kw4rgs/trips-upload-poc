# Fix & Optimization Plan — trips-upload-poc

**Created:** 2026-05-22  
**Based on:** Full codebase review (post T04–T18 completion)  
**Reviewer:** AI code review pass  
**Status:** Pending implementation

---

## Overview

Post-implementation review identified **3 critical bugs**, **6 high-priority best-practice violations**, and several medium/low quality improvements. Tasks below are numbered `FX-01` through `FX-17` and grouped by priority.

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 3 | Bugs with security or correctness impact |
| HIGH | 6 | Best-practice violations affecting reliability or security |
| MEDIUM | 7 | Observability, quality, and standard gaps |
| LOW | 1 | Refactor / cleanup |

---

## Phase 1 — CRITICAL: Bugs & Security

### FX-01 — Authorization: JWT ownership not enforced on `/upload/complete`

**Severity:** CRITICAL — Security  
**Files:** `api/v1/upload_complete.py:29`, `services/upload_complete_service.py:58-63`

**Problem:**  
`authenticate_request()` is called but its return value (`user_id`) is discarded. Any bearer with a valid JWT can invoke `/complete` for any `route_id` + `upload_session_id` they do not own — triggering validation, blob reads, and Event Hub publishes on another user's data.

**Fix:**
- Return `user_id` from `authenticate_request()` in the blueprint handler.
- Pass `user_id` into `UploadCompleteService.complete_upload()`.
- In the service, after fetching the `TripLog`, assert `trip_log.user_id == caller_user_id`; raise a new `TripOwnershipError` (403) otherwise.
- Add corresponding unit test: `test_complete_upload_rejects_wrong_owner`.

**Acceptance criteria:** A request with a valid JWT but mismatched `user_id` returns HTTP 403.

---

### FX-02 — Idempotency: publish → PUBLISHED is not atomic (double-publish risk)

**Severity:** CRITICAL — Correctness  
**File:** `services/upload_complete_service.py:90-96`

**Problem:**  
Current order: `publish_trip_event()` succeeds → `update_trip_log(status=PUBLISHED)` fails → on retry the short-circuit checks `status == PUBLISHED` but it is still `VALIDATED`, so Event Hub receives a duplicate event.

**Fix (minimal for POC):**
- Before publishing, generate a deterministic `event_id = f"{upload_session_id}:complete"`.
- Store `event_id` on the `TripLog` atomically via a conditional Cosmos patch *before* publishing.
- Only publish if the Cosmos write succeeded.
- On retry, if `event_id` is already set, skip publish and mark `PUBLISHED`.

**Fix (production-grade):**  
Transactional outbox pattern: write event to Cosmos in same transaction, relay to Event Hub asynchronously.

**Acceptance criteria:** Two consecutive calls for the same session produce exactly one Event Hub event.

---

### FX-03 — Race condition: concurrent `/complete` calls can both publish

**Severity:** CRITICAL — Correctness  
**File:** `services/upload_complete_service.py:65-96`

**Problem:**  
No distributed lock or conditional write guards the `VALIDATED → VALIDATING → PUBLISHED` state machine. Two simultaneous requests both pass the `status == PUBLISHED` check and both publish.

**Fix:**
- Use Cosmos DB optimistic concurrency: fetch the `TripLog` with its `_etag`, pass `if_match=etag` on every `replace_item()` call.
- On `CosmosHttpResponseError` (412 Precondition Failed), raise a retriable conflict exception and return 409.
- Add `CONFLICT` `ErrorCode` to responses.

**Acceptance criteria:** The second concurrent request returns 409; only one event is published.

---

## Phase 2 — HIGH: Best Practices & Reliability

### FX-04 — Health endpoint missing `auth_level=ANONYMOUS` (probe breakage)

**Severity:** HIGH — Reliability  
**File:** `api/v1/health.py:12`

**Problem:**  
`FunctionApp()` has no app-wide `http_auth_level`. Upload routes explicitly set `auth_level=func.AuthLevel.ANONYMOUS`, but the health route does not. In Azure the default is `FUNCTION`, which requires `x-functions-key` — breaking load-balancer and container probes.

**Fix:**
```python
# api/v1/health.py
@health_bp.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
```

**Acceptance criteria:** `/api/health` returns 200 without any key header in Azure.

---

### FX-05 — Health response uses unsafe f-string JSON construction

**Severity:** HIGH — Security / Correctness  
**File:** `api/v1/health.py:24-27`

**Problem:**  
`correlation_id` is interpolated directly into a raw JSON string. A crafted or malformed value breaks the response or injects extra fields.

**Fix:** Replace with `json_response()` (already available in `shared/http.py`):
```python
return json_response({"status": "ok", "correlation_id": get_correlation_id()}, status_code=200)
```

**Acceptance criteria:** Any `correlation_id` value produces valid JSON.

---

### FX-06 — Azure SDK clients recreated per request (cold start / latency)

**Severity:** HIGH — Performance  
**Files:** `api/v1/upload_session.py:65`, `api/v1/upload_complete.py:61`

**Problem:**  
`UploadSessionService()` and `UploadCompleteService()` are instantiated inside the handler, which triggers construction of `BlobStorageService`, `CosmosService`, `EventHubService`, and their underlying Azure SDK clients on every invocation.

**Fix:**
- Create module-level service singletons in `function_app.py` using `lru_cache`-wrapped factories or direct module assignment.
- Inject them into handlers via closure or pass as parameters to the blueprint constructors.

**Acceptance criteria:** Azure SDK clients are constructed once per worker process, not once per request.

---

### FX-07 — `EventHubProducerClient` not reused between invocations

**Severity:** HIGH — Performance / Resource leak  
**File:** `services/event_hub.py:57-60`

**Problem:**  
When `self._producer` is `None`, a new `EventHubProducerClient` is created on every `publish_trip_event()` call and never closed — leaking connections over time.

**Fix:**
- Initialize `_producer` lazily once in `__init__` or on first call.
- Store it as an instance attribute; reuse across calls.
- In production, implement `close()` for graceful shutdown.

**Acceptance criteria:** A single `EventHubProducerClient` instance is reused across multiple publishes within the same worker lifecycle.

---

### FX-08 — `AzureWebJobsStorage` triggers account-key SAS in production

**Severity:** HIGH — Security (violates constitution §3: MI by default)  
**Files:** `services/blob_storage.py:107-110`, `config.py:21-25`

**Problem:**  
`BlobStorageService` checks `azure_webjobs_storage` to decide between account-key SAS (Azurite) and user-delegation SAS (prod). But in production `AzureWebJobsStorage` is always set (required by the Functions runtime), so the code silently falls back to account-key SAS — bypassing Managed Identity.

**Fix:**
- Introduce a dedicated `USE_AZURITE=true` env var (or `AZURE_FUNCTIONS_ENVIRONMENT=Development` detection) to gate local emulator paths.
- Use `DefaultAzureCredential()` exclusively for SAS generation in prod regardless of `AzureWebJobsStorage`.

**Acceptance criteria:** In Azure (no `USE_AZURITE`), `BlobStorageService` always uses user-delegation SAS via MI.

---

### FX-09 — 503 responses expose internal exception messages

**Severity:** HIGH — Security  
**Files:** `api/v1/upload_session.py:80-84`, `api/v1/upload_complete.py:83-87`

**Problem:**  
`message=str(exc)` on catch-all handlers forwards raw Python exception text (file paths, config keys, SDK error details) to HTTP clients.

**Fix:**
```python
logger.error("Unexpected error", exc_info=True)
return json_response({"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."}, status_code=503)
```

**Acceptance criteria:** 503 responses contain only a generic message; full exception appears in Application Insights.

---

## Phase 3 — MEDIUM: Quality & Observability

### FX-10 — Cosmos `replace_item` without optimistic concurrency

**Severity:** MEDIUM — Correctness  
**File:** `services/cosmos_db.py:101-104`

**Problem:**  
`replace_item()` uses no `if_match` etag → last-writer-wins under any concurrent write.

**Fix:** Persist and pass `_etag` from `get_trip_log()` through to every `update_trip_log()` call; raise 409 on mismatch.

---

### FX-11 — Validation failures in `/complete` not logged

**Severity:** MEDIUM — Observability  
**File:** `api/v1/upload_complete.py:46-53`

**Problem:**  
`upload_session.py` logs Pydantic validation errors at WARNING; `upload_complete.py` silently returns 422 with no server-side log entry.

**Fix:** Add `logger.warning("Request validation failed", extra={"errors": exc.errors()})` in the `except ValidationError` block.

---

### FX-12 — Idempotent `/complete` response fabricates file results

**Severity:** MEDIUM — Correctness  
**File:** `services/upload_complete_service.py:204-214`

**Problem:**  
When a replayed request hits `status == PUBLISHED`, the response fabricates four `VALID` file results without reading what was actually validated.

**Fix:** Persist the `file_results` list on `TripLog` at validation time; return the stored snapshot on replay.

---

### FX-13 — `requirements.txt` uses open version ranges

**Severity:** MEDIUM — Reproducibility  
**File:** `requirements.txt`

**Problem:**  
Ranges like `azure-functions>=1.21.0` allow supply-chain drift between environments and CI runs.

**Fix:** Pin exact versions after validating locally:
```
azure-functions==1.21.3
pydantic==2.11.5
# ...
```
Or adopt `pip-compile` (pip-tools) to generate a lockfile from loose requirements.

---

### FX-14 — No unit tests for `shared/checksum.py`

**Severity:** MEDIUM — Test coverage  
**File:** `tests/unit/` (missing `test_checksum.py`)

**Problem:**  
The checksum fallback path in `upload_complete_service.py:138-148` (download blob when MD5 metadata is absent) has no test coverage.

**Fix:** Add `tests/unit/test_checksum.py` with cases for: valid hex, wrong hex, correct match, mismatch, empty bytes, and the download-fallback path mocked in `test_upload_complete_service.py`.

---

### FX-15 — `trip_id` derivation via string `removeprefix` is fragile

**Severity:** MEDIUM — Maintainability  
**File:** `services/upload_complete_service.py:191`

**Problem:**  
`trip_id = upload_session_id.removeprefix("sess_")` couples `trip_id` semantics to the session ID prefix forever.

**Fix:** Generate `trip_id = str(uuid.uuid4())` independently at session creation time and store it on `TripLog`; read it back at complete time instead of deriving it.

---

### FX-16 — `jwt_mock_user_id` setting unused in production auth path

**Severity:** MEDIUM — Dead config / confusion  
**Files:** `config.py:41-42`, `services/auth.py`

**Problem:**  
`Settings.jwt_mock_user_id` is only used by `tests/conftest.py`. It has no effect on actual JWT validation, making the config misleading.

**Fix:** Remove from `Settings`; expose only in `tests/conftest.py` as a local constant, or document clearly as test-only.

---

### FX-17 — E2E tests not excluded from default `pytest` run

**Severity:** LOW — CI hygiene  
**File:** `pytest.ini`, `tests/e2e/test_upload_flow.py:18`

**Problem:**  
`pytest.ini` defines the `e2e` marker but does not exclude it from `addopts`, so `pytest` runs E2E tests by default even though they mock heavily and could be reserved for a dedicated stage.

**Fix:**
```ini
[pytest]
addopts = -ra -m "not e2e"
```
Run E2E explicitly with `pytest -m e2e`.

---

## Implementation Order

```
Priority 1 (CRITICAL — implement first)
  FX-01  JWT ownership on /complete
  FX-02  Atomic publish / event_id
  FX-03  Cosmos etag concurrency

Priority 2 (HIGH — before any Azure deployment)
  FX-04  health auth_level=ANONYMOUS
  FX-05  health json_response
  FX-08  AzureWebJobsStorage vs prod MI
  FX-09  Sanitize 503 messages
  FX-06  SDK client singletons
  FX-07  EventHub producer reuse

Priority 3 (MEDIUM — quality hardening)
  FX-10  Cosmos replace_item with etag
  FX-11  Log validation failures in /complete
  FX-12  Persist file_results on TripLog
  FX-13  Pin requirements.txt
  FX-14  test_checksum.py + fallback coverage
  FX-15  trip_id generated independently
  FX-16  Remove jwt_mock_user_id from Settings

Priority 4 (LOW)
  FX-17  Exclude e2e from default pytest run
```

---

## Effort Estimate

| Priority | Tasks | Estimated effort |
|----------|-------|-----------------|
| CRITICAL | 3 | ~4–6 h |
| HIGH | 6 | ~3–4 h |
| MEDIUM | 7 | ~3–5 h |
| LOW | 1 | ~15 min |
| **Total** | **17** | **~10–15 h** |

---

## Notes

- All fixes must include corresponding tests (unit or integration where applicable).
- Before each fix group: `git add . && git commit && git push` (constitution §2 workflow).
- Fixes FX-01, FX-02, FX-03 are interdependent — implement in order.
- FX-08 requires local validation with Azurite before merging.
