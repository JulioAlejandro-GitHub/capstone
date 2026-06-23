CREATE TABLE IF NOT EXISTS dataset_split_images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    dataset_name TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    dataset_dir TEXT NOT NULL,
    split_name TEXT NOT NULL,
    class_index INTEGER NOT NULL,
    class_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    absolute_path TEXT,
    filename TEXT NOT NULL,
    original_tfds_label INTEGER,
    project_label INTEGER NOT NULL,
    label_mapping_version TEXT NOT NULL,
    image_width INTEGER,
    image_height INTEGER,
    file_size_bytes BIGINT,
    checksum_sha256 TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_dataset_split_images_split
        CHECK (split_name IN ('train', 'val', 'validation', 'test')),
    CONSTRAINT chk_dataset_split_images_class_index
        CHECK (class_index IN (0, 1)),
    CONSTRAINT chk_dataset_split_images_class_name
        CHECK (class_name IN ('uninfected', 'parasitized')),
    CONSTRAINT uq_dataset_split_images_path UNIQUE (dataset_dir, relative_path)
);

CREATE TABLE IF NOT EXISTS run_dataset_images (
    run_dataset_image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES dataset_split_images(image_id) ON DELETE CASCADE,
    split_name TEXT NOT NULL,
    usage_context TEXT NOT NULL,
    class_index INTEGER NOT NULL,
    class_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    batch_index INTEGER,
    sample_index INTEGER,
    used_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    used_for_validation BOOLEAN NOT NULL DEFAULT FALSE,
    used_for_test BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_run_dataset_images_usage_context
        CHECK (
            usage_context IN (
                'train',
                'validation',
                'evaluation',
                'explainability',
                'tta',
                'ensemble',
                'svm_features',
                'inference'
            )
        ),
    CONSTRAINT chk_run_dataset_images_split
        CHECK (split_name IN ('train', 'val', 'validation', 'test')),
    CONSTRAINT chk_run_dataset_images_class_index
        CHECK (class_index IN (0, 1)),
    CONSTRAINT chk_run_dataset_images_class_name
        CHECK (class_name IN ('uninfected', 'parasitized')),
    CONSTRAINT uq_run_dataset_images_usage
        UNIQUE (run_id, image_id, usage_context)
);

CREATE TABLE IF NOT EXISTS run_io_records (
    run_io_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    script_name TEXT NOT NULL,
    command TEXT,
    input_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_results JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    dataset_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    label_mapping_version TEXT NOT NULL,
    raw_model_score_meaning TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_dataset_split_images_split
    ON dataset_split_images(split_name);
CREATE INDEX IF NOT EXISTS idx_dataset_split_images_class
    ON dataset_split_images(class_name);
CREATE INDEX IF NOT EXISTS idx_dataset_split_images_dataset_dir
    ON dataset_split_images(dataset_dir);
CREATE INDEX IF NOT EXISTS idx_dataset_split_images_relative_path
    ON dataset_split_images(relative_path);
CREATE INDEX IF NOT EXISTS idx_dataset_split_images_dataset_id
    ON dataset_split_images(dataset_id);

CREATE INDEX IF NOT EXISTS idx_run_dataset_images_run_id
    ON run_dataset_images(run_id);
CREATE INDEX IF NOT EXISTS idx_run_dataset_images_image_id
    ON run_dataset_images(image_id);
CREATE INDEX IF NOT EXISTS idx_run_dataset_images_split
    ON run_dataset_images(split_name);
CREATE INDEX IF NOT EXISTS idx_run_dataset_images_usage_context
    ON run_dataset_images(usage_context);

CREATE INDEX IF NOT EXISTS idx_run_io_records_run_id
    ON run_io_records(run_id);
CREATE INDEX IF NOT EXISTS idx_run_io_records_script_name
    ON run_io_records(script_name);
CREATE INDEX IF NOT EXISTS idx_run_io_records_created_at
    ON run_io_records(created_at);

DROP VIEW IF EXISTS vw_run_io_summary CASCADE;
DROP VIEW IF EXISTS vw_run_dataset_usage_summary CASCADE;
DROP VIEW IF EXISTS vw_dataset_split_images_summary CASCADE;

CREATE VIEW vw_dataset_split_images_summary AS
SELECT
    dataset_name,
    dataset_source,
    dataset_dir,
    CASE WHEN split_name = 'val' THEN 'validation' ELSE split_name END AS display_split_name,
    split_name,
    class_name,
    class_index,
    COUNT(*) AS image_count,
    SUM(file_size_bytes) AS total_file_size_bytes,
    MIN(created_at) AS first_registered_at,
    MAX(updated_at) AS last_updated_at
FROM dataset_split_images
GROUP BY
    dataset_name,
    dataset_source,
    dataset_dir,
    split_name,
    class_name,
    class_index;

CREATE VIEW vw_run_dataset_usage_summary AS
SELECT
    rdi.run_id,
    r.script_name,
    m.name AS model_name,
    r.run_type,
    dsi.dataset_name,
    dsi.dataset_source,
    dsi.dataset_dir,
    COUNT(*) FILTER (WHERE rdi.split_name = 'train') AS train_images_count,
    COUNT(*) FILTER (WHERE rdi.split_name IN ('val', 'validation')) AS val_images_count,
    COUNT(*) FILTER (WHERE rdi.split_name = 'test') AS test_images_count,
    COUNT(*) FILTER (WHERE rdi.class_name = 'uninfected') AS uninfected_count,
    COUNT(*) FILTER (WHERE rdi.class_name = 'parasitized') AS parasitized_count,
    COUNT(*) FILTER (WHERE rdi.usage_context = 'explainability') AS explained_images_count,
    MIN(rdi.created_at) AS created_at,
    MAX(rdi.created_at) AS last_recorded_at
FROM run_dataset_images rdi
JOIN runs r ON r.id = rdi.run_id
LEFT JOIN models m ON m.id = r.model_id
JOIN dataset_split_images dsi ON dsi.image_id = rdi.image_id
GROUP BY
    rdi.run_id,
    r.script_name,
    m.name,
    r.run_type,
    dsi.dataset_name,
    dsi.dataset_source,
    dsi.dataset_dir;

CREATE VIEW vw_run_io_summary AS
SELECT
    rio.run_io_id,
    rio.run_id,
    r.run_name,
    r.run_type,
    r.status AS run_status,
    m.name AS model_name,
    rio.script_name,
    COALESCE(rio.command, r.command) AS command,
    rio.input_parameters,
    rio.output_results,
    rio.output_artifacts,
    rio.dataset_metadata,
    rio.label_mapping_version,
    rio.raw_model_score_meaning,
    rio.created_at,
    rio.metadata
FROM run_io_records rio
LEFT JOIN runs r ON r.id = rio.run_id
LEFT JOIN models m ON m.id = r.model_id;
