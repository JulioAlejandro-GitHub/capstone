# Flujo de Usuario MLOps: Desde Ejecuciones hasta Despliegues

**Fecha:** 2026-07-22  
**Módulo:** Frontend React + MLOps Promotion Pipeline  
**Proyecto:** Capstone MIA — Universidad Adolfo Ibáñez  

---

## 1. Visión General del Flujo de Usuario

El flujo de promoción guía al usuario científico desde un entrenamiento completado en la vista de **Ejecuciones** (`/runs`) hasta su activación inmutable en la vista de **Despliegues** (`/deployments`), sin permitir despliegues directos a producción sin pasar por la validación de gobernanza.

```text
[ Tarjeta TRAIN (Ejecuciones) ]
        │  Clic en "Preparar despliegue" (POST /prepare-release)
        ▼
[ Ficha del Modelo Liberado (Modelos liberados /model-versions/:id) ]
        │  Revisión de métricas, linaje y clic en "Desplegar versión"
        ▼
[ Modal de Solicitud de Despliegue ]
        │  Configuración de entorno (staging/production), alias y confirmación
        ▼
[ Pantalla de Despliegues (/deployments) ]
        │  Conmutación atómica a estado "active"
        ▼
[ Modelo Desplegado y Activo en Producción ]
```

---

## 2. Componentes de la Tarjeta TRAIN

La tarjeta del entrenamiento principal (**TRAIN**) incluye de forma exclusiva los siguientes dos elementos visuales junto al botón "Ver detalle":

### 2.1 Indicador Compacto de Progreso (`PromotionTracker`)
Ubicado en la celda de análisis de la tarjeta, muestra el avance de gobernanza sin alterar el diseño:

- `✓ Entrenamiento` (Verde si estado == `completed`)
- `✓ Evaluación` (Verde si existe `evaluation_run_id`)
- `✓ Explicabilidad (Opcional)` (Verde si existen mapas Grad-CAM)
- `○ Versión aprobada` (Verde si `status == 'approved'`)
- `○ Desplegada` (Verde si `deployment_status == 'active'`)

### 2.2 Botón Dinámico de Promoción (`PromotionButton`)
Evalúa deterministamente los **8 estados de promoción (A a H)**:

```
[ Estado A/B/H ]  --> [ No disponible ⚠️ ] (Borde gris, popover con motivos de bloqueo)
[ Estado C ]      --> [ Preparar despliegue ] (Boton primario azul con spinner de carga)
[ Estado D ]      --> [ Ver modelo liberado ] (Acceso directo a la ficha del modelo)
[ Estado E ]      --> [ Continuar despliegue ] (Abre modal de solicitud de despliegue)
[ Estado F ]      --> [ Ver despliegue pendiente ] (Acceso a la vista de despliegues pendientes)
[ Estado G ]      --> [ Ver despliegue ] (Acceso al despliegue activo en producción)
```

---

## 3. Modal de Solicitud de Despliegue

Al seleccionar la opción "Desplegar versión" en **Modelos liberados**, se despliega el modal interactivo con los siguientes campos:

1. **Entorno (`environment`):** `Experimental`, `Staging`, `Producción`.
2. **Nombre del Despliegue (`deployment_name`):** Identificador técnico del deployment.
3. **Alias:** `Champion` (modelo principal) o `Candidate`.
4. **Motivo o Comentario:** Registro de auditoría para la transición.

### Confirmación Reforzada de Producción
Al seleccionar el ambiente **Producción**, la interfaz despliega automáticamente un aviso destacado de gobernanza:

> ⚠️ **Confirmación de Producción:** Se activará una versión para el ambiente de producción. La activación final se realizará desde Despliegues.

---

## 4. Mapeo de Errores Legibles para el Usuario

Los códigos de bloqueo del backend se traducen automáticamente a mensajes claros y accionables:

| Código de Bloqueo Backend | Mensaje Presentado en la Interfaz |
| :--- | :--- |
| `EVALUATION_REQUIRED` | "Falta una evaluación formal del modelo." |
| `CLINICAL_THRESHOLD_REQUIRED` | "El threshold clínico no ha sido validado en el conjunto requerido." |
| `UNRESOLVED_LINEAGE` | "No es posible demostrar el entrenamiento de origen del checkpoint." |
| `CHECKPOINT_HASH_MISMATCH` | "El artefacto no coincide con el registrado." |
| `MODEL_VERSION_CONFLICT` | "Ya existe una versión incompatible para este entrenamiento." |
| `TRAINING_NOT_COMPLETED` | "El entrenamiento debe finalizar antes de preparar una versión." |

---

## 5. Accesibilidad y Compatibilidad Móvil

1. **Navegación por Teclado:** El botón de promoción y el botón de bloqueadores ⚠️ aceptan foco `Tab`, activación vía `Enter` o `Espacio` y exponen `aria-disabled` y `aria-label`.
2. **Popovers Flexibles:** El detalle de bloqueadores se renderiza con `role="status"` y posicionado para no desbordar en pantallas pequeñas.
3. **Resolución Móvil:** En pantallas pequeñas (<768px), el botón de promoción se adapta al contenedor sin romper la tarjeta ni exponer rutas físicas del servidor.
