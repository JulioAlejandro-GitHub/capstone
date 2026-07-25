# Informe final de limpieza de archivos obsoletos

Fecha: 2026-07-25  
Rama: `chore/remove-obsolete-files`  
Commit base: `8f3988d6`

## 1. Resumen ejecutivo

Se auditaron los 418 archivos versionados del repositorio. La limpieza aplicó
un criterio conservador: sólo se eliminó un componente React sin consumidores
y reemplazado por el flujo vigente de liberación de Etapa 2. No se eliminaron
adaptadores públicos, migraciones, scripts manuales, evidencia académica,
artefactos, manifests, checkpoints ni archivos locales ignorados.

El frontend conserva sus 58 pruebas y build productivo; las suites de ML y API
quedaron verdes. Los tres checkpoints versionados cargan y coinciden con sus
SHA-256. Una base PostgreSQL temporal pudo reconstruirse con todas las
migraciones 001–028 y fue eliminada al terminar.

## 2. Métricas

| Métrica | Resultado |
|---|---:|
| Archivos versionados analizados | 418 |
| Líneas de texto inventariadas | 72.081 |
| Archivos eliminados | 1 |
| Directorios eliminados | 0 |
| Líneas eliminadas por la limpieza | 109 |
| Líneas añadidas por ajustes documentales de la limpieza | 5 |
| Dependencias eliminadas | 0 |
| Reducción del árbol por el commit de limpieza | 4.054 bytes |
| Reducción del componente fuente eliminado | 4.274 bytes |

La documentación de auditoría añade tamaño neto al repositorio; la cifra de
reducción corresponde exclusivamente al commit de limpieza.

## 3. Archivo eliminado

| Archivo eliminado | Motivo | Evidencia | Reemplazo actual | Validación |
|---|---|---|---|---|
| `frontend/src/components/reports/RunPromotionAction.tsx` | Implementación anterior de la promoción desde tarjeta TRAIN | Sin importadores, ruta, lazy import, configuración, test ni consumidor; las únicas referencias externas eran informes históricos | `RunSummaryRow.tsx`, `Stage2ReleaseDetail.tsx` | 58/58 tests frontend, typecheck y build Vite; búsqueda global sin referencias operativas |

Las dos menciones documentales históricas se corrigieron para distinguir el
estado de aquella etapa del flujo vigente.

## 4. Archivos conservados por seguridad

- 43 adaptadores `src.*`, porque sostienen CLI e imports históricos declarados
  públicamente y posibles consumidores externos.
- 22 migraciones SQL, porque son necesarias para reconstrucción y auditoría.
- 18 artefactos de release, incluidos modelos, manifests, thresholds, mappings,
  firmas y checksums.
- 51 documentos, porque contienen evidencia académica, decisiones, diagnósticos
  o procedimientos.
- Fachadas finas de explicabilidad y custom metrics, porque pueden ser API
  pública o participar en carga dinámica de modelos.
- Todos los scripts de entrenamiento, evaluación, inferencia, explicabilidad,
  backfill, diagnóstico y E2E manual.
- Archivos ignorados/no versionados (`.env`, entornos virtuales, caches,
  `node_modules`, `dist`, uploads y `.DS_Store`), de acuerdo con el alcance.

## 5. Candidatos ambiguos para revisión manual

| Candidato | Riesgo | Recomendación |
|---|---|---|
| Cuatro SQL duplicados bajo `docs/` | Pueden ser anexos académicos o runbooks manuales | Confirmar con responsables del informe antes de eliminar |
| `malaria_dl_local_project/README_2.md` | Citado por auditorías y una prueba de tracking | Migrar consumidores y revisar valor académico primero |
| Tres verificadores E2E de producción | Contratos parcialmente superpuestos | Consolidar sólo en una tarea funcional separada |
| Fachadas de explicabilidad y custom metrics | Uso externo/dinámico no demostrable desde el repositorio | Mantener como API pública hasta versionar una ruptura |
| Documentos de etapas previas | Pueden parecer obsoletos, pero forman trazabilidad | Archivar con política documental, no borrar como código muerto |

