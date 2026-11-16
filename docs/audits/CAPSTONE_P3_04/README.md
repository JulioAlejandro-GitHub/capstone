# CAPSTONE-P3-04 — Índice de reproducibilidad

Auditoría local del 16 de noviembre de 2026 (America/Santiago), datasource `malaria`, ruta `http://localhost/modelo-ia/analisis`. Solo lectura científica y documentación. El UUID solicitado es un **attempt EVALUATE TEST**; su TRAIN es `87b3eff7-e09a-41c8-945d-bf31b3541adb`.

## Documentos

1. [Informe ejecutivo y científico](CAPSTONE_P3_04_INFORME_GENERAL.md).
2. [Arquitectura y flujos](CAPSTONE_P3_04_ARQUITECTURA_Y_FLUJOS.md).
3. [Catálogo de funciones y líneas](CAPSTONE_P3_04_CATALOGO_FUNCIONES.md).
4. [Datos y artefactos](CAPSTONE_P3_04_DATOS_Y_ARTEFACTOS.md).
5. [Análisis de las siete opciones y matemáticas](CAPSTONE_P3_04_ANALISIS_POR_OPCION.md).
6. [Caso principal 00b8d407](CAPSTONE_P3_04_RUN_00b8d407.md).
7. [Comparación y cobertura por modalidad](CAPSTONE_P3_04_COMPARACION_Y_COBERTURA.md).
8. [Hallazgos y recomendaciones](CAPSTONE_P3_04_HALLAZGOS.md).
9. [Evidencia para P3 y rúbrica](CAPSTONE_P3_04_EVIDENCIA_PARA_P3.md).

## Evidencia entregada

- `sql/`: SELECT dentro de transacción READ ONLY REPEATABLE READ; esquema, claves, vistas/triggers, identidades, intentos, épocas, resultados y ejemplos de linaje.
- `csv/`: funciones, fuentes, endpoints, hashes de código local/contenedor, inventario físico completo del registro, archivos auxiliares del caso, métricas/scores/épocas principales, mapas XAI, CKA y cobertura por modalidad.
- `figures/`: curvas, confusión y proyecciones ya persistidas del principal. Son gráficos derivados de auditoría, no capturas UI.
- `evidence/`: respuestas reales de servicios, capturas PostgreSQL, cálculos independientes, resúmenes de archivos y scripts. Se conservan filas/metadata, no pesos de modelos ni grandes artefactos duplicados.
- `evidence/manifest.json`: SHA-256 de documentos/scripts/CSV/SQL/JSON/figuras entregados (excluye a sí mismo). Identifica contenido, no firma clínica.

## Reproducir desde la raíz del repositorio

No iniciar contenedores ni ejecutores nuevos. Requiere los contenedores existentes `capstone_db` y `capstone_backend`. Los extractores pasan `default_transaction_read_only=on`, timeout60s y entregan SQL con BEGIN READ ONLY. Credenciales quedan dentro del contenedor y no se imprimen. Cada consulta tiene snapshot propio; no se afirma consistencia temporal global entre todas las capturas.

```sh
python3 docs/audits/CAPSTONE_P3_04/evidence/extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/case_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/lineage_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/session_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/comparison_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/contracts_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/replay_services.py
python3 docs/audits/CAPSTONE_P3_04/evidence/local_inventory.py
python3 docs/audits/CAPSTONE_P3_04/evidence/checkpoint_inspection.py
python3 docs/audits/CAPSTONE_P3_04/evidence/catalog_sources.py
node docs/audits/CAPSTONE_P3_04/evidence/typescript_inventory.mjs
python3 docs/audits/CAPSTONE_P3_04/evidence/catalog_sources.py
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/capstone_p3_04_mpl malaria_dl_local_project/.venv-metal/bin/python -B docs/audits/CAPSTONE_P3_04/evidence/compute.py
PYTHONDONTWRITEBYTECODE=1 malaria_dl_local_project/.venv-metal/bin/python -B docs/audits/CAPSTONE_P3_04/evidence/contrast.py
```

