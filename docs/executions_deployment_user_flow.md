# Flujo de usuario: Ejecuciones → liberación → despliegue

## Descripción visual

Cada grupo mantiene su estructura actual:

```text
┌─ TRAIN ───────────────────────────────────────────────┐
│ Run, modelo, métricas y análisis                     │
│ [Ver detalle]                                        │
│ Liberación                                           │
│ ✓ Entrenamiento · ✓ Evaluación · ○ Explicabilidad   │
│ ○ Versión aprobada · ○ Desplegada                   │
│ [Preparar despliegue]                                │
└──────────────────────────────────────────────────────┘
  ├─ EVALUATE [Ver evaluación]
  └─ EXPLAIN  [Ver explicabilidad]
```

El bloque de liberación está en la última celda de TRAIN, debajo de la acción
existente. Usa texto de 9–11 px, wrapping y separador fino para no aumentar
innecesariamente la tarjeta. En pantallas de hasta 700 px, el botón ocupa el ancho
disponible y mantiene 40 px de alto.

## Estados del botón

| Estado backend | Texto | Comportamiento |
|---|---|---|
| Loading GET | Consultando… | Deshabilitado |
| `unavailable` | No disponible | Deshabilitado; detalle de bloqueadores |
| `prepare_release` | Preparar despliegue | Ejecuta POST una sola vez |
| `review_model_version` | Ver modelo liberado | Abre la versión |
| `approve_model_version` | Ver modelo liberado | Abre la versión |
| `create_deployment` | Continuar despliegue | Abre la versión |
| `review_pending_deployment` | Ver despliegue pendiente | Abre el deployment |
| `view_active_deployment` | Ver despliegue | Abre el deployment |

Versiones rejected, retired o con linaje unresolved llegan como `unavailable`.
Explicabilidad se muestra “(opcional)” cuando no existe y no se convierte en bloqueo
frontend.

## Flujo

1. Al cargar Ejecuciones se consulta promotion-status para cada TRAIN.
2. El usuario conserva “Ver detalle” para revisar el run.
3. Si está listo, “Preparar despliegue” llama al endpoint de preparación.
4. El botón queda deshabilitado y muestra spinner/texto “Preparando…”.
5. El frontend sustituye el estado con la respuesta autoritativa.
6. Si existe `model_version_id`, abre Modelos liberados con esa selección.
7. Si existe `deployment_id`, abre Despliegues con esa selección.
8. Modelos liberados muestra evidencia, pero no valida, aprueba ni crea deployments
   hasta que existan permisos y operaciones backend soportadas.
9. Despliegues muestra la revisión seleccionada y continúa read-only.

No hay activación directa desde Ejecuciones.

## Navegación

Rutas de contrato:

```text
/modelo-ia/modelos-liberados/{model_version_id}
/modelo-ia/despliegues/{deployed_model_version_id}
```

El frontend actual no usa React Router. `App.tsx` traduce los destinos a
`page='model-versions'` o `page='deployments'` y conserva el ID seleccionado. Cambiar
datasource o navegar a otra sección limpia los IDs para evitar cruces.

## Mensajes

| Código | Mensaje |
|---|---|
| `TRAINING_NOT_COMPLETED` | El entrenamiento debe finalizar antes de preparar una versión. |
| `EVALUATION_REQUIRED` | Falta una evaluación formal del modelo. |
| `CLINICAL_THRESHOLD_REQUIRED` | El threshold clínico no ha sido validado en el conjunto requerido. |
| `UNRESOLVED_LINEAGE` | No es posible demostrar el entrenamiento de origen del checkpoint. |
| `CHECKPOINT_HASH_MISMATCH` | El artefacto no coincide con el registrado. |
| `MODEL_VERSION_CONFLICT` | Ya existe una versión incompatible para este entrenamiento. |

Otros códigos muestran el mensaje seguro entregado por el backend. No se presentan
paths, nombres físicos de checkpoints ni hashes completos.

## Errores y timeout

- GET/POST tienen timeout mediante `AbortController`.
- El POST usa 30 segundos; las demás solicitudes usan 15 segundos.
- Un timeout se presenta como “La consulta tardó demasiado. Intenta nuevamente”.
- Al fallar el POST, se vuelve a consultar promotion-status y se conserva el error
  visible.
- El estado de preparación evita doble clic en toda la pantalla.
- Un mensaje `role=status` anuncia la preparación exitosa cuando la vista permanece
  en Ejecuciones.

## Accesibilidad

- Botones nativos y operables con teclado.
- `aria-label` incluye el training Run ID.
- `aria-disabled` refleja el estado además de `disabled`.
- `aria-describedby` relaciona el botón con el detalle de bloqueadores.
- El detalle usa `details/summary`, por lo que es accesible por teclado.
- Errores usan `role=alert`; progreso y éxito usan `role=status`.
- El progreso usa símbolos `✓/○` y texto, no sólo color.
- Todos los controles conservan `:focus-visible`.

## Verificación

```bash
cd frontend
npm test
npm run build
```

Verificar visualmente a 1440 px, 900 px y 390 px, incluyendo foco por teclado,
motivos desplegados, loading, timeout y selección en las páginas de destino.

