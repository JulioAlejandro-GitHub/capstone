# E7 — Reporte de preparación y faltantes

**Tipo: documentación de preparación, no resultados científicos ni fallback de PostgreSQL.**

Protocolo: `capstone_science_e7_v1`.
SHA-256 canónico: `7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2`.

| Componente | Estado acreditado en esta entrega |
|---|---|
| Arquitecturas | Custom CNN, VGG16, DenseNet121; configuraciones E2/E3 congeladas |
| Semillas planificadas | 11, 29, 47 |
| Matriz original | 12 configuraciones × 3 semillas = 36 miembros planificados |
| Ablación sintética | 36 filas planificadas no disponibles; técnica/proporción/procedencia ausentes |
| Dataset/split operativo E7 | No acreditado nuevamente: acceso al socket Docker denegado |
| Población, soporte, prevalencia, número de pacientes | No consultados; sin cifras inferidas |
| Referencias EVALUATE seleccionadas | Ninguna suministrada/consultada para una comparación científica E7 |
| Resultados históricos | No inventariados operativamente; no se afirma que no existan |
| Métricas, curvas, intervalos y variabilidad | Implementados y probados con fixtures; no son resultados del proyecto |
| Umbral/checkpoint/candidato científico | Ninguno seleccionado ni congelado en datos operativos |
| Exposición histórica a TEST | Desconocida; no se denomina intacto |
| Producción | Selección manual conservada |

No hay ranking, ganador ni estimación de sensibilidad del proyecto. El objetivo **sensibilidad > 0,98** es una regla previa, no un resultado. El baseline siempre parasitized muestra por qué ese objetivo debe acompañarse de especificidad e incertidumbre.

Antes de ejecutar ciencia: completar la integración PostgreSQL E7, verificar E1 sobre la versión explícita, acreditar la población y exposición histórica, crear/congelar una campaña con el plan E4/E7, autorizar sus entrenamientos y completar repeticiones. Después podrán compararse referencias VAL explícitas, documentar sesgo de selección y congelar el candidato/decisión antes de cualquier TEST futuro autorizado. La ablación sintética requiere una futura técnica y procedencia TRAIN-only con nueva versión de protocolo.

La ejecución científica completa permanece **PENDIENTE / NO EJECUTADA EN ESTA ETAPA**. Véanse [protocolo](protocolo_e7_v1.md), [matriz](matriz_e7_v1.json) y [operación](operacion_e7.md).