## 6. Validaciones ejecutadas

| Área | Validación | Resultado |
|---|---|---|
| Frontend | `npm test` antes y después | PASS — 58/58 en ambas ejecuciones |
| Frontend | TypeScript + `vite build` antes y después | PASS — 97 módulos; bundle JS 419,43 kB y CSS 64,90 kB |
| ML | Suite completa `pytest -q` | PASS — 368 passed, 1 skipped, 37 subtests passed |
| API | Suite con entorno ML | PASS — 45 passed, 3 skipped, 4 subtests passed |
| API | Importación FastAPI + OpenAPI | PASS — 91 paths y 92 operaciones |
| Release IA | SHA-256 de `model.keras` contra manifest | PASS — 3/3 |
| Release IA | Carga TensorFlow/Keras `compile=False` | PASS — 3/3; entrada `(None, 200, 200, 3)`, salida `(None, 1)` |
| IA | Preprocesamiento e inferencia mínima | PASS dentro de la suite ML |
| IA | Mapping y threshold | PASS por manifests y suite; positivo `parasitized`, thresholds 0,2629568577 y 0,2758140266 |
| PostgreSQL | Base temporal + migraciones 001–028 desde cero | PASS; base temporal eliminada |
| Referencias | Búsqueda global del archivo eliminado | PASS — sin referencias operativas; sólo auditoría histórica explícita |
| Diff | `git diff --check` | PASS |

El entorno `backend_api/.venv` no trae `pytest`; por ello los tests de API se
ejecutaron con `malaria_dl_local_project/.venv`, que contiene FastAPI, pytest y
las dependencias del backend. No se realizó una reinstalación desde red, porque
los entornos locales disponibles fueron suficientes para reproducir las suites.

## 7. Cobertura, build e impacto funcional

No existe configuración de cobertura ni baseline versionado; por tanto no se
declara un porcentaje inventado. El número y resultado de pruebas no cambió.
El build conserva exactamente 97 módulos y los mismos nombres/tamaños de
artefactos, señal de que el archivo eliminado no formaba parte del grafo Vite.

No se modificaron contratos API, esquema, rutas, comportamiento visual,
dependencias ni lógica de IA.

## 8. Riesgos residuales y límites

- El intento contra la base persistente existente detectó un estado previo
  inconsistente: la migración 027 intenta actualizar una `model_version`
  gobernada ya inmutable. Esto no fue causado por la limpieza; la reconstrucción
  limpia 001–028 sí pasa. Debe diagnosticarse aparte antes de volver a migrar
  esa instancia.
- El repositorio no contiene Docker, Compose, Redis, Celery ni worker; no fue
  posible validar componentes inexistentes.
- La frontera `cell_detection` sólo contiene documentación/paquete vacío. No
  hay implementación versionada del flujo completo de frotis, detección de
  células o generación real de crops que permita ejecutar el smoke integral
  solicitado. La inferencia celular, calidad de imagen, explicabilidad y
  trazabilidad sí están cubiertas por las suites existentes.
- No se levantó el frontend contra una API viva ni se alteraron datos
  persistentes para ejecutar una revisión experta E2E; esa prueba requeriría
  fixtures y un orquestador que el repositorio no proporciona.

## 9. Rollback

Cada fase es reversible de forma independiente:

```bash
git revert e7a3eaa8
git revert 58e77f8b
```

El primer comando restaura el componente y las dos referencias documentales;
el segundo elimina el inventario inicial. No se requiere rollback de base de
datos: la base temporal de validación fue eliminada.

## 10. Commits

| Hash | Commit |
|---|---|
| `58e77f8b` | `chore(audit): inventory obsolete files` |
| `e7a3eaa8` | `chore(cleanup): remove obsolete frontend promotion component` |

El commit que incorpora este informe se identifica en el historial de la rama,
porque un commit no puede incluir de forma estable su propio hash.
