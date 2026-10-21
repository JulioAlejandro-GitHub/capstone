# Resultado de la intervención: costo desplazado, no ahorro equivalente

La decisión previa se conserva sin modificación en optimization_decision.md.
Después de medir el candidato, los perfiles muestran:

| Arquitectura | R1 numpy métricas observador (ms) | R1 numpy métricas arnés (ms) | R2 numpy métricas arnés (ms) |
|---|---:|---:|---:|
| Custom CNN | 40.721 | 0.506 | 38.836 |
| VGG16 | 71.765 | 0.973 | 71.818 |
| DenseNet121 | 81.551 | 0.900 | 79.660 |

R2 tiene cero llamadas del bucle eliminado y conserva 16/32 materializaciones
de tokens, además de las 144/288 lecturas de métricas del arnés común. La primera
lectura concentra el costo; cuando el observador ya la hizo, la posterior resulta
mucho más barata. El experimento desplaza la mayor parte de ese tiempo al arnés,
sin demostrar que lo elimine. No se identifica aquí el mecanismo interno de
caché/copia; las mediciones son de numpy, no del bus GPU.

La diferencia del intervalo total fuera de la función científica entre ambos
perfiles es sólo unos 4–5 ms por corrida, incluyendo cambios en overhead del
propio profiler y variabilidad. No se interpreta como ahorro causal limpio.
Tampoco se atribuye a esta intervención toda diferencia entre los benchmarks
independientes de reproducción y final.

Conclusión H2: hay llamadas repetidas removibles, pero este cambio no demuestra
una reducción neta de 40–82 ms ni explica los picos grandes. Los umbrales finales
siguen fallando en Custom CNN y DenseNet121. Se retiene la versión medida con
dictamen FAIL; no se edita retrospectivamente ni se presenta como estabilizada.
