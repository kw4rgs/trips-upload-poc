# Trips Upload POC — Material para presentación

> Fuente para NotebookLM u otras herramientas de diapositivas. Complementa [`README.md`](../README.md) y [`poc-architecture.md`](poc-architecture.md).

## 1. Contexto y objetivo

**Proyecto:** Trips Upload POC (G2K Suite Labs)  
**Qué es:** Gateway serverless en Azure Functions para ingestión de datos de viajes desde app móvil.  
**Problema:** Al terminar un viaje, la app genera archivos grandes (GPS, IMU, Bluetooth, metadata). Enviarlos por una API tradicional satura la Function App, causa timeouts y escala mal.  
**Solución:** La API no transporta archivos. Coordina la subida: emite URLs firmadas (SAS), la app sube directo a Blob Storage, y la API valida + persiste metadata + publica un evento.  
**Alcance del POC:** Termina en la publicación del evento. Los workers que procesan GPS/IMU/BT están fuera de alcance.

---

## 2. Actores del sistema

- **App móvil:** Solicita sesión, sube archivos, confirma complete.
- **Upload Service (Azure Functions):** Orquesta SAS, validación, Cosmos, eventos.
- **Blob Storage:** Almacena archivos binarios/JSON.
- **Cosmos DB:** Metadata operacional del viaje (`trip_ingestion_log`).
- **Event Hub (prod) / Kafka (local):** Bus de eventos para workers downstream.
- **Application Insights:** Telemetría y logs estructurados.

---

## 3. Arquitectura de alto nivel

```
App móvil
   │  POST /session (JWT + route_id)
   ▼
Function App ──► Cosmos DB (trip log RECEIVED)
   │  responde SAS URLs
   ▼
App móvil ──PUT directo──► Blob Storage (4 archivos)
   │
   │  POST /complete (checksums + sizes)
   ▼
Function App ──valida──► Blob
            ──actualiza──► Cosmos (PUBLISHED)
            ──publica──► Event Hub / Kafka
```

**Principio clave:** Los archivos grandes nunca pasan por la Function App.

---

## 4. Flujo paso a paso

### Paso 1 — Crear sesión

- **Request:** `POST /api/upload/session` con `{ "route_id": "..." }`
- **Auth:** `Authorization: Bearer <token>`
- **Respuesta 201:** `upload_session_id`, `route_id`, 4 SAS URLs (gps, imu, bt, metadata), `expires_at`
- **Backend:** Crea documento en Cosmos con status `RECEIVED`, genera SAS write-only (15 min TTL)

### Paso 2 — Subir archivos (app móvil → Blob)

- **4 requests PUT** (uno por archivo), cada uno a su SAS URL
- **Header obligatorio:** `x-ms-blob-type: BlockBlob`
- **No llevan Authorization** — la SAS es la credencial
- **Respuesta esperada:** HTTP 201 Created
- **Importante:** 1 PUT = 1 archivo. No se puede subir los 4 en un solo PUT.

### Paso 3 — Completar upload

- **Request:** `POST /api/upload/complete` con `route_id`, `upload_session_id`, lista de archivos (name, size, checksum MD5)
- **Backend:** Valida existencia, tamaño y checksum en Blob; actualiza Cosmos; publica evento JSON
- **Respuesta 200:** `validation_status: VALIDATED` si todo OK; 409 si falla validación

---

## 5. Los cuatro tipos de archivo por viaje

Cada viaje tiene exactamente **4 archivos** (POC actual):

| Tipo | Archivo | Formato |
|------|---------|---------|
| GPS | gps.json | JSON |
| IMU | imu.bin | Binario |
| Bluetooth | bt.json | JSON |
| Metadata | metadata.json | JSON |

Un `route_id` identifica el viaje. Los 4 archivos son piezas del mismo viaje, no viajes distintos.

---

## 6. Identificadores importantes

| Campo | Rol |
|-------|-----|
| `route_id` | Identificador del viaje. Partition key en Cosmos. Partition key del evento. |
| `upload_session_id` | ID único de cada intento de upload (`sess_<uuid>`). ID del documento en Cosmos. |
| `correlation_id` | Trazabilidad end-to-end en logs (`x-correlation-id`). |
| `event_id` | `evt_{upload_session_id}`. Se asigna al completar con éxito. Sirve para deduplicar eventos. |

**Regla crítica en complete:** `route_id` y `upload_session_id` deben ser **exactamente** los devueltos en la respuesta del session.

