# Análisis de frotis v3 — Microscopio Digital Inmersivo

Módulo de CAPSTONE-MICROSCOPE-01B. Coexiste con «Analizar imagen» (v1) y
«Análisis de frotis v2» sin sustituirlos: tiene menú, rutas, estilos y estado
de presentación propios.

## Rutas

| Ruta | Uso |
|---|---|
| `/frotis/microscopio` | Acceso A: incorporar imágenes y comenzar un análisis |
| `/frotis/microscopio/:analysisId` | Acceso B: abrir un análisis existente (`analysisId` = `analysis_run_id`) |

Parámetros opcionales: `image`, `selected_detection`, `selected_prediction`.
Ambas rutas se registran con un único patrón (`:analysisId?`) para que el
workspace no se desmonte cuando un análisis nuevo recibe su identificador.

## Estructura

```
analisis-frotis-v3/
├── MicroscopioPage.tsx   entrada de ruta: valida el UUID y elige la sesión
├── routes.ts             rutas, vistas y namespace de almacenamiento (puro)
├── adapters/             contratos existentes → modelo de presentación (puros)
├── hooks/                lectura del análisis, imagen autenticada, alto disponible
├── state/                persistencia local bajo `capstone:frotis:v3:`
├── components/           workspace, viewport, carga, sesiones, acceso desde Historial
└── styles/               tokens_frotis_v3.css + reglas bajo `.frotis-v3`
```

## Contratos reutilizados (sin cambios)

- `useSmearAnalysisWorkflow` — carga, control técnico, detección y clasificación
  de un análisis nuevo. v3 no define un pipeline propio.
- `GET /api/v1/scientific/analysis-history/:analysisRunId` — análisis existente.
- `GET /api/v1/scientific/images/:id/content` — imagen original autenticada.
- `POST /api/v1/scientific/images/upload` — mismo formulario que «Analizar imagen».
- Permisos `scientific.*` de `useAuth()`.

## Reglas del módulo

- No importar nada de `analisis-frotis-v2` ni de sus datos simulados.
- Toda regla CSS bajo `.frotis-v3`; sin selectores globales ni variables en `:root`.
- Persistencia local solo en `state/`, con el namespace `capstone:frotis:v3:`.
- Abrir un análisis existente es una consulta: no crea ni reintenta RUNs.
- Una capacidad sin implementación funcional se muestra deshabilitada con su
  fase, nunca simulada.

## Estado por fase

| Fase | Estado |
|---|---|
| 01B.1 Integración y navegación | Implementada |
| 01B.2 Experiencia visual continua | Implementada: zoom, pan, ajuste, rotación, brillo, contraste, gamma, saturación, restaurar, minimapa, instrumentos flotantes y Layout Manager. Pendientes: regla, lupa contextual y región de mayor densidad |
| 01B.3 Revisión celular | Parcial: capa de células y predicciones reales, selección, navegación, filtros, inspector y enlace compartible. Pendientes: registrar revisiones y anotaciones dentro de v3, menú contextual, explicabilidad, modos silencioso/guiado |
| 01B.4 Reporte | Implementado en lectura: resumen, imágenes, hallazgos y «Ver en microscopio». Pendiente: anotaciones |
| 01B.5 Contexto avanzado | Parcial: `image`, `selected_detection` y `selected_prediction` con validación de pertenencia; preferencias persistidas. Pendiente: viewport persistido por análisis y multifrotis |
| 01B.6 Rendimiento | Pendiente |

Pruebas: `frontend/tests/frotis-v3.test.mjs`.
