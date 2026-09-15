# E9.3 — Reconciliación administrativa del gate global, 15/09/2026

**Decisión administrativa explícita, no un diagnóstico de causa raíz.** Esta intervención
limpia un bloqueo de exclusividad global que quedó en estado "no verificable" por un
efecto colateral operativo (reinicio del contenedor backend); **no declara resuelto el
OOM del run `79f39931-ac71-4bc1-a317-149a975d1f74` ni de ningún intento anterior**, y no
sustituye la instrumentación de memoria por fase que las auditorías previas
(`docs/audits/e9_3_verificacion_2026-09-15/auditoria.md`) pidieron obtener antes de
cualquier nuevo intento.

## Contexto inmediato

Al preparar el ejecutor local para un intento controlado real contra la campaña
`3acf89b7-dc42-4b7a-8e2a-ca6ea024c344` (miembro posición 0,
`2fbd5862-b68b-4845-9445-a30d7ec61382`, autorizado explícitamente por el usuario en esta
misma sesión), se reinició el contenedor `capstone_backend` (`docker compose up -d
backend`) para aplicar un bind mount de artefactos necesario (`LocalBackend.claim()`
necesita leer el checkpoint real dentro del contenedor para `verify_session`). Ese
reinicio **destruyó** el contenedor anterior (`3dba8e7dcf1b`) y creó uno nuevo
(`6283301a7b5e`).

`experiment_execution_gate.process_evidence` conservaba la identidad del worker
SIGKILLed del intento anterior, referenciando el host `3dba8e7dcf1b` —evidencia que ya
tenía `release_confirmed: true` desde la verificación oficial de ayer
(`docs/audits/e9_3_verificacion_2026-09-15/auditoria.md`, tres lecturas independientes).
Tras el reinicio, `process_absent()`/`verify_retained_processes()` (en
`execution/global_gate.py`) comparan primero el `host`/`boot_id` de esa identidad contra
el del contenedor **actual**; como ya no coinciden, el chequeo no llega siquiera a mirar
`release_confirmed` y devuelve `REMOTE_PROCESS_ABSENCE_UNPROVEN` — una incertidumbre
introducida por el reinicio, no evidencia nueva de que el proceso siga vivo.

Adicionalmente, `experiment_execution_gate.blocked_reason='NEW_CONTAINER_OOM_PAUSE'`
seguía activo desde el intento fallido anterior. `LocalBackend.claim()`
(`local_execution/backend.py`) no implementa ningún mecanismo de `acknowledge` para este
circuito — a diferencia de `GlobalGate` (usado por el coordinador Docker), rechaza
incondicionalmente cualquier reserva mientras `blocked_reason` esté seteado. No existe
hoy ningún camino de código para continuar sin una intervención administrativa directa.

## Evidencia verificada antes de intervenir

- `docker ps -a --filter id=3dba8e7dcf1b` → sin resultados; `docker inspect
  3dba8e7dcf1b` → `no such object`. El contenedor anterior no existe ni siquiera
  detenido: fue destruido por completo. La destrucción total del contenedor es evidencia
  de ausencia **más fuerte**, no más débil, que una comprobación de PID en un host vivo —
  cualquier proceso que hubiera existido en él está necesariamente terminado.
- El `release_confirmed: true` ya registrado en `process_evidence` antes de esta
  intervención fue obtenido por la verificación oficial de ayer, sobre el mismo
  contenedor, con tres lecturas independientes coincidentes. Esta intervención no repite
  ni sustituye esa verificación: sólo evita que un artefacto de identidad de host
  (invalidado por el reinicio, no por incertidumbre real) bloquee su lectura.
- `owner` del gate ya era `NULL` antes de esta intervención (la reserva anterior ya
  estaba correctamente liberada).

## Qué NO acredita esta intervención

- No determina la causa del OOM del run `79f39931-...` ni de sus predecesores.
- No acredita que el crecimiento de memoria del pipeline esté resuelto o entendido.
- No es una reproducción, medición ni instrumentación por fase de memoria.
- No autoriza reintentos adicionales más allá del intento controlado único ya acordado
  (miembro posición 0, campaña `3acf89b7`) ni relaja el circuito para el futuro: un
  nuevo `NEW_CONTAINER_OOM_PAUSE` (u otro `blocked_reason`) que se genere en el intento
  que sigue a esta reconciliación debe tratarse con el mismo rigor que el anterior, no
  como un artefacto operativo a limpiar de nuevo sin evidencia equivalente a la de esta
  sección.

## Autorización y acción

Autorización explícita del usuario en conversación interactiva, 2026-09-15: *"Autorizar
explícitamente limpiar blocked_reason + reconciliar process_evidence como una decisión
administrativa consciente (registrando por qué), aceptando que no se ha diagnosticado la
causa raíz del OOM."*

Acción aplicada (vía `docker compose exec backend`, conexión real, commit real):

```sql
UPDATE experiment_execution_gate
SET blocked_reason=NULL, process_evidence='{}', updated_at=clock_timestamp();
```

Estado antes (mismo valor observado por la verificación oficial de ayer):

```json
{"owner": null, "blocked_reason": "NEW_CONTAINER_OOM_PAUSE",
 "process_evidence": {"sessions": [42346],
   "identities": [{"pid": 42342, "host": "3dba8e7dcf1b",
                    "boot_id": "20f8def3-9666-499d-8d01-4cfb5819ed90",
                    "start_ticks": "24436838"}],
   "release_confirmed": true}}
```

Estado después, confirmado desde una conexión nueva:

```json
{"owner": null, "blocked_reason": null, "process_evidence": {}}
```

`process_evidence='{}'` es semánticamente correcto (no un vaciado arbitrario):
`verify_retained_processes()` trata un valor vacío como "nada que verificar" — exactamente
la situación real, dado que la única identidad registrada pertenecía a un contenedor que
ya no existe.

## Verificación posterior

`LocalBackend.dry_run(...)` contra la campaña real, miembro posición 0, tras la
reconciliación: `execution_ready: true`, `global.available: true`,
`global.reason: null`. Sin escrituras (`writes: 0, reservations: 0`). Confirma que el
camino de reserva ya no está bloqueado por este artefacto operativo.
