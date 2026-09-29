# E10.10.5 — Riesgos pendientes al entregar A

## Actualización E10.10.5B — bloqueo arquitectónico

Gate A fue aprobado por el usuario. **Gate B permanece bloqueado.** PostgreSQL 17.9 rechazó la provisión de `pg_v2_migrator` porque reserva los nombres que comienzan con `pg_`; `pg_v2_runtime` comparte el problema. Se requiere decisión explícita sobre nuevos nombres antes de modificar el contrato y reanudar B. Propuesta pendiente: `capstone_v2_migrator` / `capstone_v2_runtime`.

La instancia aislada y su preflight fueron acreditados; el contenedor quedó detenido y su volumen exclusivo retenido. No se creó la base prevista. Todos los riesgos de instalación, catálogo, permisos efectivos, restricciones, rollback, no-op y restauración siguen abiertos. No se atribuye este rechazo a una diferencia comprobada entre PostgreSQL 18.4 y 17.9.

[Resultado y evidencia del bloqueo](e10_10_5_route_a_results.md). El registro de A siguiente se conserva como historia; su frase sobre gates no refleja la aprobación posterior del usuario.

---

**Sólo implementación y validación estática de A. Ningún gate aprobado por el agente.**

| Riesgo / límite | Evidencia pendiente | Etapa |
| --- | --- | --- |
| El parser disponible es PostgreSQL 18.4; no resuelve tipos ni cuerpos SQL en un servidor 17 | Instalación íntegra PostgreSQL 17 y comparación real contra manifiesto | B |
| ACL/ownership y permisos de la extensión confiable pgcrypto aún no probados con roles aislados | Preparar roles sin privilegios administrativos y probar DDL, DML permitido/prohibido, TEMP, funciones y ledgers | B |
| La guarda de identidad está probada con metadatos sintéticos, no con Docker/servidor | Acreditar contenedor, volumen exclusivo, puerto, system_identifier, OID, owner y roles | B |
| La atomicidad declarada por la transacción Alembic todavía no tiene prueba de servidor | Fallo deliberado intermedio, ausencia de objetos/head parcial, segunda ejecución no-op | B |
| Sin backup/restore ejecutado | Restauración íntegra y catálogo equivalente | B |
| Typmods/colaciones de campos heredados proceden del diseño complementado por dump offline | Contrastar con copia autorizada; no cambiar dominios protegidos ante discrepancias sin revisión | D |
| `external` no equivale a `external_validation`; URI/hash no prueba contenido ni disponibilidad | Evidencia de población/procedencia y mapeos explícitos; abortar ante insuficiencia | C/D/E |
| El writer legacy conserva su contrato operativo pero sus INSERT antiguos no satisfacen la nueva evaluación obligatoria | Adaptación explícita de writers v2, ResultService y lectores; pruebas transaccionales con procedencia | E |
| Las vistas legacy conservan sus consultas históricas, incluidas preferencias por external; no son la vista oficial v2 | Adaptar API/React para separar evidencia externa y excluirla de selección/VALIDATION/TEST oficial | E |
| El head nuevo será rechazado por `execution/schema.py` legacy, que permanece intacto | Allowlist/capacidades v2 explícitas y pruebas de rechazo preclaim | E |
| Triggers y FK no acreditan por sí solos semántica científica, carreras ni recuperación | Pruebas sintéticas E10, configuración congelada, publicación, métricas nullable, calibración val y XAI | B/E |
| Sin recenso de la copia legacy; vacíos históricos no garantizan vacíos actuales | Preflight/reconciliación de usuarios, dataset, modelos, eventos y hashes antes de cualquier transformación | C/D |

A-01 quedó resuelta por autorización explícita del usuario; no se mantiene como bloqueo pendiente. La corrección no autoriza mappings automáticos ni ampliar el TEST oficial.
