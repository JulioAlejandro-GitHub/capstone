# SCC-ART.1 — Acceso HTTP a artefactos científicos

Estado documental: `CURRENT_DOC`. Fecha: 2026-10-15.
Estado de entrega: **implementado y probado automáticamente; certificación operativa HTTP autenticada/navegador pendiente**.
Base: rama `main`, HEAD `c9aad366d48731366440c941ffed722948c7f7d3`. Sin commit ni push.

## Problema y solución

CAPSTONE-REPORTS-01A identificó dos causas confirmadas en el código: `/artifacts/file`
consultaba únicamente `artifacts`, mientras EXPLAIN registra sus UUID en
`assessment_artifacts`; además la lista histórica de raíces no incluía assessments.
El frontend enviaba rutas físicas y `<img>`/enlaces no podían adjuntar el bearer.

Se amplía el endpoint existente con fuente explícita. Las consultas permanecen en
repositorio y en transacciones PostgreSQL de solo lectura. Para assessments se unen
artefacto → intento → identidad → TRAIN. Para TRAIN se une `artifacts.run_id` con
`runs.id`. No se infieren relaciones por arquitectura, fecha ni nombre de muestra.
El UUID del payload y la muestra se contrastan con las columnas del registro.

Se reutilizan el resolutor histórico para TRAIN, `LocalStorage.resolve`,
`verify_regular_file`, `require_permission`, `requestBlob`, el ciclo de vida de
`useAuthenticatedObjectUrl` y `view=traceability` de SCC-CORE.1. No se duplican las
consultas de linaje. El nuevo repositorio solo consulta un artefacto individual.

## Contrato HTTP

```text
GET /artifacts/file?artifact_id=<UUID>&source=assessment
    [&attempt_id=<UUID>][&training_run_id=<UUID>][&datasource=malaria]
GET /artifacts/file?artifact_id=<UUID>&source=training
```

`source=training` es el valor predeterminado compatible con consumidores anteriores.
No se busca primero en una tabla y luego en otra: incluso si hay UUID iguales,
la fuente decide exclusivamente el catálogo. `attempt_id` y `training_run_id`
son restricciones opcionales de pertenencia, nunca sustitutos del artifact ID.
El cliente compartido requiere fuente explícita y EXPLAIN envía ambas restricciones.

Se conserva `path` para consumidores históricos de imágenes sin UUID, bajo las
raíces y extensiones anteriores y con el mismo permiso. No habilita assessments
por ruta ni formatos de descarga nuevos por ruta. Las referencias con UUID tienen
precedencia sobre `path`. Los nuevos consumidores científicos deben usar UUID.
Los DTO históricos con rutas conservan su compatibilidad; el cliente EXPLAIN usa
la proyección pública `view=traceability`, que no contiene rutas.

Autorización: dependencia existente `require_permission(ARTIFACTS_READ)`, que usa
`current_principal` y roles vigentes de PostgreSQL. La política actual otorga lectura
científica por rol, no por propietario de TRAIN; no se añade otra política. Las
relaciones científicas se comprueban después de autorizar. Se conserva la semántica
configurada del sistema para `AUTH_MODE`; en el entorno comprobado es `local_jwt`.

| Resultado | HTTP / código |
|---|---|
| Bytes entregados | 200 |
| UUID/fuente inválidos | 400 `ARTIFACT_ID_INVALID` / `ARTIFACT_SOURCE_INVALID` |
| Sin sesión | 401, mecanismo existente |
| Sin `artifacts.read` | 403, mecanismo existente |
| UUID no registrado en esa fuente | 404 `ARTIFACT_NOT_REGISTERED` |
| Intento/TRAIN solicitado distinto | 404 `ARTIFACT_RELATION_MISMATCH` |
| Archivo registrado ausente | 410 `ARTIFACT_CONTENT_MISSING` |
| Tamaño o SHA-256 discrepante | 409 `ARTIFACT_INTEGRITY_FAILED` |
| Ubicación insegura/inconsistente | 409 `ARTIFACT_LOCATION_INVALID` |
| Payload científico inconsistente | 409 `ARTIFACT_RELATION_MISMATCH` |
| Tipo/firma no permitido | 415 |
| Almacenamiento inaccesible | 503 `ARTIFACT_STORAGE_UNAVAILABLE` |
| Error interno inesperado | 500, handler existente |

