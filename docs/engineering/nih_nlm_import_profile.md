# Perfil NIH-NLM

`source_system=nih_nlm_thin_blood_smears_pf` y
`acquisition_origin=research_dataset_import`. La carpeta del paciente es un
valor opaco en `external_patient_id`; no se interpreta ni copia a
`external_sample_id`. Sin ID de muestra, Capstone genera `sample_code`, registra
`sample_identity_origin=generated_by_capstone` y usa el paciente como
`source_group_key`.

Se ordena por nombre y se asigna secuencia estable. Cuatro válidas producen
`incomplete`, cinco `complete`, seis `inconsistent`. Ocultos, `.DS_Store` y
`Thumbs.db` no cuentan. Fuente, grupo y ruta lógica permiten reintentos sin
duplicar paciente, muestra, lote, frotis o imagen.
