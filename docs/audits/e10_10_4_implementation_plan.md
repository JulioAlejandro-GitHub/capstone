# E10.10.4 — Plan verificable E10.10.5 a E10.10.9
> Actualización E10.10.5A: A-01 fue aprobada por el usuario. La sección final documenta la enmienda; el cuerpo original conserva su contexto histórico. Implementación y límites actuales: [e10_10_5_implementation.md](e10_10_5_implementation.md).

**Plan propuesto, no ejecución autorizada por esta entrega.** Cada etapa produce un resultado revisable y una condición de salida. No se ejecuta TRAIN, VALIDATION, TEST ni EXPLAIN clínico para probar migraciones; usar datos sintéticos y adaptadores fake en PostgreSQL aislado cuando la etapa sea autorizada.

## E10.10.5 — Cierre de contratos, catálogo v2 y baseline aislada

Entradas: aprobación del diseño y decisiones nullable/merge/XAI/schema único. Resolver RA de typmods, ACL, clientes externos y todos los aliases científicos de run_metrics. Revisar los 97 destinos contra código, especialmente rutas históricas aún activas. Formalizar DTO v2 y contrato de eventos v1 preservado. Definir identificador final de baseline y capacidad v2 del guard; no editar revisiones aplicadas.

Implementar en rama de trabajo la nueva raíz Alembic con tablas/FK/UNIQUE/CHECK, funciones/trigger SQL explícito, vistas, índices/extensión y singleton técnico. Separar administrador alembic_version de objetos de aplicación. Archivar historia inmutable con hashes documentales. Probar instalación vacía exclusivamente aislada, compare catálogo y backup/restore. No importar ciencia/usuarios productivos como fixtures.

**Salida:** Ruta A construye 103 tablas y todos los objetos esperados mediante Alembic únicamente; no dependencia ejecutiva de 22 SQL. DDL inválido o trigger omitido impide cierre. Guard v2 falla ante revisión desconocida/dañada; guard legacy preservado.

## E10.10.6 — Writers, ResultService y configuración congelada

Implementar mapper de configuración resuelta y proyección de EVALUATION_COMPLETED a E/M con FK al ledger; materialización de épocas y recursos medidos. Mantener envelope/hashes v1, locks, owner, secuencia, OOM y recuperación. Adaptar repositorios de tracking/matrices/reportes y assessment para un único escritor canónico; no dejar safe_track que acepte evento sin resultado.

Conservar callbacks científicos, políticas de checkpoint y defaults; registrar explícitamente particularidades de perfiles batch que hoy habilitan calibración. No cambiar defaults de archivos de modelos para resolver el rediseño. Guard de columnas frente a snapshot y mapper inverso de compatibilidad probado. No permitir uso de TEST para selección/pesos/calibración.

**Pruebas aisladas:** duplicate event_id idéntico/conflictivo; secuencia repetida/gap/out-of-order; dos writers concurrentes; owner perdido; sesión cerrada; rollback antes/después del INSERT de métrica; pérdida de ACK; legado canonical hash; controlled paused; job reportado sin exit; checkpoint no registrado; calibración val con linaje incorrecto; denominadores cero/una clase; muestras y TP+FP+FN+TN coherentes. No cambiar completed por mera presencia de métricas.

**Salida:** mismo resultado con DockerRunReporter y HttpRunReporter, y ningún evento aceptado sin proyección requerida. Todos los escritores de tablas MERGE trasladados. TRAIN técnico conserva criterios vigentes.

## E10.10.7 — Lecturas científicas, API, React y resumen físico

Implementar servicios de lectura de configuración/evaluación/historial/ensemble y DTO versionado. Redirigir training_summaries, run_lineage, dashboard y catalog a resultados canónicos; adaptar aliases de vistas legacy sin mezclar checkpoint final, calibración y época. Preservar endpoints de publicación con FK compuesta y elegibilidad actual.

React: métricas NULL con motivo, matrices orientadas correctamente, denominador/split/protocolo visibles, comparación por arquitectura/optimizer/seed y variabilidad; selección sólo val; mostrar TEST separado y ensemble con miembros. Curvas por fase/época y contexto del checkpoint. Corregir summary físico por raíz y separar del universo oficial; no mover rutas ni reasignar split.

**Pruebas:** datos sintéticos dos raíces/permutaciones; tres arquitecturas×cuatro optimizers×varias seeds; cohorts incompatibles rechazadas; counts y media/stddev correctos con seeds ausentes; final y calibración con umbral distinto; paginación estable ante múltiples artefactos; publicación TRAIN/EVALUATE válida sin XAI ni recall .98; FK par versión/TRAIN incorrecto rechazada.

