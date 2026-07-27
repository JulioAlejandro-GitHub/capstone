# Frontend

Use Node 22/npm 10. `npm ci`, `npm test`, `npm run build` y `npm run dev`. El JWT se
mantiene sólo en memoria; recargar requiere autenticar nuevamente. La UI maneja 401,
403 y rutas protegidas sin agregar todavía el flujo Frotis.
# Ejecución local

```bash
npm --prefix frontend run dev
```

El frontend oficial se ejecuta con Node/Vite local. Docker no es un gate ni una dependencia.

`/frotis/cargar` permite buscar o generar paciente, seleccionar o generar muestra
y cargar múltiples originales sin calcular metadata técnica en el cliente.
