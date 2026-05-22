# Runbook — trips-upload-poc

Guía operativa para levantar, probar y desplegar el Upload Service.

---

## 1. Prerrequisitos

- Python 3.13
- Azure Functions Core Tools v4
- Cuenta Azure con recursos del POC ([azure-portal-checklist.md](azure-portal-checklist.md))
- Opcional local: [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) (Blob) y Cosmos Emulator

---

## 2. Setup local

```bash
git clone git@github.com:kw4rgs/trips-upload-poc.git
cd trips-upload-poc
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp local.settings.json.example local.settings.json
```

Completar `local.settings.json` con valores de tu entorno lab.

---

## 3. Generar JWT mock (POC)

```python
from services.auth import create_mock_token
token = create_mock_token("user-test", "<JWT_MOCK_SECRET>")
print(token)
```

---

## 4. Levantar Function App

```bash
func start
```

---

## 5. Demo curl

### Health

```bash
curl http://localhost:7071/api/health
```

### Crear sesión de upload

```bash
export JWT="<token>"
export CORR="corr_demo001"

curl -X POST http://localhost:7071/api/upload/session \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -H "x-correlation-id: $CORR" \
  -d '{"route_id":"route-demo-001"}'
```

Respuesta **201**: `upload_session_id`, SAS URLs por source, `expires_at`.

### Subir archivos a Blob

Usar las SAS URLs devueltas (PUT directo desde la app móvil o curl).

### Confirmar upload

```bash
curl -X POST http://localhost:7071/api/upload/complete \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -H "x-correlation-id: $CORR" \
  -d '{
    "route_id": "route-demo-001",
    "upload_session_id": "<upload_session_id>",
    "files": [
      {"name": "gps.json", "size": 123, "checksum": "<md5-hex>"},
      {"name": "imu.bin", "size": 456, "checksum": "<md5-hex>"},
      {"name": "bt.json", "size": 789, "checksum": "<md5-hex>"},
      {"name": "metadata.json", "size": 100, "checksum": "<md5-hex>"}
    ]
  }'
```

---

## 6. Tests

```bash
pytest                          # unit + integration (skip si no hay emuladores)
pytest tests/unit -v            # solo unit
pytest tests/integration -m integration
pytest tests/e2e -m e2e
```

---

## 7. Emuladores locales (opcional)

### Azurite

```bash
azurite --silent --blobHost 127.0.0.1 --blobPort 10000
```

En `local.settings.json`:

```json
"AzureWebJobsStorage": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUz1HT2LtL7vADFjPUPE=;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
```

### Cosmos DB Emulator

Endpoint: `https://localhost:8081/` — ver documentación Microsoft para certificado.

---

## 8. Deploy Azure

1. Completar checklist Portal ([azure-portal-checklist.md](azure-portal-checklist.md))
2. Function App Python 3.13 + Managed Identity
3. Application Settings (ver `local.settings.json.example`)
4. Asignar roles MI: Blob, Cosmos, Event Hub
5. `func azure functionapp publish func-trips-upload-poc`

---

## 9. Observabilidad

- Logs estructurados JSON en stdout / App Insights
- OpenTelemetry se activa cuando `APPLICATIONINSIGHTS_CONNECTION_STRING` está configurado
- Dimensiones custom: `correlation_id`, `route_id`, `upload_session_id`

Query ejemplo en App Insights:

```kusto
traces
| where customDimensions.correlation_id == "corr_demo001"
| order by timestamp desc
```

---

## 10. Documentación relacionada

| Doc | Contenido |
|-----|-----------|
| [constitution.md](constitution.md) | Reglas inmutables |
| [poc-architecture.md](poc-architecture.md) | Requisitos y arquitectura |
| [implementation-plan.md](implementation-plan.md) | Tasks T01–T18 |
| [history.md](history.md) | Historial de commits |
| [technical-plan.md](technical-plan.md) | Diseño técnico |
