# Frontend

Use Node 22/npm 10. `npm ci`, `npm test`, `npm run build` y `npm run dev`. El JWT se
mantiene sólo en memoria; recargar requiere autenticar nuevamente. La UI maneja 401,
403 y rutas protegidas sin agregar todavía el flujo Frotis.
# Ejecución local

```bash
npm --prefix frontend run dev
```

El frontend oficial se ejecuta con Node/Vite local. Docker no es un gate ni una dependencia.

La navegación separa el desarrollo de modelos en **Modelo IA** de su uso operacional en
**Análisis de frotis**. Este último módulo se muestra a los mismos usuarios autenticados
que ya tenían acceso a la carga y contiene **Cargar imágenes** (`/frotis/cargar`), que
permite buscar o generar paciente, seleccionar o generar muestra y cargar múltiples
originales sin calcular metadata técnica en el cliente. Las futuras funciones operacionales
de la Etapa 2 se incorporarán bajo este módulo; este cambio no agrega funcionalidad nueva.
# Control de calidad

La ruta protegida `/frotis/analisis` lista lotes, crea runs, ejecuta el gate y
presenta métricas y revisión según los permisos del usuario.
