# Navegación lateral profesional

## Problema original

El sidebar funcionaba con rutas reales, pero era una columna básica de botones y texto: no tenía modo contraído, iconografía consistente, agrupación cognitiva, drawer móvil ni una presentación profesional del estado de conexión.

## Alternativas evaluadas

### `react-pro-sidebar`

Es compatible conceptualmente con React y React Router, pero añadiría una dependencia, un sistema de estilos y una API de composición para una navegación que ya tenía layout, rutas y estados bien delimitados. También obligaría a adaptar su comportamiento mobile y accesibilidad a las reglas específicas del proyecto.

### Componente propio

La estructura existente ya utilizaba `NavLink`, `Outlet`, rutas tipadas y datasource transversal. Se eligió evolucionarla con componentes pequeños y CSS basado en tokens. El resultado tiene menor superficie de dependencia, preserva el routing y permite controlar foco, drawer y tooltips.

**Decisión:** no se instaló `react-pro-sidebar` ni una biblioteca de iconos.

## Arquitectura

`Layout` mantiene el header, datasource, breadcrumb y `Outlet`. `AppSidebar` administra exclusivamente presentación de navegación:

- preferencia expandida/contraída;
- apertura del grupo Modelo IA;
- drawer mobile;
- bloqueo de scroll y ciclo de foco;
- cierre por Escape, overlay o navegación.

La ruta activa procede siempre de React Router.

## Componentes

- `components/Layout.tsx`: layout compartido, header móvil, datasource y breadcrumb.
- `components/navigation/AppSidebar.tsx`: sidebar desktop y drawer mobile.
- `components/navigation/navigationConfig.ts`: configuración tipada y grupos.
- `components/navigation/NavigationIcon.tsx`: única familia de iconos SVG.

## Menú

- General: Resumen.
- Experimentación: Ejecuciones, Evaluaciones, Comparación de modelos, Explicabilidad.
- Gobernanza: Modelos liberados, Despliegues, Trazabilidad.
- Operación: Predicciones, Errores y logs.
- Datos: Dataset, Datasets y modelos.

Los grupos son visuales; no añaden niveles interactivos. Modelo IA es el único grupo desplegable.

## Estados desktop

Expandido usa `268px`, muestra identidad, grupos, iconos y etiquetas. Contraído usa `76px`, muestra el isotipo `ML`, iconos, indicador activo y tooltips por hover o foco. La preferencia se valida y guarda como `ml-dashboard.sidebar.collapsed`; no se persisten rutas ni objetos.

## Mobile

Desde `900px` la navegación es un drawer oculto:

- botón “Abrir navegación” en el header;
- overlay y botón de cierre;
- Escape;
- cierre al navegar;
- bloqueo del scroll de fondo;
- foco inicial dentro del drawer;
- focus trap;
- retorno del foco al disparador al cerrar sin navegación.

La preferencia contraída de desktop no oculta etiquetas dentro del drawer.

## Routing y datasource

Cada opción es un `NavLink` y utiliza las rutas de `router.ts`. `withAllowedQuery` conserva `datasource`. La función `sectionForPath` reconoce igualdad o prefijo, por lo que las rutas de detalle activan su sección:

- ejecución → Ejecuciones;
- model version → Modelos liberados;
- deployment → Despliegues.

Atrás, Adelante, recarga y deep links continúan usando History API.

## Accesibilidad

- landmarks `aside`, `nav`, `main`;
- enlaces reales y `aria-current` proporcionado por `NavLink`;
- `aria-expanded` y `aria-controls`;
- nombres accesibles para botones de icono;
- ArrowRight/ArrowLeft en Modelo IA;
- Escape y focus trap en mobile;
- tooltips visibles por `:focus-visible`;
- indicador activo mediante fondo, peso y borde lateral;
- `prefers-reduced-motion`;
- contraste alto sobre fondo neutro oscuro.

## Design tokens

Los tokens viven en `:root`:

- anchos expandido y contraído;
- fondos, foreground y muted;
- hover y active;
- borde y acento;
- duración de transición;
- altura y radio de los items.

No existe tema oscuro global, por lo que no se agregó un selector de tema falso. Los tokens permiten extender la navegación más adelante.

## Iconografía

`NavigationIcon` ofrece SVG lineales de 24×24 con el mismo stroke, alineación y semántica decorativa. No se mezclan emojis ni bibliotecas diferentes.

## Estado de conexión

“Backend conectado” aparece en el footer del sidebar y como indicador compacto en el header. Es una etiqueta de integración del frontend, no representa el ambiente de deployment del modelo.

## Tests

Los tests verifican:

- router y `NavLink`;
- rutas de lista y detalle;
- grupos y opciones reales;
- estados expandido/contraído;
- persistencia;
- drawer, overlay, Escape, scroll y foco;
- datasource;
- tooltips por hover/focus;
- design tokens y responsive;
- ausencia de paths internos.

## Descripción visual

Desktop presenta una columna azul grafito de altura completa, identidad compacta, encabezados de grupo discretos y enlaces de 42px. La ruta activa combina superficie azul, tipografía reforzada y una barra lateral celeste. El contenido permanece claro.

Contraído conserva una columna de iconos alineados y tooltips oscuros. Mobile utiliza el mismo componente como drawer sobre overlay, mientras el header muestra identidad corta, sección actual y datasource.

## Agregar una opción

1. Confirmar que la página y ruta existen.
2. Añadir un item a `navigationConfig.ts` dentro del grupo correcto.
3. Reutilizar un icono existente o añadir uno a `NavigationIconName` y `paths`.
4. No construir rutas manualmente ni agregar lógica al layout.
5. Verificar ruta activa, datasource, teclado, mobile y ausencia de información interna.
