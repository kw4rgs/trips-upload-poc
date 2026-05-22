# Constitution — trips-upload-poc

**Status:** Immutable — overrides implementation decisions  
**Version:** 1.0

> Este documento define reglas permanentes del proyecto. Tiene prioridad sobre decisiones de implementación específicas.

## 1. Objetivo

- Mantener consistencia
- Reducir deuda técnica
- Facilitar escalabilidad y mantenimiento
- Desacoplar componentes
- Facilitar trabajo con agentes y equipos

## 2. Principios generales

### 2.1 Bajo acoplamiento
Los componentes se comunican mediante contratos bien definidos. Evitar dependencias directas innecesarias y lógica compartida duplicada.

### 2.2 Separación de responsabilidades
Cada componente tiene una única responsabilidad. Upload Service: autenticación, SAS, validación, publicación de eventos. No procesa payloads pesados ni lógica de negocio externa.

### 2.3 El backend coordina
Clientes móviles: solicitan sesiones, cargan archivos, notifican eventos. No construyen rutas internas, nombres físicos, estructura de almacenamiento ni gestionan credenciales Azure.

## 3. Seguridad

- Nunca exponer Storage Keys, Connection Strings, secretos Azure ni credenciales administrativas
- Solo SAS temporales, JWT y Managed Identity
- Mínimo privilegio en SAS: escritura única, tiempo limitado, recursos específicos
- Managed Identity por defecto cuando Azure lo soporte

## 4. Manejo de datos

- Payloads grandes nunca viajan por mensajería — solo metadata, referencias e identificadores
- Persistencia inmediata — no procesar solo en memoria
- Metadata operacional separada de archivos físicos (estado, correlation_id, upload_session_id, timestamps)

## 5. Contratos

- Contratos tipados obligatorios con **Pydantic** — no dict arbitrarios
- Versionar contratos incompatibles: `v1/upload/session`, `v2/upload/session`

## 6. Observabilidad

- Logging estructurado obligatorio — no `print()`
- `correlation_id` obligatorio en APIs, eventos, logs, almacenamiento y procesamiento
- Trazabilidad completa vía `route_id`, `correlation_id`, timestamps

## 7. Diseño de APIs

- APIs stateless
- Validación temprana: JWT, estructura, tamaños, tipos, integridad

## 8. Código

- Configuración vía env / Settings / Secret Store — nunca hardcodeada
- Lógica compartida como servicios reutilizables (`BlobStorageService`, `CosmosService`, `EventHubService`)
- Idempotencia en operaciones con reintentos

## 9. Evolución futura

La arquitectura debe permitir reemplazar Event Hub, Cosmos DB, Azure Functions y proveedores de auth sin afectar contratos funcionales ni componentes externos.

## 10. Regla principal

Optimizar: simplicidad, mantenibilidad, desacoplamiento, observabilidad, escalabilidad. Evitar complejidad prematura.
