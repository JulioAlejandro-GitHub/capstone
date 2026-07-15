-- Vista canónica para auditar una predicción junto con su fuente y explicación.
--
-- Esta migración es deliberadamente no destructiva. Los campos reservados para
-- imágenes completas (source_image_id, patient_id, slide_id y bbox_*) se leen de
-- JSONB mientras no existan columnas físicas, por lo que productores actuales y
-- futuros pueden convivir sin alterar las tablas ni perder datos.

CREATE OR REPLACE VIEW vw_visual_explainability_audit AS
WITH audit_source AS (
    SELECT
        er.id AS explainability_id,
        er.prediction_id,
        er.run_id,
        r.experiment_id,
        r.model_id,
        m.name AS model_name,
        m.model_type,
        COALESCE(dsi.dataset_id, p.dataset_id, r.dataset_id) AS dataset_id,
        COALESCE(dsi.dataset_name, d.name) AS dataset_name,
        COALESCE(
            dsi.dataset_source,
            d.source,
            NULLIF(p.metadata->>'source', ''),
            NULLIF(r.parameters->>'dataset_source', '')
        ) AS dataset_source,
        COALESCE(
            NULLIF(p.metadata->>'dataset_split', ''),
            NULLIF(p.metadata->>'split_name', ''),
            NULLIF(er.metadata->>'dataset_split', ''),
            rdi.split_name,
            NULLIF(r.parameters->>'dataset_split', ''),
            NULLIF(r.parameters->>'split_name', '')
        ) AS dataset_split,
        CASE
            WHEN COALESCE(
                NULLIF(p.metadata->>'dataset_index', ''),
                NULLIF(er.metadata->>'dataset_index', '')
            ) ~ '^[0-9]+$'
            THEN COALESCE(
                NULLIF(p.metadata->>'dataset_index', ''),
                NULLIF(er.metadata->>'dataset_index', '')
            )::BIGINT
            ELSE rdi.sample_index::BIGINT
        END AS dataset_index,
        COALESCE(
            NULLIF(p.metadata->>'manifest_id', ''),
            NULLIF(er.metadata->>'manifest_id', ''),
            NULLIF(rdi.metadata->>'manifest_id', ''),
            NULLIF(dsi.metadata->>'manifest_id', ''),
            dsi.image_id::TEXT
        ) AS manifest_id,
        dsi.image_id AS dataset_image_id,
        COALESCE(
            CASE
                WHEN COALESCE(
                    NULLIF(p.metadata->>'original_tfds_label', ''),
                    NULLIF(er.metadata->>'original_tfds_label', '')
                ) ~ '^[+-]?[0-9]+$'
                THEN COALESCE(
                    NULLIF(p.metadata->>'original_tfds_label', ''),
                    NULLIF(er.metadata->>'original_tfds_label', '')
                )::INTEGER
            END,
            dsi.original_tfds_label
        ) AS original_tfds_label,
        COALESCE(
            CASE
                WHEN COALESCE(
                    NULLIF(p.metadata->>'project_label', ''),
                    NULLIF(p.metadata->>'remapped_label', ''),
                    NULLIF(er.metadata->>'project_label', ''),
                    NULLIF(er.metadata->>'remapped_label', '')
                ) ~ '^[+-]?[0-9]+$'
                THEN COALESCE(
                    NULLIF(p.metadata->>'project_label', ''),
                    NULLIF(p.metadata->>'remapped_label', ''),
                    NULLIF(er.metadata->>'project_label', ''),
                    NULLIF(er.metadata->>'remapped_label', '')
                )::INTEGER
            END,
            dsi.project_label
        ) AS project_label,
        COALESCE(
            CASE
                WHEN COALESCE(
                    NULLIF(p.metadata->>'remapped_label', ''),
                    NULLIF(p.metadata->>'project_label', ''),
                    NULLIF(er.metadata->>'remapped_label', ''),
                    NULLIF(er.metadata->>'project_label', '')
                ) ~ '^[+-]?[0-9]+$'
                THEN COALESCE(
                    NULLIF(p.metadata->>'remapped_label', ''),
                    NULLIF(p.metadata->>'project_label', ''),
                    NULLIF(er.metadata->>'remapped_label', ''),
                    NULLIF(er.metadata->>'project_label', '')
                )::INTEGER
            END,
            dsi.project_label
        ) AS remapped_label,
        COALESCE(
            NULLIF(dsi.label_mapping_version, ''),
            NULLIF(p.metadata->>'label_mapping_version', ''),
            NULLIF(er.explanation_parameters->>'label_mapping_version', ''),
            NULLIF(er.metadata->>'label_mapping_version', ''),
            NULLIF(r.parameters->>'label_mapping_version', '')
        ) AS label_mapping_version,
        r.run_name,
        r.run_type,
        r.status AS run_status,
        r.script_name,
        r.command,
        r.started_at,
        r.finished_at,
        er.created_at,
        p.created_at AS prediction_created_at,
        er.method,
        COALESCE(er.true_label, p.true_label) AS true_label,
        COALESCE(er.predicted_label, p.predicted_label) AS predicted_label,
        COALESCE(
            NULLIF(p.metadata->>'positive_label', ''),
            NULLIF(er.explanation_parameters->>'positive_label', ''),
            NULLIF(r.parameters->>'positive_label', ''),
            NULLIF(r.parameters->>'positive_class_name', ''),
            'parasitized'
        ) AS positive_label,
        COALESCE(NULLIF(er.case_type, ''), NULLIF(p.case_type, ''), 'unknown')
            AS recorded_case_type,
        COALESCE(p.score, er.score) AS score,
        COALESCE(
            CASE
                WHEN NULLIF(p.metadata->>'probability_parasitized', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (p.metadata->>'probability_parasitized')::NUMERIC
            END,
            p.score_positive_label,
            CASE
                WHEN NULLIF(er.metadata->>'probability_parasitized', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (er.metadata->>'probability_parasitized')::NUMERIC
            END,
            er.score
        ) AS probability_parasitized,
        COALESCE(
            CASE
                WHEN NULLIF(p.metadata->>'probability_uninfected', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (p.metadata->>'probability_uninfected')::NUMERIC
            END,
            CASE
                WHEN NULLIF(er.metadata->>'probability_uninfected', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (er.metadata->>'probability_uninfected')::NUMERIC
            END,
            CASE
                WHEN NULLIF(r.parameters->>'probability_uninfected', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (r.parameters->>'probability_uninfected')::NUMERIC
            END
        ) AS recorded_probability_uninfected,
        COALESCE(
            p.threshold,
            CASE
                WHEN NULLIF(er.explanation_parameters->>'threshold_used', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (er.explanation_parameters->>'threshold_used')::NUMERIC
            END,
            CASE
                WHEN NULLIF(er.explanation_parameters->>'threshold', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (er.explanation_parameters->>'threshold')::NUMERIC
            END,
            CASE
                WHEN NULLIF(r.parameters->>'threshold_used', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (r.parameters->>'threshold_used')::NUMERIC
            END,
            CASE
                WHEN NULLIF(r.parameters->>'threshold', '')
                    ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN (r.parameters->>'threshold')::NUMERIC
            END,
            rtc.threshold_selected,
            0.5
        ) AS threshold_used,
        COALESCE(
            NULLIF(p.metadata->>'threshold_source', ''),
            NULLIF(er.explanation_parameters->>'threshold_source', ''),
            NULLIF(er.metadata->>'threshold_source', ''),
            NULLIF(r.parameters->>'threshold_source', ''),
            NULLIF(r.metadata->>'threshold_source', ''),
            rtc.threshold_source,
            'fixed_cli'
        ) AS threshold_source,
        p.is_correct,
        p.image_id,
        COALESCE(
            NULLIF(er.image_path, ''),
            NULLIF(p.image_path, ''),
            NULLIF(p.metadata->>'crop_path', ''),
            NULLIF(er.metadata->>'crop_path', ''),
            NULLIF(dsi.absolute_path, ''),
            CASE
                WHEN dsi.dataset_dir IS NOT NULL AND dsi.relative_path IS NOT NULL
                THEN CONCAT(RTRIM(dsi.dataset_dir, '/'), '/', LTRIM(dsi.relative_path, '/'))
            END
        ) AS image_path,
        COALESCE(
            NULLIF(p.metadata->>'source_image_path', ''),
            NULLIF(er.metadata->>'source_image_path', ''),
            NULLIF(er.explanation_parameters->>'source_image_path', ''),
            NULLIF(dsi.absolute_path, ''),
            CASE
                WHEN dsi.dataset_dir IS NOT NULL AND dsi.relative_path IS NOT NULL
                THEN CONCAT(RTRIM(dsi.dataset_dir, '/'), '/', LTRIM(dsi.relative_path, '/'))
            END,
            NULLIF(p.image_path, ''),
            NULLIF(er.image_path, ''),
            NULLIF(sa.path, ''),
            NULLIF(p.metadata->>'original_image_path', ''),
            NULLIF(sa.metadata->>'original_image_path', '')
        ) AS source_image_path,
        COALESCE(
            NULLIF(p.metadata->>'original_image_path', ''),
            NULLIF(er.metadata->>'original_image_path', ''),
            NULLIF(sa.metadata->>'original_image_path', ''),
            NULLIF(dsi.absolute_path, '')
        ) AS original_image_path,
        COALESCE(
            NULLIF(p.metadata->>'original_filename', ''),
            NULLIF(er.metadata->>'original_filename', ''),
            NULLIF(sa.metadata->>'original_filename', ''),
            dsi.filename,
            sa.name
        ) AS original_filename,
        COALESCE(
            NULLIF(p.metadata->>'image_stored_path', ''),
            NULLIF(p.metadata->>'stored_image_path', ''),
            NULLIF(p.image_path, ''),
            NULLIF(sa.path, '')
        ) AS image_stored_path,
        COALESCE(
            NULLIF(p.metadata->>'crop_path', ''),
            NULLIF(er.metadata->>'crop_path', ''),
            NULLIF(er.explanation_parameters->>'crop_path', ''),
            NULLIF(p.image_path, ''),
            NULLIF(er.image_path, ''),
            NULLIF(dsi.absolute_path, ''),
            CASE
                WHEN dsi.dataset_dir IS NOT NULL AND dsi.relative_path IS NOT NULL
                THEN CONCAT(RTRIM(dsi.dataset_dir, '/'), '/', LTRIM(dsi.relative_path, '/'))
            END
        ) AS crop_path,
        COALESCE(
            NULLIF(p.metadata->>'source_image_id', ''),
            NULLIF(er.metadata->>'source_image_id', ''),
            NULLIF(er.explanation_parameters->>'source_image_id', ''),
            dsi.image_id::TEXT,
            CASE
                WHEN COALESCE(p.metadata->>'source', sa.metadata->>'source')
                    = 'uploaded_for_prediction'
                THEN NULLIF(p.image_id, '')
            END
        ) AS source_image_id,
        COALESCE(
            NULLIF(p.metadata->>'patient_id', ''),
            NULLIF(er.metadata->>'patient_id', ''),
            NULLIF(er.explanation_parameters->>'patient_id', '')
        ) AS patient_id,
        COALESCE(
            NULLIF(p.metadata->>'slide_id', ''),
            NULLIF(er.metadata->>'slide_id', ''),
            NULLIF(er.explanation_parameters->>'slide_id', '')
        ) AS slide_id,
        CASE
            WHEN COALESCE(
                NULLIF(p.metadata->>'bbox_x', ''),
                NULLIF(p.metadata #>> '{bbox,x}', ''),
                NULLIF(er.metadata->>'bbox_x', ''),
                NULLIF(er.explanation_parameters->>'bbox_x', '')
            ) ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
            THEN COALESCE(
                NULLIF(p.metadata->>'bbox_x', ''),
                NULLIF(p.metadata #>> '{bbox,x}', ''),
                NULLIF(er.metadata->>'bbox_x', ''),
                NULLIF(er.explanation_parameters->>'bbox_x', '')
            )::NUMERIC
        END AS bbox_x,
        CASE
            WHEN COALESCE(
                NULLIF(p.metadata->>'bbox_y', ''),
                NULLIF(p.metadata #>> '{bbox,y}', ''),
                NULLIF(er.metadata->>'bbox_y', ''),
                NULLIF(er.explanation_parameters->>'bbox_y', '')
            ) ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
            THEN COALESCE(
                NULLIF(p.metadata->>'bbox_y', ''),
                NULLIF(p.metadata #>> '{bbox,y}', ''),
                NULLIF(er.metadata->>'bbox_y', ''),
                NULLIF(er.explanation_parameters->>'bbox_y', '')
            )::NUMERIC
        END AS bbox_y,
        CASE
            WHEN COALESCE(
                NULLIF(p.metadata->>'bbox_width', ''),
                NULLIF(p.metadata #>> '{bbox,width}', ''),
                NULLIF(er.metadata->>'bbox_width', ''),
                NULLIF(er.explanation_parameters->>'bbox_width', '')
            ) ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
            THEN COALESCE(
                NULLIF(p.metadata->>'bbox_width', ''),
                NULLIF(p.metadata #>> '{bbox,width}', ''),
                NULLIF(er.metadata->>'bbox_width', ''),
                NULLIF(er.explanation_parameters->>'bbox_width', '')
            )::NUMERIC
        END AS bbox_width,
        CASE
            WHEN COALESCE(
                NULLIF(p.metadata->>'bbox_height', ''),
                NULLIF(p.metadata #>> '{bbox,height}', ''),
                NULLIF(er.metadata->>'bbox_height', ''),
                NULLIF(er.explanation_parameters->>'bbox_height', '')
            ) ~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
            THEN COALESCE(
                NULLIF(p.metadata->>'bbox_height', ''),
                NULLIF(p.metadata #>> '{bbox,height}', ''),
                NULLIF(er.metadata->>'bbox_height', ''),
                NULLIF(er.explanation_parameters->>'bbox_height', '')
            )::NUMERIC
        END AS bbox_height,
        COALESCE(
            NULLIF(p.metadata->>'prediction_upload_id', ''),
            NULLIF(er.metadata->>'prediction_upload_id', ''),
            NULLIF(sa.metadata->>'prediction_upload_id', ''),
            NULLIF(sa.metadata->>'image_id', ''),
            CASE
                WHEN COALESCE(p.metadata->>'source', sa.metadata->>'source')
                    = 'uploaded_for_prediction'
                THEN p.id::TEXT
            END
        ) AS prediction_upload_id,
        CASE
            WHEN COALESCE(p.metadata->>'source', sa.metadata->>'source')
                = 'uploaded_for_prediction'
            THEN COALESCE(sa.created_at, p.created_at)
        END AS uploaded_at,
        COALESCE(NULLIF(er.output_path, ''), NULLIF(ea.path, ''))
            AS explanation_output_path,
        er.last_conv_layer,
        er.success,
        er.error_message,
        COALESCE(er.explanation_parameters, '{}'::jsonb) AS explanation_parameters,
        COALESCE(p.metadata, '{}'::jsonb) AS prediction_metadata,
        COALESCE(er.metadata, '{}'::jsonb) AS explainability_metadata,
        COALESCE(rdi.metadata, '{}'::jsonb) AS source_usage_metadata,
        COALESCE(dsi.metadata, '{}'::jsonb) AS source_dataset_metadata,
        COALESCE(r.parameters, '{}'::jsonb) AS run_parameters,
        COALESCE(r.metadata, '{}'::jsonb) AS run_metadata,
        COALESCE(
            NULLIF(p.metadata->>'confidence_level', ''),
            NULLIF(er.metadata->>'confidence_level', ''),
            NULLIF(r.parameters->>'confidence_level', '')
        ) AS confidence_level,
        sa.id AS source_artifact_id,
        sa.path AS source_artifact_path,
        sa.artifact_type AS source_artifact_type,
        ea.id AS explanation_artifact_id,
        ea.path AS explanation_artifact_path,
        ea.artifact_type AS explanation_artifact_type
    FROM explainability_results er
    LEFT JOIN predictions p ON p.id = er.prediction_id
    LEFT JOIN runs r ON r.id = er.run_id
    LEFT JOIN models m ON m.id = r.model_id
    LEFT JOIN LATERAL (
        SELECT
            linked_rdi.*,
            linked_dsi.dataset_id,
            linked_dsi.dataset_name,
            linked_dsi.dataset_source,
            linked_dsi.dataset_dir,
            linked_dsi.absolute_path,
            linked_dsi.filename AS dataset_filename,
            linked_dsi.original_tfds_label,
            linked_dsi.project_label,
            linked_dsi.label_mapping_version,
            linked_dsi.metadata AS dataset_metadata
        FROM run_dataset_images linked_rdi
        JOIN dataset_split_images linked_dsi
          ON linked_dsi.image_id = linked_rdi.image_id
        WHERE linked_rdi.run_id = er.run_id
          AND (
              linked_rdi.image_id::TEXT = COALESCE(
                  NULLIF(p.metadata->>'dataset_image_id', ''),
                  NULLIF(p.metadata->>'registered_image_id', '')
              )
              OR linked_rdi.sample_index = CASE
                  WHEN COALESCE(
                      NULLIF(p.metadata->>'dataset_index', ''),
                      NULLIF(er.metadata->>'dataset_index', '')
                  ) ~ '^[0-9]+$'
                  THEN COALESCE(
                      NULLIF(p.metadata->>'dataset_index', ''),
                      NULLIF(er.metadata->>'dataset_index', '')
                  )::INTEGER
              END
              OR NULLIF(p.image_path, '') IN (
                  linked_dsi.absolute_path,
                  linked_dsi.relative_path,
                  CONCAT(
                      RTRIM(linked_dsi.dataset_dir, '/'),
                      '/',
                      LTRIM(linked_dsi.relative_path, '/')
                  )
              )
              OR NULLIF(er.image_path, '') IN (
                  linked_dsi.absolute_path,
                  linked_dsi.relative_path,
                  CONCAT(
                      RTRIM(linked_dsi.dataset_dir, '/'),
                      '/',
                      LTRIM(linked_dsi.relative_path, '/')
                  )
              )
          )
        ORDER BY
            (linked_rdi.usage_context = 'explainability') DESC,
            linked_rdi.created_at DESC
        LIMIT 1
    ) source_link ON TRUE
    LEFT JOIN run_dataset_images rdi
      ON rdi.run_dataset_image_id = source_link.run_dataset_image_id
    LEFT JOIN dataset_split_images dsi
      ON dsi.image_id = source_link.image_id
    LEFT JOIN datasets d
      ON d.id = COALESCE(dsi.dataset_id, p.dataset_id, r.dataset_id)
    LEFT JOIN LATERAL (
        SELECT threshold_selected, threshold_source
        FROM run_threshold_calibration calibration
        WHERE calibration.run_id = er.run_id
        ORDER BY calibration.created_at DESC
        LIMIT 1
    ) rtc ON TRUE
    LEFT JOIN LATERAL (
        SELECT source_artifact.*
        FROM artifacts source_artifact
        WHERE source_artifact.run_id = er.run_id
          AND (
              source_artifact.path = p.image_path
              OR source_artifact.path = er.image_path
              OR source_artifact.path = p.metadata->>'source_image_path'
              OR source_artifact.path = p.metadata->>'crop_path'
              OR source_artifact.artifact_type = 'uploaded_input_image'
          )
        ORDER BY
            (source_artifact.path = p.image_path) DESC,
            (source_artifact.path = er.image_path) DESC,
            (source_artifact.artifact_type = 'uploaded_input_image') DESC,
            source_artifact.created_at DESC
        LIMIT 1
    ) sa ON TRUE
    LEFT JOIN LATERAL (
        SELECT explanation_artifact.*
        FROM artifacts explanation_artifact
        WHERE explanation_artifact.run_id = er.run_id
          AND (
              explanation_artifact.path = er.output_path
              OR (
                  er.output_path IS NULL
                  AND explanation_artifact.artifact_type IN (
                      'gradcam_image',
                      'lime_image',
                      'shap_image'
                  )
                  AND explanation_artifact.artifact_type = CONCAT(LOWER(er.method), '_image')
              )
          )
        ORDER BY
            (explanation_artifact.path = er.output_path) DESC,
            explanation_artifact.created_at DESC
        LIMIT 1
    ) ea ON TRUE
), classified AS (
    SELECT
        audit_source.*,
        COALESCE(
            recorded_probability_uninfected,
            CASE
                WHEN probability_parasitized BETWEEN 0 AND 1
                THEN 1 - probability_parasitized
            END
        ) AS probability_uninfected,
        CASE
            WHEN recorded_case_type = 'low_confidence' THEN 'low_confidence'
            WHEN true_label IS NULL OR predicted_label IS NULL
                THEN recorded_case_type
            WHEN true_label = positive_label AND predicted_label = positive_label
                THEN 'true_positive'
            WHEN true_label <> positive_label AND predicted_label <> positive_label
                THEN 'true_negative'
            WHEN true_label <> positive_label AND predicted_label = positive_label
                THEN 'false_positive'
            WHEN true_label = positive_label AND predicted_label <> positive_label
                THEN 'false_negative'
            ELSE recorded_case_type
        END AS case_type
    FROM audit_source
), confidence AS (
    SELECT
        classified.*,
        CASE
            WHEN probability_parasitized IS NOT NULL AND threshold_used IS NOT NULL
            THEN ABS(probability_parasitized - threshold_used)
        END AS confidence_distance
    FROM classified
)
SELECT
    explainability_id,
    prediction_id,
    run_id,
    experiment_id,
    model_id,
    model_name,
    model_type,
    dataset_id,
    dataset_name,
    dataset_source,
    dataset_split,
    dataset_index,
    manifest_id,
    dataset_image_id,
    original_tfds_label,
    project_label,
    remapped_label,
    label_mapping_version,
    run_name,
    run_type,
    run_status,
    script_name,
    command,
    method,
    case_type,
    recorded_case_type,
    true_label,
    predicted_label,
    positive_label,
    score,
    probability_parasitized AS score_positive_label,
    probability_parasitized,
    probability_uninfected,
    threshold_used AS threshold,
    threshold_used,
    threshold_source,
    confidence_distance,
    confidence_level,
    CASE
        WHEN probability_parasitized IS NULL OR threshold_used IS NULL THEN 'unknown'
        WHEN case_type = 'low_confidence' OR confidence_distance <= 0.10
            THEN 'low_confidence'
        ELSE 'confident'
    END AS confidence_status,
    COALESCE(
        is_correct,
        CASE
            WHEN true_label IS NOT NULL AND predicted_label IS NOT NULL
            THEN true_label = predicted_label
        END
    ) AS is_correct,
    image_id,
    image_path,
    source_image_path,
    original_image_path,
    original_filename,
    image_stored_path,
    crop_path,
    source_image_id,
    patient_id,
    slide_id,
    bbox_x,
    bbox_y,
    bbox_width,
    bbox_height,
    prediction_upload_id,
    uploaded_at,
    explanation_output_path,
    explanation_output_path AS output_path,
    last_conv_layer,
    success,
    error_message,
    explanation_parameters,
    CASE case_type
        WHEN 'false_positive' THEN
            'La imagen estaba etiquetada como no parasitada, pero el modelo la clasificó como parasitada. Este caso debe revisarse como posible confusión visual, artefacto o umbral demasiado sensible.'
        WHEN 'false_negative' THEN
            'La imagen estaba etiquetada como parasitada, pero el modelo la clasificó como no parasitada. Este caso es crítico porque representa una célula parasitada no detectada por el modelo.'
        WHEN 'true_positive' THEN
            'La imagen estaba etiquetada como parasitada y el modelo también la clasificó como parasitada. La explicación visual permite revisar si la decisión se apoya en una región microscópica plausible.'
        WHEN 'true_negative' THEN
            'La imagen estaba etiquetada como no parasitada y el modelo también la clasificó como no parasitada.'
        WHEN 'low_confidence' THEN
            'La predicción está cercana al umbral de decisión. Este caso debe priorizarse para revisión humana.'
        ELSE
            'No hay información suficiente para generar una interpretación automática del caso.'
    END AS interpretation,
    'Uso experimental; no sustituye la revisión de un profesional de salud.'::TEXT
        AS disclaimer,
    source_artifact_id,
    source_artifact_path,
    source_artifact_type,
    explanation_artifact_id AS artifact_id,
    COALESCE(explanation_artifact_path, explanation_output_path) AS artifact_path,
    explanation_artifact_type AS artifact_type,
    explanation_artifact_id,
    explanation_artifact_path,
    explanation_artifact_type,
    prediction_metadata,
    explainability_metadata,
    source_usage_metadata,
    source_dataset_metadata,
    run_parameters,
    run_metadata,
    started_at,
    finished_at,
    prediction_created_at,
    created_at
FROM confidence;

COMMENT ON VIEW vw_visual_explainability_audit IS
    'Contrato de lectura null-safe para auditar fuente/crop, predicción, umbral y explicación visual por caso.';
