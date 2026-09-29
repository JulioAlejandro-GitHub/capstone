# E10.10.5D.2 — Riesgos y bloqueos

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

- **D-01 resuelto:** IDENTITY nativo conservado, sin segunda secuencia; pruebas reales correctas.
- **D-02 resuelto:** 39 bindings núcleo explícitos y verificados; nuevos defaults/MERGE sin cambios globales.
- **D-04 abierto:** guarda de ownership rechaza 36 funciones de extensión idénticas a Ruta A. Requiere decisión para comparar las funciones de extensión íntegramente contra certificado conservando sus owners/ACL. No reasignar propietarios para satisfacer la guarda.
- Adopción, catálogo adoptado, equivalencia, rollback, repetición y restore adoptado no ejecutados. Pueden existir bloqueos posteriores; recertificación Ruta A no los descarta.
- El backup legacy no contiene runs/eventos/campañas poblados; no acredita preservación de historial poblado. No generar datos científicos para llenar esa cobertura.
- Backups privados fuente en /private/tmp conservados y sin cambios; requieren retención para continuidad. La referencia de datos corresponde a ese backup, no al estado operativo actual.
- E y cutover no autorizados. Cero conexiones operativas durante D.2.

[Decisión solicitada y evidencia](e10_10_5_route_b_results.md), [riesgos anteriores](e10_10_5d2_evidence/pre_d2_e10_10_5_open_risks.md).
