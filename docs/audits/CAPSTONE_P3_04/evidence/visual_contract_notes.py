from pathlib import Path
B=Path(__file__).resolve().parents[1]
p=B/'CAPSTONE_P3_04_ANALISIS_POR_OPCION.md';s=p.read_text();s=s.replace('overlay usa abs(heat)/max y mezcla0.6RGB+0.4colormap rojo/azul','overlay PNG guardado usa abs(heat)/max y mezcla 0.6RGB+0.4colormap rojo/azul');s=s.replace('por lo que **pierde distinción positiva/negativa**. Diferente al JET de Grad-CAM.','por lo que **ese PNG pierde distinción positiva/negativa**. La superposición canvas de la UI se reconstruye desde NPY y sí conserva el signo, como se detalla más abajo. Es diferente del JET de Grad-CAM.');s=s.replace('Overlay de magnitud absoluta no comunica signo.','El overlay PNG guardado de magnitud absoluta no comunica signo; la vista canvas alternativa sí utiliza el NPY firmado.');s=s.replace('La función attribution_overlay elimina signo de LIME/SHAP: es una propiedad de visualización comprobada, no del mapa.npy.','La función attribution_overlay elimina signo de LIME/SHAP en el PNG persistido. La vista Superposición usa otro camino: vuelve a pintar el mapa.npy firmado. No se debe atribuir al canvas la limitación del PNG.');p.write_text(s)
p=B/'CAPSTONE_P3_04_HALLAZGOS.md';s=p.read_text().replace('HECHO VERIFICADO: overlay LIME/SHAP usa magnitud absoluta; el mapa NPY conserva signo.','HECHO VERIFICADO: el PNG overlay LIME/SHAP usa magnitud absoluta; el NPY y la vista canvas Superposición conservan el signo.').replace('Distinguir atribución firmada de intensidad visual; no interpretar azul como contribución negativa automáticamente.','Distinguir el PNG persistido del canvas: este último sí usa rojo positivo y azul negativo para LIME/SHAP.');p.write_text(s)
p=B/'CAPSTONE_P3_04_INFORME_GENERAL.md';s=p.read_text();p.write_text(s)
p=B/'CAPSTONE_P3_04_ANALISIS_POR_OPCION.md';s=p.read_text()+'''
## Verificación específica del visor XAI: PNG frente a mapa firmado

**HECHO VERIFICADO EN CÓDIGO:** hay dos caminos de visualización diferentes, no un único overlay:

1. **Comparación de cuatro cuadros:** original y PNG de cada método recuperados como blob autenticado. Para LIME/SHAP, el PNG creado en runtime resume magnitud absoluta. Grad-CAM usa su JET no negativo.
2. **Vista ampliada → Superposición:** `XAIOverlayView` recupera los mapas NPY, los interpreta con `parseNpy` y crea un canvas por método. LIME/SHAP se pintan con signo: rojo `(214,39,40)` a favor, azul `(31,119,180)` en contra de la **clase explicada**; Grad-CAM usa rampa de activación no negativa. No se está volviendo a explicar el modelo: se transforman números persistidos en píxeles.

`parseNpy` valida magic NUMPY, shape de dos dimensiones, orden C (`fortran_order=False`), dtype little-endian f4 o f8 y longitud; f8 se convierte a float32. Para mapa firmado, escala=max|atribución|; para Grad-CAM, escala=max(activación). Cada valor se divide por su propia escala, alpha=round(255×magnitud_normalizada); regiones neutras transparentes. En Grad-CAM se usa activationColor interpolando seis nodos de color; no el JET del PNG guardado. Las intensidades no se comparan entre métodos porque las escalas son independientes.

La composición canvas dibuja el original redimensionado a resolución del input y luego capas Grad-CAM→LIME→SHAP con `globalAlpha=opacidad/100`. Defaults: Grad-CAM50 %, LIME0 %, SHAP0 %; cada capa tiene checkbox y slider0–100 %. Por eso un método existente puede ser invisible inicialmente sin estar ausente. El orden, escala y alpha son transformaciones visuales; no son suma científica de atribuciones ni consenso entre métodos.

Exportación adicional real: `CellTrace` ofrece **Descargar JSON completo por método**, con referencia de artefacto e identidad/metadata completa. La UI compacta listas de samples al mostrar metadata, pero el JSON descargado conserva esa información. No se encontró exportador integral de las siete opciones.

La agrupación `groupXAIComparisons` usa clase objetivo, contexto canónico (modelo/dataset/decisión/protocolo, sin localizadores físicos), TRAIN, versión, checkpoint, sample_id, dataset version, split y purpose. Excluye método/background/semilla/batch/code como claves de equivalencia entre métodos. Repetir un método produce otra fila; no sobrescribe evidencia. SHAP background se conserva como referencia, no como célula target. La equivalencia de contexto no significa identidad de parámetros de perturbación ni comparación cuantitativa de fidelidad.

Recuperación de originales: UUIDs válidos, pertenencia a TRAIN/attempt/sample y dataset/split, snapshot concordante, ruta confinada y SHA del source record. Error de relación404, ID400, archivo faltante410, integridad409, almacenamiento503; cliente los traduce a missing/denied/integrity_failed/not_comparable/error. No son valores cero ni una nueva inferencia.

Fuentes: [XAIOverlayView.tsx](../../../frontend/src/components/reports/XAIOverlayView.tsx#L8), [attributionMaps.ts](../../../frontend/src/utils/attributionMaps.ts#L6), [XAIComparisonViewer.tsx](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L24), [comparison.ts](../../../frontend/src/components/reports/xai/comparison.ts#L74), [dataset_samples.py](../../../backend_api/app/services/dataset_samples.py#L14).
''';p.write_text(s)
for name in ['CAPSTONE_P3_04_ARQUITECTURA_Y_FLUJOS.md','CAPSTONE_P3_04_DATOS_Y_ARTEFACTOS.md']:
 p=B/name;s=p.read_text();s+='''
### Exportación y color XAI: precisión del contrato

Además de copiar enlaces/IDs y descargar archivos, la trazabilidad XAI ofrece un JSON completo por método. El PNG persistido de LIME/SHAP representa magnitud, pero la vista canvas Superposición lee el NPY firmado y sí distingue rojo positivo/azul negativo con opacidad por capa. Ver la ficha05 antes de interpretar colores o exportar una captura.
''';p.write_text(s)
print('XAI visual paths distinguished and export documented')