---

## 7. Cosmos DB — trip_ingestion_log

**Partition key:** `/route_id`  
**Document id:** `upload_session_id`

### Ciclo de vida del status

```
RECEIVED → VALIDATING → VALIDATED → PUBLISHED
                    └──► FAILED

(downstream, futuro) → PROCESSING → SUCCESS | FAILED
```

### Cuándo se llenan campos clave

- **Session:** status `RECEIVED`, `event_id` null, flags `gps_exists` false
- **Complete exitoso:** status `PUBLISHED`, `event_id` = `evt_sess_...`, flags en true

**Nota:** Consumir mensajes en Kafka/Event Hub **no** actualiza Cosmos. Eso lo harían workers downstream (no implementados).

---

## 8. Blob Storage — convención de paths

El cliente **no construye rutas**. Las recibe en la respuesta del session.

```
landing/source={gps|imu|bt|metadata}/year=YYYY/month=MM/day=DD/{timestamp}_{userId}_{routeId}_{archivo}
```

---

## 9. Evento publicado (TripEvent)

Metadata only — **sin payloads binarios**.

Campos principales: `event_id`, `correlation_id`, `route_id`, `upload_session_id`, `user_id`, `trip_date`, `uploaded_at`, `available_sources`, `trip_storage_root`, `trip_file_prefix`.

Workers downstream usan este evento para saber **qué procesar** y **dónde leerlo** en Blob.

---

## 10. Kafka local vs Event Hub producción

| | Local | Producción |
|--|-------|------------|
| Broker | Kafka (Docker :9092) | Azure Event Hub |
| Topic/Hub | `trip-processing` | `trip-processing-eventhub` |
| SDK | kafka-python | Azure Event Hubs AMQP SDK |
| Auth | Ninguna | Managed Identity |
| Mensaje | Mismo JSON `TripEvent` | Mismo JSON `TripEvent` |
| Partition key | `route_id` | `route_id` |

Kafka local **simula el rol** de Event Hub. El contrato del mensaje es idéntico; cambia la infraestructura y el SDK.

---

## 11. Entorno local (Docker Compose)

| Servicio | Puerto | Uso |
|----------|--------|-----|
| Azurite | 10000 | Emula Blob Storage |
| Cosmos Emulator | 8081 | Metadata trip_ingestion_log |
| Kafka | 9092 | Eventos locales |
| Kafka UI | 8090 | Ver topics y mensajes |
| Cosmos UI shortcut | 8082 | Redirect al Explorer |

**Variable clave:** `ENVIRONMENT=local` activa emuladores + Kafka.

**Auth local simplificada:** `Authorization: Bearer local-dev-token` (sin generar JWT).

---

## 12. API resumida

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/health | Liveness |
| POST | /api/upload/session | Crea sesión, SAS, trip log |
| POST | /api/upload/complete | Valida blobs, publica evento |

---

## 13. Idempotencia

- **Complete con status PUBLISHED:** reintentar devuelve VALIDATED sin republicar evento.
- **event_id determinístico:** `evt_{upload_session_id}` evita duplicados en consumidores.
- **Nueva session con mismo route_id:** crea **nuevo** upload_session_id y **nuevo** trip log.

---

## 14. Demo end-to-end (checklist)

1. `docker compose up -d`
2. `func start`
3. POST /upload/session → guardar `upload_session_id`, `route_id`, SAS URLs
4. 4× PUT a Blob con archivos de [`samples/`](../samples/) (body File, header `x-ms-blob-type`)
5. POST /upload/complete con sizes/checksums de `manifest.json`
6. Verificar: Cosmos → PUBLISHED + event_id; Kafka UI → mensaje JSON

---

## 15. Fuera de alcance (POC)

- Workers GPS / IMU / BT
- Auth real (Entra / Auth0)
- Terraform / IaC
- App móvil
- Múltiples archivos por tipo — hoy es 1 por tipo
- Un solo documento Cosmos por route_id — hoy es 1 por upload_session_id

---

## 16. Mensajes clave para diapositivas

1. **La API coordina, no transporta.**
2. **SAS = la app sube directo a la nube.**
3. **Cosmos = estado del viaje; Blob = archivos; Kafka/Event Hub = aviso a procesadores.**
4. **El POC termina cuando se publica el evento.**
5. **Local usa Kafka; producción usa Event Hub — mismo mensaje, distinto broker.**