Los códigos de artefactos se integran en `error.code` del envelope existente.
No se envían excepciones de filesystem ni rutas al navegador. El comportamiento
histórico de errores de `path` permanece compatible.

PNG (`image/png`), JPEG (`image/jpeg`) y WebP (`image/webp`) conservan comprobación
de firma y extensión. NPY (`application/octet-stream`) comprueba firma NUMPY;
JSON (`application/json`) y CSV (`text/csv`) se permiten solo por UUID. Los formatos
no visuales usan `Content-Disposition: attachment`; imágenes, `inline`. El filename
es UUID + extensión, sin ruta. Cabeceras: `nosniff`, `private, no-store` y CSP
`default-src 'none'; sandbox`. No se habilitan checkpoints Keras ni otros formatos.

## Almacenamiento e integridad

No se añade variable de entorno. Se reutiliza `MALARIA_DL_PROJECT_ROOT` y la estructura
del productor actual: `artifacts/assessments/<attempt_id>/<artifact_id>.<ext>`.
La raíz se obtiene de ese proyecto configurado, independientemente del cwd.
Compose ya fija `/app/malaria_dl_local_project` y monta el proyecto en lectura.
`/proc/self/mountinfo` del backend confirmó el montaje y su opción `ro`.

Para una ruta histórica se exige que esté dentro del `artifact_root` registrado,
que ese root termine exactamente en `artifacts/assessments/<attempt_id>` y que
el archivo corresponda al UUID registrado. Solo ese subárbol se resuelve bajo la
raíz actual. No se aplica una sustitución general de prefijos macOS/Docker.
Se rechaza `..`; `LocalStorage` rechaza symlinks y verifica archivo regular y raíz.
El resolutor TRAIN mantiene su confinamiento canónico por componentes.

Si existe SHA-256, `verify_regular_file` valida tamaño disponible y hash mediante
lectura sin seguir symlinks del archivo final. Si falta tamaño registrado se usa
el tamaño físico únicamente para efectuar la verificación del SHA. Si no existe
SHA, se conserva la política anterior: servir archivo confinado sin certificación
criptográfica; no se inventa ni persiste hash. Ningún registro o archivo se modifica.

`.env.example` solo añade comentarios explicativos. `.env`, Compose y `.dockerignore`
no cambian. No se crean almacenamiento paralelo, migraciones ni copias de artefactos.

## Frontend reutilizable

`api.getArtifactBlob` centraliza fuente, UUID y restricciones científicas, utiliza
el bearer vigente y preserva cancelación/logout. `ScientificArtifact` ofrece carga
diferida, estado de error, PNG y descarga mediante blob URL revocada al desmontar.
Los errores de ausencia física/integridad se traducen a mensajes específicos.
`LegacyArtifactMedia` mantiene consumidores antiguos con autenticación y rechaza
URLs ajenas al origen/API esperados. El detalle TRAIN copia IDs en vez de rutas.

EXPLAIN utiliza la proyección existente sin ampliar DTOs del backend. Se conserva
su paginación y navegación. SCC-REPORT.1, SCC-REPORT.2, SCC-EXP.1 y la página SCC
pueden consumir directamente `getArtifactBlob`/`ScientificArtifact` con IDs de
SCC-CORE.1. Esas entregas no se implementan aquí.

## Evidencia operativa, 2026-10-15

Consultas SELECT dentro de `read_only_transaction`, seguidas de lectura física con
el resolutor real desde backend Docker. **No equivalen a GET autenticados reales.**

