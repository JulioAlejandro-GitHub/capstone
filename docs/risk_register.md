# Registro de riesgos

Escala cualitativa: probabilidad/impacto Bajo, Medio, Alto; nivel combina ambos.

|ID|Categoría|Riesgo y evidencia actual|Causa|Consecuencia|Prob.|Impacto|Nivel|Mitigación|Contingencia|Componente|Prompt|Estado|
|---|---|---|---|---|:---:|:---:|:---:|---|---|---|---|---|
|R01|Arquitectura|Implementación actual aún no acopla catálogo y default|Evolución paralela histórica|Modelo visible no inferible hasta implementar ADR|Media|Alto|Alto|ADR-002 aprobado; FK/servicio transaccional/default único|Bloquear inferencia ante divergencia|Gobierno|P3/P10|Controlado por diseño|
|R02|Operación|Endpoint actual ejecuta inferencia síncrona|No worker implementado todavía|Timeout, pérdida por reinicio|Alta|Alto|Crítico|ADR-001/006: cola PostgreSQL, worker, lease, retry, idempotencia|No usar endpoint legacy para frotis|Jobs|P6|Diseño cerrado; implementación pendiente|
|R03|Ciencia|Clasificar imagen completa con clasificador celular|Smoke reutiliza `dataset_split_images`|Resultado inválido interpretado como científico|Media|Alto|Crítico|Scope explícito y detector/crops antes de agregado|Marcar sólo smoke técnico|Inference|P1/P10|Abierto|
|R04|Datos|Split actual carece de patient_id|TFDS celular|Leakage y métricas infladas|Alta|Alto|Crítico|Manifest/split por paciente|No publicar métricas E2 sin gate|Dataset|P7|Abierto|
|R05|Seguridad|Auth/RBAC base implementado; algunos writes legacy aún requieren migración de guard/audit|Superficie histórica amplia|Operación no autorizada en ruta no inventariada|Media|Alto|Alto|Completar matriz endpoint y audit append-only|Restringir demo a rutas verificadas|Backend|P2/P3|Mitigación parcial|
|R06|Datos|Originales aún no tienen provider global|Filesystem directo actual|Sobrescritura/pérdida de evidencia|Media|Alto|Crítico|ADR-003 LocalStorageProvider write-once/checksum|Backup read-only y quarantine|Storage|P4|Diseño cerrado; implementación pendiente|
|R07|Arquitectura|`predictions` mezcla legacy/image/cell/review|Reserva anticipada en 026|Acoplamiento y pérdida semántica|Alta|Alto|Crítico|Tablas especializadas + vistas|Congelar nuevas columnas|DB|P3|Abierto|
|R08|Ciencia|QC warnings igualmente pasan|`passed = not fatal`|Imágenes deficientes llegan al detector|Alta|Alto|Crítico|Policy versionada y gate revisable|Warning visible; revisión manual|QC|P5|Abierto|
|R09|Reproducibilidad|Paths físicos persistidos|Sin storage abstraction|Migración S3 rompe lineage|Alta|Medio|Alto|URI lógica/provider|Resolver paths históricos con adapter|Storage/artifacts|P4|Abierto|
|R10|ML|No detector ni contrato coords|Frontera documental|Crops/boxes incompatibles|Alta|Alto|Crítico|CellDetector + coordinate ADR + fake|Annotation adapter como baseline|Detection|P8|Abierto|
|R11|Datos|Formato/licencia RBCNet/NIH no verificados aquí|No descarga por alcance|Retraso o restricción de uso|Media|Alto|Alto|Spike con fuentes primarias|Detector alternativo/anotaciones|Dataset/detector|P1/P7|Abierto|
|R12|Operación|Host puede tener Python 3.14; runtime soportado es 3.12|Dos venvs locales|Import/runtime incompatibles|Media|Medio|Medio|CI 3.12 y venv local|Recrear venv backend 3.12|Infra|P2|Mitigado|
|R14|Auditoría|Correlation ID HTTP completo; persistencia futura pendiente|Jobs aún fuera de alcance|No reconstruir request→job futuro|Media|Alto|Alto|Propagar a analysis_jobs en P6|Consulta por logs|Observability|P2/P6|Mitigación parcial|
|R15|Seguridad|Upload sin límite/MIME fuerte|Helper centrado en path|DoS/image bomb/contenido inválido|Media|Alto|Crítico|Streaming limits, decode sandbox, MIME|Quarantine y rechazo|Ingest|P4|Abierto|
|R16|Superado|Docker/demo fuera de arquitectura operativa|Decisión Prompt 2.2.1|No aplica|Baja|Bajo|Bajo|Base local única y backups|Runbook Capstone|Infra|P2|Cerrado|
|R17|UX|Páginas reales ocultas del menú|Config comentada|Flujos inconsistentes|Alta|Medio|Alto|IA de navegación por roles|Deep links documentados|Frontend|P14|Abierto|
|R18|UX|Viewer científico inexistente|Frontend experimental|No revisar boxes/contexto|Alta|Alto|Crítico|Viewer con coordinate contract|Galería estática temporal|Workbench|P14|Abierto|
|R19|Ciencia|Agregación por imagen no definida|Sin entidad/método|Claims no comparables|Alta|Alto|Crítico|Protocolo científico/versionado|Mostrar sólo células, sin agregado|Aggregator|P11|Abierto|
|R20|Ciencia|Threshold 0.5 operativo puede publicarse|Availability fallback|Confusión con threshold clínico|Media|Alto|Crítico|Distinguir/calibrar por manifest|Warning y bloquear report final|Governance|P10|Abierto|
|R21|ML/Coste|LIME/SHAP para todas las células|Sin scheduler/policy|Cola saturada|Media|Alto|Alto|Selección prioritaria/presupuesto|Sólo Grad-CAM o on-demand|XAI|P12|Abierto|
|R22|Auditoría|Review plano puede sobrescribirse|Campos en predictions|Pierde resultado humano previo|Alta|Alto|Crítico|Revisions append-only|Prohibir endpoint de update|Review|P13|Abierto|
|R23|Alcance|OOD sin datos/protocolo|Capacidad solicitada no existente|Desvía MVP|Media|Medio|Medio|Spike y diferir por gate|Declarar no soportado|Classifier|P15|Abierto|
|R24|Agentes IA|Sin restricciones ejecutables|No hay módulo/policy|Diagnóstico o mutación indebida|Media|Alto|Crítico|Read-only, RBAC, approvals, red-team|Desactivar agentes en MVP|Agents|P15|Abierto|
|R25|Privacidad|Modelo de paciente aún no existe|Dataset actual no clínico|Ingreso accidental de PII|Media|Alto|Crítico|Pseudónimo, allowlist metadata, retention|Quarantine/borrado gobernado de PII|Domain|P3|Abierto|
|R26|Arquitectura|Adaptadores legacy son dependencia interna activa|Canon importa `src.*`|Retiro rompe backend/CLIs|Alta|Alto|Crítico|Migración por capas y contract tests|Restaurar facade en release|Python|P1–2|Abierto|
|R27|DB|Baseline Alembic posterior a 029 implementada|Transición dual controlada|Stamp incorrecto si se omite verificación|Baja|Alto|Medio|Verifier obligatorio y CI efímero|Backup + forward fix|Migrations|P2|Mitigado|
|R28|Seguridad|CORS sólo GET/POST localhost|Configuración fija|Futuros métodos fallan o apertura ad hoc insegura|Media|Medio|Medio|Origins/methods por perfil|Proxy same-origin|Backend|P2|Abierto|
|R29|Reproducibilidad|Git commit no garantizado en cada futuro stage|Tracking heterogéneo|No reproducir resultado|Media|Alto|Alto|Pipeline manifest obligatorio|Bloquear cierre de job incompleto|Pipeline|P11|Abierto|
|R30|Alcance científico|Producto puede percibirse diagnóstico|Terminología “productivo”|Uso indebido|Media|Alto|Crítico|Vocabulario experimental, disclaimers, RBAC|Retirar report/export ambiguo|Producto|P1/P15|Abierto|
