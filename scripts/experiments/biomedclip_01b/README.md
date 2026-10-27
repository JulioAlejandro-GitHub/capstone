# BIOMEDCLIP-01B: validación aislada

Estos scripts no importan ejecutores productivos ni escriben PostgreSQL. `prepare.py` usa `psql` dentro de `capstone_db` exclusivamente con `default_transaction_read_only=on`; las credenciales permanecen en el contenedor. `supplement.py` importa únicamente la función existente de CKA del proyecto.

## Reproducción

Ejecutar desde la raíz del repositorio en macOS Apple Silicon con Python 3.12, dataset gobernado/materializado y Docker PostgreSQL accesible. Para una nueva ejecución, **usar directorios nuevos**: los checkpoints rechazan sobrescritura. Los resultados JSON del destino corresponden a una ejecución; no reutilizar la carpeta de evidencia entregada.

```sh
export BIOMEDCLIP_WORK_DIR="/ruta/absoluta/nueva/biomedclip-01b"
export BIOMEDCLIP_EVIDENCE_DIR="/ruta/absoluta/nueva/biomedclip-01b-evidence"
python3.12 -m venv "$BIOMEDCLIP_WORK_DIR/venv"
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" -m pip install -r docs/audits/evidence/biomedclip_01b/requirements.lock.txt
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" -m pip check
export HF_HOME="$BIOMEDCLIP_WORK_DIR/hf"
export PYTHONDONTWRITEBYTECODE=1
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" scripts/experiments/biomedclip_01b/prepare.py
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" scripts/experiments/biomedclip_01b/zero_shot.py
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" scripts/experiments/biomedclip_01b/linear.py
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" scripts/experiments/biomedclip_01b/fine_tuning.py
"$BIOMEDCLIP_WORK_DIR/venv/bin/python" scripts/experiments/biomedclip_01b/supplement.py
```

La instalación limpia del lock en otra máquina no fue ejecutada en 01B. La ejecución certificada usó una copia APFS independiente de `.venv-metal` y añadió los paquetes del informe. Los ejecutables se invocaron siempre mediante el Python de esa copia (`python -m pip`), evitando shebangs heredados.

`prepare.py` descarga sólo los cinco archivos de las revisiones oficiales fijadas. `common.load()` verifica sus hashes, modifica las rutas de config **en memoria** y carga offline. La configuración del encoder textual se construye localmente; sus pesos vienen del checkpoint BiomedCLIP, no de pesos BERT adicionales. El uso de `_MODEL_CONFIGS` es una API interna de OpenCLIP fijada por versión, aislada aquí; una integración productiva debe encapsularla o elegir una API pública equivalente probada.

Las pruebas usan 16 TRAIN y 8 VAL; no leen imágenes TEST. El primer benchmark usa las primeras 8 TRAIN del manifiesto (parasitizadas); el suplemento compara las 8 VAL balanceadas. El umbral y los prompts se fijan en `common.py`, no se seleccionan según el resultado. Las dos actualizaciones Fine-tuning son una prueba de gradiente, no una campaña.

Outputs grandes: original/ (modelo y tokenizer), original_embeddings.npy, linear_epoch_1/2/3.keras, fine_tuning.pt, parity_and_representations.npz y linear_timing_probe.keras. Los JSON, logs y manifests describen evidencia experimental, sin sustituir la persistencia productiva.

`finalize.py` es el cierre de la ejecución entregada: revalida hashes, captura controles read-only y genera el manifiesto. Espera archivos auxiliares de instalación/freeze de esa ejecución; no es necesario para repetir los forwards. El informe contiene valores medidos, limitaciones y diseño de Opción B. No ejecuta el registro Zero-shot ni inicia 01C.