| Artefacto | PostgreSQL | Archivo accesible desde backend | Integridad | HTTP real autenticado |
|---|---|---|---|---|
| Grad-CAM `ea5dd236-0f9c-4595-869e-fc34ea157a9f` | Sí, intento `a1acbb5c-170e-437c-b310-f7be6cc671d9` | PNG, 35.712 bytes | SHA-256 coincide | Pendiente |
| LIME `34663c81-c06f-44fd-b862-6768865ee442` | Sí, intento `e7ef3690-b0cf-4c2f-8fdc-7255907fb245` | PNG, 22.762 bytes | SHA-256 coincide | Pendiente |
| SHAP `98cd7f34-2966-435d-9cfb-9ea0504d06f8` | Sí, intento `24023051-41a3-4bf9-a2a7-25f771e2a4c8` | PNG, 19.413 bytes | SHA-256 coincide | Pendiente |
| Histórico `15a1778c-4b74-4d5d-af96-40908a982baf` | Sí | Ausente; resolutor produce 410 | No verificable | Pendiente |

TRAIN `338136db-a207-47fc-bbf3-d17ce85c0dc2` existe, `completed`. Los intentos
`4703ff9e-2d20-413f-9b9a-cd945c8dd632` y `da1f46d6-0f17-46b0-8f51-9f0fcacf0c76`
pertenecen a ese TRAIN. No se confunden con los intentos de los tres PNG anteriores.
La consulta acotada de `artifacts.path LIKE '%.png'` no encontró registros; la
compatibilidad TRAIN se valida mediante fixtures, no se afirma PNG TRAIN real 200.
GET real sin bearer al proceso activo devolvió **401**.

La revisión automática rechazó generar un token para una cuenta administradora
existente por riesgo de suplantación. La acción no se ejecutó ni se sustituyó por
un bypass. Se solicitó validación desde una sesión legítima. Navegador y GET real
autenticado siguen pendientes: no se certifica el cierre operativo total.

Para completar esa comprobación: iniciar sesión normalmente, abrir
`/modelo-ia/evaluaciones/e6/a1acbb5c-170e-437c-b310-f7be6cc671d9?datasource=malaria`,
pulsar «Ver imagen» y registrar GET 200, `image/png`, bytes y visualización. Repetir
para LIME/SHAP con sus intentos y descargar NPY si está registrado. No enviar tokens
en URLs ni guardar credenciales en evidencia.

## Validación automatizada y cambios

Comando reproducible: `make test-scc-art` (Docker/Makefile). Incluye resolución,
colisión de UUID entre fuentes, relaciones, autenticación, autorización, traversal,
symlink, archivos ausentes, checksum, MIME y bytes HTTP con repositorio simulado;
regresiones LocalStorage, explainability, SCC-CORE.1, frontend y TypeScript.
No ejecuta TRAIN/EVALUATE/EXPLAIN/TEST ni fixtures con escrituras científicas.

Resultado final: **55 pruebas de artefactos/almacenamiento/explicabilidad + 75 de
SCC-CORE.1 + 35 frontend = 165 aprobadas, cero fallos**. TypeScript y
`git diff --check` correctos. Sin regresiones en las suites ejecutadas; no se afirma
cobertura de toda la aplicación. La primera ejecución
falló por ausencia de `pytest-asyncio`; se corrigió a AnyIO ya instalado, sin cambiar
dependencias. Las siguientes ejecuciones previas al cierre fueron satisfactorias.
Advertencias existentes: deprecaciones Starlette/httpx/AnyIO.

Archivos cambiados:

- `.env.example`, `Makefile`.
- `backend_api/app/main.py`, `routes/artifacts.py`, `services/artifacts.py`, nuevo `repositories/artifacts.py`.
- Nuevo `backend_api/tests/test_scc_art.py`.
- `frontend/src/services/api.ts`, `types/api.ts`.
- `frontend/src/components/reports/AssessmentExplanationDetail.tsx`, nuevos `ScientificArtifact.tsx` y `LegacyArtifactMedia.tsx`.
- `frontend/src/components/explainability/CaseExplainabilityView.tsx`.
- `frontend/src/pages/RunDetail.tsx`, `UploadedPredictions.tsx`.
- `frontend/tests/e6-lineage.test.mjs`, nuevo `scc-art.test.mjs`.
- Este documento y `docs/README.md`.

