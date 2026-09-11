# E5 — Línea base y discrepancia de evidencia de entrada

Revisión comprobada: `cd5c64d703358797570f5183dd598d93314dc0eb`, rama `main`, árbol inicialmente limpio. Los **25 archivos** del manifiesto E4 `etapa_4_manifiesto_concurrencia_driver_2026-09-11.json` coinciden con sus SHA-256. No se atribuyen las pruebas E4 a cambios posteriores. Este documento no constituye implementación ni aprobación de E5.

La nueva solicitud declara E4 aprobada según el cierre del usuario. Sin embargo, el último cierre versionado (`etapa_4_integracion_sintetica_aprobada_2026-09-11.md`) acredita 49 pruebas sintéticas aprobadas y conserva el dictamen global NO APROBADA por instalación pública pendiente. No se encontró un cierre posterior de esa comprobación. Se solicitó la evidencia faltante, sin pedir autorización para repetir una acción ya autorizada.

El intento de consultar base/esquema/revisión con Compose y SET TRANSACTION READ ONLY no alcanzó PostgreSQL: acceso denegado a Docker API. No prueba que la BD esté caída ni que las migraciones falten. El head del código es 20260911_02; la revisión instalada sigue sin comprobación directa en esta sesión.

## Hallazgos preliminares de integración

- `run_train_all_models.py` genera una matriz desde el registro actual y lanza TRAIN por subprocess; aún no consume miembros congelados ni tiene propiedad/recuperación.
- `CampaignRepository.create_attempt` serializa campaña y miembro, crea ordinal y libera la transacción antes de devolver la lectura. Falta una operación de reclamación de elegibles y propiedad persistida.
- Las guardas E4 reservan verified/accepted_attempt_id y rechazan su uso (`VERIFICATION_REQUIRES_E5`). E5 requiere revisión aditiva sobre el head real, conservando 01 y 02.
- `training/trainer.py` crea el TRAIN mediante start_tracking_run, escribe CSVLogger por fase, historias CSV y resúmenes JSON laterales. No basta con adaptar el bucle exterior: hay que integrar el propietario único de runs y sustituir los escritores alcanzados por TRAIN.
- TRAIN ya carga splits con include_test=False antes de fit, pero conserva una vía de evaluación TEST optativa; el ejecutor debe prohibirla según el contrato congelado.
- Los adaptadores E2 entregan modelo, fases y contratos; compile_phase valida firmas y registra configuración efectiva. Deben conservarse sin resolver otra vez desde defaults actuales las configuraciones de campañas congeladas.
- La identidad habitual usa snapshots por run, pero el entrenamiento aún prepara y reutiliza una carpeta mutable por arquitectura. E5 debe asignar almacenamiento exclusivo desde el inicio y verificar checkpoints/resultados antes de aceptar.

No se modificó código funcional, migraciones, datasets, checkpoints ni publicaciones. No se ejecutaron modelos, campañas, migraciones o pruebas científicas.

## Evidencia de entrada pendiente

La sección 7 del contrato 0B v1.1 exige «baseline/revisión identificada, requisitos asignados y dependencias satisfechas». La fila de entrada E5 incluye E4. La declaración de aprobación en la nueva solicitud se registra como tal; no se convierte por sí sola en un resultado PostgreSQL inventado.

Para resolver la discrepancia basta aportar el cierre operativo existente o ejecutar la comprobación de sólo lectura, si 02 ya está instalada:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py::test_public_migration_readonly
```

Esta prueba no aplica migraciones. Si falla por revisión/estructuras pendientes, el resultado debe conservarse; no se sustituye por el renderizado offline ni por el éxito de esquemas sintéticos.
