# Certificación estructural persistente

PASS: los bytes JSON normalizados del catálogo real tienen SHA-256 `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`, exactamente DBV2.2. Revisión raíz SHA-256 `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279`. Se verificaron además todos los hashes de SQL y manifest de recursos certificados; no se modificaron.

Se reutilizó scripts/db/v2_catalog_probe.py y la serialización DBV2.2 (JSON indent=2, sort_keys=True, newline final). Catálogos: catalog_before_restart.json, catalog_after_restart.json y catalog_after_fixture_rollback.json; todos idénticos.

Comparación de 18 categorías: relaciones/ownership/ACL; columnas/tipos/nulabilidad/defaults/identity/generated; funciones de defaults y dependencias; PK/FK/UNIQUE/CHECK/diferibilidad; índices/predicados; views; funciones/cuerpos/ACL; triggers; secuencias; tipos; extensiones; ACL de esquema/base/default; roles y privilegios efectivos de runtime. Se excluyen identidades físicas no deterministas del hash, conservando identidad lógica y definición.

Conteos: 104 tablas de aplicación + alembic_version; 104 PK aplicación; 251 FK; 518 CHECK; 77 UNIQUE; 413 índices de aplicación, 41 UNIQUE explícitos adicionales incluidos; 414 índices al incluir PK Alembic; 79 funciones propias; 105 triggers; 33 views. pgcrypto 1.3 y plpgsql 1.0.

Las nueve tablas XAI están presentes: xai_method_configurations, xai_evidence, xai_artifacts, xai_region_attributions, xai_evaluation_protocols, xai_quantitative_evaluations, xai_evaluation_members, xai_interpretations, xai_specialist_reviews. Ausentes xai_explanations, schema_migrations y model_governance_backfill_audit. confusion_matrices/classification_reports son views. R1 y todas las definiciones E-04 coinciden con DBV2.2.

clinical_target_recall: tipo numeric, attnotnull=true, expression=NULL (sin DEFAULT); CHECK (((clinical_target_recall > (0)::numeric) AND (clinical_target_recall <= (1)::numeric))). No está fijado a 0.98.

No restore, dump instalador, SQL legacy, adoption ni stamp. Se ejecutó únicamente python -m alembic -c alembic_v2.ini upgrade head, equivalente al CLI solicitado, con descriptor/URL explícitos y credencial privada. current/heads y ScriptDirectory confirman una raíz, un head, down_revision=None.
