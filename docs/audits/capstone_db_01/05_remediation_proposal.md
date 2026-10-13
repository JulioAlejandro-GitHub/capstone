# CAPSTONE-DB-01 — Propuesta para fases posteriores

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Propuesta; no ejecutada ni autorizada por esta auditoría.

## Orden de intervención

1. **Aceptar alcance y respaldo.** Revisar manifiesto local, los tres hallazgos y pendientes D. Antes de DDL posterior, actualizar respaldo y ensayar restauración en entorno aislado si se autoriza, con roles/extensiones y artefactos externos disponibles. Nunca restaurar sobre la base operativa para verificar un dump.
2. **DB-02: retirar selección histórica en conjunto.** Modificar execution/schema.py, execution/repository.py, persistence/result_repository.py y services/scientific_results.py; cubrir llamadas en health, campaign, local_execution, controlled y plan. Usar SQL/objetos actuales directamente. Retirar ramas de escritura en runs.parameters que solo existan como alternativa de esquema. No ampliar whitelists, cambiar alembic_version ni añadir otra capa de compatibilidad.
3. **DB-03: corregir lectura E6 de extremo a extremo.** Modificar assessment_lineage.py, training_summaries.py, lineage_children.py, DTO Pydantic/TypeScript, Runs y presentación/detalle de hijos. Incorporar kind explain, seleccionar intento por identidad y conservar estado verificado/fallido/activo. Usar las relaciones ya persistidas. No crear runs, nuevas tablas o duplicados solo para adaptar la UI.
4. **DB-01: alinear evidencia de dataset y mejorar errores.** Cambiar la subcondición instalada de campaign_guard para evaluar suficiencia de evidencia de train/val, global frozen metadata y verificación física de splits requeridos; preservar event_type, success, error_code, snapshot, dataset_version y demás integridad. Correlacionar el código genérico CAMPAIGN_DATABASE_OPERATION_FAILED con la excepción interna de la solicitud; mejorar mapeo de errores y logging seguro sin imprimir driver parameters. No exigir TEST para crear una campaña TRAIN.
5. **Simplificación acotada.** Sustituir consultas de tolerancia a columnas antiguas de execution_record_readers por columnas actuales. Revisar pinning del baseline como verificación fuera de runtime, sin inventar versión sucesora. Investigar guards controlled/technical y fallbacks de publicaciones solo donde haya evidencia de uso y equivalencia.
6. **Retiro de historial/migraciones, si se aprueba.** Solo tras resolver dependencias activas y checks de mantenimiento/pruebas/documentación. Preparar baseline reproducible del esquema vigente si se necesita aprovisionamiento; no usar historial como validador de validez. No mezclar esta limpieza con eliminación indiscriminada de controles científicos.

## Conservar

PK, FK, UNIQUE, tipos, NOT NULL, separación de pacientes/splits, dataset identity, referencias run/model/checkpoint, evidencia inmutable, propiedad de sesiones, secuencia e idempotencia de eventos, transacciones diferidas, linaje clínico, snapshots celulares, revisión humana y controles de destino de base. Conservar relación con evaluación verificada y selección/cierre final de TEST. Un nombre con versión histórica no justifica eliminar su función.

## Candidatos concretos

| Candidato | Acción propuesta | Riesgo/dependencia |
|---|---|---|
| SUPPORTED_REVISIONS / consulta alembic_version en require_e10_schema | Retirar requisito de revisión | Todas las ramas V2_REVISION deben cambiar en el mismo trabajo. |
| `revision ==/!= V2_REVISION` | Adoptar persistencia/lectura actual | Riesgo de omitir configuración, calibración o normalización si quedan ramas antiguas. |
| `campaign_guard` comparación exclusiva verified | Corregir semántica de evidencia suficiente | No admitir evidencia rechazada, snapshot diferente ni splits faltantes. No retirar trigger completo. |
| Proyección EXPLAIN basada exclusivamente en runs | Incorporar assessments vigentes | Contadores, lista, detalle, métodos y navegación deben concordar; deduplicar por identidad/intento real. |
| to_jsonb(record) para ausencia de event_id/event_sequence | Consultar columnas actuales | Separar compatibilidad de esquema de conservación de registros históricos reales. |
| Guard de revisión en maintenance/database.snapshot | Revisar procedimiento antes de reutilizar | Protege operaciones de mantenimiento; no retirar verificaciones de identidad/destino/integridad. |
| campaign_technical_guard, controlled_pause_guard, e04_legacy_admission | Investigar; no DROP propuesto | Requieren conocer consumidores, intentos activos y política de historia científica. |

No hay propuesta de SQL correctivo ejecutable en estos archivos. Las definiciones SQL adjuntas son evidencia, no instrucciones de aplicación.

## Pruebas de aceptación futuras

Estas pruebas requieren autorización de implementación y entorno aislado; no se ejecutaron en Fase 1. Usar la orquestación de pruebas del Makefile.

- **Esquema único:** un head histórico no interviene en la decisión runtime; pruebas negativas siguen detectando ausencia de tablas/columnas realmente requeridas mediante errores claros, sin whitelist de versiones.
- **TRAIN:** reserva, run_configurations, evento idempotente, secuencia contigua y resultado/calibración referencian el mismo run/attempt/checkpoint. Una segunda identidad o un propietario incorrecto se rechazan; rollback no deja resultado parcial.
- **DB-02 transversal:** reporte scientific-results y readiness operan contra esquema actual; Docker/local/controlado usan el mismo contrato; no caen a escritura histórica.
- **EXPLAIN E6:** con el dataset de inspección actual, el TRAIN correspondiente muestra dos EXPLAIN verificados y un EVALUATE. Contadores y filas coinciden, incluso con límites/caché. No se crean filas en runs para satisfacer la UI; se muestran estados fallidos/activos sin métricas certificadas y se evita duplicar reintentos.
- **Detalle XAI:** método, intento, evidencia y referencia de artefacto mantienen identidad; errores por archivo ausente no se presentan como ausencia de ejecución. Verificar contenido externo por hash solo cuando corresponda al alcance aprobado.
- **Campaña:** evidencia física válida train/val permite creación; evidencia fallida, sin splits requeridos, de otra versión o con snapshot distinto se rechaza. Crear TRAIN no lee TEST. Hash y matriz siguen protegidos. Transacción revierte campaña/configuraciones/miembros ante fallo.
- **Errores UI:** red, timeout, 422 científico y 500 tienen mensajes distinguibles y correlation_id cuando exista; nunca se exponen credenciales, SQL con parámetros ni datos clínicos.
- **Regresión de integridad:** FK/UNIQUE/NOT NULL y triggers conservados rechazan referencias inválidas; catálogos y dependencias muestran únicamente los cambios aprobados.

## Pendientes antes de limpieza general

Correlacionar el código genérico DB-01 con su excepción interna; revisar semántica de restricciones D; establecer uso de vistas y lectores históricos; revisar constantes específicas de dataset y fallbacks en su auditor de contrato; planificar recuperación conjunta de base y artefactos. La evidencia disponible permite preparar correcciones acotadas, pero no respalda una eliminación general de guards/triggers o historial sin revisar dependencias.
