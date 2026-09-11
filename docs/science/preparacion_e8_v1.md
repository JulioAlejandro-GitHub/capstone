# E8 — Preparación y faltantes

**Documento de preparación, no reporte de resultados científicos ni fallback de BD.**

Se implementaron promedio uniforme y ponderado con linaje E6, revisión de configuración, probabilidades por muestra y comparación E7. Contrato `probability_ensemble_e8_v1`, hash `8744f0e7326088b4a7ac419c6439007a655810adb7e38ff6f0dbb2193d5cc001`.

| Elemento | Estado |
|---|---|
| Configuraciones individuales | Plan E7 conservado, sin nueva ejecución científica |
| Ensemble uniforme | 12 grupos planificados: cuatro optimizadores × tres semillas |
| Ensemble ponderado | 12 grupos planificados; pesos/procedencia aún no designados operativamente |
| Dataset/split/población/pacientes | No consultados ni acreditados operativamente en E8 |
| TRAIN, versiones/checkpoints y EVALUATE miembros | Sin referencias operativas seleccionadas para combinar |
| Probabilidades combinadas y métricas clínicas | Sólo fixtures controlados; no resultados del proyecto |
| Comparación o superioridad frente a miembros | Pendiente, sin ranking ni ganador |
| Umbral/configuración operativa de ensemble | No creado ni congelado |
| TEST | Deshabilitado en la ruta E8 actual; ninguna ejecución operativa |
| Calibradores / búsqueda de pesos | No implementados; sólo raw y pesos previos explícitos |
| Latencia | No medida; no se confunde combinación con inferencia completa |

El bloqueo de Docker no implica que no existan experimentos históricos ni que PostgreSQL esté caído. Impide comprobarlos en esta sesión. Antes de realizar ciencia se necesitan los resultados E7 y referencias E6 completas de tres arquitecturas en un grupo explícito; los pesos ponderados requieren una declaración previa. No se combinan semillas ni se elige el mejor miembro de TEST.

El ejemplo numérico de [ensembles_e8_v1.md](ensembles_e8_v1.md) es un fixture identificado, no evidencia clínica. [Matriz planificada](matriz_e8_v1.json). La selección de Producción permanece manual; E9 no se inicia.
