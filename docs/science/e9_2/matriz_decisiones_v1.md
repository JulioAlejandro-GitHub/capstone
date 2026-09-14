# E9.2 — Matriz de decisiones

Las rutas abreviadas src/configs se resuelven bajo malaria_dl_local_project. No es configuración operativa.

| Decisión | Regla vigente | Fuente verificable | Estado | Acción necesaria |
| --- | --- | --- | --- | --- |
| Matriz | 36 miembros originales: 3 arquitecturas × 4 optimizadores × 3 semillas; sintéticos no disponibles | configs/science/e7_v1.json; contrato PostgreSQL | Confirmada | No reducir |
| Arquitecturas/semillas | custom_cnn,vgg16,densenet121; 11,29,47 | science/protocol.py; E7 | Confirmada | Preservar grupos |
| Dataset/split/paciente | UUID designado y snapshot sellado; paciente unidad de remuestreo | contrato campaña; data/governed_dataset.py | Confirmada | Revalidar E1 antes de consumo posterior, no regenerar |
| Preprocesamiento/aumentación | Contrato E3 por arquitectura; aumentación sólo TRAIN | configuraciones E7; execution/train.py | Confirmada | No cambiar entradas |
| Presupuesto | 50 épocas base; 20 FT preentrenados; 3 intentos/miembro; sin búsqueda de pesos aprobada | E7; campaign protocol budget | Confirmada | No exceder ni ocultar fallos |
| Checkpoint | val_f2_parasitized a umbral 0.5 y política/early stopping congelados | E7; execution/train.py; checkpoint_policy.py | Confirmada | No seleccionar con TEST |
| Calibración de probabilidades | No usada: scores raw, sin calibradores aprendidos | E7; E8; science/ensemble.py | Confirmada | Distinguir calibración de umbral E5 de calibración probabilística |
| Umbral | Scores VAL únicos + 0/1; sensibilidad >0.98; especificidad, F2, umbral mayor | E7; science/statistics.py | Confirmada | Sin ambas clases: no estimable; sin factible: máximo recall y objetivo no alcanzado |
| Candidato individual | Matriz completa; cumplir en todas semillas; media especificidad, media F2, hash; representante semilla11 | E7; science/comparison.py | Confirmada | Fallback max mínimo sensibilidad, exploratorio; no elegir mejor semilla |
| Ensemble uniforme | Tres arquitecturas, mismo optimizador/semilla/población; 1/3 por miembro | E8 | Confirmada | No combinar semillas ni omitir miembros |
| Ensemble ponderado | Pesos fijos predeclared, suma1 tolerancia1e-12, >=2 positivos; valores ausentes | E8; búsqueda documental; cero eventos configuración | Faltante | Propuesta e9_2_fixed_weights_proposal_v1; decisión humana pendiente |
| Comparación VAL | Checkpoint/umbral/configuración comparten VAL; comparación exploratoria | E7 y E8 | Confirmada | Declarar optimismo; no inventar partición independiente |
| Principal individual vs ensembles | E7 selecciona individual; E8 no define campeón global conjunto | E7/E8 | Ambigua | Conservar principal E7; proponer ensembles como contrastes secundarios, no nueva selección TEST |
| Contrastes finales | Parejas arquitecturas, mismo optimizador/semilla; ensemble vs miembros/baseline en E8; lista final aún no congelada | E7/E8; freeze_final | Ambigua | E9.5 debe enumerar configuraciones y propósito; no inferir autorización del lock individual |
| TEST | TRAIN lo prohíbe; E6 requiere final lock; E8 sólo soporta VAL | execution/train.py; assessment; science/ensemble.py | Incompatible con la ejecución actual | Implementación final posterior necesaria; autorización no elimina guarda |
| Independencia TEST | No acreditada; rutas históricas de evaluación repetida documentadas | auditoría 0A; metadatos E9.2 | Ambigua | Sólo análisis final descriptivo con limitación; confirmación independiente exige datos no expuestos |
