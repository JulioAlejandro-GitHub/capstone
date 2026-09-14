# E9.2 — Decisiones experimentales pendientes

**Estado: PARCIAL.** Falta decisión científica sustantiva sobre pesos ponderados y aprobación de la propuesta de alcance de contraste final. No se aprueba E9, no se inicia E9.3.

## Evidencia y compatibilidad

Fecha real 2026-09-14, zona America/Santiago. HEAD host `c83ea299331149a0b184fc8c001231aeb2900b46`; árbol inicialmente limpio. Los seis entregables del manifiesto E9.1 conservan sus hashes. Su conteo 1 activo/35 pendientes fue histórico. Snapshot actual 15:10:17.872640 UTC / 12:10:17 local: **1 activo, 33 pendientes, 2 fallidos**, 36 miembros; estado campaña active. No se investigó rendimiento ni se intervinieron esos fallos en esta subetapa metodológica.

Campaña 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344: hash de contrato válido; 12 configuraciones coinciden con E7; semillas 11/29/47. Environment actual coincide con el congelado, huella d8569d8faaa80eca42b130e6096203d851e2c663b4cdb8cd599dda950fbe6430. La evidencia E9.1 contrastó configuración/dataset/environment de las sesiones entonces existentes; aquí no se cargaron payloads de resultados y no se atribuye esa comprobación antigua a nuevos intentos sin examinarlos.

El coordinador lee contrato/configuración desde PostgreSQL y vuelve a comprobar huellas src/configs antes de cada claim; el worker nuevo carga módulos del filesystem. Por ello modificar configs, incluso un JSON aparentemente auxiliar, puede invalidar la campaña. Todos los nuevos artefactos están bajo **docs/science/e9_2** y docs/audits, fuera de las rutas src/configs que planning_environment calcula; no se activaron ni conectaron al coordinador. No se modifica el contrato congelado.

Fuentes: protocolo/configuración E7, contrato/configuración E8, auditorías E9/E9.1, science/protocol.py, science/comparison.py, science/ensemble.py, execution/campaign.py, worker.py y train.py; búsqueda de pesos en docs/science, configuraciones y auditorías E9; metadatos de eventos de configuración E8 en PostgreSQL. No se encontró AGENTS.md en las búsquedas vigentes del repositorio/ancestros efectuadas en estas subetapas. No se atribuyen a AGENTS restricciones inferidas.

## Reglas confirmadas y orden

1. **Checkpoint:** entrenamiento E5 con política congelada, selección VAL por val_f2_parasitized a 0.5; no lo sustituye el ajuste de umbral posterior.
2. **Pesos:** uniforme fijo; ponderado pendiente, sin algoritmo de aprendizaje autorizado. Ninguna búsqueda aprobada se deduce de disponer de VALIDATION.
3. **Calibración probabilística:** no utilizada. Calibración/selección de threshold E5 no es temperature scaling ni otro calibrador de probabilidades.
4. **Umbral:** scores VAL únicos más 0/1, score >= threshold, sensibilidad parasitized estrictamente >0.98; maximizar especificidad, F2 y umbral más alto. Sin ambas clases: no estimable; sin factible: máxima sensibilidad con desempates y objetivo no alcanzado. Un extremo todo-positivo puede satisfacer recall sin utilidad; informar especificidad/baseline.
5. **Principal:** E7 exige matriz original completa y semillas comunes, objetivo en todas las semillas, media especificidad, media F2, hash estable. Fallback máximo mínimo de sensibilidad con desempates, exploratorio; representante seed11, no mejor semilla.
6. **Contrastes:** E7 pares de arquitecturas por mismo optimizador/semilla; E8 ensembles vs miembros y baseline. E8 no define un campeón global conjunto. Se propone conservar principal individual E7 y ensembles secundarios descriptivos; no se presume esa propuesta aprobada ni se usa TEST para decidirla.

