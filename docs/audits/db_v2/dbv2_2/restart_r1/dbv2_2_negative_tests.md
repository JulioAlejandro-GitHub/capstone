# DBV2.2 — Pruebas conductuales

PASS. Resultados individuales y SQLSTATE reales en dbv22_server_tests.json y e04_contract_tests.json.

- Recall: acepta 0.01/0.95/0.98/0.99/1.00; rechaza 0/-0.01/1.01 con 23514 y NULL con 23502. Se inserta configuración coherente con el canon; no se desactivan triggers.
- FK: procedencia de publicación/checkpoint, región XAI→evidencia y medición→protocolo rechazan referencias inválidas (23503).
- Unicidad: configuración XAI, región, membresía N:M y publicaciones rechazan duplicados (23505). E-04 verifica identidades de evento/pareja.
- XAI: relación N:M válida, evidencia compartida por varias mediciones, métricas NULL con razón, rechazo de NULL sin razón, ausencia/alteración de membresía y modificación de evidencia. Artefacto conserva URI/hash, rol numérico y visual separados; no se calculan métricas científicas.
- E-04: 27 casos existentes conservados, seis órdenes de inserción, fallo real de COMMIT con rollback total de fixture. Eventos y métricas fijos sintéticos; sin ResultService ni algoritmos SW. Invariantes de identidad/procedencia/umbral, separación migrador/runtime y completitud se mantienen.
- ACL runtime: lectura Alembic permitida; DDL, TEMP, TRUNCATE y UPDATE Alembic rechazados. schema_migrations ausente (42P01).

Todas las transacciones de fixtures de la suite completa se revierten; nunca se muestran password hashes ni se copian datos operativos.
