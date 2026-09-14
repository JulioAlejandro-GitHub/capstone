# E9.5 — Lista de comprobación propuesta v1

Esto es una especificación de campos pendientes, **no un manifiesto final ni un lock autorizado**. No contiene IDs de candidatos/checkpoints inventados.

| Campo obligatorio | Ya definido | Valor pendiente / control |
| --- | --- | --- |
| Protocolo | hashes E7/E8 en propuesta E9.2 | Enmienda aprobada, hash y fecha de exposición |
| Candidato principal | Regla E7 individual, representante seed11 | Reporte VAL íntegro y candidato real; no elegir con TEST |
| Contrastes | Parejas E7; miembros/baseline E8 | Enumeración exacta y propósito; resolver propuesta de mantener ensemble como contraste secundario |
| TRAIN/versión/checkpoint | Identidad exacta, no última versión | IDs reales, SHA-256, bytes y accesibilidad verificados |
| Miembros ensemble | Tres arquitecturas, mismo optimizador y semilla | Tres referencias E6 verificadas, mismos sample IDs y población |
| Pesos | Uniforme 1/3; restricciones E8 | Ponderados y procedencia aprobados; no normalizar inválidos |
| Preprocessing | E3 por arquitectura | Snapshot exacto y hash por miembro |
| Calibradores | No usados; scores raw | Ausencia explícita, no confundir con umbral |
| Umbral | Regla estricta E7 sobre VAL | Valor, scores/evaluación VAL de origen, hash, comparación >= |
| Dataset/split/muestras | Dataset explícito sellado | Snapshot vigente, IDs y hashes de muestras TEST; sin consumir desempeño |
| Repeticiones | 11,29,47 sin mezcla | Grupo/configuración/semilla de cada contraste y evaluaciones finales previstas |
| Código | Fuente exacta y Git cuando disponible | Huella efectiva de ejecución final y compatibilidad con evidencia VAL |
| Selección | Matriz original completa; fallback explícito | Estado objetivo VAL y reporte persistido, consulta desde conexión nueva |
| Historial TEST | Independencia no acreditada | Alcance/limitaciones actualizados, accesos documentados |
| Reintento técnico | Misma identidad congelada | Motivo, intento anterior y prohibición de ajuste |
| Persistencia | PostgreSQL autoridad | Manifiesto/lock real confirmado y releído antes de TEST |

E7 freeze_final hoy valida al representante individual; no acredita por sí solo todos los contrastes o ensembles. E8 bloquea TEST. La ampliación técnica deberá ser probada en una subetapa posterior sin eliminar guardas. La autorización científica general no equivale a soporte técnico ni a un lock persistido. Publicación sigue siendo decisión manual separada.
