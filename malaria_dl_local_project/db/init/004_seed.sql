INSERT INTO experiments (
    name,
    description,
    project_name,
    metadata
)
SELECT
    'Capstone Malaria Classification',
    'Línea base de experimentos para clasificación de imágenes microscópicas de malaria.',
    'malaria_dl_local_project',
    '{"seeded": true}'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM experiments WHERE name = 'Capstone Malaria Classification'
);

INSERT INTO datasets (
    name,
    source,
    version,
    description,
    total_images,
    num_classes,
    class_names,
    class_distribution,
    license,
    url,
    metadata
)
SELECT
    'NIH/NLM Malaria Cell Images',
    'TensorFlow Datasets',
    'tfds-malaria',
    'Dataset de imágenes celulares para clasificación parasitized/uninfected.',
    27558,
    2,
    ARRAY['parasitized', 'uninfected'],
    '{"parasitized": 13779, "uninfected": 13779}'::jsonb,
    NULL,
    'https://www.tensorflow.org/datasets/catalog/malaria',
    '{"seeded": true, "tfds_name": "malaria"}'::jsonb
WHERE NOT EXISTS (
    SELECT 1
    FROM datasets
    WHERE name = 'NIH/NLM Malaria Cell Images'
);

WITH ds AS (
    SELECT id
    FROM datasets
    WHERE name = 'NIH/NLM Malaria Cell Images'
    LIMIT 1
)
INSERT INTO dataset_splits (
    dataset_id,
    split_name,
    num_samples,
    class_distribution,
    split_strategy,
    random_seed,
    metadata
)
SELECT
    ds.id,
    split_name,
    num_samples,
    '{}'::jsonb,
    'TFDS train split partitioned as 80/10/10',
    42,
    '{"seeded": true}'::jsonb
FROM ds
CROSS JOIN (
    VALUES
        ('train', 22046),
        ('validation', 2756),
        ('test', 2756)
) AS split_data(split_name, num_samples)
WHERE NOT EXISTS (
    SELECT 1
    FROM dataset_splits s
    WHERE s.dataset_id = ds.id
      AND s.split_name = split_data.split_name
);

INSERT INTO models (
    name,
    model_type,
    framework,
    architecture,
    description,
    input_shape,
    output_shape,
    pretrained,
    pretrained_source,
    metadata
)
SELECT
    name,
    model_type,
    framework,
    architecture,
    description,
    input_shape,
    output_shape,
    pretrained,
    pretrained_source,
    metadata
FROM (
    VALUES
        (
            'custom_cnn',
            'cnn',
            'tensorflow/keras',
            'custom sequential CNN',
            'CNN propia con bloques Conv2D, MaxPooling, Dense y Dropout.',
            '(200, 200, 3)',
            '(1)',
            FALSE,
            NULL,
            '{"seeded": true}'::jsonb
        ),
        (
            'vgg16_transfer_learning',
            'transfer_learning',
            'tensorflow/keras',
            'VGG16 + custom binary head',
            'VGG16 preentrenada en ImageNet con cabeza binaria.',
            '(200, 200, 3)',
            '(1)',
            TRUE,
            'imagenet',
            '{"seeded": true}'::jsonb
        ),
        (
            'cnn_features_svm',
            'svm',
            'scikit-learn',
            'CNN feature extractor + SVM RBF',
            'SVM RBF entrenado sobre características extraídas desde CNN.',
            NULL,
            '(2)',
            FALSE,
            NULL,
            '{"seeded": true}'::jsonb
        ),
        (
            'ensemble',
            'ensemble',
            'tensorflow/keras',
            'weighted average ensemble',
            'Promedio ponderado de scores de modelos Keras.',
            '(200, 200, 3)',
            '(1)',
            FALSE,
            NULL,
            '{"seeded": true}'::jsonb
        ),
        (
            'tta',
            'inference_strategy',
            'tensorflow/keras',
            'test time augmentation',
            'Estrategia de inferencia que promedia predicciones aumentadas.',
            '(200, 200, 3)',
            '(1)',
            FALSE,
            NULL,
            '{"seeded": true}'::jsonb
        )
) AS model_data(
    name,
    model_type,
    framework,
    architecture,
    description,
    input_shape,
    output_shape,
    pretrained,
    pretrained_source,
    metadata
)
WHERE NOT EXISTS (
    SELECT 1 FROM models m WHERE m.name = model_data.name
);
