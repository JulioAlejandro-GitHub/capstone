# Frontend

Frontend React + Vite para visualizar experimentos ML del Capstone.

## Configuracion

```bash
cd frontend
cp .env.example .env
npm install
```

## Ejecutar

```bash
npm run dev
```

Por defecto se conecta a:

```text
http://localhost:8000
```

El frontend no se conecta a PostgreSQL directamente. Toda lectura pasa por `backend_api`.

## Vistas clinicas

La navegacion incluye `Evaluacion clinica` y `Run Detail` con:

- F2-score, PR-AUC, recall/sensibilidad parasitized, specificity y balanced accuracy.
- Checkpoint policy, selected epoch y policy_satisfied.
- Threshold clinico calibrado, target recall y threshold_source.
- Matriz de confusion con TN/FP/FN/TP bajo `0 = uninfected`, `1 = parasitized`.
- Predicciones por imagen, artefactos y explicabilidad visual experimental.

Detalle metodologico:

```text
../malaria_dl_local_project/docs/frontend_clinical_dashboard.md
```

## Validacion

Este paquete no define todavia `npm test` ni `npm run lint`. La validacion disponible es:

```bash
npm run build
```
