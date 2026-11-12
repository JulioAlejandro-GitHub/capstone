# CAPSTONE-MICROSCOPE-01B — Desarrollo del Microscopio Digital Inmersivo
## Especificación integral de implementación para Codex

### 0. Misión

Actúa como arquitecto de software senior, especialista en React, UX/UI de microscopía digital, visión computacional, integración FastAPI y PostgreSQL.

Implementa el nuevo módulo **Análisis de frotis v3 — Microscopio Digital Inmersivo**, integrado con Capstone.

El desarrollo debe ser funcional y utilizar datos científicos reales.

No construir una maqueta aislada, no reproducir el diseño actual de Scopio Labs y no utilizar los datos simulados de `analisis-2` como resultados científicos.

Trabaja por fases verificables, implementando las funcionalidades disponibles y documentando las brechas que requieran nuevos contratos.

---

# 1. NUEVO MENÚ PRINCIPAL — OBLIGATORIO

## 1.1 Incorporar «Análisis de frotis v3»

En el menú de navegación existente de Capstone, agregar una nueva opción inmediatamente debajo de:

**Análisis de frotis v2**

Nombre exacto:

**Análisis de frotis v3**

Utilizar preferentemente un icono de microscopio de la biblioteca de iconos existente.

No sustituir, renombrar ni eliminar «Análisis de frotis v2».

Mantener el mismo sistema de navegación, permisos, agrupación, diseño y comportamiento responsive del menú principal.

## 1.2 Ruta de entrada

El nuevo menú debe navegar a:

`/frotis/microscopio`

Esta es la **entrada para comenzar un nuevo análisis microscópico**.

Al ingresar, se presenta el primer estado inmersivo:

**Pantalla 1 — Incorporar imágenes de frotis.**

No abrir directamente Review Cells.

No exigir `analysisId` para iniciar un análisis nuevo.

## 1.3 Flujo completo desde el menú

El comportamiento debe ser:

```text
MENÚ GLOBAL CAPSTONE
    │
    ├── Análisis de frotis v2
    │
    └── Análisis de frotis v3
             │
             ▼
       /frotis/microscopio
             │
             ▼
       CARGA DE IMÁGENES
             │
             ▼
       REVISIÓN TÉCNICA
       Imagen visible
       Línea horizontal de escaneo
             │
             ▼
       MICROSCOPIO DIGITAL
             │
             ▼
       /frotis/microscopio/:analysisId
             │
             ├── FULL FIELD REVIEW
             ├── REVIEW CELLS
             └── REPORT
```

Las tres etapas se desarrollan dentro del mismo workspace.

La sensación debe ser que el usuario nunca abandonó el microscopio.

Cuando el backend devuelve el identificador del análisis, actualizar la URL a `/frotis/microscopio/:analysisId` mediante el mecanismo de navegación compatible con el router existente, preservando el estado del visor.

Evitar desmontar el workspace, reemplazar bruscamente la imagen o generar una transición de página.

## 1.4 Carga real de imágenes

Reutilizar el workflow de carga e ingestión existente de Capstone.

Permitir los formatos y cantidades de imágenes efectivamente soportados por el backend.

Cuando se incorporen varias imágenes, conservar sus identidades y relaciones reales.

No inventar posiciones espaciales entre capturas ni asumir que forman un mosaico registrado.

Reutilizar la preparación, validación y orquestación científica disponible; no construir un pipeline paralelo.

Si una capacidad de carga aún no está soportada, mostrar una restricción explícita en lugar de simular que funciona.

---

# 2. NUEVO ACCESO DESDE HISTORIAL — OBLIGATORIO

## 2.1 Ruta existente

Inspeccionar:

`/frotis/historial?datasource=malaria`

Localizar la tabla o listado de análisis y el botón existente:

**Ver detalle**

## 2.2 Agregar icono de acceso al microscopio

Inmediatamente junto a «Ver detalle», agregar un botón compacto con icono de microscopio.

Acción:

**Abrir análisis en Microscopio Digital**

Destino:

