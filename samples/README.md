# Trip upload samples

Archivos de prueba para Insomnia, curl y Azure. Cada carpeta incluye los 4 blobs del viaje más un `manifest.json` con `route_id`, `size` y `checksum` para el complete.

## Estructura

| Carpeta | Mes | Viajes | `route_id` sugerido |
|---------|-----|--------|---------------------|
| [`trip-upload/`](trip-upload/) | genérico | 1 | `route-demo-001` |
| [`2026-05/trip-001/`](2026-05/trip-001/) | Mayo 2026 | 1 | `route-2026-05-001` |
| [`2026-06/trip-001/`](2026-06/trip-001/) | Junio 2026 | 1 | `route-2026-06-001` |
| [`2026-06/trip-002/`](2026-06/trip-002/) | Junio 2026 | 1 | `route-2026-06-002` |

Las fechas dentro de `gps.json` y `metadata.json` coinciden con el mes del viaje. Al subir a Blob, la ruta real (`year=/month=/day=`) la define la API en el momento del **session** (timestamp del servidor), no la fecha del sample — los samples sirven para distinguir contenido y `route_id` en Cosmos/Kafka.

## Flujo

1. Elegí una carpeta y usá su `route_id` en `POST /api/upload/session`
2. PUT de `gps.json`, `imu.bin`, `bt.json`, `metadata.json` (File body en Insomnia)
3. `POST /api/upload/complete` con `route_id`, `upload_session_id` y el array `files` de `manifest.json`
