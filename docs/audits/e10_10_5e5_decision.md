# E10.10.5E.5 — decisión pendiente sobre target_recall

**E-05 abierta. Integración detenida por el apartado 15 de la solicitud E.4. Gate E bloqueado.** E-04 está resuelta y su baseline recertificada.

## Incompatibilidad reproducida

El resolver real `resolve_config(custom_cnn, overrides=...)` y el calculador real de calibración aceptan objetivos explícitos 0,80 y 0,99. El escritor real TRAIN `ExecutionRepository._create_run` intenta conservarlos, pero PostgreSQL rechaza la configuración con SQLSTATE 23514, `v2_run_configurations_check_d6094850fee4`: `clinical_target_recall = 0.98`. Además, `ck_v2_calibration_val` fija `target_recall = 0.98` junto a VALIDATION y threshold default 0,5.

[Diagnóstico ejecutado](e10_10_5e4_evidence/integration/e05_target_contract.json) y [script](../../scripts/db/probe_v2_e5_target.py). Control 0,98 aceptado por resolver/escritor; 0,80 y 0,99 rechazados por el CHECK exacto. El control de calibración 0,98 sólo comprueba INSERT con FK diferidas y rollback; no se presenta como pareja completa. La pareja completa se acredita separadamente en E-04. Todas las filas de este diagnóstico se revirtieron. Sin entrenamiento, campañas ni reserva de ejecución real.

El primer intento del probe suponía que el escritor aceptaría esos valores; el servidor demostró que el rechazo ocurre antes. Se corrigió exclusivamente el diagnóstico para exigir ese rechazo preciso, sin cambiar constraints ni datos científicos.

## Alternativas concretas para aprobación

**A — conservar 0,98 en v2 (recomendada para mantener el alcance científico certificado).** Mantener ambos CHECK, el protocolo congelado y los hashes actuales. Incorporar admisión explícita de target_recall=0,98 antes de reservar/escribir TRAIN o EVALUATE v2; rechazar otros valores con error de contrato identificable, sin sustituirlos por 0,98. Conservar el comportamiento configurable de legacy. Probar 0,98 positivo, 0,80/0,99 negativos, ausencia de efectos parciales y coherencia del productor con configuración/protocolo. Continuar después el contexto real y la matriz E.

**B — autorizar objetivos parametrizados por contrato científico.** Cambiar los dos CHECK fijos por un contrato que vincule objetivo, configuración TRAIN congelada, protocolo aplicable y evento de calibración; rechazar ausencia o discrepancia. Mantener 0,98 para el protocolo E7 congelado, VALIDATION exclusiva y default 0,5. Requiere definir la autoridad del objetivo y recertificar otra baseline completa antes de continuar E. No se ha implementado esta alternativa.

No se cambia silenciosamente el objetivo ni se selecciona una alternativa sin decisión. Solicitud: aprobar A o B. Ninguna alternativa autoriza Gate E, cutover o campañas reales.