Medir planes y EXPLAIN ANALYZE únicamente aislados con cardinalidades documentadas. Confirmar o rechazar candidatos de índices Top-N/publicaciones/prefijos; no usar idx_scan=0 como criterio. No afirmar rendimientos antes de medir.

**Salida:** contratos frontend estables, lectura sin JSON heterogéneo para comparar, y 27.558 nunca confundidas con 55.116 filas físicas.

## E10.10.8 — Trazabilidad XAI y recorrido de frotis

Integrar xai_evidence con tres padres actuales, reutilizar mapas assessment NPY y PNG. Extender capturas de pipeline/inferencia/celular donde falten datos numéricos, conservando algoritmos y archivos anteriores. Registro de background real, clase/salida, modelo/checkpoint/input contract/entorno/config/seed. Artefactos externos con URI/hash/shape/coordenadas y disponibilidad, sin blobs grandes en DB.

Crear lectura/comparación por misma entrada; mantener ACL de contenido. Integrar en Explainability/CaseExplainabilityView/historial de frotis sin ofrecer SHAP/LIME celular hasta que la ruta esté implementada y aprobada. Implementar estructuras de interpretación/revisión con usuarios actuales y evidencia de competencia.

Las tablas de evaluación cuantitativa quedan disponibles; habilitar un algoritmo de estabilidad/faithfulness/localización/concordancia requiere protocolo científico específico, no aprobación implícita del esquema. Puede completarse la capacidad de persistencia/consulta con fixtures sin ejecutar esos algoritmos.

**Pruebas:** XOR de padres/origen; misma imagen con métodos distintos; crop no coincide con imagen completa; SHAP background TRAIN vs synthetic_zero_plus_input; falta de clase/salida/config bloquea comparación; referencia de anotación versionada; mapas signed vs unsigned; archivo missing/compensación de storage; review no modifica predicción ni diagnóstico.

**Salida:** cadena modelo/experimento/evaluación/predicción/imagen/caso recuperable, y separación visible de las cuatro capas de XAI. No regenerar evidencia real existente.

## E10.10.9 — Ensayo de adopción y decisión de cutover

Implementar herramienta de adopción sobre copia, preflight con checksums de 22 SQL, transformaciones/reconciliación y manifiesto de mapeo. Inventariar nuevamente datos existentes; abortar ante ambigüedad. Comparar catálogo Ruta A/B y preservar protected rows/fingerprints almacenados, identities, splits, materializaciones, rutas, credenciales y relaciones. No repetir checksum físico de imágenes.

Ensayar fallos, restore, rollback de aplicación, recuperación y periodo sin writes. Registrar nueva baseline en copia sólo después de equivalencia y aprobación correspondiente. Revisar scripts/Makefile/reset tools para que no invoquen fundación histórica en instalaciones v2. Documentar plan de reversión antes y después de abrir escrituras.

**Salida:** informe completo de aceptación y propuesta concreta de cutover; la promoción operativa necesita autorización expresa de esa etapa. No iniciar campañas como test de migración. No mezclar dos instancias escritoras. El archivo de historia permanece inmutable.

## Matriz de riesgos y puertas de salida

| Riesgo | Etapa responsable | Evidencia que lo cierra |
| --- | --- | --- |
| Métricas indefinidas hoy cero | 5–7 | Mapper v1→v2 nullable, DTO versionado y conservación exacta de eventos |
| Defaults batch calibran aunque default general OFF | 5–6 | Perfil solicitado explícito, config congelada y decisión documentada; no cambio inadvertido |
| Guard exige head antiguo | 5–6 | Allowlist/capacidades y rechazo preclaim probado |
| Writers ocultos de tablas MERGE | 5–7 | Corpus por path, contract tests y compatibilidad de clientes |
| TEST contamina selección | 6–7 | Protocolo congelado, final locks y pruebas negativas de threshold/ensemble |
| XAI visual incompleto | 8 | Estado legacy/incompleto explícito, no rellenar datos inventados |
| Archivos y DB no atómicos | 8 | Stage/promote/reconcile; fallos parciales y disponibilidad controlados |
| Copia diverge de catálogo/rutas/ciencia | 9 | Equivalencia certificada, protección de datos y ensayo restore |
| Rendimiento incierto | 7/9 | Carga sintética, planes y medidas reproducibles; sin benchmark operativo |

