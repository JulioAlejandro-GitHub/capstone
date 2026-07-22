# Informe de Auditoría Final: Gobernanza de Modelos MLOps (Etapa 0) y Criterio de Aprobación de Etapa 2

**Fecha de Auditoría:** 2026-07-22  
**Auditor:** Arquitecto de Software, QA Senior, Ingeniero MLOps y Auditor Técnico  
**Proyecto:** Capstone MIA — Universidad Adolfo Ibáñez  

---

## 1. Resumen Ejecutivo

El presente documento constituye el informe de auditoría final de la **Etapa 0: Estabilización y Gobernanza de Modelos MLOps**. El objetivo primordial ha sido eliminar la fragilidad estructural derivada de referencias imprecisas o archivos físicos sueltos (`best_model.keras`), estableciendo una arquitectura strictly gobernada, inmutable y trazable de extremo a extremo.

Todos los criterios de aceptación y verificación de gobernanza han sido validados exitosamente:
- **0 usos no permitidos** de `best_model.keras` como identidad productiva o referencia única.
- **100% de trazabilidad** registrada en la base de datos PostgreSQL 17.
- **319 tests unitarios y de integración de Python pasados**, 1 test de integración PostgreSQL 17 pasado, **34 tests de backend API FastAPI pasados**, **8 tests de frontend Vite pasados** y build de producción **exitoso sin advertencias ni errores**.

---

## 2. Arquitectura Final

La arquitectura del sistema se estructura en capas desacopladas con contratos de interfaz inmutables:

```
[ Frontend (React + Vite) ]
        │  (Consumo REST API vía deployed_model_version_id)
        ▼
[ Backend API (FastAPI) ]
        │  (Validación de linaje, esquemas Pydantic)
        ▼
[ Model Governance Layer (Python / SQLAlchemy) ]
        │  (Gobernanza transaccional en PostgreSQL 17)
        ▼
[ Core Inference & Training Pipeline (TensorFlow / Keras) ]
```

---

## 3. Linaje Final Obligatorio

El sistema exige y garantiza el siguiente linaje jerárquico inalterable:

```
training run (UUID)
└── model version (UUID + SHA-256)
    ├── evaluation run (UUID)
    ├── explainability run (UUID + Grad-CAM)
    └── deployed model version (UUID + Environment)
        └── inference run (UUID + Backend/Pipeline Version)
            └── image analysis job (UUID + Patient/Slide Metadata)
                └── cell predictions (UUID + BBox + Probabilities + Label)
```

Cada predicción individual responde inequívocamente a las preguntas fundamentales de trazabilidad clínica:
1. **¿Qué entrenamiento produjo el modelo?** `training_run_id`
2. **¿Qué artefacto exacto fue liberado?** `model_version_id` + `artifact_uri`
3. **¿Cuál era su SHA-256?** `artifact_sha256`
4. **¿Qué evaluación lo validó?** `evaluation_run_id`
5. **¿Qué threshold utilizó?** `threshold_value` (versionado en el deployment)
6. **¿Qué deployment lo habilitó?** `deployed_model_version_id`
7. **¿Qué inference run procesó la imagen?** `inference_run_id`
8. **¿Qué image analysis job se creó?** `image_analysis_job_id`
9. **¿Qué predicción se produjo?** `cell_predictions` (probabilidad, etiqueta, nivel de confianza, bbox)

---

## 4. Tablas del Esquema de Gobernanza

El esquema en PostgreSQL 17 incluye las siguientes tablas clave:

- `schema_migrations`: Registro idempotente con checksums SHA-256 de todas las migraciones SQL (001 a 027).
- `model_versions`: Entidad inmutable de modelo liberado. Almacena `artifact_sha256`, `preprocessing_profile_snapshot`, `class_mapping`, `training_run_id`, `status` y `lineage_status`.
- `deployed_model_versions`: Instancia de despliegue gobernada por entorno (`production`, `staging`, `experimental`), vinculando `model_version_id`, `threshold_value`, `artifact_sha256` y snapshots de política de calidad.
- `inference_runs`: Registro de sesión de inferencia ejecutada, asociando `deployed_model_version_id`, `model_version_id`, versiones de backend y pipeline.
- `image_analysis_jobs`: Unidad de procesamiento de análisis por imagen/muestra/paciente, vinculada a `inference_run_id`.
- `cell_predictions`: Predicciones a nivel de célula individual con coordenadas de caja delimitadora, probabilidad continua, umbral aplicado, etiqueta inferida y artefacto de explicabilidad visual.

