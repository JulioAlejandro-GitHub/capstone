# Frontend

SPA React 19/TypeScript para gobierno de modelos y análisis técnico de frotis.
Requiere Node.js 22 y npm 10.

## Desarrollo y validación

Desde la raíz del repositorio:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend test
npm --prefix frontend run build
```

Vite usa `frontend/.env` o `frontend/.env.example` para resolver el backend y el
datasource por defecto. El `Dockerfile` es un entrypoint opcional utilizado por
la configuración Compose; las pruebas y el build oficiales son los scripts npm.

## Sesión

El login obtiene un bearer desde `/api/v1/auth/login`. La aplicación guarda sólo
ese token en `localStorage`, valida el principal mediante `/api/v1/auth/me` al
recargar y elimina la sesión ante logout o autenticación fallida. El backend sigue
siendo la autoridad de roles y permisos.

## Navegación

- `/modelo-ia/dataset?datasource=malaria` consulta Dataset Versions gobernadas
  mediante `/api/datasets` y `/api/datasets/{dataset_version_id}`.
- `/frotis/analizar` es el workflow canónico de ingesta, calidad, detección,
  clasificación y resultados.
- `/frotis/historial` y `/frotis/historial/:analysisRunId` reconstruyen análisis
  persistidos.

`/frotis/cargar`, `/frotis/analisis` y `/frotis/revision` se conservan como
redirects de compatibilidad hacia `/frotis/analizar`. El workflow muestra por
separado resultados automáticos y decisiones humanas, y no selecciona un modelo
ni un threshold alternativo cuando falta una publicación válida.