## Revisión estática efectuada en E10.10.4

Controles ejecutados exclusivamente sobre archivos, sin servidor:

- **1336 sentencias** analizadas sintácticamente por pglast 8.4 / parser PostgreSQL 18.4; el diseño usa construcciones disponibles en PostgreSQL 17. Esta prueba no certifica ejecución ni resolución de catálogo en PostgreSQL 17.
- **103 tablas, 32 vistas, 75 funciones propias y 95 triggers de aplicación** en el DDL final; **248 FK** con tablas/columnas de origen y destino existentes, y objetivos UNIQUE/PK localizados. Índices parciales no se aceptaron como targets de FK.
- **72 cuerpos PL/pgSQL** pasaron el parser de cuerpos sin errores sintácticos. Se usó la salida cruda del parser: la conversión JSON de pglast para algunos triggers tiene un defecto de serialización y no se presenta como prueba de compilación semántica.
- **97 filas únicas** del CSV coinciden exactamente con tablas del baseline: 17 PROTECTED, 67 KEEP, 11 REFACTOR y 2 MERGE. DDL = 95 existentes + 8 nuevas.
- Los **65 cuerpos de funciones** y **77 definiciones de triggers** actuales se encuentran íntegros en el documento; no se alteraron funciones de ownership/fencing ni migraciones históricas.
- Matriz JSONB: 130 columnas actuales; apéndice adicional de 83 claves literales de productores/CLI con destino/política. No se afirma censo de claves de runs poblados: están vacíos en evidencia.
- Estado final de workspace: sólo los ocho archivos E10.10.4 nuevos. Los documentos de entrada conservan sus SHA-256; no se modificó código de aplicación, execution/schema.py, archivos históricos, dataset ni credenciales.

Límite: un parser no valida tipos/relaciones dentro de SQL dinámico ni comportamiento de triggers, concurrencia o planes. Pruebas de PostgreSQL 17 y equivalencia A/B siguen siendo gates explícitos de implementación, no trabajo iniciado en E10.10.4.

## Criterios de aceptación del diseño

| Requisito E10.10.4 | Evidencia entregada |
| --- | --- |
| Todas las tablas clasificadas | CSV, 97 filas únicas y destinos; 103 tablas objetivo inventariadas |
| Sin retiros por vacío | Dos MERGE con writers/readers y vistas; seis ACTIVE conservadas |
| Resultados tipados | E + M + history/calibration, UNIQUE/FK/CHECK y transacción |
| JSON estructurado con destino | Matriz de rutas y 130 columnas JSONB inventariadas |
| E10 preservado | Orden de locks, idempotencia, hashes, Local/Docker, OOM y completion |
| Ciencia protegida | Dataset/splits/usuarios inalterados; TEST final; NULL explícito |
| Alembic limpio / transición | Ruta A integral, Ruta B copia/equivalencia antes de baseline |
| Backend/React | Matriz de componentes y cambios incompatibles identificados |
| Implementación secuencial | E10.10.5–9 con pruebas/puertas verificables |
| DDL revisado | Controles estáticos registrados abajo, con límites explícitos |
| Operación intacta | Sin conexión ni SQL ejecutado; sólo documentos generados |


### Matriz de creación de entidades nuevas

| Objeto actual | Objeto futuro | Acción | Datos existentes | Dependencias | Riesgo | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| JSON configuración TRAIN | run_configurations | CREATE + normalizar | Cero runs capturados; copia futura se recensa | runs, snapshot/session/campaign | Hash o parámetros discrepantes | Config resuelta = columnas; hash canónico y guard inmutable |
| training_results / assessment verification | evaluations | CREATE + proyectar | Evidencia se preserva, no reescribir v1 | runs, dataset_versions, model_versions, artifacts, records, attempts, calibration | Parcialidad o mezcla de población | Misma transacción; origen/rol/split/protocolo y final lock TEST |
| Configuración de ensemble | evaluation_ensemble_members | CREATE + relacionar | No ensemble histórico acreditado | evaluations, model_versions, artifacts | Pesos o checkpoint divergentes; uso TEST | >=2, suma pesos 1, miembros exactos y protocolo precomprometido |
| Explicaciones de tres subsistemas | xai_evidence | CREATE + extensión | Padres/artefactos originales no cambian | ML/cell/assessment, predicciones, entradas, versión/checkpoint | Linaje parcial o clase/salida mal atribuida | XOR y checks cruzados; legacy incompleto no inventado |
| artifacts / assessment_artifacts / storage keys | xai_artifacts | CREATE + manifiesto | Reutilizar referencias, nunca regenerar | xai_evidence; FK opcionales a registros actuales | Referencia rota, hash o shape incorrectos | URI/hash/bytes coinciden, disponibilidad y compensación |
| No capacidad general acreditada | xai_quantitative_evaluations | CREATE para capacidad futura | Sin backfill de métricas inventadas | xai_evidence, annotations/version/manifiesto | Confundir concordancia con validación clínica | Protocolo y pares compatibles, NULL con razón |
| Notas humanas de explicación | xai_interpretations | CREATE | Sin inferir texto de heatmap | xai_evidence, users | Edición sin historia/autorización | Append-only, autor y supersedes coherente en servicio |
| Revisión especializada de interpretación | xai_specialist_reviews | CREATE | Sin alterar reviews de predicción existentes | xai_interpretations, users/roles vigentes | Atribuir diagnóstico confirmado | Competencia/ACL/razón, resultado separado de IA |

