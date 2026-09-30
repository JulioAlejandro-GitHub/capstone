# DBV2.2 — BASELINE V2 CONSTRUIDA Y CERTIFICADA

Estado técnico: PASS; pendiente aprobación **GATE DBV2.2**. Esta evidencia complementa el [intento inicial bloqueado](../dbv2_2_baseline_report.md) y la [resolución R1](../dbv2_2_r1_xai_trigger_resolution.md).

## Baseline y catálogo real

| Propiedad | Resultado |
|---|---|
| Revision / head | pg_v2_baseline |
| down_revision | None |
| Roots / heads | 1 / 1 |
| PostgreSQL | 17.9 / server_version_num 170009 |
| Tablas de aplicación / técnica Alembic | 104 / 1 |
| PK aplicación / FK / CHECK / UNIQUE | 104 / 251 / 518 / 77 |
| Índices UNIQUE adicionales | 41 |
| Índices aplicación / con Alembic | 413 / 414 |
| Funciones propias / triggers / views | 79 / 105 / 33 |
| Extensiones | pgcrypto 1.3; plpgsql 1.0 preinstalada |
| Comparación de catálogo | 18 categorías; cero diferencias |

Las nueve tablas XAI están confirmadas: xai_artifacts, xai_evaluation_members, xai_evaluation_protocols, xai_evidence, xai_interpretations, xai_method_configurations, xai_quantitative_evaluations, xai_region_attributions, xai_specialist_reviews. `schema_migrations`, `model_governance_backfill_audit` y `xai_explanations` están ausentes. `confusion_matrices` y `classification_reports` son views.

`clinical_target_recall numeric NOT NULL`, sin DEFAULT. Definición real: `CHECK (((clinical_target_recall > (0)::numeric) AND (clinical_target_recall <= (1)::numeric)))`. Acepta 0.01, 0.95, 0.98, 0.99 y 1.00; rechaza 0, -0.01, 1.01 y NULL.

## Pruebas

35 pruebas estáticas; 111 comprobaciones PostgreSQL (77 generales/XAI/recall/privilegios + 27 E-04 + 7 órdenes/atomicidad E-04), todas PASS. Adicionalmente R1 mínimo real PASS. Ningún test mocked se presenta como evidencia de PostgreSQL.

Instalación desde cero sólo mediante `alembic -c alembic_v2.ini upgrade head`, ejecutado con `python -m alembic` en el entorno disponible y `PGV2_TARGET`/`PGV2_DATABASE_URL` explícitos. Sin historia legacy ni stamp. El esquema científico permanece vacío; sólo existen el head y el singleton técnico aprobado.

Segundo upgrade: mismo head, mismo catálogo, mismos OID/relfilenodes. Fallo real después de 500 DDL: rollback completo, sin ledger falso; instalación posterior completa y catálogo idéntico. Backup/restore en otra base: mismo catálogo, head, ownership y ACL. E-04 se conserva íntegro y pasa los casos estructurales aplicables sin consumidores SW.

## Hashes

- Manifest estructural: `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`.
- Revisión raíz: `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279`.
- Manifest de recursos (agrega hashes por SQL/sentencia): `232871ff0241c2912eef40daeee2c849fde70bdec5d64784cb72844e667b009a`.

`dbv2_2_hashes.sha256` contiene revisión, todos los recursos SQL, evidencias y código utilizado. No es freeze final; corresponde a esta certificación DBV2.2.

## Seguridad y límites

Cero conexiones y cero escrituras a PostgreSQL operacional. Instancia nueva, volumen exclusivo, host/puerto/base/versión/identificador verificados antes de escrituras. Roles sin privilegios elevados ni memberships; runtime sin DDL/TEMP/TRUNCATE/escritura Alembic. PUBLIC sin acceso al esquema ni ejecución de funciones propias.

Contenedor de certificación detenido; volumen `capstone_v2_isolated_15ea056917ee` conservado para revisión. Contenedor tmpfs R1 eliminado. No se transfirieron datasets, usuarios, roles reales, campañas ni resultados. No se iniciaron DBV2.3/DBV2.4, SW-v2 o cutover.

Diferencias finales contra DBV2.1 + R1: **cero**. El detalle del delta inicial está en baseline_delta.json; las normalizaciones textuales del parser no cambian AST/semántica. Solicitud final: **GATE DBV2.2**.
