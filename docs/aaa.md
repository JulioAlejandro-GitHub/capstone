Necesito que analices la información de todo el proyecto y me des una descripción clara, estructurada y de alto nivel del proyecto.
Ruta local: `/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone`
git: https://github.com/JulioAlejandro-GitHub/capstone
wiki: https://deepwiki.com/JulioAlejandro-GitHub/capstone

Dime si necestas mas de talles.


Estructura de subsistemas:
backend_api
    Encargado de gestionar los datos desde BD a frontend.
docs
    Aqui esta toda la documentacion del sistema.
frontend
    Interfaz UX/UI para usuarios:
        Cientificos de datos IA.
            Crear, configurar, monitorear, los resultados de las ejecuciones de modelos IA. 
            Campaña + métricas + matriz de confusión
            Explicabilidad y análisis de representaciones
            Comparación entre representaciones/explicaciones
            Comparación espacial Grad-CAM
        Expertos en analisis de frotis.
            Ingresan las imagenes micriscopiacas de frotis.
            El sistema busca las celulas y las envia al modelo activo para su prediccion.
            El resultado se muestra en interfaz inmersiva donde el experto valid los resultados automaticos y hace las anotacones.
            Comparación espacial Grad-CAM
graphify-analysis
    Se intalo esta aplicacion como experimento.
    Se puede usar para analizar.
malaria_dataset_split_project
    Este es una sistema que hace la descarga del dataset.
    Se encarga de hacer el split y sus validaciones.
malaria_dl_local_project
    Sistema IA.
    Aqui esta toda la logica de los modelos IA.
    Modelos de predicción: Custom CNN, VGG16 y Densetet121 con etapas finales de finetuning.
    Modelos de DETECCIÓN: YOLO Detector entrenado con (malaria_dl_local_project/data/NIH-NLM-ThinBloodSmea) y connected_components_v1
smear_segmentation_project
    Entrenamiento de YOLO Detector