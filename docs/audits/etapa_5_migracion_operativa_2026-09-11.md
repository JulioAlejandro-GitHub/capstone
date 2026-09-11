# E5 — Migración operativa acreditada por el usuario

El usuario aporta la salida completa de make db-migrate-check y make db-migrate. El precheck valida malaria_experiments con revisión 20260911_02 y head de código 20260912_01. El wrapper verifica identidad canónica, crea respaldo custom y verifica su contenido mediante pg_restore --list.

Respaldo comunicado: capstone_20260911T171532Z.dump, en el directorio temporal capstone-backups de la terminal del usuario. SHA-256 comunicado: `9f4103466e01e4ecb96eb0062bfe9e06e58a76f1a8654bfc0ab008e79ede3c89`. No se afirma inspección independiente ni restauración del respaldo por el agente.

El preflight ejecuta 20260911_02 → 20260912_01 dentro de transacción, confirma rollback y revisión persistente 20260911_02. Después el wrapper aplica el upgrade y muestra 20260912_01 (head) tanto para current como para heads. La instalación operativa queda VERIFICADA según esa evidencia aportada; no es sólo renderizado offline ni instalación en esquema sintético.

Al recibir la evidencia, HEAD local sigue siendo `cd5c64d703358797570f5183dd598d93314dc0eb`; los 19/19 archivos del manifiesto diagnóstico E5 coinciden. No se modificó código ni se atribuyó una ejecución propia. Se preservan los informes anteriores, incluido el fallo público anterior a esta instalación.

Pendientes posteriores al upgrade: suite E5 completa (14 casos, incluida lectura pública) y /ready conforme a la política Alembic. Los trece casos sintéticos ya aprobados conservan su procedencia y revisión; no se sustituyen las comprobaciones posteriores por aquel resultado.

Dictamen global: E5 NO APROBADA hasta completar las comprobaciones pendientes. No se inició E6 ni una campaña científica.
