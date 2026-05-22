# Azure Portal — Tu to-do list (T01–T03)

**Estado del código:** ✅ **T04–T18 completos** (repo listo para deploy)  
**Tu trabajo pendiente:** ⬜ **T01–T03** — crear infra en Azure Portal y asignar roles MI  
**Scope:** Manual (Portal o CLI) — sin Terraform

Marca cada ítem. Anota nombres/IDs reales en la columna **Mis valores**.

---

## Resumen rápido — orden de ejecución

```
1. Resource Group
2. Storage Account + container landing
3. Application Insights
4. Function App (Python 3.13) + habilitar Managed Identity  ← anotar Object ID
5. Cosmos DB (database + container)
6. Event Hub (verificar existente o crear)
7. Asignar 3 roles RBAC a la MI de la Function App
8. Application Settings en Function App
9. Deploy código (func azure functionapp publish)
10. Validación manual (curl + App Insights)
```

---

## Matriz RBAC — Managed Identity de la Function App

Asignar **después** de crear la Function App (F3) y **antes** del deploy.

| # | Recurso Azure | Rol RBAC | Scope (asignar en) | Para qué lo usa el código |
|---|---------------|----------|--------------------|---------------------------|
| R1 | Storage Account `satripsuploadpoc` | **Storage Blob Data Contributor** | Cuenta de storage | User Delegation SAS, validar blobs |
| R2 | Cosmos DB account | **Cosmos DB Built-in Data Contributor** | Cuenta Cosmos DB | CRUD `trip_ingestion_log` |
| R3 | Event Hubs namespace `backendnodeeventhub` | **Azure Event Hubs Data Sender** | Namespace (o el hub) | `publish_trip_event()` |

**Portal:** Resource → Access control (IAM) → Add role assignment → Managed identity → seleccionar `func-trips-upload-poc`.

**CLI (ejemplo):**
```bash
# Variables — reemplazar con tus IDs
FA_PRINCIPAL_ID="<object-id-managed-identity>"
STORAGE_ID="/subscriptions/<sub>/resourceGroups/rg-g2k-suite-labs/providers/Microsoft.Storage/storageAccounts/satripsuploadpoc"
COSMOS_ID="/subscriptions/<sub>/resourceGroups/rg-g2k-suite-labs/providers/Microsoft.DocumentDB/databaseAccounts/cosmos-trips-upload-poc"
EH_NAMESPACE_ID="/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.EventHub/namespaces/backendnodeeventhub"

az role assignment create --assignee-object-id $FA_PRINCIPAL_ID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope $STORAGE_ID
az role assignment create --assignee-object-id $FA_PRINCIPAL_ID --assignee-principal-type ServicePrincipal --role "Cosmos DB Built-in Data Contributor" --scope $COSMOS_ID
az role assignment create --assignee-object-id $FA_PRINCIPAL_ID --assignee-principal-type ServicePrincipal --role "Azure Event Hubs Data Sender" --scope $EH_NAMESPACE_ID
```

---

## Fase A — Resource Group (T01)

- [ ] **A1. Resource Group**
  - Nombre sugerido: `rg-g2k-suite-labs`
  - Región: misma que el resto de recursos G2K/labs
  - Tags: `project=trips-upload-poc`, `env=lab`
  - **Mis valores:** ___________________________

---

## Fase B — Storage (T01)

- [ ] **B1. Storage Account**
  - Nombre: `satripsuploadpoc` (globalmente único)
  - Performance: Standard · Redundancy: LRS
  - **Mis valores:** ___________________________

- [ ] **B2. Container `landing`**
  - Access level: **Private**

- [ ] **B3. Rol R1** — MI Function App → **Storage Blob Data Contributor** en B1

- [ ] **B4. Anotar connection string** (para `AzureWebJobsStorage` runtime Functions)

---

## Fase C — Cosmos DB (T02)

- [ ] **C1. Cosmos DB account**
  - API: **Core (SQL)**
  - Nombre sugerido: `cosmos-trips-upload-poc`
  - Mode: Serverless (POC) o Provisioned
  - **Mis valores:** ___________________________

- [ ] **C2. Database:** `trips`

- [ ] **C3. Container:** `trip_ingestion_log`
  - Partition key: **`/route_id`**

- [ ] **C4. Rol R2** — MI Function App → **Cosmos DB Built-in Data Contributor** en C1