---

## 5. APIs del Backend (FastAPI)

Las APIs exponen endpoints estricta y gobernadamente:

- `/api/governance/model-versions`: Consulta de versiones de modelos registradas, filtradas por estado y linaje.
- `/api/governance/deployments`: Consulta y resolución de deployments activos por entorno.
- `/api/runs/grouped-lineage`: Obtención de corridas agrupadas con su linaje completo (entrenamiento -> evaluación -> explicabilidad).
- `/api/runs/{run_id}`: Detalle exhaustivo de una corrida específica.
- `/api/catalog/model-comparison`: Comparativa de rendimiento entre arquitecturas gobernadas (VGG16, DenseNet121, Custom CNN).
- `/api/explainability/runs`: Registro y consulta de mapas de calor Grad-CAM asociados a predicciones.
- `/api/dataset/browser`: Explorador de imágenes de entrenamiento y prueba con paginación y filtrado.

---

## 6. Scripts de Control MLOps

- `scripts/init_db.py`: Ejecutor transaccional de migraciones SQL con verificación de checksums e idempotencia.
- `scripts/backfill_run_lineage.py`: Migrador de linaje para corridas previas.
- `scripts/diagnose_run_lineage.py`: Diagnóstico de integridad de relaciones en la base de datos.
- `scripts/clean_training_outputs.py`: Limpiador seguro de temporales manteniendo artefactos gobernados.
- `scripts/test_db.py`: Verificador de conexión e integridad de esquemas.

---

## 7. Frontend y Navegación

- **Menú Padre `Modelo IA`**: Agrupa jerárquicamente las vistas de "Modelos Liberados", "Despliegues", "Comparativa" y "Linaje".
- **Sin referencias físicas**: Se eliminaron completamente textos o inputs relativos a `best_model.keras` o rutas absolutas del disco.
- **Consumo dinámico**: El selector de inferencia consume únicamente `deployed_model_version_id` provenientes de despliegues activos.
- **Manejo de estados**: Interfaz resiliente que informa adecuadamente en ausencia de deployments activos y deshabilita modelos con estado `unresolved` o `retired`.
- **Accesibilidad**: Teclado, foco y atributos ARIA completamente validados (`role="menu"`, `aria-expanded`, `aria-controls`).

---

## 8. Clasificación de Usos de `best_model.keras`

Se auditó la totalidad del código fuente. Las referencias remanentes a `best_model.keras` se clasifican en:

1. **Permitido (Desarrollo / Artefacto de salida de entrenamiento / Compatibilidad legacy / Tests):**
   - `src/train.py`: Nombre por defecto del archivo generado por el callback `ModelCheckpoint` de Keras durante la fase de entrenamiento, el cual es inmediatamente empaquetado y registrado con SHA-256 en `model_versions`.
   - `src/calibrate.py`: Texto de ayuda CLI para compatibilidad legacy `--checkpoint`.
   - `tests/*`: Archivos de prueba unitaria explícita.

2. **No Permitido (Identidad principal, Inferencia productiva, Selector Frontend, Referencia única):**
   - **0 instancias encontradas en backend API, frontend React o lógica de inferencia productiva.**

---

## 9. Estado de Modelos Existentes

Existen 12 `model_versions` registradas en la base de datos PostgreSQL:
- **VGG16 (vgg16_tracked):** 4 versiones registradas, linaje `resolved`, artefactos empaquetados con SHA-256.
- **DenseNet121 (densenet121_tracked):** 4 versiones registradas, linaje `resolved`, artefactos empaquetados con SHA-256.
- **Custom CNN (custom_cnn_tracked):** 4 versiones registradas, linaje `resolved`, estado `discovered / candidate`.

---

## 10. Estado del Custom CNN (`outputs/custom_cnn/best_model.keras`)

