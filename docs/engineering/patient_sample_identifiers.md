# Identificadores de paciente y muestra

`subject_code` se normaliza a mayúsculas, admite sólo caracteres seguros y se
busca en forma exacta. El modo automático genera `PAT-{8 hex}` en backend.
`sample_code` se genera como `SMP-{8 hex}` y se vincula al caso del paciente.
No se aceptan nombres, RUT, correo, teléfono, dirección o diagnóstico.
