# E5 — Cierre de integración e instalación

Dictamen actualizado: **APROBADA en el alcance técnico verificado de E5**. Se conservan los informes previos y sus resultados históricos.

## Revisión y procedencia

HEAD comprobado: `cd5c64d703358797570f5183dd598d93314dc0eb`. La implementación efectiva incluye los cambios sin commit identificados en `etapa_5_manifiesto_diagnostico_instalacion_2026-09-11.json`; sus **19/19 hashes coinciden** al recibir el cierre. Este documento añade evidencia, sin modificar código. Las ejecuciones PostgreSQL y HTTP fueron aportadas por el usuario desde su terminal autorizada; no se atribuyen al agente ni se afirma una captura independiente de hashes del contenedor.

## Evidencia consolidada

- Pruebas locales del informe E5: **96 aprobadas**, con sus límites y avisos registrados.
- Primera integración sintética: **13 aprobadas y una deseleccionada en 3,76 s**.
- Instalación mediante make db-migrate: identidad y respaldo verificados, preflight de 20260911_02 a 20260912_01 con rollback confirmado, posterior upgrade y current=head=20260912_01. Referencia: `etapa_5_migracion_operativa_2026-09-11.md`.
- Suite posterior completa: **14 passed in 3.45s**, incluyendo `test_public_e5_revision_readonly`.
- GET http://localhost:8000/ready: `status=ready`; componentes database, migrations y storage en ready; versión 0.3.0, entorno development.

Comando PostgreSQL comunicado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE5_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaign_executor_postgres.py
```

La comprobación HTTP fue `curl --fail --silent --show-error http://localhost:8000/ready`.

## Alcance acreditado y límites

La suite acredita sus aserciones de matriz sintética congelada, intentos vinculados, aceptación y reanudación, fallos individuales/sistémicos, presupuesto, idempotencia, exclusión concurrente por miembro, rechazo de escritura del propietario de una sesión terminal, interrupción controlada y puntos de fallo conservando evidencia. Los fixtures verifican rollback/limpieza y ausencia de esquemas desde otra conexión. La comprobación pública acredita revisión, tablas y trigger inspeccionados. Las pruebas locales incluyen el control de TRAIN con adaptador/modelo sintéticos, restricción a train/val, ausencia de CSV/JSON laterales y rechazo de evidencia/checkpoints incompletos o alterados.

No equivale a un entrenamiento científico real ni acredita desempeño clínico. La inyección after_accept no demuestra recuperación de un commit incierto real; KeyboardInterrupt no prueba caída del host; la prueba con commits en esquema sintético no acredita durabilidad ante reinicio de PostgreSQL. La recuperación automática sigue limitada a ausencia comprobada de PID locales; propietarios indeterminados se pausan para diagnóstico.

Los límites de consumidores legacy EVALUATE/EXPLAIN y su linaje/versiones permanecen explícitos en la guía e informe E5 para E6. No se declara eliminado todo escritor histórico del repositorio. La evidencia de E4 conserva su propia revisión y no se reutiliza como prueba de E5.

Con estas ejecuciones se cierran los pendientes de integración PostgreSQL, instalación y readiness que mantenían NO APROBADA esta entrega. No se autoriza una campaña científica extensa, no se publica ni promueve ningún modelo, y **no se inicia E6**. Dataset, split, checkpoints históricos y selección manual de Producción Etapa 2 se preservan.
