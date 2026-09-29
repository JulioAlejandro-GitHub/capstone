# RESET.2 — Ejecución operativa detenida

**RESET.2 — DETENIDO. Fase 1: barrera inicial. Causa: STOP — RESET2_NOT_READY.**

La autorización recibida permite el reset real de forma condicionada. Exige un cierre formal de RESET.2B como `RESET.2 PREPARACIÓN — LISTO PARA GO/NO-GO.` y ordena no corregir automáticamente requisitos ausentes. No se encontró RESET.2B ni esa declaración en la búsqueda del repositorio. Por tanto, no se inició el reset.

## Evidencia de la barrera

Se leyeron íntegramente RESET.1B y RESET.2A y se analizaron sus evidencias JSON junto con la preparación RESET.2. RESET.2A aprueba **retomar preparación**, y deja expresamente pendientes el backup operativo nuevo restaurado y verificado, inventario definitivo con escritores congelados, ejecutor operacional y cuarentena persistente. No equivale a RESET.2B aprobado.

El archivo `scripts/reset/reset2/operational.py` continúa siendo una barrera incondicional, no un ejecutor operacional. No se invocó, modificó ni desbloqueó. Tampoco se reutilizó el runner aislado retirando guardas. No se creó backup ni se usó el de RESET.1 como sustituto.

HEAD al inicio: `acd7ea3ec50bffa07478beefca751bb2dd66d790`; working tree limpio. El SHA-256 de la autorización es `64543d5dba0cc4498d0e7c895e4a21269996aac20c6ecdab71085ff87809078f`. Los hashes de los scripts inspeccionados y el alcance de búsqueda constan en [reset_2_execution_evidence.json](reset_2_execution_evidence.json). No hubo código de reset ejecutado.

## Estado real de PostgreSQL

SELECT de diagnóstico en transacción **READ ONLY**, a las `2026-09-28T22:53:50.921938+00:00`:

| Dato | Valor observado |
|---|---|
| Destino | malaria_experiments.public, instancia Docker capstone_db |
| System identifier | 7668020338728398886 |
| Revisión Alembic | 20260915_01 |
| Runs / campañas / miembros | 99 / 2 / 72 |
| Attempts / sessions / jobs Local | 11 / 11 / 1 |
| Publicaciones | 4; 1 activa |
| Deployments | 3; 1 activo |
| Schemas históricos presentes | 9 |

El historial y el modelo productivo continúan presentes. La transacción de diagnóstico cerró normalmente; **no hubo transacción de reset ni solicitud de COMMIT del reset**. No se ejecutó DELETE, retiro de publicaciones, cuarentena, migración, entrenamiento, evaluación, explicación, TEST ni gestión de campañas. No se congeló ni cambió la admisión.

## Integridad, recuperación y límites

Esta intervención no modificó datos, guards, catálogo, deployments, schemas ni archivos operativos. Al detenerse en la barrera inicial no se recalcularon los hashes completos de tablas/archivos ni las 208 FK; no se declara una nueva acreditación integral de integridad. El conteo de nueve schemas sólo acredita su presencia en este diagnóstico.

Filas eliminadas: **0**; archivos movidos: **0**. Postcondiciones de reset: no ejecutadas, porque el reset no comenzó. Estado de COMMIT: **NOT_STARTED**, no COMMIT_UNCERTAIN. No se necesita rollback ni restauración y no se ejecutó restore destructivo.

La recuperación aislada acreditada en RESET.2A permanece como antecedente. Falta la evidencia operacional RESET.2B exigida por la autorización: backup nuevo y SHA-256, restauración del mismo archivo contra el inventario definitivo, ejecutor aprobado, cuarentena y recuperación operativas verificadas. No se completaron ni fabricaron esos requisitos en esta ejecución.

**STOP — RESET2_NOT_READY.** Detenido sin reset operativo, conforme a la condición expresa de la autorización.
