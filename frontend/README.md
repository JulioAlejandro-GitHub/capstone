# Frontend

SPA React 19/TypeScript para gobierno de modelos y análisis técnico de frotis.
Requiere Node.js 22 y npm 10.

## Desarrollo

Desde la raíz del repositorio:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

El backend debe estar disponible en `http://127.0.0.1:8000` y permitir el
origen Vite configurado. Docker no forma parte del runtime.

## Sesión

El login obtiene un JWT desde `/api/v1/auth/login`. La aplicación lo guarda en
`localStorage`, restaura el principal al recargar mediante `/api/v1/auth/me` y
lo elimina al cerrar sesión. El frontend maneja 401/403, pero el backend sigue
siendo la autoridad de roles y ownership. Nunca escriba tokens, credenciales o
paths físicos en URLs, mensajes o logs.

## Navegación

- `/modelo-ia/...`: datasets, ejecuciones, evaluaciones, versiones,
  publicaciones y trazabilidad.
- `/frotis/analizar`: workflow canónico de configuración, ingesta, calidad,
  detección, clasificación y resultados.
- `/frotis/historial`: lista de análisis persistidos.
- `/frotis/historial/:analysisRunId`: reconstrucción de un análisis por UUID.

`/frotis/cargar`, `/frotis/analisis` y `/frotis/revision` son redirects de
compatibilidad hacia `/frotis/analizar`. Las rutas se construyen exclusivamente
con `src/router.ts`; los deep links se restauran desde la API, no desde objetos
React serializados.

El workflow muestra por separado resultados automáticos, decisiones humanas,
modelo/threshold congelados y advertencia experimental. Un modelo no disponible
produce un estado bloqueado explícito; la UI no elige el último checkpoint ni
inventa un fallback.

## Calidad

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Diseño, rutas y accesibilidad: [`../docs/design-system.md`](../docs/design-system.md).
Workflow científico: [`../docs/ai-pipeline.md`](../docs/ai-pipeline.md) y
[`../docs/stage2-workflow.md`](../docs/stage2-workflow.md).
