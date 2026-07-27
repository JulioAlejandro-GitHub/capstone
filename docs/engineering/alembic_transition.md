# Transición a Alembic

Las migraciones SQL históricas 001–029 y sus checksums permanecen intactos. La base Capstone
existente representa ese esquema y `20260726_00` es su baseline vacía deliberada. No se
reconstruye el historial. Toda revisión futura usa backup, preflight y upgrade; nunca
downgrade.

`scripts/db/verify_alembic_adoption.py` valida identidad, esquema, migración 029 y revisiones
conocidas. Consulte `alembic_simple_policy.md`.
