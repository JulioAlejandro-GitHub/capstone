# E10.10.5E.4 — E-04 resuelta y baseline recertificada

E10.10.5E permanece en integración. Gate E bloqueado y no solicitado. La continuación se detuvo por [E-05](e10_10_5e5_decision.md), sin implementar todavía el productor real del contexto.

## Contrato implementado

PostgreSQL comprueba al COMMIT una calibración y exactamente dos miembros E10 VALIDATION, default y selected. La identidad compartida incluye linaje, modelo, checkpoint, dataset/población, protocolo y snapshot, input contract y evento, con comparaciones NULL-safe. Se admiten las seis permutaciones de inserción sin desactivar constraints. Selected exige referencia inversa, procedencia de calibración y threshold coincidente. Default exige 0,5, fuente default y ausencia de calibration_id. Se verifican contexto, evento canónico y métricas.

Dos índices parciales imponen unicidad por evento/rol y por identidad científica/rol; el segundo usa NULLS NOT DISTINCT y excluye threshold/source_record_key. UUID5 por evento/rol genera miembros distintos, sin modificar el evento. ResultService inserta ledger, calibración, pareja y métricas en una sola transacción. Los siete fallos SQL exigidos revierten todo; el reintento y la repetición con otro servicio son idempotentes.

La admisión legacy usa current_user en función SECURITY INVOKER: runtime recibe 42501; migrador autenticado puede adoptar. Se conservan el cierre E-01, E-02 y el comportamiento del PostgreSQL legacy. El contrato runtime detecta ausencia/alteración de funciones, triggers, CHECK, FK diferida e índices E-04.

## Certificación

[Certificado final](e10_10_5e4_evidence/route_a/certificate.json), instalado desde cero en PostgreSQL 17.9 aislado, puerto 55495. Pins promovidos sólo después de los controles:

- MANIFEST_HASH: `2ef834913bc23490ed364168143c157b8ceb2d588a8264902a5fce0baaf1d858`.
- CATALOG_HASH: `7cd7829ef16a849a71c3a9055010bc901f87eaba1cab38bab239b4bef0b8ae8d`.

| Evidencia | Resultado |
|---|---|
| Servidor, autoridad runtime/migrador | 49 aprobados |
| D-01/D-02/D-03 y contratos previos | 45 aprobados |
| D-05/D-06 | 5 aprobados; cuatro CHECK exactos y dependencias D-04 preservadas |
| E-04: ocho rechazos nuevos, once previos y casos adicionales | 27 aprobados |
| Orden, COMMIT real, NULL, identidad y procedencia | 17 aprobados |
| Atomicidad SQL y recuperación | 7 puntos aprobados |
| Admisión runtime ante alteración del contrato | 5 controles aprobados |
| Tests adopción/baseline | 101 aprobados |
| Servicio y routing | 76 aprobados |
| Regresión de repositorios/servicio legacy en PG aislado | 50 aprobados |
| Catálogo, ACL E-01, E-02, rollback instalación, idempotencia, backup/restore | Aprobados |

La corrección del renderizador conserva NULLS NOT DISTINCT antes de WHERE; el primer intento de instalación fallido se revirtió íntegramente. La primera emisión E-04 se conserva en `e10_10_5e4_evidence/certificate_01/`; la emisión final incorpora controles de admisión runtime, conserva los mismos hashes de baseline y enlaza su predecesora. D.4/E.1 continúan históricos; los 167 archivos históricos comprobados no cambiaron. E-03 no recibe certificación retroactiva.

## Adopción y alcance

[Route B](e10_10_5e4_evidence/route_a/route_b_regression.json) ejecutó preflight, plan, aplicación, reconciliación y repetición (`already_adopted`) sobre una copia aislada de un backup archivado. Conservó los datos y splits. Ese backup no contenía evaluations legacy: la admisión positiva de parejas legacy se cubrió además con migrador autenticado en las pruebas de servidor. No se accedió al PostgreSQL operativo.

La evidencia de pareja/proyección usa fixtures sintéticos explícitos y el servicio real. No acredita el productor real de `execution_parameters.e10_v2_evaluation_context_v1`, TRAIN integral, transporte, reinicio de procesos, API ni React. Véase [matriz pendiente](e10_10_5e_integration_results.md). Sin cutover, campañas reales, entrenamiento clínico ni alteración de eventos o hashes históricos.
