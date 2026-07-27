# Métricas técnicas de imagen

La orientación EXIF se aplica solo en memoria. La imagen conserva aspect ratio y
se reduce con LANCZOS si su lado mayor supera 2048 px. RGB se convierte a
luminancia normalizada con `Y=0.2126R+0.7152G+0.0722B`.

- Brillo: media y percentiles lineales p05, p50 y p95.
- Contraste: p95 menos p05; dispersión: desviación estándar poblacional.
- Entropía: Shannon en histograma de 256 bins.
- Laplaciano: varianza del kernel cruz `[0,1,0;1,-4,1;0,1,0]`.
- Tenengrad: media de gradientes centrales horizontales y verticales al cuadrado.
- Borde negro: proporción bajo `dark_threshold` en una franja perimetral de 5%.
- Campo útil: proporción total sobre `dark_threshold`; es una heurística, no
  segmentación celular.

Las unidades, escala y resolución analizada se persisten. Estos indicadores no
han sido validados clínicamente.
