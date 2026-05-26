# Trip upload samples

Archivos de ejemplo para probar el flujo completo (Insomnia, curl, Azure).

> Más sets por mes: ver [`../README.md`](../README.md) (`2026-05/`, `2026-06/`).

| Archivo | Descripción |
|---------|-------------|
| `gps.json` | Puntos GPS con lat/lon, speed y heading |
| `imu.bin` | Muestras IMU binarias (3 frames × 6 float32) |
| `bt.json` | Dispositivos Bluetooth detectados |
| `metadata.json` | Metadata del viaje, app y device |

## Uso con Insomnia

1. `POST /api/upload/session` → copiar las 4 `sas_url`
2. `PUT` cada archivo usando su SAS URL (header `x-ms-blob-type: BlockBlob`)
3. `POST /api/upload/complete` usando `manifest.json`:

```json
{
  "route_id": "route-demo-001",
  "upload_session_id": "<tu upload_session_id>",
  "files": [
    {"name": "gps.json", "size": 622, "checksum": "d73bf6a0870e393a839fa39cba3f3c90"},
    {"name": "imu.bin", "size": 72, "checksum": "9fef63705e18a7370d12af8b498612a6"},
    {"name": "bt.json", "size": 403, "checksum": "b3a7719ba7878cbfb34b37ded2247860"},
    {"name": "metadata.json", "size": 363, "checksum": "aa2f0f49004983d44b09833938cd7ff7"}
  ]
}
```

Los valores exactos de `size` y `checksum` están en [`manifest.json`](./manifest.json).

## Regenerar checksums

Si editas algún archivo:

```bash
python3 - <<'PY'
import hashlib, json
from pathlib import Path
files = ["gps.json", "imu.bin", "bt.json", "metadata.json"]
manifest = {"description": "Sample trip upload files for local and Azure manual testing", "files": []}
for name in files:
    data = Path(name).read_bytes()
    manifest["files"].append({"name": name, "size": len(data), "checksum": hashlib.md5(data, usedforsecurity=False).hexdigest()})
Path("manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
PY
```