Estos comandos actualizan **solo evidencia y derivados dentro de la auditoría**; en particular compute/contrast no importan runtimes ni ajustan PCA/UMAP: leen arrays y calculan métricas/CKA/elección de threshold en memoria. Ningún cálculo escribe umbrales productivos. `replay_services.py` invoca directamente módulos de lectura y únicamente arquitectura Keras principal; no llama estructura ViT, generación, activation POST/DELETE, login ni endpoints con auditoría de escritura. Verificar que el código actual siga manteniendo esos contratos antes de repetir después de cambios del sistema.

La generación documental es separada: write_reports.py → write_options.py → write_remaining.py → finish_docs.py. `catalog_sources.py` regenera el índice nominal y finish_docs añade fichas curadas. No ejecutar finish_docs varias veces sin regenerar antes los documentos, pues agrega anexos. La reproducción de datos puede conservar los informes originales y dejar un nuevo snapshot aparte si se necesita comparación temporal. Las capturas contienen paths y pseudónimos de pacientes del dataset: conservar el alcance local previsto para estos documentos.

## Comprobaciones realizadas

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend_api:malaria_dl_local_project malaria_dl_local_project/.venv-metal/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_clinical_metrics.py backend_api/tests/test_representation_generation.py -q
node --test frontend/tests/scientific-results-v2.test.mjs frontend/tests/scientific-review-ui.test.mjs frontend/tests/vit-architecture.test.mjs
```

Resultado: 15 pruebas Python y 15 frontend aprobadas; logs en evidence/tests_python.txt y evidence/tests_frontend.txt. No se escribieron pruebas productivas ni se ejecutaron pruebas de persistencia contra la BD científica. Las pruebas de contratos/dobles no validan fidelidad XAI ni diagnóstico.

Reproducción numérica principal: métricas coinciden exactamente, hash de checkpoint y mapas/matrices seleccionados coincide, cuatro originales coinciden. 35.341 referencias inventariadas por stat; 43 artefactos hash comprobados y cuatro originales aparte. 5.386 archivos de un EXPLAIN ajeno al principal ausentes en rutas comprobadas. El resto de hashes globales no se comprobó.

## Límites y cierre

Se documentaron las siete opciones, funciones, contratos reales, tablas/artefactos, fórmulas, figuras y el caso solicitado con sus identidades reales. Las ausencias se distinguen de capacidades no implementadas. Hay matrices por seis modalidades y preguntas científicas, contraste con P3-03 y criterios P3.

No se verificó navegador, bundle servido, transporte HTTP autenticado, todas las variantes de renderer ni la rama ViT con caché generadora. No se acreditan validación clínica externa, conceptos morfológicos expertos ni sensibilidad por frotis/paciente desde estas métricas celulares. BiomedCLIP tiene motor y evaluaciones pero no aparece en selector actual. El catálogo nominal es estático con límites explícitos, complementado por fichas y replay de servicios; no afirma cobertura dinámica de cada callback o función de dependencias.

No se modificaron código productivo, esquema, registros, umbrales, checkpoints ni selección activa. Las modificaciones previas del usuario en frontend se conservaron. No se requiere aprobación para leer esta evidencia; cualquier implementación de recomendaciones pertenece a otra fase autorizada.

## Validación de la entrega y compactación

`python3 docs/audits/CAPSTONE_P3_04/evidence/validate_audit.py` comprueba los diez documentos, enlaces locales, consultas sin mutaciones, coincidencia de fuentes local/contenedor, métricas reproducidas, originales y logs de pruebas; luego compacta JSON grandes sin cambiar su contenido semántico y actualiza manifiesto. Resultado en [audit_validation.json](evidence/audit_validation.json).

El índice nominal final incluye funciones y métodos Python y AST TypeScript, incluidos callbacks; se entrega como superconjunto estático de las fuentes, con fichas centrales aparte. Las referencias nominales de pruebas no equivalen a cobertura dinámica.

Para reconstruir también la edición final después de generar los borradores: `polish.py`, `visual_contract_notes.py`, `polish_comparison.py` y `validate_audit.py`, en ese orden. Si se regenera solo el catálogo, `append_catalog.py` vuelve a añadir sus fichas centrales sin repetir los demás anexos. No ejecutar scripts generadores sobre la entrega original si se quiere conservar su manifiesto como snapshot histórico.