Árbol inicialmente limpio; queda con cambios locales de SCC-ART.1. Sin cambios de
rama/HEAD, commits ni pushes. PostgreSQL, artefactos, datasets y configuración
científica conservados. El estado pendiente corresponde únicamente a la evidencia
operativa autenticada y visual; el archivo histórico ausente continúa ausente.


## SCC-ART.1 FIX — Integración del reporte (2026-10-15)

Estado: **corrección implementada y pruebas aprobadas; cierre funcional pendiente
por falta de validación HTTP autenticada y visual con sesión legítima**.

### Punto de interrupción comprobado

El frontend Docker tiene montado el código actual. `AssessmentDetail` entrega el
ID del intento a `AssessmentExplanationDetail`; `useAssessmentArtifacts` consulta
`/assessments/{attempt_id}/artifacts?view=traceability&limit=100&offset=...`.
La proyección real devuelve los UUID y relaciones correctos sin rutas. No se
confirmó un fallo de catálogo ni de resolución para el PNG solicitado.

El componente `ScientificArtifact` inicializaba `requested=false` y deshabilitaba
`useAuthenticatedObjectUrl` hasta pulsar «Ver imagen»: al abrir el reporte la
cadena se detenía antes de la solicitud de bytes (pasos 4–5). Además, el PNG
solicitado ocupa la posición 480 y solo aparece en la página 5 (`offset=400`).
No se atribuye a este hallazgo un hipotético fallo posterior al clic: ese recorrido
operativo no pudo reproducirse sin una sesión legítima disponible.

### Evidencia PostgreSQL y archivo existente

Todas las consultas se ejecutaron dentro de `read_only_transaction`, sin escrituras.

- Intento `4703ff9e-2d20-413f-9b9a-cd945c8dd632`: `verified`, método `gradcam`,
  TRAIN `338136db-a207-47fc-bbf3-d17ce85c0dc2`, background vacío.
- 2.693 registros `overlay` y 2.693 registros `map`.
- Búsqueda del archivo indicado en el payload registrado: PK real
  `0a8f6c3a-c8aa-4b77-9ca1-10cafd7eeeeb`, rol `overlay`, muestra explicada
  `15964d8b-66ff-5026-91a6-3e9f26deef36`. La coincidencia del UUID del filename
  con la PK fue comprobada, no usada como mecanismo de asociación.
- El servicio de listado real devuelve ese registro entre los 100 elementos de
  `offset=400`, con `attempt_id`, `training_run_id` y `sample_id` correctos.
- El resolutor existente, con fuente `assessment` y restricciones de intento/TRAIN,
  verificó SHA-256 `227dfca2b5244c972f64f25de37403b7f5b77974bb096270408d379e81577273`,
  33.790 bytes y firma PNG `89504e470d0a1a0a`; devuelve `image/png`.
- Los intentos SHAP `24023051-41a3-4bf9-a2a7-25f771e2a4c8` y
  `96f84072-678b-48fb-8c70-3e8260b5114c` pertenecen al mismo TRAIN, tienen una
  muestra seleccionada y referencia `000f6007-9330-5085-972a-247631c541c6`.
  Estos datos son compatibles con el comando histórico, pero no identifican
  inequívocamente su intento. El comando no corresponde al intento Grad-CAM.

### Corrección y contratos reutilizados

Los `overlay` se cargan automáticamente al abrir cada página del reporte usando
`autoLoad` explícito. Los mapas conservan descarga diferida. Método y muestra
explicada acompañan a cada artefacto; SHAP muestra aparte las muestras de
`identity.explanation.background`. No se infiere ninguna muestra ausente.
Se muestra el número de página. El hook oculta resultados previos inmediatamente
al cambiar intento o página y mantiene cancelación de solicitudes.

