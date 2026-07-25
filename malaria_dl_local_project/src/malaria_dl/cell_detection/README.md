# Detección celular futura

El sistema actual clasifica imágenes microscópicas completas. No existe una
implementación activa de detección de objetos, segmentación ni YOLO.

Una incorporación futura requerirá imágenes completas anotadas, un contrato de
entrada y salida, evaluación de *bounding boxes* o segmentación y pruebas
específicas. El detector deberá entregar regiones de interés a un clasificador
validado. Esta frontera no forma parte del flujo clínico actual.
