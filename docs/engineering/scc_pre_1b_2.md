# SCC-PRE.1B.2 — Backend de Preflight

Implementación y pruebas: 2026-10-16. SCC-PRE.1A y SCC-PRE.1B.1/V1–V7 no se modifican.

## Operación y contrato

`POST /models/comparison/preflight?datasource=malaria`. Consulta sin persistencia, con respuesta `Cache-Control: private, no-store`. Contratos Pydantic: `PreflightRequest` y `PreflightResponse`; versión de respuesta `scc_pre_1`. No hay versión/guard de esquema PostgreSQL.

Ejemplo de cuerpo (UUID ilustrativos):

```json
{
  "selections": [
    {
      "training_run_id": "00000000-0000-0000-0000-000000000001",
      "evaluation": {
        "source": "assessment",
        "identity_id": "00000000-0000-0000-0000-000000000031",
        "attempt_id": "00000000-0000-0000-0000-000000000021"
      },
      "split": "val",
      "checkpoint_artifact_id": "00000000-0000-0000-0000-000000000041"
    }
  ]
}
```

También se admite `evaluation: {source: "evaluations", evaluation_id: UUID}`. Se contrasta su TRAIN y se usa únicamente el vínculo explícito `source_assessment_attempt_id`, verificando split, dataset, checkpoint y definición de métricas. Sin vínculo no se inventa alineación ni se mezclan predicciones históricas.

Evaluación, split y checkpoint son opcionales para permitir evidencia TRAIN independiente. Si se suministran, se contrastan con la evidencia efectiva. No se elige ningún intento automáticamente, aun cuando solo exista uno. Múltiples alternativas producen `AMBIGUOUS_EVALUATION`; selección ausente produce un motivo explícito. UUID inválidos, TRAIN repetidos y exceso del límite dinámico `SCC_MAX_COMPARISON_RUNS` producen 422. Se permite un TRAIN para evidencia individual, pero la comparación conjunta queda insuficiente.

La respuesta separa selecciones efectivas, evidencia, dimensiones, análisis, poblaciones, checkpoints, errores técnicos y resumen. Las observaciones distinguen conocido, desconocido, no comprobado y error. No contiene estado global. Un conflicto demostrado y una carencia se desglosan en entradas con distintos `scope_id`/`analysis_id`; ninguna tiene precedencia sobre la otra. El resumen cuenta estas entradas concretas una sola vez. La comparación de métricas usa población original; consenso usa intersección explícita.

Ajustes acotados respecto al diseño propuesto B.1: conjunto de módulos fijo y alcances derivados, sin selección de subconjuntos arbitrarios; checkpoint efectivo identificado por artifact UUID, registro/linaje y comprobaciones físicas separadas; no se proyectan época/política/hash como acreditados sin lectura específica. No se aceptan selecciones EXPLAIN en este contrato inicial: la metodología P5 queda pendiente. Las exclusiones/ausencias se expresan mediante hallazgos por selección, sin simular un subconjunto comparable.

## Correspondencia documental → código y cobertura

Se leyeron primero contrato y auditoría; no se encontró inventario equivalente en el repositorio. Se consultaron SQL_B1, contratos/lectores E6 y proyección de configuración. Las columnas utilizadas se comprobaron mediante SELECT contra PostgreSQL activo, sin migraciones ni comprobaciones de versión.

| Dimensión | Reutilización / extensión mínima | Cobertura efectiva |
|---|---|---|
| A1 | `ScientificReadRepository.preflight_training`: runs + relación dataset_versions | Identidad/registro completos cuando existen. Diferencias de versión son contexto, no equivalencia por nombre; evaluación y TRAIN mantienen atribución distinta |
| A2 | Identidad exacta E6/evaluations y pertenencia gobernada consultada en A3 | Completa para población E6 acreditada; insuficiente sin pertenencia. VAL–TEST incompatible; mismo nombre no acredita población |
| A3 | `AssessmentReadRepository.preflight_population`, extensión de la lectura por intento | Agregados completos dentro del snapshot, sin páginas ni cargas masivas de predicciones. Cruza población declarada/observada, assignments y registros fuente; únicos, duplicados, conflictos, intersección, faltantes, exclusivos y ratios. Históricos sin vínculo E6: insuficiente |
| A4 | `read_run_configurations` compartido con lector científico existente | Parcial según campos persistidos. Arquitectura, semilla, preprocessing, augmentación en extension_configuration.execution.no_augment, optimizador, hiperparámetros y políticas; no defaults ni snapshots arbitrarios expuestos |
| A5 | `ArtifactReadRepository.get`, ahora acepta conexión externa | Registro y TRAIN de origen contrastados. Disponibilidad física e integridad SHA-256: `not_checked`, checked_at null. No se consulta filesystem ni se interpreta artifacts-summary.exists |
| A6 | `AssessmentReadRepository.preflight_detail/preflight_candidates` y `ScientificReadRepository.evaluation` | Intento exacto, estado, protocolo, umbral, semántica de scores/clase, batch/input y métricas observadas. Definiciones/clase incompatibles se distinguen de diferencias de umbral. Históricos sin intento: parcial |

