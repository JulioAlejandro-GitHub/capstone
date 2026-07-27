# Perfiles de quality gate

Perfiles inmutables de código: `manual_microscopy_v1`, `nih_nlm_v1` y
`external_capture_v1`, versión `1.0.0`, algoritmo `pillow-quality-1.0.0`.

Thresholds conservadores iniciales: dimensiones 128×128, 16.384 píxeles;
dark/bright 0,02/0,98; ratios warning/fail dark y bright 0,35/0,80;
contraste mínimo warning/fail 0,18/0,04; entropía 4,0/1,0 bits; Laplaciano
warning 0,00035; Tenengrad warning 0,0008; borde negro máximo 0,45/0,85;
campo útil mínimo 0,45/0,10. Todos se guardan en el snapshot JSONB del run y
son configurables en una futura versión, sujetos a calibración experta.
