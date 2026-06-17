CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    project_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source TEXT,
    version TEXT,
    description TEXT,
    total_images INTEGER,
    num_classes INTEGER,
    class_names TEXT[],
    class_distribution JSONB DEFAULT '{}'::jsonb,
    license TEXT,
    url TEXT,
    local_path TEXT,
    checksum TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS dataset_splits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    split_name TEXT NOT NULL,
    num_samples INTEGER,
    class_distribution JSONB DEFAULT '{}'::jsonb,
    split_strategy TEXT,
    random_seed INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    model_type TEXT NOT NULL,
    framework TEXT,
    architecture TEXT,
    description TEXT,
    input_shape TEXT,
    output_shape TEXT,
    num_parameters BIGINT,
    pretrained BOOLEAN DEFAULT FALSE,
    pretrained_source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE SET NULL,
    model_id UUID REFERENCES models(id) ON DELETE SET NULL,
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    run_name TEXT,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    command TEXT,
    script_name TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_seconds NUMERIC,
    user_name TEXT,
    host_name TEXT,
    working_directory TEXT,
    git_commit TEXT,
    git_branch TEXT,
    python_version TEXT,
    tensorflow_version TEXT,
    keras_version TEXT,
    platform TEXT,
    machine TEXT,
    processor TEXT,
    gpu_available BOOLEAN,
    gpu_devices JSONB DEFAULT '[]'::jsonb,
    random_seed INTEGER,
    parameters JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES models(id) ON DELETE CASCADE,
    version_name TEXT,
    checkpoint_path TEXT,
    final_model_path TEXT,
    best_model_path TEXT,
    training_run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS run_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    split_name TEXT,
    class_name TEXT,
    step INTEGER,
    epoch INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS training_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    epoch INTEGER NOT NULL,
    loss NUMERIC,
    accuracy NUMERIC,
    precision_value NUMERIC,
    recall_value NUMERIC,
    auc NUMERIC,
    val_loss NUMERIC,
    val_accuracy NUMERIC,
    val_precision NUMERIC,
    val_recall NUMERIC,
    val_auc NUMERIC,
    learning_rate NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS confusion_matrices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    split_name TEXT,
    labels TEXT[],
    matrix JSONB NOT NULL,
    true_positive INTEGER,
    true_negative INTEGER,
    false_positive INTEGER,
    false_negative INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS classification_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    split_name TEXT,
    class_name TEXT,
    precision_value NUMERIC,
    recall_value NUMERIC,
    f1_score NUMERIC,
    support INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    image_id TEXT,
    image_path TEXT,
    true_label TEXT,
    predicted_label TEXT,
    score NUMERIC,
    score_positive_label NUMERIC,
    threshold NUMERIC,
    is_correct BOOLEAN,
    case_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    name TEXT,
    path TEXT NOT NULL,
    mime_type TEXT,
    file_size_bytes BIGINT,
    checksum TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS explainability_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    prediction_id UUID REFERENCES predictions(id) ON DELETE SET NULL,
    method TEXT NOT NULL,
    image_path TEXT,
    output_path TEXT,
    true_label TEXT,
    predicted_label TEXT,
    score NUMERIC,
    case_type TEXT,
    last_conv_layer TEXT,
    explanation_parameters JSONB DEFAULT '{}'::jsonb,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    log_level TEXT,
    message TEXT,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    script_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS environment_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    package_name TEXT NOT NULL,
    package_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS synthetic_data_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    method TEXT,
    num_images_generated INTEGER,
    source_dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    output_path TEXT,
    generation_parameters JSONB DEFAULT '{}'::jsonb,
    quality_checks JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