- [ ] **C5. Anotar** `COSMOS_ENDPOINT` (Cosmos → Keys → URI)

---

## Fase D — Event Hub (T03)

- [ ] **D1. Namespace** — verificar `backendnodeeventhub` (puede estar en otro RG)

- [ ] **D2. Event Hub:** `trip-processing-eventhub` (2–4 partitions)

- [ ] **D3. Consumer groups** (workers futuros — no los implementa este POC)
  - [ ] `gps-consumer`
  - [ ] `imu-consumer`
  - [ ] `bt-consumer`

- [ ] **D4. Rol R3** — MI Function App → **Azure Event Hubs Data Sender** en namespace

- [ ] **D5. Anotar** `EVENTHUB_FULLY_QUALIFIED_NAMESPACE` = `{namespace}.servicebus.windows.net`

---

## Fase E — Application Insights (T03)

- [ ] **E1. Application Insights:** `ai-trips-upload-poc`
  - Vinculado a Log Analytics workspace

- [ ] **E2. Anotar** `APPLICATIONINSIGHTS_CONNECTION_STRING`

---

## Fase F — Function App (T03)

- [ ] **F1. Crear Function App**
  - Nombre: `func-trips-upload-poc`
  - Runtime: **Python 3.13** · OS: **Linux**
  - Plan: Consumption (Y1) o Premium (lab)
  - Storage runtime: cuenta B1
  - Vincular App Insights E1

- [ ] **F2. Managed Identity**
  - Habilitar **System-assigned**
  - Anotar **Object (principal) ID:** ___________________________

- [ ] **F3. Asignar roles R1, R2, R3** (si no lo hiciste arriba)

- [ ] **F4. Application Settings** (Configuration)

| Setting | Valor POC | Mis valores |
|---------|-----------|-------------|
| `FUNCTIONS_WORKER_RUNTIME` | `python` | |
| `AzureWebJobsStorage` | Connection string storage | |
| `STORAGE_ACCOUNT_NAME` | `satripsuploadpoc` | |
| `STORAGE_CONTAINER` | `landing` | |
| `COSMOS_ENDPOINT` | URI Cosmos | |
| `COSMOS_DATABASE` | `trips` | |
| `COSMOS_CONTAINER` | `trip_ingestion_log` | |
| `EVENTHUB_NAME` | `trip-processing-eventhub` | |
| `EVENTHUB_FULLY_QUALIFIED_NAMESPACE` | `{ns}.servicebus.windows.net` | |
| `JWT_MOCK_SECRET` | Secreto fuerte (≥32 chars) | |
| `JWT_MOCK_USER_ID` | `user456` (POC) | |
| `SAS_TTL_MINUTES` | `15` | |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | De E2 | |

- [ ] **F5. CORS** (opcional — si app móvil llama directo al lab)

- [ ] **F6. Deploy código**
  ```bash
  func azure functionapp publish func-trips-upload-poc
  ```

---

## Fase G — Validación (DoD infra)

- [ ] **G1.** `GET /api/health` → 200
- [ ] **G2.** `POST /api/upload/session` con JWT mock → 201 + SAS URLs
- [ ] **G3.** Upload blob vía SAS + `POST /api/upload/complete` → 200
- [ ] **G4.** Documento visible en Cosmos `trip_ingestion_log`
- [ ] **G5.** Evento visible en Event Hub (metrics / explorer)
- [ ] **G6.** Traces en App Insights con `correlation_id`
- [ ] **G7.** IAM: 3 role assignments activos para la MI

Ver curl detallado en [`runbook.md`](runbook.md).

---

## Local dev (opcional — sin Azure completo)

| Emulador | Puerto | Para qué |
|----------|--------|----------|
| Azurite | 10000 | Blob (`AzureWebJobsStorage`) |
| Cosmos Emulator | 8081 | Cosmos CRUD |

Tests integration hacen skip si emuladores no están corriendo.

---

## Qué NO tenés que crear

- ❌ Workers GPS / IMU / BT
- ❌ Terraform / IaC
- ❌ Auth0 / Entra (POC usa JWT mock)
- ❌ API Management / Front Door (opcional futuro)

---

## Estado tasks código vs Azure

| Tasks | Quién | Estado |
|-------|-------|--------|
| T01–T03 | **Vos** — Azure Portal | ⬜ Pendiente |
| T04–T18 | Repo / CI | ✅ Completo |

*Última actualización: post T18 — ver [`history.md`](history.md)*
