# Corrección Prompt 2.2.1

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; conserva las correcciones efectuadas en ese prompt.
> **Snapshot:** 2026-07-27 / Prompt 2.2.1.

Fecha: 2026-07-27.

Se retiraron los archivos frontend Docker creados por los prompts, el target Docker del
Makefile y el job Docker de CI. Los archivos preexistentes se conservaron como marcadores
históricos `SUPERSEDED`, sin servicios operativos ni gates.

Se agregaron entonces pruebas PostgreSQL directas para un usuario sintético deshabilitado y para el
rollback ante un fallo real de FK al persistir `audit_events`. Toda fixture usa UUID y
prefijo `capstone_test_`, conexión compartida y rollback externo.

Las credenciales `CAPSTONE_E2E_USERNAME` y `CAPSTONE_E2E_PASSWORD` no estaban disponibles.
No se creó usuario, no se cambió password ni rol y el login autorizado quedó BLOCKED.