`/frotis/microscopio/:analysisId`

Utilizar el identificador real correspondiente a la fila seleccionada.

No utilizar un UUID fijo ni uno simulado.

No modificar la acción actual de «Ver detalle».

Ambos accesos deben coexistir:

- **Ver detalle:** conserva su comportamiento histórico.
- **Icono Microscopio:** abre el nuevo espacio inmersivo.

## 2.3 Reglas UX

El icono debe:

- Utilizar la biblioteca de iconos existente.
- Mantener el estilo de los botones de acción del historial.
- Disponer de tooltip «Abrir en Microscopio Digital».
- Tener nombre accesible para lectores de pantalla.
- Permitir navegación mediante teclado.
- Tener estados hover, focus y disabled.
- Respetar permisos y restricciones de acceso.
- Funcionar en diseños responsive.
- No modificar la selección ni los filtros actuales del historial antes de navegar.

## 2.4 Comportamiento del análisis existente

Al ingresar desde historial:

1. Recuperar el análisis mediante `analysisId`.
2. Resolver sus relaciones científicas.
3. Obtener la imagen o preparación inicial válida.
4. Mostrar el frotis directamente.
5. Recuperar resultados disponibles.
6. Habilitar los instrumentos correspondientes.

**No solicitar nuevamente la carga de imágenes.**

**No repetir ficticiamente la validación técnica de un análisis terminado.**

Si el análisis todavía está procesándose, mostrar su estado real.

---

# 3. RUTA CANÓNICA Y DEEP LINKS

Ruta obligatoria de análisis:

`/frotis/microscopio/:analysisId`

`analysisId` es el único parámetro obligatorio para abrir un análisis existente.

Admitir los parámetros opcionales:

- `image`
- `selected_detection`
- `selected_prediction`

Ejemplo:

`/frotis/microscopio/:analysisId?image=:imageId&selected_detection=:detectionId&selected_prediction=:predictionId`

Estos parámetros permiten acceder directamente a una imagen, detección o predicción.

Deben servir para compartir hallazgos entre especialistas.

Orden de prioridad de selección:

1. Contexto explícito de la URL.
2. Contexto persistido y válido.
3. Selección inicial determinista.

Validar pertenencia, permisos y coherencia entre análisis, imagen, detección, predicción y RUNs.

No eliminar la lógica de navegación contextual existente en `/frotis/historial/:analysisRunId`.

No alterar las reglas globales de `datasource`.

---

# 4. ARQUITECTURA UX INMERSIVA

El microscopio representa un único instrumento de trabajo.

Debe mantener tres estados progresivos:

## Estado 1 — Carga

La imagen se incorpora dentro del mismo workspace que posteriormente permitirá examinarla.

No presentar una página administrativa completamente distinta del microscopio.

## Estado 2 — Revisión técnica

Una vez disponible, la imagen ocupa el viewport.

Durante procesamiento real:

- Mostrar línea horizontal de escaneo.
- Comunicar el estado técnico.
- Permitir zoom y pan.
- Mantener la imagen visible.
- Habilitar controles básicos.
- Mostrar advertencias cuando corresponda.

La animación no debe ocultar ni bloquear innecesariamente la exploración.

Si el control técnico falla, distinguir la inspección visual de las operaciones científicas que no pueden ejecutarse.

## Estado 3 — Microscopio

La imagen permanece en el mismo lugar visual.

Se retira la animación cuando termina el procesamiento correspondiente y aparecen las herramientas habilitadas.

El cambio debe ser suave, sin pérdida de zoom, posición ni contexto.

---

# 5. HEADER Y NAVEGACIÓN INTERNA

Mantener intacto el header global de Capstone.

Agregar un único header compacto para el microscopio.

Debe incorporar las opciones fijas:

1. **FULL FIELD REVIEW**
2. **REVIEW CELLS**
3. **REPORT**

Y dos controles:

4. **Mostrar/ocultar Imagen y Óptica**
5. **Mostrar/ocultar IA y Revisión**

