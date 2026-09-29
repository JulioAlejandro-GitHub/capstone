# E10.10.5 — Riesgos al entregar C

Gate B aprobado expresamente por el usuario. B-01 cerrada; roles vigentes `capstone_v2_migrator` y `capstone_v2_runtime`. **Gate C pendiente de revisión y aprobación.**

| Riesgo / límite | Estado y condición de cierre | Etapa |
| --- | --- | --- |
| Forma legacy de la base actual desconocida | Contrato de la captura auditada; cualquier deriva bloquea. Capturar e inventariar exclusivamente una copia autorizada. | D |
| Parser 18.4 frente a PostgreSQL 17.9 | Baseline certificada en B; delta de adopción sólo parseado en C. Probar todas sus sentencias en 17.9. | D |
| Configuraciones/canonical/umbrales/procedencia insuficientes | Bindings referenciados y hashes obligatorios; no inventar evidencia. Un bloqueo de datos debe resolverse con evidencia; conflicto arquitectónico requiere decisión. | D |
| XAI legacy incompleto | Padres/payloads preservados y disposición expresa; exclusión no equivale a evidencia XAI certificada. No generar interpretaciones ni revisiones ficticias. | C/D |
| Comparación exacta de catálogo | Incluye owners/ACL, extensiones, secuencias, tipos, funciones, índices, vistas y triggers. La copia debe prepararse conforme a B; diferencias no se normalizan para pasar. | D |
| Credenciales y payloads en archivo de recuperación | Archivo privado 0600, directorio propio 0700 fuera del repositorio y fsync; acceso/retención y backup del archivo deben revisarse para D. La auditoría pública sólo publica conteos/hashes. | D |
| Locks, concurrencia y sesiones | Locks exclusivos y rechazo de otras sesiones; aislamiento de escritores requerido. Tiempo de ejecución/volumen de memoria deben medirse sobre la copia. | D |
| Memoria para inventario/archivo íntegro | Implementación materializa filas y plan en memoria para exactitud. Sin benchmark sobre población actual; agotar recursos antes del DDL bloquea, durante transacción revierte. | D |
| Recuperación real y resultado incierto de COMMIT | Flujo probado con mocks; ensayo PostgreSQL y restauración pendientes. Un recibo preparado no es confirmación de COMMIT. | D |
| Huellas/URI frente a existencia física | Se preservan hashes almacenados sin recalcular imágenes. URI/hash por sí solos no acreditan disponibilidad ni procedencia científica; revisar evidencia autorizada. | D/E |
| Consumidores y writers legacy | No adaptados en C; contratos de aplicación, elegibilidad de publicación y flujos de usuario requieren la etapa correspondiente. | E |
| Instancias B retenidas | Certificación y backups B conservados; C no contactó Docker ni cambió contenedores/volúmenes. No reutilizar sus descriptores para adopción. | Revisión |

75 tests offline aprobados; ninguna ejecución real de adopción declarada. **PostgreSQL operativo permanece intacto por C. No se inició D/E ni cutover.**

[Plan y límites](e10_10_5_route_b_adoption_plan.md), [pruebas](e10_10_5_adoption_tests.md). El registro al cierre de B permanece en [snapshot anterior a C](e10_10_5c_evidence/pre_c_e10_10_5_open_risks.md); sus estados de gate describen aquel momento.