- **Estado Actual:** `candidate` / `unresolved`.
- **Justificación Auditora:** El modelo `custom_cnn` ha sido empaquetado y registrado en la base de datos con su linaje de entrenamiento. Sin embargo, **no cuenta con una evaluación formal en el conjunto de prueba utilizando el umbral clínico calibrado**.
- **Regla de Gobernanza:** Por esta razón, el modelo **NO está marcado como `approved` para uso clínico y NUNCA se despliega automáticamente en entornos productivos**.
- **Permisividad Experimental:** Solo se permite su activación en entorno `experimental` si se solicita explícitamente y con advertencia formal de uso no clínico.

---

## 11. Resumen de Ejecución de Tests

| Suite de Tests | Herramienta | Total Tests | Pasados | Fallados | Omitidos | Estado |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Python Unit & Integration** | `pytest` | 335 | 319 | 0 | 16 | **PASS** |
| **PostgreSQL 17 Integration** | `pytest` | 1 | 1 | 0 | 0 | **PASS** |
| **Backend API (FastAPI)** | `pytest` | 34 | 34 | 0 | 0 | **PASS** |
| **Frontend React / Nav** | `node --test` | 8 | 8 | 0 | 0 | **PASS** |
| **Frontend TypeScript Build** | `vite build / tsc` | 1 | 1 | 0 | 0 | **PASS** |

---

## 12. Riesgos e Identificación

- **Riesgos Mitigados:**
  - Inferencia sobre modelos no rastreados o modificados en disco (prevenido por SHA-256 mismatch check).
  - Ambigüedad de umbral diagnóstico (prevenido por snapshots inmutables en `deployed_model_versions`).
  - Pérdida de contexto en predicciones clínicas (prevenido por el linaje jerárquico completo en `cell_predictions`).
- **Riesgos Residuales:**
  - Operación en entorno offline sin acceso a PostgreSQL 17 (requiere base local o contingencia SQLite).

---

## 13. Limitaciones

- Ninguna versión de modelo puede pasar a producción sin contar con `approved_at` y evaluación en test set con threshold clínico.
- No se permiten escrituras directas sobre `model_versions` o `deployed_model_versions` fuera de los servicios de gobernanza.

---

## 14. Procedimiento de Rollback

Si una versión desplegada presenta anomalías en producción:
1. Invocar la función de desactivación/retiro registrando `retired_by` y `retirement_reason`.
2. Crear un nuevo registro en `deployed_model_versions` para la versión estable previa, estableciendo `rollback_of_deployment_id` igual al ID del deployment fallido.
3. El frontend y backend apuntarán automáticamente a la nueva `deployed_model_version_id` activa.

---

## 15. Procedimiento para Liberar un Modelo Nuevo

1. Ejecutar entrenamiento con `src/train.py`, produciendo el artefacto Keras y métricas de validación.
2. Registrar el artefacto en `model_versions` calculando su hash SHA-256, `preprocessing_profile_snapshot` y `class_mapping`.
3. Ejecutar evaluación formal sobre el test set con `src/evaluate.py --require-lineage`.
4. Ejecutar explicabilidad con `src/explain.py --require-lineage`.
5. Marcar la versión como `validated` y solicitar aprobación para `approved`.

---

## 16. Procedimiento para Desplegar un Modelo

1. Verificar que la `model_version` posea `lineage_status = 'resolved'` y `status = 'approved'`.
2. Definir el entorno objetivo (`production`, `staging`, `experimental`).
3. Registrar la nueva fila en `deployed_model_versions` asociando el umbral clínico calibrado y snapshots de preprocesamiento.
4. Desactivar deployments previos en dicho entorno asignando `retired_at` y `supersedes_deployment_id`.

---

## 17. Procedimiento para Retirar un Modelo

1. Cambiar el estado de la `model_version` a `retired`.
2. Asignar fecha en `retired_at`, usuario en `retired_by` y motivo en `retirement_reason`.
3. Retirar cualquier `deployed_model_version` activa asociada.

---

## 18. Criterios para Comenzar Etapa 2

Todos los 16 criterios bloqueantes han sido auditados y verificados positivamente.

---

## Conclusión

### **ETAPA 2 HABILITADA**
