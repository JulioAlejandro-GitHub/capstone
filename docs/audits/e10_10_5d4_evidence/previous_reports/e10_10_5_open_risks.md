# E10.10.5D.3 — Riesgos abiertos

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

- D-01/D-02 permanecen resueltos. D-04 resuelta mediante comparación estricta por clase y dependencias; sin cambiar propietarios/ACL.
- **D-05 abierto:** baseline carece de la generación STORED de assessment_identities.structural_hash. No retirar generación legacy ni rellenar hashes para forzar equivalencia. Corrección del contrato requiere decisión y recertificación.
- **D-06 abierto:** cuatro CHECK difieren en representación. No declarar equivalencia sin comparar función/operador resuelto y semántica, ni eliminar diferencias del diff.
- No hay destino adoptado comprometido. Rollback completo comprobado; inyección intermedia, repetición y backup/restore adoptado pendientes.
- El respaldo legacy tiene tablas E10/runs/campañas vacías; las pruebas no acreditan preservación de historial poblado.
- Snapshots/planes privados (~1.4 GB en este ensayo) y backups fuente permanecen fuera del repositorio, en /private/tmp; conservarlos para continuidad.
- No acceso operativo en D.3, E ni cutover. El certificado D-03 no debe interpretarse como certificación de equivalencia con legacy tras descubrir D-05.

[Diagnóstico y decisión](e10_10_5_route_b_results.md), [historial de riesgos](e10_10_5d3_evidence/pre_d3_e10_10_5_open_risks.md).
