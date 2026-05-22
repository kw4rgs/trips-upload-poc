# Azure Portal — Checklist de recursos (T01–T03)

**Task ID:** trips-upload-poc  
**Scope:** Infraestructura manual (Portal o Azure CLI) — sin Terraform  
**Cuándo:** En paralelo o antes de desplegar la Function App (T12+)

Marca cada ítem cuando esté listo. Anota nombres reales si difieren del POC.

---

## Fase A — Base

- [ ] **A1. Resource Group**
  - Nombre sugerido: `rg-g2k-suite-labs`
  - Región: la misma que el resto de recursos G2K/labs
  - Tags opcionales: `project=trips-upload-poc`, `env=lab`

---

## Fase B — Storage (blobs de viaje)

- [ ] **B1. Storage Account**
  - Nombre sugerido: `satripsuploadpoc` (globalmente único, solo minúsculas y números)
  - Performance: Standard
  - Redundancy: LRS (suficiente para POC)
  - Habilitar **Blob Storage**

- [ ] **B2. Container**
  - Nombre: `landing`
  - Access level: Private

- [ ] **B3. Permisos para Function App (después de crear FA)**
  - Managed Identity de la Function App → rol **Storage Blob Data Contributor** en esta cuenta
  - (Necesario para User Delegation SAS)

---

## Fase C — Cosmos DB (metadata `trip_ingestion_log`)

- [ ] **C1. Azure Cosmos DB account**
  - API: **Core (SQL)**
  - Nombre: elegir uno (ej. `cosmos-trips-upload-poc`)
  - Capacity mode: Serverless o Provisioned (POC: serverless si está disponible en la región)

- [ ] **C2. Database**
  - Nombre sugerido: `trips`

- [ ] **C3. Container**
  - Nombre: `trip_ingestion_log`
  - Partition key: `/route_id`
  - Throughput: default / serverless

- [ ] **C4. Permisos Function App**
  - MI → rol **Cosmos DB Built-in Data Contributor** (o equivalente para SQL API con MI)

---

## Fase D — Event Hub (verificar existente)

- [ ] **D1. Namespace**
  - Verificar que existe: `backendnodeeventhub`
  - Si no existe: crear Event Hubs namespace Standard

- [ ] **D2. Event Hub**
  - Nombre: `trip-processing-eventhub`
  - Partitions: 2–4 (POC)

- [ ] **D3. Consumer groups** (para workers futuros; no los implementa este POC)
  - [ ] `gps-consumer`
  - [ ] `imu-consumer`
  - [ ] `bt-consumer`

- [ ] **D4. Permisos Function App**
  - MI → rol **Azure Event Hubs Data Sender** en el namespace o hub

- [ ] **D5. Connection info**
  - Anotar namespace FQDN y nombre del hub para `local.settings.json`

---

## Fase E — Observabilidad

- [ ] **E1. Application Insights**
  - Nombre sugerido: `ai-trips-upload-poc`
  - Workspace: Log Analytics (crear nuevo o usar existente)

- [ ] **E2. Copiar connection string**
  - Guardar `APPLICATIONINSIGHTS_CONNECTION_STRING` para configuración local/deploy

---

## Fase F — Function App (Upload Service)

- [ ] **F1. Function App**
  - Nombre sugerido: `func-trips-upload-poc` (único globalmente)
  - Runtime: **Python 3.11**
  - Plan: Consumption (Y1) o Premium según política del lab
  - OS: Linux
  - Vincular a Application Insights (E1)

- [ ] **F2. Storage para Functions runtime**
  - Usar la misma `satripsuploadpoc` o cuenta dedicada (requerido por Azure Functions)

- [ ] **F3. Managed Identity**
  - Habilitar **System-assigned managed identity**
  - Anotar `principalId` / Object ID para asignar roles (B3, C4, D4)

- [ ] **F4. Application settings** (en Portal → Configuration, post-deploy)
  - `STORAGE_ACCOUNT_NAME`
  - `STORAGE_CONTAINER=landing`
  - `COSMOS_ENDPOINT`
  - `COSMOS_DATABASE=trips`
  - `COSMOS_CONTAINER=trip_ingestion_log`
  - `EVENTHUB_NAME=trip-processing-eventhub`
  - `EVENTHUB_FULLY_QUALIFIED_NAMESPACE` (si usás MI sin connection string)
  - `JWT_MOCK_SECRET` (POC)
  - `SAS_TTL_MINUTES=15`
  - `APPLICATIONINSIGHTS_CONNECTION_STRING`

- [ ] **F5. CORS** (si la app móvil llama directo a la API en lab)
  - Configurar orígenes permitidos en Function App → CORS

---

## Fase G — Validación manual (DoD infra)

- [ ] **G1.** Desde Portal: container `landing` visible y accesible con MI de prueba
- [ ] **G2.** Cosmos: insertar/leer un documento de prueba en `trip_ingestion_log`
- [ ] **G3.** Event Hub: ver métricas de namespace; permiso de send OK
- [ ] **G4.** Application Insights: recibir un evento de prueba desde Function App
- [ ] **G5.** Todos los roles MI asignados (Blob, Cosmos, Event Hubs)

---

## Valores para copiar a `local.settings.json`

Cuando tengas los recursos, completá (ver `local.settings.json.example` en la raíz del repo):

| Variable | Dónde obtenerla |
|----------|-----------------|
| `AzureWebJobsStorage` | Connection string cuenta storage (runtime Functions) |
| `STORAGE_ACCOUNT_NAME` | Nombre cuenta blobs |
| `COSMOS_ENDPOINT` | Cosmos → Keys → URI |
| `COSMOS_DATABASE` | `trips` |
| `COSMOS_CONTAINER` | `trip_ingestion_log` |
| `EVENTHUB_NAME` | `trip-processing-eventhub` |
| `EVENTHUB_FULLY_QUALIFIED_NAMESPACE` | `{namespace}.servicebus.windows.net` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights → Properties |

---

## Notas

- **Event Hub existente:** Si `backendnodeeventhub` ya está en otro RG, solo verificá permisos; no hace falta recrearlo.
- **POC no incluye workers:** Los consumer groups son para validar que el hub está listo; el código del POC termina al publicar el evento.
- **Orden recomendado:** A → B → E → F (MI) → C → D → asignar roles → G

*Checklist alineado con spec.md, plan.md y tasks T01–T03*
