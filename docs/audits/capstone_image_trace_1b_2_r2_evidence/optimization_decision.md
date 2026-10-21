# Decisión posterior al perfil R1, previa a medir el candidato R2

Las 15 variantes diagnósticas terminaron y conservaron las salidas comparadas.
Fuente: `profile_summary.json`, timelines y comparaciones individuales.

El bucle `observer.py:execute:96` materializa nueve métricas por batch además
del token. Mediciones inclusivas bajo profiler: CNN 144 llamadas / 40,721 ms;
VGG16 288 / 71,765 ms; DenseNet121 288 / 81,551 ms. El mismo retorno se
materializa otra vez en el arnés común A/B. Este costo host medido justifica
eliminar la materialización redundante del observador, no cambiar el baseline.

Único cambio candidato: quitar ese bucle. Se conserva `token.numpy().tolist()`;
el token mantiene dependencias de TODOS los resultados originales y de la
lectura de `optimizer.iterations` en TRAIN. No se cambia el paso original,
grafo matemático, pipeline, callbacks científicos, agregación ni journal.
La función debe retornar y el token debe materializarse antes de confirmar.
Se repetirán especialmente los fallos antes/durante/después y la equivalencia
de tensores, gradientes, pesos, optimizador, restauración y selección.

Esto elimina llamadas concretas, pero NO demuestra que elimine la dispersión
p95. La reproducción falló en las tres arquitecturas; las latencias grandes
de primeras formas incompletas también existen en A y no aumentan los contadores
de trazado de sus funciones TRAIN/VAL. No se atribuyen a una compilación Metal
individual sin traza nativa: XPlane sólo expone host y xctrace no está instalado.
Los límites y el calentamiento permanecen exactamente iguales.

No se modifica ledger.py: en los perfiles completos, Store.put acumula
6,700/12,254/14,112 ms; Aggregator.add 2,974/5,616/6,756 ms. No hay evidencia que
justifique tocar fsync, intervalos, tamaños, hashes, recuperación o durabilidad
para corregir los picos observados. Sin colas ni trabajo asíncrono.