No crear un segundo header grande ni filas innecesarias de títulos.

La imagen debe ocupar prácticamente toda la superficie restante.

## Full Field Review

Visor principal con imagen real, minimapa, zoom, pan, rotación, regla, filtros y controles visuales.

## Review Cells

Mantener el mismo visor, incorporando selección, navegación, inspector, anotaciones, revisión y explicabilidad.

## Report

Mostrar una superficie documental con predicciones, estadísticas, conteos, anotaciones y resultados reales.

Ocultar el frotis como fondo, conservando su estado para regresar.

Incluir navegación contextual «Ver en microscopio».

---

# 6. INSTRUMENTOS FLOTANTES Y LAYOUT MANAGER

No reservar columnas laterales permanentes.

Implementar dos grupos flotantes retráctiles:

- Imagen y Óptica.
- IA y Revisión.

Ambos se activan desde el header.

Controles rápidos mediante popovers compactos.

Operaciones prolongadas mediante paneles acoplables.

Crear un sistema de posicionamiento que evite superposiciones.

Los paneles fijos de la vista activa tienen prioridad sobre instrumentos móviles.

En particular:

**Al entrar a REVIEW CELLS, el inspector de revisión puede desplazar o integrar los instrumentos flotantes. Nunca deben quedar ocultos detrás de otro menú.**

No intentar resolver esto únicamente mediante `z-index`.

Calcular zonas disponibles, posiciones seguras y comportamiento responsive.

Conservar el centro de observación al cambiar el tamaño del viewport.

---

# 7. HERRAMIENTAS ÓPTICAS

Implementar progresivamente:

- Zoom digital.
- Pan.
- Ajustar a pantalla.
- Rotación.
- Brillo.
- Contraste.
- Gamma.
- Saturación.
- Restaurar imagen original.
- Regla en píxeles y unidades físicas cuando exista calibración.
- Lupa contextual.
- Minimap.
- Centrar región de interés.
- Localizar región de mayor densidad celular cuando exista cálculo real.

Todos los ajustes visuales deben ser reversibles.

No modificar la imagen original ni las entradas científicas utilizadas para inferencia.

No afirmar aumento óptico físico sin calibración.

---

# 8. IA, CÉLULAS Y ANOTACIONES

Reutilizar los componentes científicos conectados de:

`frontend/src/components/cell-review/`

Integrar:

- Detecciones.
- Bounding boxes.
- Máscaras disponibles.
- Predicciones.
- Clasificación parasitada/no infectada.
- Selección celular.
- Navegación.
- Pendientes de revisión.
- Confirmaciones y correcciones humanas.
- Anotaciones.
- Historial.
- Explicabilidad disponible.
- Compartir enlaces de hallazgos.

Implementar clic derecho contextual sobre célula, región o anotación.

Diferenciar rechazo de predicción y rechazo de detección.

No inventar operaciones que no tenga el backend.

Las decisiones humanas deben conservar trazabilidad y no sobrescribir predicciones originales.

Las anotaciones de célula y análisis deben reutilizar sus contratos existentes.

Los alcances de frotis y región requieren verificar o ampliar los contratos correspondientes antes de habilitar persistencia.

---

# 9. MODOS SILENCIOSO Y GUIADO

## Silencioso

- Imagen protagonista.
- Controles mínimos.
- Predicciones y anotaciones ocultables.
- Activación selectiva de capas.
- Sin diálogos invasivos.

## Guiado

- Destacar hallazgos disponibles.
- Mostrar pendientes.
- Ofrecer navegación asistida.
- Mostrar predicciones seleccionadas.
- Incorporar mensajes contextuales.

No cambiar resultados científicos al alternar modos.

Mantener advertencias críticas visibles.

---

# 10. DISEÑO VISUAL

Nombre de diseño:

**Optical Precision**

Combinar Dark UI con neumorfismo moderado en instrumentos.

Paleta oficial:

- Amarillo `#B68006`
- Verde `#04A141`
- Azul `#00028C`
- Plateado/gris `#8A8E97`
- Blanco `#DBEAF8`
- Negro `#00011E`

