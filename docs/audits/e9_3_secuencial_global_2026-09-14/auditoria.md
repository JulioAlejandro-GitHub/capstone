# Auditoría complementaria E9.3 — preparación secuencial global

Fecha local: 14/09/2026, America/Santiago. Revisión Git: `1fc5201474bb158a8f84d12b543b255abb1d3d7e`, con cambios locales anteriores conservados y cambios de esta intervención identificados por hashes en el manifiesto. No se realizó commit.

## Dictamen

**E9.3 EN SEGUIMIENTO. Implementación preparada y probada en aislamiento; instalación y activación pendientes.** E9.2 permanece parcial. No se declara E9 aprobada.

Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`: 36 experimentos, 31 pendientes, 5 fallidos, 0 activos, 0 completados y 0 verificados; 5 intentos, ninguno adicional durante esta intervención. Pausa persistida. No hay procesos gestionados activos ni reservas nuevas. Dataset obligatorio `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`: contrato y matriz conservados, cero discrepancias de dataset entre intentos y campaña. No se regeneraron particiones ni se ejecutó diagnóstico con datos reales en esta intervención.

## Correcciones y alcance comprobado

Nuevo global_gate: advisory lock con propietario validado en SQL, exclusión cruzada entre campañas y tipos, evidencia PID/inicio/sesión, handshake previo a ejecutar, espera y adopción de descendientes, circuito persistido de recursos y fallos. Nueva migración forward 20260914_02; no se reescribe historia instalada. Se integra en coordinador, workers, standalone, controlled y entrada assessment. execution/repository vincula revisiones técnicas explícitas y campaign_id al crear intentos; campaign.py conserva códigos de salida y verifica artefactos antes de continuar. process_verification usa el cargador oficial en proceso desechable. Se mantienen los controles de revisión científica y la fuente congelada original.

La ausencia de optimización de memoria deja de bloquear por sí sola. Se exige exclusividad, margen de recursos, migración, integridad y revisión. La secuencialidad no soluciona los OOM anteriores: el contador sigue en 5; no hay nuevas atribuciones individuales demostradas. Los antiguos códigos de salida perdidos no se reconstruyen. Se pausa ante un nuevo OOM, recursos insuficientes o dos fallos consecutivos; permanece el presupuesto congelado de intentos. No se modificaron batch, resolución, precisión, optimizador, semillas ni épocas.

## Validación real

`pruebas_final.txt`: **128 passed, 2 deselected, 7 warnings in 27.79s**, mediante Compose y PostgreSQL sintético aislado. Incluye dos coordinadores, exclusividad entre campañas/TRAIN/assessment, reserva con propietario, pérdida de lock, hijos con setsid, liberación y carga oficial de checkpoint, fallos de lanzamiento/verificación, pausa entre trabajos, OOM simulado, presupuesto/circuito y dry-run sin reservas. Las advertencias son de dependencias/fixture Keras. No hubo entrenamiento científico ni EVALUATE operativo. Los dos controles públicos E5/E6 se excluyeron explícitamente; no se declaran reejecutados.

La limpieza final confirma cero esquemas capstone_test_e4_ y cero sesiones activas. Las pruebas con commits utilizan exclusivamente esquemas sintéticos; no constituyen prueba de durabilidad de TRAIN operativo. La publicación y el deployment coinciden exactamente con la referencia inicial. TEST permaneció cerrado.

`dry_run.json`: writes=0, reservations=0, campaña paused, siguiente posición 5 / member e1ceb448-195a-4b80-9c96-a4e67734e16a (CustomCNN, Adam, semilla 47). execution_ready=false por migración global ausente y revisión no registrada; memory_optimization_required=false. El preflight E1 de archivos sellados sigue siendo obligatorio antes de reservar, no se sustituye por este dry-run.

## Instalación pendiente y límites

Public mantiene 20260912_02; global gate no instalado. El SQL offline 20260912_02→20260914_02 sólo demuestra generación. /ready continúa 503 por migraciones pendientes; database y storage disponibles. No se aplicaron migraciones ni se registró la propuesta técnica. No se activó ni reinició ningún proceso operativo.

El contrato de exclusividad requiere Linux/Compose/base canónica. La salida de proceso sin prueba completa o un host distinto bloquea conservadoramente; no se supone liberación por expirar una lease. El margen de 1 GiB no garantiza capacidad para todas las arquitecturas. La futura ejecución debe comprobar este límite y detenerse ante OOM recurrente.

Procedimiento y política completos: `docs/science/e9_3_operacion_secuencial_2026-09-14.md`. La siguiente acción segura es revisar la propuesta y autorizar la instalación mediante wrapper en un límite sin procesos activos. La activación requiere una autorización posterior. No se ejecuta E9.4.
