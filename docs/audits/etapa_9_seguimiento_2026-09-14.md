# E9 — Seguimiento operativo, sin cierre científico

Solicitud autorizada: TRAIN, VALIDATION, ensembles previstos, congelamiento, TEST condicionado a controles, EXPLAIN y auditoría aislada de publicación. Publicación real y E10 no autorizados ni ejecutados.

## Revisión y antecedentes

HEAD al retomar: `c782c4b8092a6c3cfbe7c9fb399939952b6ac554`; árbol inicialmente limpio. Preservado el cambio de clasificación de ese commit. En el preflight anterior de esta misma solicitud se verificaron 95/95 hashes del manifiesto final E8 sobre `f4e79d62c15f21d84f0d61d483f6a7dac7f8accf`. Los cierres E6–E8 son históricos, con sus propias revisiones; las aprobaciones de fixtures no se presentan como ciencia ejecutada. No se encontró AGENTS.md en el repositorio ni sus ancestros inspeccionados.

Se leyeron contrato 0B v1.1, cierres E6/E7/E8, protocolo/operación/preparación E7, preparación/contrato E8, linaje de los consumidores, almacenamiento local y contratos de publicación. E7 conserva hash `7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2`; E8 `8744f0e7326088b4a7ac419c6439007a655810adb7e38ff6f0dbb2193d5cc001`.

## Preflight observado

El primer acceso al socket fue denegado por sandbox; el acceso ampliado autorizado a Compose permitió consultar y ejecutar en la instancia existente. No se cambiaron permisos, servicios ni migraciones. `/ready`: database, migrations y storage ready. Revisión SQL pública: `20260912_02`. Python 3.12.14, TensorFlow 2.17.1, Keras 3.15.1, NumPy 1.26.4, SQLAlchemy 2.0.52, psycopg 3.3.5.

E1 se ejecutó mediante `resolve_governed_dataset` y su conexión explícita REPEATABLE READ, READ ONLY, sin wrapper de auditoría. Pasó comprobación canónica del sello, archivos, asignaciones y fingerprints. La creación/congelamiento de campaña posteriormente utilizó el wrapper escritor oficial en transacciones separadas.

Dataset designado: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; materialización `e15dc166-1c4b-558e-b77b-727b1783430c`.

| Partición | parasitized | uninfected | Total | Pacientes por clase (no sumar sin deduplicar) |
| --- | ---: | ---: | ---: | --- |
| TRAIN | 11137 | 11043 | 22180 | 121 / 161 |
| VAL | 1325 | 1368 | 2693 | 15 / 20 |
| TEST | 1317 | 1368 | 2685 | 15 / 20 |

Consultar soporte e integridad de TEST no es evaluar predicciones sobre TEST. Fingerprints sellados: pacientes `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`; registros `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`; población `eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0`; identidad clínica `d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59`.

Recursos observados: 16 CPU lógicas, ningún GPU TensorFlow, MemTotal 8125656 kB y aproximadamente 6581720 kB disponibles; disco libre observado 855672430592 bytes. No son reservas de capacidad. Los pesos ImageNet no estaban en caché: se descargaron con el mecanismo Keras y su comprobación de hash oficial. Caché efectiva `/tmp/.keras/models`, temporal. SHA-256 VGG16 no-top `bfe5187d0a272bed55ba430631598124cff8e880b98d38c9e56c8d66032abdc1`; DenseNet121 no-top `acdb8da1b8e1e82feebe6be07ef63ce75e8dcfb302eaa49065b9d0311c089d3e`. Tamaños 58889256 y 29084464 bytes respectivamente. No se sustituyó ImageNet por inicialización aleatoria.

Presupuesto original intacto: 36 miembros, 12 configuraciones × semillas 11/29/47; hasta 50 épocas base por miembro y 20 de fine-tuning para preentrenados: máximo 2280 épocas. La ablación sintética de 36 filas permanece no disponible por ausencia de generador/procedencia predefinidos. E8 añade 12 grupos uniformes y 12 ponderados; estos últimos esperan pesos y justificación predeclarados, solicitados al usuario antes de disponer de resultados comparables.

Concurrencia elegida: uno. El intento interrumpido alcanzó TRAIN y mostró alrededor de 4 s/lote y 347 lotes/época: aproximadamente 23 minutos sólo de entrenamiento por época para ese caso, sin validación/serialización. No extrapolar ese tiempo como benchmark de las tres arquitecturas; el presupuesto máximo puede requerir semanas en CPU. No se redujeron épocas ni semillas. Espacio definitivo no estimable aún sin tamaños de checkpoints completos; el ejecutor conserva un checkpoint por época. No se afirma que el espacio libre garantice el máximo.

## Incidentes y correcciones