Utilizar `tokens_frotis_v2.css` y respetar `DESIGN-SYSTEM.md`.

Separar colores de interfaz, perfiles de tinción y estilos científicos de anotaciones.

Permitir personalización de colores y contraste de contornos para imágenes de diferentes tinciones.

No utilizar el color como único indicador de clasificación o estado.

Evitar copiar literalmente interfaces de Scopio Labs, Avivator o Google AI Studio.

---

# 11. FROTIS, IMÁGENES Y JERARQUÍA CIENTÍFICA

El especialista debe percibir que trabaja sobre un frotis físico, no sobre archivos aislados.

El análisis puede requerir navegación entre preparaciones y múltiples imágenes.

Revisar las relaciones efectivas de:

- `microscopy_analysis_runs`
- `smear_slides`
- `microscopy_images`
- `microscopy_analysis_run_images`
- `cell_detection_runs`
- `cell_detections`
- `cell_predictions`

La auditoría identificó `microscopy_analysis_runs.slide_id` como singular.

Inspeccionar cómo se representan múltiples frotis del mismo trabajo o análisis antes de implementar su navegación consolidada.

No crear asociaciones artificiales.

Distinguir secuencia de imágenes, matriz de capturas, mosaico registrado y pirámide multirresolución.

Preservar siempre identificadores y coordenadas científicas reales.

---

# 12. PERSISTENCIA Y RECUPERACIÓN DE CONTEXTO

Mantener, según disponibilidad:

- Análisis.
- Frotis activo.
- Imagen activa.
- Detección seleccionada.
- Predicción seleccionada.
- RUNs correspondientes.
- Zoom.
- Centro espacial.
- Rotación.
- Filtros.
- Capas.
- Modo silencioso/guiado.
- Paneles abiertos.
- Vista activa.

Los parámetros explícitos de la URL prevalecen sobre el contexto local.

Al regresar desde Report, recuperar el contexto del microscopio.

Al compartir una célula, generar un enlace reproducible.

Validar que todos los identificadores continúan perteneciendo al análisis.

---

# CAPSTONE-MICROSCOPE-01B — REGLA DE AISLAMIENTO V1 / V2 / V3

## Restricción arquitectónica obligatoria

**Las tres versiones de Análisis de Frotis deben coexistir de manera independiente.**

- Análisis de frotis v1.
- Análisis de frotis v2.
- Análisis de frotis v3 — Microscopio Digital Inmersivo.

La implementación de v3 no puede alterar, reemplazar ni degradar el funcionamiento actual de v1 o v2.

Esta restricción tiene prioridad sobre las decisiones de reutilización de componentes, refactorización y diseño visual.

## 1. Independencia de módulos

Implementar v3 dentro de una feature propia, por ejemplo:

```text
frontend/src/features/
├── [módulos existentes v1 — conservar]
├── analisis-frotis-v2/         # Sin alteraciones funcionales
└── analisis-frotis-v3/         # Nuevo módulo
    ├── pages/
    ├── components/
    ├── hooks/
    ├── services/
    ├── state/
    ├── styles/
    └── adapters/
```

La estructura es orientativa y debe adaptarse a la arquitectura actual del repositorio.

Evitar importar componentes de demostración v2 que dependan de estados simulados.

Para integrar capacidades científicas existentes, reutilizar sus APIs y contratos públicos mediante adaptadores propios de v3.

## 2. Independencia de rutas

Conservar íntegramente las rutas v1 y v2.

Añadir exclusivamente las nuevas rutas de v3:

- `/frotis/microscopio`
- `/frotis/microscopio/:analysisId`

No introducir redirects de v1 o v2 hacia v3.

No cambiar los destinos de sus menús.

No modificar la interpretación de sus parámetros.

No alterar el comportamiento de `/frotis/historial` ni de sus enlaces contextuales.

## 3. Independencia de navegación

El menú principal debe presentar las tres versiones como opciones independientes.

**Análisis de frotis v1**

