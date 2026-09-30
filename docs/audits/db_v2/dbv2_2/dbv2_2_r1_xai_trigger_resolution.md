# DBV2.2-R1 — XAI deferred validation trigger correction

Estado: **RESOLVED**. Corrección explícitamente aprobada por el usuario; no es cambio del modelo científico.

## Defecto, causa y decisión

El intento inicial confirmó SQLSTATE 42703 sobre `NEW.evaluation_id` en xai_quantitative_evaluations y sobre `NEW.id` en xai_evaluation_members. CASE resuelve ambas referencias al RECORD. Se conserva íntegro el [informe original](dbv2_2_baseline_report.md), la reproducción y sus hashes.

Se sustituyó exclusivamente el despacho de fila por IF / ELSIF / ELSE, con rechazo de tabla desconocida:

```sql
IF TG_TABLE_NAME = 'xai_quantitative_evaluations' THEN
    eid := NEW.id;
ELSIF TG_TABLE_NAME = 'xai_evaluation_members' THEN
    eid := NEW.evaluation_id;
ELSE
    RAISE EXCEPTION
        'dbv21_xai_evaluation_complete invoked from unsupported table: %',
        TG_TABLE_NAME;
END IF;
```

El resto del cuerpo de la función conserva sus invariantes. No se cambiaron tablas, columnas, PK/FK/UNIQUE, cardinalidad N:M, semántica XAI, triggers diferidos, E-04 ni el dominio de recall para resolver R1.

## Archivos DBV2.1 modificados

- dbv2_1_target_schema.sql: despacho autorizado. Continúa DESIGN ARTIFACT ONLY / DO NOT EXECUTE / NOT AN ALEMBIC MIGRATION; no se ejecutó para instalar.
- dbv2_1_functions_triggers.md: inventario derivado incorpora el nuevo rechazo explícito de origen no soportado.
- dbv2_1_static_validation.json: SHA-256 del SQL corregido.

Los demás entregables DBV2.1 permanecen byte a byte intactos. `before_hashes.json` registra todos. `scripts/db/validate_dbv2_1.py` permite verificar el archivo histórico de fuentes tras reconstruir la candidata, sin cambiar sus hashes originales ni decisiones KEEP/MODIFY/REMOVE.

| Archivo | SHA-256 anterior | SHA-256 nuevo |
|---|---|---|
| `dbv2_1_target_schema.sql` | `5a17a6b0eb0f717e33ab43d03166e05388ff3d8a64b836cd62f10038d4a28961` | `4ed5ccd6e9feba3ed9ce7086fef7a413d0fcc090b3bb567f6b75b5063ec6e749` |
| `dbv2_1_functions_triggers.md` | `479b73ebb1c90571aee418271e676885f24f232534a943dc598b68ccaad75d2a` | `2529e3f0e60052aa514c7d20f964000d5858e7e68a614ead633c14edf56b0fd4` |
| `dbv2_1_static_validation.json` | `99bf8ee14872e66951e5d0e0d69648bbae4fc7c6868848285a1939c71888449e` | `1add835c24db31cb3e30068ad20deb6c3dd43b4189ff46d063c4b50ffd451e11` |

Razón de cada cambio: **DBV2.2-R1 — XAI deferred validation trigger correction**. Detalle legible por máquina: [hashes antes/después](restart_r1/dbv21_hash_changes.json).

## Validación

- DBV2.1: PASS_STATIC_ONLY; todas las relaciones, catálogos derivados, modelo XAI, índices, funciones/triggers y E-04 consistentes. Sin nuevas decisiones estructurales.
- Regresión estática: 3 tests; acepta IF/ELSIF explícito, rechaza mutante CASE original y ausencia del rechazo de tabla desconocida.
- PostgreSQL 17.9: [SQL mínimo](restart_r1/r1_probe.sql), [salida](restart_r1/r1_probe.log), [identidad](restart_r1/r1_identity.txt). Se usa la función corregida completa y los triggers exactos, con dependencias de fila mínimas sintéticas. Las FK de membresía son inmediatas; sólo los triggers de completitud son diferidos. Dos transacciones coherentes evaluación+miembro llegan a COMMIT; la misma evidencia participa en dos evaluaciones. Evaluación sin miembros e identidad de membresía incorrecta siguen rechazadas con P0001. Ambos errores 42703 desaparecen.
- El harness mínimo no certifica el resto del esquema. La suite completa posterior sobre baseline exacta confirma N:M, NULL con razón, FK, PK/UNIQUE, inmutabilidad y referencia/hash de artefactos.

La primera versión del harness mínimo permitía member-first con FK diferida; ese caso no representa la FK inmediata DBV2.1 y no se usa como evidencia de su contrato. Se repitió desde una base nueva con las FK inmediatas y el orden autorizado. No se modificó ninguna constraint de la baseline.

## Continuación autorizada

Intento inicial BLOCKED → corrección R1 aprobada → DBV2.1 revalidado → baseline reconstruida → instancia nueva PostgreSQL 17.9 → Alembic upgrade desde cero → certificación completa.

[Resultado vigente](restart_r1/dbv2_2_baseline_report.md), [certificado](restart_r1/certificate.json). La evidencia original permanece sin sobrescribir. Cero conexiones/escrituras a PostgreSQL operacional. No transferencia, SW-v2, cutover ni freeze final. Pendiente **GATE DBV2.2**.
