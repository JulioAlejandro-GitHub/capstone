# Validación técnica de imágenes

Se aceptan JPEG, PNG y TIFF de un frame. El backend no confía en extensión ni
Content-Type: Pillow detecta firma/formato, decodifica completamente y valida
frame, dimensiones y límite de píxeles. GIF/WebP animado, TIFF multipágina,
SVG, PDF, ZIP, DICOM, corrupción y bombas de descompresión se rechazan.
El original no se convierte, orienta, reescala, recorta ni recomprime.
