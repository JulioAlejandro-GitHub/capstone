# Revisión técnica de advertencias

Solo administrator y researcher tienen
`scientific.analysis.quality.review`. Una decisión requiere comentario y se
inserta en `quality_gate_decisions`; no hay endpoint de update o delete.
`approve_with_warnings` habilita el run sin cambiar el gate `warning`; `reject`
lo bloquea. Un gate `fail` nunca puede aprobarse y produce 409. Actor, fecha,
evento operacional y audit event se obtienen del JWT.