Se reutilizan `api.getAssessmentArtifacts`, `view=traceability`,
`api.getArtifactBlob`, `requestBlob`, `/artifacts/file`, `source=assessment`,
las restricciones de intento/TRAIN y `useAuthenticatedObjectUrl` con revocación.
No se añade endpoint ni cliente. TRAIN conserva su fuente explícita y carga diferida.
Los errores 401/403 tienen mensaje de autorización; otros HTTP incluyen el estado.
Se mantienen mensajes específicos para archivo físico ausente e integridad fallida.

Archivos modificados por este FIX, sobre el trabajo local previo:

- `frontend/src/components/reports/AssessmentExplanationDetail.tsx`
- `frontend/src/components/reports/ScientificArtifact.tsx`
- `frontend/src/hooks/useAssessmentArtifacts.ts`
- `frontend/src/services/api.ts`
- `frontend/src/types/api.ts`
- `frontend/tests/scc-art.test.mjs`
- `frontend/tests/e6-lineage.test.mjs`
- `docs/contracts/scc_art_1.md` (ya indexado en `docs/README.md`; sin cambio de estado documental).

### Validación y límites

`make test-scc-art`: **55 + 75 backend y 44 frontend = 174 pruebas aprobadas**.
TypeScript pasa. Incluye consulta de artefactos, UUID, fuente, bearer, múltiples
imágenes, render de PNG/blob y descarga, ausencia legítima, archivo faltante,
HTTP/integridad/autorización y regresión TRAIN. El render automatizado usa React
SSR y dependencias simuladas; no equivale a una sesión de navegador. La primera
corrida detectó una expectativa antigua de «Ver imagen»; se actualizó al nuevo
estado «Cargando artefacto» y la suite completa pasó.

HTTP real sin sesión al PNG: **401**. La lectura real del resolutor y el listado
no equivalen a un GET 200 autenticado. Las pruebas HTTP del endpoint emplean
fixtures. No hubo navegador conectado con sesión legítima ni se crearon tokens.
**GET autenticado, visualización y descarga operativa siguen pendientes**.
Para verificarlos, abrir con sesión legítima
`/modelo-ia/evaluaciones/e6/4703ff9e-2d20-413f-9b9a-cd945c8dd632?datasource=malaria`,
avanzar a página 5 y comprobar PNG objetivo, otras imágenes, GET 200 con bearer
y descarga. La carga de imágenes ya no exige pulsar «Ver imagen».

Git conserva los cambios locales previos de SCC-ART.1 y estos cambios adicionales;
sin commits ni pushes. No se modificaron PostgreSQL, artefactos ni datasets y no
se ejecutaron TRAIN, EVALUATE, EXPLAIN ni TEST científicos.


## SCC-ART.1 FIX — Caso obligatorio SHAP desde TRAIN

Fecha: 2026-10-15. **Implementación corregida; aceptación visual autenticada pendiente.**
Esta corrección adicional afecta «Explicabilidad por caso» de `RunDetail`, que
seguía consultando exclusivamente `getRunExplainability` (catálogo histórico).
La corrección anterior del detalle E6 no conectaba esa sección del TRAIN a los
intentos E6: por eso su contador histórico podía mostrar cero pese a existir
artefactos recuperables en `assessment_artifacts`.

### Identidad comprobada antes de modificar la integración

Consultas de solo lectura acreditaron:

- TRAIN `d3d42cf3-0800-468c-b3ed-995860967da1`.
- Intento `93966b5d-5548-4b29-96f9-0b67e5c98f9f`, `verified`, método `shap`.
- Búsqueda por ruta del PNG indicado dentro de ese intento: PK de artefacto
  `2b4f68d6-2826-489c-980b-69f686223b11`, rol `overlay`, 19.413 bytes,
  SHA-256 `58833149477dc835aa074e89629acc3dfffbae6408e9fa2c44696e196cd84bb0`.