**E10.10.4 — DISEÑO POSTGRESQL V2 COMPLETADO, PENDIENTE DE APROBACIÓN.**

## Enmienda A-01 aprobada — 2026-09-29

**A-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5A PUEDE REANUDARSE.** Autorización explícita del usuario, limitada a diseño, baseline y validación estática; no autoriza B ni cutover. El texto anterior conserva la decisión original. Sus hashes y la definición original de evaluations están en [e10_10_5a_design_before_a01.json](e10_10_5a_design_before_a01.json); el bloqueo original se conserva en [e10_10_5a_initial_block.md](e10_10_5a_initial_block.md).

- `evaluations.split` admite `external` además de los tres splits oficiales. `external_validation` permanece intacto en el dataset protegido; no se crea un alias ni mapping automático.
- Ámbito (`split`), población (`population_hash` y manifiesto), origen (`dataset_origin_id`, `dataset_origin_role` y evidencia de procedencia), protocolo (`protocol_hash/version/snapshot`) y finalidad (`purpose`) son conceptos independientes.
- External exige `purpose=complementary`, `evaluation_role=external_complementary`, manifiestos de población/procedencia recuperables con SHA-256 y FK a la PK existente `(dataset_version_id,dataset_id,role)` del origen registrado en `dataset_version_sources`, sin añadir UNIQUE al dominio protegido. La versión evaluada puede diferir de la versión de entrenamiento; se conserva íntegro el linaje TRAIN/checkpoint/modelo. No se crean versiones ni fuentes ficticias para completar esa FK.
- `source_kind=external_record` identifica nuevas entradas externas; `legacy` permite adopción con evidencia suficiente. No se hace pasar una entrada externa por evento E10 ni por assessment cuyo contrato actual sólo admite splits oficiales.
- Se prohíbe usar external como calibración, selección de checkpoint/modelo, VALIDATION sustitutiva o agregado TEST oficial. Los roles y la finalidad lo impiden en evaluations, el par de calibración exige val, y `vw_v2_model_comparison` sólo contiene train/val/test. `vw_v2_external_evidence` expone evidencia complementaria sin agregación, con población, protocolo y procedencia. El catálogo pasa de 32 a **33 vistas**; mantiene **103 tablas**.
- `run_clinical_metrics.split_name` sigue representando `external`; su trigger lo deriva de la evaluación externa trazada. Se conservan el lector/escritor legacy en la aplicación operativa. Adaptar esos escritores al contrato transaccional v2 corresponde a E10.10.5E: esta enmienda no afirma compatibilidad binaria de INSERT antiguos que carezcan de evaluation_id.
- La existencia de un URI/hash no certifica disponibilidad o validez científica del manifiesto. La adopción abortará sin mapping si falta evidencia; los servicios deben verificar procedencia y políticas de selección. No se modifican imágenes, asignaciones ni hashes históricos.


## Resolución B-01 — roles de instalación v2 (2026-09-29)

Por decisión arquitectónica aprobada, el propietario/migrador se denomina `capstone_v2_migrator` y el runtime independiente `capstone_v2_runtime`. Ambos carecen de SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS y memberships. El runtime no dispone de DDL, TEMP, TRUNCATE ni escritura en alembic_version o modificación directa de los ledgers protegidos. Sólo se provisionan en el destino aislado autorizado para B. La evidencia de los nombres reservados anteriores se conserva en el informe B-01.
