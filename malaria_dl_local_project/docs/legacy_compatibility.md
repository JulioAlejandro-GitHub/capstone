# Compatibilidad heredada

Los módulos raíz siguen como adaptadores porque pruebas, notebooks y
automatizaciones importan `src.*`. Apuntan a la misma implementación canónica,
sin una segunda copia de la lógica.

Comandos históricos soportados: `python -m src.{train,evaluate,calibrate,explain,predict_image,tta,ensemble,svm_features} --help`.

Comandos canónicos nuevos:

```bash
python -m src.malaria_dl.training.cli --help
python -m src.malaria_dl.evaluation.cli --help
python -m src.malaria_dl.explainability.cli --help
python -m src.malaria_dl.inference.cli --help
```

Para eliminar adaptadores se deben migrar antes notebooks y consumidores
externos, buscar referencias globales y mantener una versión completa con la
suite verde.