- `sample_id` explicado: `000f6007-9330-5085-972a-247631c541c6`.
  PostgreSQL registra también ese UUID en `explanation.background`. Son dos roles
  científicos separados que en este caso corresponden a la misma muestra; no se
  deduce la muestra explicada a partir del background.
- El listado público del intento devuelve el PNG y el mapa
  `25d46786-144a-4177-bf23-7f1c66ffe693`, con sus relaciones y sin rutas físicas.
- El servicio real `get_training_lineage_children` devuelve dos evaluaciones y
  un EXPLAIN: exactamente ese intento SHAP, con `result_count=1`.
- El resolutor existente verifica integridad y devuelve `image/png`, 19.413 bytes
  y firma PNG correcta. No se generó ni modificó el archivo.

### Integración corregida

`useTrainingExplanations` consulta el endpoint existente
`/runs/{training_run_id}/lineage-children` mediante el cliente compartido. Recorre
sus páginas mixtas (evaluaciones y explicaciones), selecciona únicamente
`source_kind=assessment_explain_e6` y verifica pertenencia al TRAIN. Cancela al
cambiar de TRAIN y oculta datos anteriores. No consulta un «último intento» ni
asocia imágenes por filenames.

«Explicabilidad por caso» muestra el número de intentos E6 disponibles antes del
contador histórico: para este caso, un intento disponible en lugar de «0 resultados
cargados». Cada intento muestra método, estado e ID. «Ver imágenes y artefactos»
abre el detalle dentro del mismo TRAIN; reutiliza `useAssessment`, valida su
pertenencia y monta `AssessmentExplanationDetail`. Este consulta los artefactos
y carga el PNG por `ScientificArtifact` / `api.getArtifactBlob`, siempre con
`source=assessment`, `attempt_id` y `training_run_id`. Mantiene descarga del mapa,
referencia SHAP y muestra explicada. Los casos históricos continúan disponibles.

Archivos de esta corrección adicional:

- `frontend/src/pages/RunDetail.tsx`
- Nuevo `frontend/src/hooks/useTrainingExplanations.ts`
- Nuevo `frontend/src/components/reports/TrainingExplanationAttempt.tsx`
- `frontend/tests/scc-art.test.mjs`
- Este contrato (mantiene `CURRENT_DOC` y su índice existente).

### Evidencia operativa y límites

HTTP real sin sesión: el endpoint existente de linaje respondió **200**;
`/artifacts/file` para el PNG con `source=assessment` respondió **401**.
No se cambió ninguna política de autorización. El acceso al PNG con bearer y su
visualización/descarga desde una sesión legítima siguen **pendientes**: no hay
navegador conectado con sesión autenticada, ni se generaron tokens artificiales.
El servicio real de listado y la lectura segura de bytes no sustituyen ese GET.

Recorrido pendiente de aceptación:
`/modelo-ia/ejecuciones/d3d42cf3-0800-468c-b3ed-995860967da1?datasource=malaria`
→ «Explicabilidad por caso» → intento `93966b5d-5548-4b29-96f9-0b67e5c98f9f`
→ «Ver imágenes y artefactos». Comprobar SHAP/verified, imagen, GET PNG 200 con
bearer y `source=assessment`, y descarga. No se declara validación visual aprobada.

No se modificó PostgreSQL, ni se ejecutó EXPLAIN ni se regeneraron artefactos.
Se conservaron los cambios locales anteriores; sin commits ni pushes.


Validación automatizada de esta corrección: `make test-scc-art`, **178 aprobadas**
(55 artefactos + 75 regresiones backend + 48 frontend), TypeScript correcto y
`git diff --check` sin errores. Las nuevas pruebas cubren paginación mixta del
linaje, pertenencia al TRAIN, apertura del intento SHAP con los identificadores
del caso obligatorio, render simulado del PNG y fuente `assessment`. La primera
corrida falló por aislamiento incompleto del loader de pruebas (`import.meta`);
se corrigió el mock de la dependencia y se repitió la suite completa con éxito.
El render usa fixtures y React SSR: no es evidencia visual autenticada.