No se utiliza el agregado completo scientific-results: no carga curvas, contenidos XAI ni representaciones. Historia se consulta con conteos de épocas/ejes; la configuración comparte su consulta canónica. El SQL adicional permanece en repositorios de dominio, sin catálogo central.

Análisis implementados: curvas TRAIN/VAL descriptivas, métricas VAL/TEST originales, consenso/desacuerdo en intersección, XAI, embeddings, PCA, UMAP y CKA. Los cinco últimos requieren evidencia metodológica P5 y permanecen insuficientes en esta entrega; no se supone comparabilidad por presencia de archivos. Los datos individuales se mantienen disponibles o pendientes de consulta independientemente del dictamen conjunto. No se ejecuta ninguno de estos análisis.

Una intersección parcial permite únicamente el alcance pareado acreditado; las métricas originales de poblaciones diferentes son incompatibles para comparación directa. Conflictos y duplicados no se corrigen. Cobertura no acreditada implica numerador/ratio desconocidos, sin extrapolar una página.

## Seguridad, consistencia y errores

Se reutilizan Principal, current_principal y require_permission. Se requieren RUNS_READ, MODELS_READ, DATASETS_READ, PREDICTIONS_READ y ARTIFACTS_READ antes de consultar cualquier dominio. RBAC vigente es global, sin ACL por propietario de TRAIN; no se añade otro sistema de permisos. Se valida existencia/tipo de TRAIN y pertenencia de evaluación/intento; un recurso ajeno al TRAIN solicitado no se devuelve. El principal anónimo de auth_mode=disabled se rechaza con 401.

Todos los repositorios usan una conexión READ ONLY + REPEATABLE READ, con los timeouts existentes (statement 10 s, lock 2 s). Savepoint por dominio permite continuar tras errores SQL. No se convierten fallos en listas vacías ni incompatibilidad. Una incompatibilidad ya probada puede mantener dictamen y errores auxiliares; cuando falta evidencia por error, estado null/not_evaluated. Caída que impida establecer o cerrar el snapshot devuelve 503 sanitizado.

La proyección pública reutiliza public_evidence y listas explícitas de campos; no expone rutas de checkpoints, SQL, comandos, snapshots libres ni secretos. Los errores tienen correlación y referencias a alcances afectados. La instantánea PostgreSQL no acredita bytes ni vigencia futura de artefactos.

Brecha fuera de alcance: rutas históricas runs/assessments señaladas en B.1 siguen sin refactorización general de autorización. Autenticación/permisos HTTP del endpoint nuevo se probaron mediante ASGI y Principals controlados, no mediante credenciales de usuarios reales del despliegue.

## Validación

Comando de regresión:

```sh
docker compose exec -T backend pytest -q   tests/test_scientific_preflight.py tests/test_scc_core.py   tests/test_scc_art.py tests/test_scientific_results_v2.py   malaria_dl_local_project/tests/test_assessment_api_e6.py
```

Resultado final: **79 passed** (incluye 40 pruebas nuevas de Preflight). Ruff completo sobre los cuatro archivos nuevos de código/pruebas, revisión E9/F de los archivos existentes modificados y git diff --check: sin errores.

Se ejecutaron pruebas unitarias/HTTP, SQL real con fixtures CTE SELECT-only (105 muestras, más que la página inicial histórica), consultas de metadatos persistidos, aislamiento READ ONLY/REPEATABLE READ y recuperación por savepoint. La prueba de rechazo DML utiliza DELETE WHERE false bajo READ ONLY: PostgreSQL lo rechaza y ninguna fila puede cambiar. No se crearon tablas ni resultados científicos.

Lectura operacional acotada adicional: selección explícita de dos TRAIN con intentos verified; el servicio completó consulta real, incluidos agregados poblacionales, sin errores técnicos. Inicialmente el agregado excedió el timeout: se reemplazaron correlaciones repetidas por joins y agregados, manteniendo el timeout existente. Esta lectura encontró evidencia mixta; no certifica comparabilidad científica general.

No se verificó concurrencia con escritores en una base desechable, caída real de conexión, rendimiento a escala máxima de todos los datasets, JWT de un usuario real ni bytes/hash de checkpoints. No se declara aprobación de esos comportamientos ni validación científica operativa integral.

## Archivos y siguiente etapa

Nuevos: schemas/scientific_preflight.py, routes/scientific_preflight.py, services/scientific_preflight.py, tests/test_scientific_preflight.py y este informe. Modificados: app/main.py, app/db.py, repositories/scientific_results.py, repositories/assessments.py, repositories/artifacts.py.

SCC-PRE.1B.3: integración frontend, Preflight abierto por defecto, módulos restantes con consulta diferida, selección explícita, presentación de estados/alcances mixtos y conservación de respuestas por identidad y sesión. Retención/deduplicación de POST, invalidación, reintento local y separación del flujo generador XAI son trabajo frontend pendiente. No se modificó el acordeón XAI, ni se incorporaron cachés, tablas, migraciones o procesos científicos. Sin commit ni push.
