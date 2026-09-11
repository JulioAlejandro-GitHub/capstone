# E6 — Instalación operativa pendiente confirmada

**E6 NO APROBADA.** Evidencia aportada por el usuario al ejecutar la suite completa: `1 failed, 16 passed in 2.28s`.

La única prueba fallida, `test_public_e6_revision_readonly`, leyó:

- Revisión esperada: `20260912_02`; obtenida: `20260912_01`.
- Ausentes en public: assessment_artifacts, assessment_attempts, assessment_campaign_consumers, assessment_final_locks, assessment_identities y assessment_results.
- Triggers E6 habilitados esperados: 8; encontrados: 0.

Esto confirma que la migración E6 no está instalada en la instancia consultada. No demuestra si el wrapper no se ejecutó, falló o se ejecutó contra otro entorno; falta su salida para distinguir esas posibilidades. No corresponde debilitar la prueba ni crear tablas manualmente.

El usuario también recibió HTTP 503 de `/ready` mediante `curl --fail`. No se proporcionó el cuerpo de la respuesta: el desfase de migraciones es una explicación compatible, pero no se atribuye con certeza el 503 a un componente concreto ni se afirma que PostgreSQL esté caído. La prueba pública sí accedió a PostgreSQL y pudo leer el esquema.

Las 16 pruebas sintéticas pasaron nuevamente. Sus tablas/commits de prueba permanecen aislados y no instalan la migración en public. Se conserva el diagnóstico confirmado y la corrección de concurrencia.

HEAD local: `cd5c64d703358797570f5183dd598d93314dc0eb`; **57/57 hashes** del manifiesto anterior coinciden. Este turno agrega sólo evidencia documental y manifiesto; no modifica código, pruebas ni migraciones, ni ejecuta un upgrade.

Siguiente paso desde la raíz Capstone:

```sh
make db-migrate-check
make db-migrate
```

Continuar con el segundo comando únicamente si el precheck es satisfactorio. El wrapper conserva validación de identidad/adopción, backup custom validado y preflight con rollback antes del upgrade. Revisar su salida completa si falla; no sustituirlo por un upgrade directo ni repetir pruebas esperando que instalen tablas operativas.

Tras una migración satisfactoria, repetir la suite completa E6 y `/ready` según la guía. Para diagnosticar el 503 conservando el cuerpo de respuesta puede usarse `curl --silent --show-error --include http://localhost:8000/ready`.

Migración, prueba pública y readiness siguen pendientes. No se inicia E7 ni se ejecutan evaluaciones científicas o cambios de producción.
