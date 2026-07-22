# Navegación frontend “Modelo IA” y Flujo de Promoción de Modelos

## Inventario y Arquitectura

El frontend es React 19 + TypeScript + Vite. La navegación se administra en `App.tsx` manteniendo claves de página inmutables.
El menú padre colapsable **Modelo IA** agrupa jerárquicamente:

```text
Modelo IA
├── Resumen
├── Ejecuciones (/runs)  <-- Punto de entrada para promoción desde tarjeta TRAIN
├── Evaluaciones
├── Comparación de modelos
├── Modelos liberados (/model-versions) <-- Ficha de model_version e iniciación de despliegue
├── Despliegues (/deployments) <-- Activar/retirar/rollback de deployed_model_version
├── Trazabilidad
├── Explicabilidad
├── Predicciones
├── Dataset
└── Datasets y modelos

Errores y logs
```

## Flujo de Promoción MLOps

El flujo de promoción se inicia exclusivamente en la **tarjeta TRAIN** del menú Ejecuciones mediante el botón `PromotionButton`:

$$\text{TRAIN} \longrightarrow \text{Preparar despliegue} \longrightarrow \text{model\_version} \longrightarrow \text{Modelos liberados} \longrightarrow \text{Crear deployment} \longrightarrow \text{Despliegues} \longrightarrow \text{Activar}$$

### Responsabilidades por Pantalla
1. **Ejecuciones (`/runs`)**: Visualiza el linaje agrupado y permite iniciar/continuar la promoción desde la tarjeta TRAIN (`training_run_id`). Las tarjetas de EVALUATE y EXPLAIN no contienen botones de despliegue directo.
2. **Modelos liberados (`/model-versions`)**: Permite inspeccionar la versión inmutable (`model_version_id`), validar linaje, revisar la evaluación formal y solicitar la creación de un despliegue en estado `pending`.
3. **Despliegues (`/deployments`)**: Permite activar, desactivar, retirar o ejecutar rollback de instancias (`deployed_model_version_id`).

## Matriz de Estados del Botón de Promoción

| Estado | Condición Backend | Etiqueta Botón | `button_enabled` | Comportamiento / Destino |
| :---: | :--- | :--- | :---: | :--- |
| **A** | Entrenamiento no completado. | **No disponible** | `false` | Tooltip: "El entrenamiento debe finalizar antes de preparar una versión." |
| **B** | Falta evaluación, linaje o hash mismatch. | **No disponible** | `false` | Muestra popover accesible ⚠️ con la lista de `blocking_reasons`. |
| **C** | Entrenamiento listo, sin `model_version`. | **Preparar despliegue** | `true` | Llama `POST /prepare-release` y navega a `/modelo-ia/modelos-liberados/{id}`. |
| **D** | `model_version` en `candidate` / `validated`. | **Ver modelo liberado** | `true` | Redirige a `/modelo-ia/modelos-liberados/{mv_id}`. |
| **E** | `model_version` aprobada sin despliegue. | **Continuar despliegue** | `true` | Redirige a `/modelo-ia/modelos-liberados/{mv_id}?action=deploy`. |
| **F** | Despliegue en estado `pending`. | **Ver despliegue pendiente** | `true` | Redirige a `/modelo-ia/despliegues/{dep_id}`. |
| **G** | Despliegue en estado `active`. | **Ver despliegue** | `true` | Redirige a `/modelo-ia/despliegues/{dep_id}`. |
| **H** | Modelo en `rejected` / `retired` / `unresolved`. | **No disponible** | `false` | Explicación en popover de bloqueo. |

## Indicador Compacto de Progreso (`PromotionTracker`)

Ubicado en la tarjeta TRAIN para brindar visibilidad sin recargar visualmente:
- `✓ Entrenamiento`
- `✓ Evaluación`
- `✓ Explicabilidad (Opcional)`
- `○ Versión aprobada`
- `○ Desplegada`

## Endpoints Consumidos

- `GET /runs/grouped-lineage`: Obtiene árbol agrupado.
- `GET /api/training-runs/{training_run_id}/promotion-status`: Consulta *read-only* de estado de promoción.
- `POST /api/training-runs/{training_run_id}/prepare-release`: Registra o resuelve la `model_version` de forma idempotente.
- `GET /api/model-versions` y `GET /api/model-versions/{id}`
- `POST /api/deployments`: Crea un nuevo despliegue pendiente.
- `POST /api/deployments/{id}/activate`: Activa atómicamente un despliegue.

## Accesibilidad y Verificación

- Atributos `aria-disabled`, `aria-label`, `role="button"` y navegación por teclado.
- Sin exposición de rutas físicas ni archivos genéricos (`best_model.keras`).
- Pruebas automatizadas ejecutadas mediante `npm test` (`promotion_ui.test.mjs`) y compilación validada con `npm run build`.