Conserva su ruta y experiencia actual.

**Análisis de frotis v2**

Conserva su ruta y experiencia actual.

**Análisis de frotis v3**

Nuevo acceso a `/frotis/microscopio`.

No reutilizar la misma opción de menú cambiándole el destino según la versión.

No configurar v3 como reemplazo automático de v1 o v2.

El botón nuevo del Historial abre exclusivamente v3 y no modifica «Ver detalle».

## 4. Aislamiento visual y CSS

El nuevo diseño Optical Precision debe quedar encapsulado dentro de v3.

Utilizar un contenedor raíz propio, por ejemplo:

`.frotis-v3`

Establecer tokens propios o una capa de variables derivadas:

`tokens_frotis_v3.css`

El archivo `tokens_frotis_v2.css` puede servir como referencia, pero no debe modificarse de manera que cambie la apariencia de v2.

No introducir selectores globales que afecten:

- `body`
- `html`
- Controles compartidos.
- Botones de otras vistas.
- Paneles de v1/v2.
- Tipografías globales.
- Variables de color consumidas por módulos existentes.

Evitar colisiones de clases y estilos.

Si se utilizan Tailwind, CSS Modules o estilos encapsulados, comprobar que las reglas de v3 no afecten a los otros módulos.

## 5. Aislamiento de estado

v3 debe mantener su propio estado de:

- Vista activa.
- Imagen y frotis seleccionados.
- Zoom y pan.
- Rotación.
- Filtros.
- Instrumentos flotantes.
- Capas de IA.
- Célula seleccionada.
- Modo silencioso/guiado.
- Preferencias de presentación.

No reutilizar estados globales mutables de v1 o v2 si ello puede producir efectos cruzados.

Si se utiliza persistencia local, emplear claves con namespace exclusivo de v3, por ejemplo:

`capstone:frotis:v3:...`

La identidad científica sigue siendo compartida, pero el estado de presentación es independiente.

## 6. Reutilización científica segura

Es válido compartir:

- Servicios backend.
- Identificadores científicos.
- PostgreSQL.
- Endpoints existentes.
- Contratos de detección.
- Contratos de clasificación.
- Anotaciones científicas.
- Autenticación y permisos.
- Utilidades puras que no dependan de una versión visual.

No es válido compartir implícitamente:

- Estados de interfaz.
- Mocks.
- Configuraciones visuales mutables.
- Estilos locales.
- Reglas de navegación específicas de una versión.
- Procesamiento que se ejecute automáticamente solo por abrir otra vista.

Cuando sea necesario reutilizar lógica existente, priorizar un adaptador específico de v3.

No modificar componentes compartidos para satisfacer exclusivamente una necesidad visual de v3 si eso puede afectar consumidores existentes.

Si un cambio compartido es imprescindible, debe ser compatible hacia atrás y estar respaldado por pruebas de regresión.

## 7. Independencia de procesos

Abrir o utilizar v3 no debe alterar las ejecuciones científicas de v1 o v2.

Las tres versiones pueden consultar los mismos datos persistidos, pero cada una debe respetar los contratos actuales.

Evitar:

- Lanzar trabajos automáticamente al entrar a un análisis completado.
- Modificar RUNs o resultados por operaciones visuales.
- Duplicar detecciones o clasificaciones.
- Cambiar el análisis activo de otra interfaz por efectos globales.
- Sobrescribir preferencias de usuario de otras versiones.

Las operaciones de escritura científica legítimas de v3 deben utilizar los mismos mecanismos autorizados de persistencia, concurrencia, versionado y auditoría.

## 8. Cambios permitidos fuera de v3

Autorizar únicamente cambios de integración puntuales y justificados:

1. Registrar las nuevas rutas en el router existente.
2. Añadir «Análisis de frotis v3» al menú global.
3. Añadir el icono Microscopio junto a «Ver detalle» en Historial.
4. Incorporar permisos o configuración estrictamente necesarios, sin alterar los existentes.
5. Introducir extensiones compatibles de servicios compartidos, solo si son indispensables.

