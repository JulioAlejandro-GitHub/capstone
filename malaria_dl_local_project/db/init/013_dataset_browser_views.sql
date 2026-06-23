DROP VIEW IF EXISTS vw_dataset_browser_images CASCADE;
DROP VIEW IF EXISTS vw_dataset_browser_summary CASCADE;

CREATE VIEW vw_dataset_browser_summary AS
SELECT
    dsi.dataset_id,
    dsi.dataset_name,
    dsi.dataset_source,
    COALESCE(d.url, d.metadata->>'source_url') AS source_url,
    COALESCE(d.description, d.metadata->>'description') AS description,
    dsi.dataset_dir,
    COALESCE(
        d.metadata->>'split_type',
        dsi.metadata->>'split_type',
        'physical_stratified_split'
    ) AS split_type,
    NULLIF(COALESCE(d.metadata->>'train_ratio', dsi.metadata->>'train_ratio'), '')::NUMERIC
        AS train_ratio,
    NULLIF(COALESCE(d.metadata->>'val_ratio', dsi.metadata->>'val_ratio'), '')::NUMERIC
        AS val_ratio,
    NULLIF(COALESCE(d.metadata->>'test_ratio', dsi.metadata->>'test_ratio'), '')::NUMERIC
        AS test_ratio,
    NULLIF(COALESCE(d.metadata->>'seed', dsi.metadata->>'seed'), '')::INTEGER
        AS seed,
    dsi.label_mapping_version,
    dsi.split_name,
    CASE WHEN dsi.split_name = 'val' THEN 'validation' ELSE dsi.split_name END
        AS display_split_name,
    dsi.class_name,
    dsi.class_index,
    COUNT(*) AS image_count,
    MIN(dsi.created_at) AS first_registered_at,
    MAX(dsi.updated_at) AS last_updated_at,
    COALESCE(d.metadata, '{}'::jsonb) AS dataset_metadata
FROM dataset_split_images dsi
LEFT JOIN datasets d ON d.id = dsi.dataset_id
GROUP BY
    dsi.dataset_id,
    dsi.dataset_name,
    dsi.dataset_source,
    COALESCE(d.url, d.metadata->>'source_url'),
    COALESCE(d.description, d.metadata->>'description'),
    dsi.dataset_dir,
    COALESCE(
        d.metadata->>'split_type',
        dsi.metadata->>'split_type',
        'physical_stratified_split'
    ),
    NULLIF(COALESCE(d.metadata->>'train_ratio', dsi.metadata->>'train_ratio'), '')::NUMERIC,
    NULLIF(COALESCE(d.metadata->>'val_ratio', dsi.metadata->>'val_ratio'), '')::NUMERIC,
    NULLIF(COALESCE(d.metadata->>'test_ratio', dsi.metadata->>'test_ratio'), '')::NUMERIC,
    NULLIF(COALESCE(d.metadata->>'seed', dsi.metadata->>'seed'), '')::INTEGER,
    dsi.label_mapping_version,
    dsi.split_name,
    dsi.class_name,
    dsi.class_index,
    COALESCE(d.metadata, '{}'::jsonb);

CREATE VIEW vw_dataset_browser_images AS
SELECT
    dsi.image_id,
    dsi.dataset_id,
    dsi.dataset_name,
    dsi.dataset_source,
    COALESCE(d.url, d.metadata->>'source_url') AS source_url,
    dsi.dataset_dir,
    dsi.split_name,
    CASE WHEN dsi.split_name = 'val' THEN 'validation' ELSE dsi.split_name END
        AS display_split_name,
    dsi.class_name,
    dsi.class_index,
    dsi.relative_path,
    dsi.absolute_path,
    dsi.filename,
    dsi.original_tfds_label,
    dsi.project_label,
    dsi.image_width,
    dsi.image_height,
    dsi.file_size_bytes,
    dsi.checksum_sha256,
    dsi.label_mapping_version,
    dsi.created_at,
    dsi.updated_at,
    dsi.metadata
FROM dataset_split_images dsi
LEFT JOIN datasets d ON d.id = dsi.dataset_id;
