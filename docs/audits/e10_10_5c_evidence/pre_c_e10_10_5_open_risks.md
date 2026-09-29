# E10.10.5 — Riesgos al entregar B

**E10.10.5B — RUTA A CERTIFICADA EN POSTGRESQL 17. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

B-01 está cerrada por decisión arquitectónica y comprobación real. Gate B queda **pendiente de revisión**, sin fallos obligatorios de B abiertos.

| Riesgo / límite | Estado / evidencia pendiente | Alcance |
| --- | --- | --- |
| Parser 18.4 frente a destino 17 | Cerrado para la instalación y pruebas ejecutadas en PostgreSQL 17.9; no implica certificar otras versiones | B |
| Nombres de rol reservados | Cerrado B-01: nuevos nombres, guards/ACL/tests coherentes, evidencia original preservada | B |
| Identidad, ACL, rollback, no-op y restauración | Ensayados y aprobados en el destino aislado; sus descriptores no autorizan otro clúster | B |
| Restore como superusuario cambia owner de extensión; dump omite ACL de base y representa owner-only por defecto | Procedimiento probado usa --role migrador y reproduce ACL contractuales. Debe conservarse al reproducir restore | B / operación futura |
| Comparador usa manifiesto como especificación | La representación canónica PostgreSQL 17 acredita conformidad; no descubre por sí sola errores científicos compartidos por especificación e implementación | Revisión de Gate B |
| Ejecución de funciones parcial | Todos los objetos se crearon; casos críticos ensayados, no todas las ramas/carreras de cada función ni recuperación de workflows reales | E |
| Typmods/colaciones y población legacy no recenseados | Requiere copia autorizada y reconciliación explícita; no usar esta instalación como certificado de adopción | C/D |
| External no equivale a external_validation; URI/hash no acredita contenido o disponibilidad | No se inventaron mappings; datos de prueba son sintéticos. Evidencia real pendiente | C/D/E |
| Writer legacy y consumidores operativos no adaptados | Sus contratos no fueron modificados; requieren evaluación obligatoria, capacidades v2 y separación de vistas oficial/externa | E |
| Publicación de aplicación / API / React | Se ensayaron FK, estado, unicidad y append-only del esquema; elegibilidad y flujos de servicio completos siguen fuera de B | E |
| Instancias de prueba retenidas | Ambos contenedores quedan detenidos; volúmenes y backup conservados. La autenticación trust fue sólo de estas pruebas locales, no una configuración operativa | Revisión / limpieza posterior |

**No se inició C, D ni E y no se ejecutó cutover.** La base operativa no recibió conexiones SQL. Los riesgos futuros no se presentan como pruebas de B aprobadas o como permiso para avanzar.

[Certificación y límites](e10_10_5_route_a_results.md), [B-01](e10_10_5b_b01_resolution.md). El registro de riesgos previo a B-01 se conserva en [snapshot histórico](e10_10_5b_evidence/b01_original/pre_b01_e10_10_5_open_risks.md).