Orden efectivo: probabilidad raw del miembro → sin calibrador de miembro → combinación fija → sin calibrador ensemble → umbral VAL. En individuales se omite combinación. VAL es compartida por checkpoint/umbral/selección y comparación: **exploratoria con optimismo por reutilización**, como E7 reconoce. No se fabricaron subdivisiones de VAL ni separación independiente retrospectiva. Una futura calibración aprendida o búsqueda exige otra metodología, procedencia, presupuesto y separación por pacientes; no está aprobada ahora.

## Ponderado: ruta C, propuesta concreta

No existen valores previos acreditados ni procedimiento aprobado encontrado; cero eventos ml.ensemble_configuration al snapshot. El ejemplo uniforme no se reutiliza como condición ponderada distinta. Recomendación: **un vector fijo no uniforme declarado por el responsable científico con justificación externa al desempeño de esta campaña**, idéntico por arquitectura en los 12 grupos. Datos para ajustar pesos: ninguno; presupuesto de búsqueda: cero; tolerancia 1e-12, pesos finitos >=0, al menos dos positivos. No se proponen números desiguales arbitrarios.

La propuesta JSON queda PROPOSED_NOT_APPROVED, active=false, weights=null y weight_source=null. Debe completarse y aprobarse antes de combinar miembros, sin alterar TRAIN. No se llama preexistente ni prerregistrada al comienzo de E9: es una decisión nueva, posterior al comienzo de TRAIN y anterior a la combinación. Sus resultados se etiquetarán con fecha y exposición. Impacto: no repetir TRAIN sólo por combinación fija; evaluaciones/comparaciones posteriores deben referenciar la revisión aprobada. Si ya se hubiera combinado con otra decisión, conservarla y repetir las comparaciones afectadas, nunca sobrescribir.

Una alternativa de aprender pesos no se implementa como supuesto: E8 actual la prohíbe. Exigiría enmienda y mecanismo de selección/comparación por paciente que controle reutilización; la nueva subdivisión no podría pretender estar intacta tras haber servido a selección de checkpoint. El vector uniforme permanece baseline, no resuelve la condición ponderada.

## Exposición y clasificación de cambios

E9/E9.1 registraron actividad TRAIN y artefactos intermedios; durante E9 anterior se vieron líneas de progreso de entrenamiento. No consta comparación científica final ni candidato. En esta subetapa sólo se consultaron estados/metadatos; **ninguna métrica o predicción TEST**. No puede verificarse qué resultados consultaron otros actores. No se usa el estado failed para retirar semillas o favorecer arquitecturas.

Aclaraciones sin cambio: orden raw/umbral, regla estricta, VAL exploratoria, 36 miembros y limitación TEST. Enmienda futura propuesta: vector fijo y propósito final de ensembles. Cambios que invalidarían comparabilidad/requerirían campaña o evaluaciones nuevas: preprocessing, arquitectura, semilla, presupuesto, calibradores aprendidos o selección retrospectiva; no realizados. No se sobrescribieron protocolos ni hashes históricos.

## TEST y congelamiento

Informe separado delimita 36 evaluaciones legacy sin partición explícita en claves inspeccionadas, rutas históricas capaces de TEST y ausencia de identidades E6/locks actuales. **Independencia TEST no acreditada; uso para ajuste no confirmado.** E7 permite evaluación final descriptiva con limitación después de controles; no una afirmación confirmatoria independiente. La lista E9.5 es un esquema de campos, no manifiesto final ni permiso de inferencia. E8 final aún requiere soporte técnico.

## Verificación y salida

Se validaron parseo JSON, campos de propuesta, estado no activo, referencias/hash E7/E8, arquitecturas, semillas, mapping y consistencia documento/configuración. No hay pesos numéricos que validar: ese control está pendiente, no aprobado por null. No se inventaron IDs de candidatos ni checkpoints. El UUID de campaña es una referencia existente. Se comprobó que estos archivos no entran en src/configs; se preserva fuente funcional y no se escribieron registros PostgreSQL.

Próxima acción habilitada: decisión del responsable sobre vector/procedencia y alcance propuesto, para completar la enmienda documental. No habilita evaluación, ajuste, apertura TEST o nueva etapa. Ningún coordinador fue modificado, detenido o lanzado; publicación/deployment no se consultaron con escrituras ni cambiaron.
