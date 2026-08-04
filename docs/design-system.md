# Sistema de diseño y navegación

La interfaz combina un shell operativo común con una superficie inmersiva
“Liquid Glass” para el workflow de frotis. El diseño debe comunicar estado y
trazabilidad sin sugerir certeza clínica.

## Navegación canónica

| Área | Ruta | Propósito |
|---|---|---|
| Resumen IA | `/modelo-ia/resumen` | Estado general |
| Ejecuciones | `/modelo-ia/ejecuciones` | TRAIN/EVALUATE/EXPLAIN y publicación |
| Modelos liberados | `/modelo-ia/modelos-liberados` | Inventario versionado |
| Despliegues | `/modelo-ia/despliegues` | Compatibilidad de gobierno existente |
| Analizar frotis | `/frotis/analizar` | Workflow unificado y reanudable |
| Historial | `/frotis/historial` | Análisis previos |
| Detalle histórico | `/frotis/historial/:analysisRunId` | Reconstrucción desde API |

`frontend/src/router.ts` es la fuente única para construir URLs. Las rutas
`/frotis/cargar`, `/frotis/analisis` y `/frotis/revision` redirigen a
`/frotis/analizar` conservando el query string. Los redirects legacy de Modelo
IA también se conservan con `replace`. El mapa completo se mantiene en
[frontend_clean_urls_and_routing.md](frontend_clean_urls_and_routing.md).

## Principios visuales

- El shell usa jerarquía, espaciado y navegación lateral consistentes.
- El workflow de frotis encapsula sus variables y superficies glass para no
  contaminar el resto de la aplicación.
- Color, icono y texto comunican estado juntos; nunca se depende sólo del color.
- IDs, hashes, thresholds y métricas usan tratamiento monoespaciado cuando
  mejora la lectura técnica.
- Las acciones destructivas o de publicación requieren confirmación inline y
  feedback específico; no se ocultan errores tras un redirect.
- Resultados automáticos, revisiones humanas y advertencias experimentales se
  distinguen visual y semánticamente.

## Accesibilidad

Controles interactivos deben ser elementos nativos, tener nombre accesible y un
estado `:focus-visible` claro. Cargas y confirmaciones usan regiones
`aria-live`; disclosures conectan `aria-expanded` con `aria-controls`. El foco
se mueve al encabezado principal tras navegar. Las animaciones respetan
`prefers-reduced-motion` y el layout conserva funcionalidad en viewport móvil.

## Estado, URL y sesión

- IDs públicos y filtros estables viven en path/query; objetos, tokens y paths
  físicos nunca se serializan en la URL.
- Un deep link debe reconstruirse mediante GET y mostrar 404/ID inválido de
  forma explícita.
- La sesión JWT se guarda en `localStorage` y se restaura al recargar. Esto es
  persistencia de autenticación, no fuente de verdad del workflow.
- El estado del análisis se reconstruye desde PostgreSQL; un refresh no debe
  volver a ejecutar detección, clasificación ni Grad-CAM.

## Extensión

Antes de agregar una vista, confirme que existe un endpoint estable, añada la
ruta a `router.ts`, mantenga breadcrumbs/título, pruebe teclado, recarga,
Atrás/Adelante, viewport móvil y estados 401/403/404. Reutilice patrones del
shell o del workflow; no cree un tercer lenguaje visual para una pantalla
aislada.
