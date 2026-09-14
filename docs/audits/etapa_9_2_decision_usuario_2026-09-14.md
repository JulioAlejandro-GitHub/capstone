# E9.2 — Decisión del usuario y propuesta de aprendizaje

Fecha de registro: 2026-09-14. Fuente: mensaje explícito del usuario posterior al informe E9.2.

Decisiones aprobadas: conservar candidato principal individual seleccionado por E7; ensembles únicamente contrastes secundarios; promedio uniforme de1/3 por arquitectura. No asignar pesos fijos desiguales sin justificación independiente del desempeño. La propuesta v1 queda conservada como historia, no aprobada ni activada.

El usuario solicita propuesta de aprendizaje de pesos sólo dentro de VALIDATION, con separación ajuste/comparación, objetivo, presupuesto y desempates. Se entrega `docs/science/e9_2/enmienda_aprendizaje_propuesta_v2.md` y JSON homónimo. Sigue **pendiente de aprobación**; no hay pesos aprendidos ni búsqueda ejecutada. E9.2 continúa **PARCIAL** por decisión pendiente sobre esa enmienda, no por el alcance principal/contrastes, que ahora sí está aprobado.

Autorización adicional: E9.3 para completar/verificar TRAIN de la matriz congelada, dejando continuar coordinador existente; sin segundo coordinador ni resume con actividad confirmada. No autoriza evaluaciones posteriores, TEST ni publicación. E9.3 no depende del ponderado.

Validación de la propuesta: parser JSON; estado inactivo; arquitecturas/semillas consistentes con E7; rejilla de228 vectores racionales con soporte mínimo2 más uniforme=229; 12 grupos=2748 puntuaciones; ninguna propuesta de vector desigual fijo como ganador. Los numeradores/denominadores de uniforme son1/3 exacto. No se accedió a imágenes ni probabilidades para construir la propuesta, ni se asignaron pacientes realmente a roles analíticos.

Exposición: ya existen estados y progreso TRAIN; no hay comparación ensemble realizada por este agente. La aprobación de una propuesta futura no será denominada prerregistro al inicio de la campaña. La separación propuesta conserva explícitamente la limitación de selección previa de checkpoints sobre toda VAL.