Cada archivo modificado fuera de v3 debe aparecer en el informe de cambios, con justificación.

No aprovechar esta tarea para reorganizar todo el frontend ni realizar refactorizaciones no relacionadas.

## 9. Pruebas obligatorias de coexistencia

Implementar y ejecutar pruebas que verifiquen:

- v1 abre su ruta original.
- v2 abre su ruta original.
- v3 abre `/frotis/microscopio`.
- Las tres opciones aparecen correctamente en el menú.
- Ninguna opción redirige involuntariamente a otra versión.
- Historial conserva «Ver detalle».
- Historial incorpora el nuevo acceso a v3.
- Los estilos de v3 no afectan a v1/v2.
- Cambiar opciones de visualización en v3 no modifica preferencias de las otras versiones.
- La navegación entre versiones no deja estados residuales.
- Los endpoints científicos continúan funcionando.
- La carga, revisión y reporte de v1/v2 mantienen sus comportamientos originales.
- Los enlaces profundos del historial siguen funcionando.
- Los cambios visuales de v3 no modifican los datos científicos persistidos.

Realizar una comparación de pruebas antes y después de la implementación.

Si existe una prueba de v1/v2 que falla por un cambio introducido por v3, corregir la regresión antes de declarar terminada la fase.

No aceptar la eliminación o desactivación de pruebas para ocultar incompatibilidades.

## 10. Regla de aceptación

**CAPSTONE-MICROSCOPE-01B no puede declararse completado si v3 funciona, pero v1 o v2 dejan de funcionar correctamente.**

El éxito exige simultáneamente:

1. v3 implementado y operativo.
2. v2 funcionando sin regresiones.
3. v1 funcionando sin regresiones.
4. Historial intacto, salvo el nuevo acceso explícito a v3.
5. Datos científicos, identificadores y contratos compartidos preservados.

**Implementar v3 como una nueva experiencia independiente, no como una sustitución ni una evolución destructiva de v1/v2.**

---

# 13. MOTOR GRÁFICO

Evaluar:

- `CellImageViewer` existente.
- Viv.
- deck.gl.

No instalar dependencias sin verificar compatibilidad.

Priorizar una primera experiencia funcional conectada a datos reales.

Separar fuente de imagen, viewport, coordenadas, renderizado de overlays y herramientas UX.

Preparar una arquitectura que permita incorporar posteriormente WSI, tiles, OME-TIFF piramidal y OME-Zarr.

No afirmar que esas capacidades están implementadas sin pruebas.

---

# 14. PLAN DE IMPLEMENTACIÓN

## 01B.1 — Integración y navegación

Implementar primero:

- Menú «Análisis de frotis v3» debajo de v2.
- Entrada `/frotis/microscopio`.
- Ruta `/frotis/microscopio/:analysisId`.
- Icono Microscopio junto a «Ver detalle» en Historial.
- Resolución real por `analysisId`.
- Estados de carga, permisos y error.
- Workspace inmersivo base.

Verificar que ambos accesos funcionan.

## 01B.2 — Experiencia visual continua

- Carga de imagen.
- Integración con workflow técnico real.
- Línea animada de escaneo.
- Header compacto.
- Full Field Review real.
- Controles ópticos.
- Instrumentos flotantes.
- Layout Manager.

## 01B.3 — Revisión celular

- Células y predicciones reales.
- Review Cells.
- Inspector.
- Navegación celular.
- Pendientes.
- Anotaciones y revisiones.
- Menú contextual.
- Explicabilidad.
- Modos silencioso/guiado.

## 01B.4 — Reporte

- Reporte científico conectado.
- Conteos y estadísticas reales.
- Anotaciones.
- Navegación hacia hallazgos.
- Retorno al visor sin perder el contexto.

## 01B.5 — Contexto avanzado

- Parámetros opcionales.
- Compartir hallazgos.
- Persistencia del viewport.
- Navegación entre imágenes.
- Multifrotis según contrato verificado.

## 01B.6 — Rendimiento