1. `planning_environment()` lanzó FileNotFoundError por ausencia del ejecutable git. Corrección mínima: Git no disponible queda como null; se conserva SHA-256 de contenido como identidad de ejecución. La revisión host y los cambios se documentan por separado, sin inventar commit dentro del contenedor.
2. Preflight intentó `outputs/campaign_runs`, dentro del bind de código read-only: OSError errno 30. Se usó el argumento oficial `--artifact-root /app/var/artifacts/campaign_runs`, bajo ARTIFACTS_ROOT configurado. No se modificaron mounts ni permisos. Ese directorio no tiene volumen persistente propio declarado en Compose: no se acredita supervivencia al reemplazo del contenedor.
3. Tres intentos fallaron al compilar Adadelta. Reproducción sobre configuración leída de PostgreSQL: Keras rechazó `learning_rate=1` entero. JSONB normaliza números integrales; se convierte a float sólo al construir el optimizador, preservando el valor y configuración sellados. Se detuvo el coordinador con SIGTERM: el cuarto intento quedó interrumpido, no excluido por desempeño. El diagnóstico no usó TEST ni selección por métricas.

No se reescribió el contrato de la campaña original. La modificación de fuente requiere una sucesora según la guarda E5. Todos los intentos previos permanecen en PostgreSQL.

## Campañas y persistencia real

- Original: `ec442763-7eea-499d-a94f-9a3ddfb7c0f0`, hash `ef9bdf8089bc94649f007d651092d4e8f600b139002f05c180901b9e74e26580`, pausada: 3 fallidos, 1 interrumpido, 32 pendientes, 0 verificados. Runs fallidos: `d99aac41-a1a3-4264-a110-48be6584d7a4`, `7e7ec232-2ab7-4f03-8458-d3f0b394d2a5`, `1b90a974-f81b-41cf-bdda-c3a24962689a`; interrumpido: `66fa0104-e6f9-4099-b0c9-14b1b61995da`.
- Sucesora: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`, hash `02a63b0c76dc600bcb17c7163699abf7dd4e5579643b6adbc783f50d30fcf1ba`; conserva protocolo/matriz y registra en purpose la relación con la original y motivo. Fuente congelada `d8569d8faaa80eca42b130e6096203d851e2c663b4cdb8cd599dda950fbe6430`. Iniciada mediante el ejecutor E5; consultar estado actual en BD, no inferirlo de este documento.

La creación y congelamiento fueron confirmados por el servicio; una llamada posterior del repositorio desde otro proceso recuperó la campaña original. PostgreSQL es la autoridad de runs, estados y resultados. Este documento registra observaciones operativas: no sustituye un ledger ni es fallback de resultados científicos.

## Pruebas

- Correcciones y regresiones E5/publicación: **26 passed, 2 warnings en 3.82 s**; no sumar la ejecución anterior de 25 casos.
- Commit sintético E9 más regresiones E7: **4 passed en 3.26 s**. Reporte confirmado y leído exactamente desde nueva conexión; rollback de E7 deja cero eventos desde otra conexión.
- Publicación sintética: **1 passed en 0.57 s**. Versión/checkpoint explícitos, repetición idempotente, baja manual y rollback de publicaciones/eventos. No se activa deployment real. Tablas padre simplificadas del fixture no acreditan todas las constraints públicas.
- Consulta posterior: cero esquemas `capstone_test_e4_%` remanentes. No se ejecutó la prueba legacy que escribe sobre publicaciones reales.
- No se verificó persistencia ante reinicio o fallo físico. Commit confirmado y rollback son evidencias diferentes.

## Pendientes científicos y puertas

No hay resultados científicos completos, candidato elegido, manifiesto final congelado, TEST predictivo, EXPLAIN E9 ni publicación real. Objetivo >0,98: **no evaluable**. No se presenta el desempeño parcial de un lote como resultado.

El inventario previo contenía 36 EVALUATE legacy (12 con este dataset, 24 sin UUID) y cero assessment_attempts E6. No se reutilizaron: falta compatibilidad completa. La exposición histórica de TEST no está descartada; no se denomina independiente intacto. Debe completarse su auditoría antes de conclusiones finales.

E8 actual sólo implementa VAL. E7 freeze_final valida el candidato individual representativo, no un manifiesto completo de contrastes/ensembles. La autorización E9 no elimina esas guardas: antes de TEST deben completarse y probarse los contratos correspondientes sin ajustar resultados observados. Ningún TEST se abrirá por omitir una guarda.

Estado: implementación técnica **parcial**; campaña científica **parcial/en seguimiento**; objetivo **no evaluable**; publicación manual **con hallazgos** (informe separado); publicación real **no ejecutada**. E9 NO APROBADA mientras falten sus evidencias críticas. Este documento no es cierre final ni inicia E10.
