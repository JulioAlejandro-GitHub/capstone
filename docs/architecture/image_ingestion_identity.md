# Identidad de ingesta

La cadena obligatoria es:

`usuario JWT → sujeto pseudonimizado → caso → muestra → frotis → lote → imagen`.

El usuario es el autor (`created_by`, `audit_events.actor_user_id`); no es el
paciente. UUID es identidad interna estable. Los códigos `PAT-*`, `SMP-*`,
`CAS-*`, `SLD-*` e `IMG-*` son visibles, no enumerables y generados en backend.
`external_patient_id` y `external_sample_id` nunca sustituyen esos códigos.