- Paginación.
- Carga diferida.
- Gestión de memoria.
- Pruebas gráficas.
- Preparación para imágenes de gran resolución.
- Evaluación técnica de Viv + deck.gl.

---

# 15. PRUEBAS Y CRITERIOS DE ACEPTACIÓN

Las pruebas deben incluir:

### Navegación principal

- Existe «Análisis de frotis v3» inmediatamente debajo de v2.
- El menú abre `/frotis/microscopio`.
- El formulario permite comenzar un análisis utilizando el workflow existente.
- Una vez obtenido `analysisId`, se continúa en la ruta correspondiente sin perder el workspace.
- El menú v2 sigue funcionando.

### Historial

- Se conserva «Ver detalle».
- Aparece el icono Microscopio junto a cada análisis elegible.
- El icono utiliza el UUID real de la fila.
- El destino es `/frotis/microscopio/:analysisId`.
- No se exige `image` para ingresar.
- El historial conserva filtros, navegación y comportamiento existentes.

### Microscopio

- Se muestra la imagen real.
- Los instrumentos funcionan.
- Las capas están vinculadas a datos reales.
- No existen colisiones entre paneles.
- Review Cells conserva la selección.
- Report conserva el contexto para regresar.
- Funcionan los parámetros `image`, `selected_detection` y `selected_prediction`.
- No se inventan métricas ni resultados.

### Seguridad y regresión

- Autenticación y permisos.
- UUID inválido.
- Análisis inexistente.
- Imagen inaccesible.
- Predicción de otro análisis.
- RUNs incompatibles.
- Estados científicos incompletos.
- Funcionamiento intacto de `/frotis/historial`.
- Funcionamiento intacto de `/frotis/historial/:analysisRunId`.
- Funcionamiento intacto de `/frotis/analisis-2`.

Utilizar el análisis real previamente auditado:

`0eaed5d3-9e9a-4aac-8003-d207be388823`

Sin modificar sus resultados científicos durante las verificaciones.

---

# 16. RESTRICCIONES

- No modificar destructivamente PostgreSQL.
- No duplicar registros científicos.
- No utilizar mocks para resultados productivos.
- No modificar las vistas actuales de historial ni `analisis-2` salvo la incorporación puntual del botón de acceso donde corresponda.
- No alterar la normalización global de datasource.
- No introducir Alembic.
- No guardar artefactos persistentes dentro de Docker.
- No realizar push remoto sin autorización.
- No introducir modelos, métricas ni resultados inexistentes.
- No cambiar la semántica de las identidades científicas.
- No iniciar nuevos procesamientos al abrir un análisis completado.

---

# 17. ENTREGABLES

Para cada fase, entregar:

1. Código implementado.
2. Archivos creados y modificados.
3. Contratos reutilizados.
4. Pruebas automatizadas ejecutadas.
5. Resultado de compilación.
6. Evidencia visual cuando sea posible.
7. Brechas técnicas identificadas.
8. Funciones implementadas frente a pendientes.

No declarar como funcional una característica que solamente tiene representación visual.

---

# 18. INSTRUCCIÓN FINAL

**Comienza el desarrollo, no una nueva auditoría general.**

El primer objetivo obligatorio es comprobar funcionalmente los dos accesos:

**Acceso A — Nuevo análisis**

`Menú Análisis de frotis v3 → Cargar imágenes → Revisión técnica → Microscopio Digital`

**Acceso B — Análisis existente**

`Historial → Icono Microscopio → /frotis/microscopio/:analysisId`

Ambos deben conducir al mismo Microscopio Digital Inmersivo.

No crear dos experiencias independientes.

Una vez verificados los accesos, continuar con las fases visuales y científicas descritas.

El resultado final debe sentirse como un instrumento microscópico continuo: el especialista incorpora un frotis, lo examina, observa resultados de IA, realiza anotaciones y consulta el informe sin perder su contexto de observación.

**CAPSTONE-MICROSCOPE-01B — Implementación funcional, integrada, trazable e inmersiva.**