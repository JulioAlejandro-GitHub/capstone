"""Add the scientific dataset versioning foundation.

Revision ID: 20260811_01
Revises: 20260810_05
"""

from alembic import op


revision = "20260811_01"
down_revision = "20260810_05"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE datasets
          ADD COLUMN provider TEXT,
          ADD COLUMN source_type TEXT,
          ADD COLUMN source_reference TEXT,
          ADD COLUMN source_version TEXT;

        CREATE TABLE dataset_versions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          semantic_version TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'DRAFT',
          grouping_strategy TEXT NOT NULL,
          grouping_field TEXT NOT NULL,
          stratification_strategy TEXT NOT NULL,
          split_algorithm TEXT NOT NULL,
          split_algorithm_version TEXT NOT NULL,
          random_seed INTEGER NOT NULL,
          target_train_ratio NUMERIC(8,7) NOT NULL,
          target_val_ratio NUMERIC(8,7) NOT NULL,
          target_test_ratio NUMERIC(8,7) NOT NULL,
          positive_class TEXT NOT NULL,
          class_mapping JSONB NOT NULL DEFAULT '{}'::jsonb,
          source_record_count BIGINT NOT NULL DEFAULT 0,
          methodology_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          generated_at TIMESTAMPTZ,
          validated_at TIMESTAMPTZ,
          frozen_at TIMESTAMPTZ,
          archived_at TIMESTAMPTZ,
          CONSTRAINT uq_dataset_versions_name_semver UNIQUE (name, semantic_version),
          CONSTRAINT chk_dataset_versions_status CHECK (
            status IN ('DRAFT','GENERATED','VALIDATED','FROZEN','ARCHIVED')
          ),
          CONSTRAINT chk_dataset_versions_train_ratio CHECK (
            target_train_ratio BETWEEN 0 AND 1
          ),
          CONSTRAINT chk_dataset_versions_val_ratio CHECK (
            target_val_ratio BETWEEN 0 AND 1
          ),
          CONSTRAINT chk_dataset_versions_test_ratio CHECK (
            target_test_ratio BETWEEN 0 AND 1
          ),
          CONSTRAINT chk_dataset_versions_ratio_sum CHECK (
            target_train_ratio + target_val_ratio + target_test_ratio = 1.0
          ),
          CONSTRAINT chk_dataset_versions_source_count CHECK (source_record_count >= 0),
          CONSTRAINT chk_dataset_versions_class_mapping_object CHECK (
            jsonb_typeof(class_mapping) = 'object'
          ),
          CONSTRAINT chk_dataset_versions_methodology_object CHECK (
            jsonb_typeof(methodology_json) = 'object'
          )
        );
        CREATE INDEX ix_dataset_versions_status ON dataset_versions(status);

        CREATE TABLE dataset_version_sources (
          dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
          role TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (dataset_version_id, dataset_id, role),
          CONSTRAINT chk_dataset_version_sources_role CHECK (
            role IN ('PRIMARY','EXTERNAL_VALIDATION','AUXILIARY')
          )
        );
        CREATE INDEX ix_dataset_version_sources_dataset_id
          ON dataset_version_sources(dataset_id);

        CREATE TABLE clinical_identities (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
          identity_type TEXT NOT NULL,
          source_identifier TEXT NOT NULL,
          status TEXT NOT NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_clinical_identities_source UNIQUE (
            dataset_id, identity_type, source_identifier
          ),
          CONSTRAINT chk_clinical_identities_type CHECK (identity_type IN ('PATIENT')),
          CONSTRAINT chk_clinical_identities_status CHECK (
            status IN ('VERIFIED','UNRESOLVED','CONFLICT')
          ),
          CONSTRAINT chk_clinical_identities_metadata_object CHECK (
            jsonb_typeof(metadata) = 'object'
          )
        );

        CREATE TABLE dataset_source_records (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
          clinical_identity_id UUID REFERENCES clinical_identities(id) ON DELETE RESTRICT,
          source_record_key TEXT NOT NULL,
          tfds_index BIGINT,
          source_filename TEXT,
          class_index INTEGER NOT NULL,
          class_name TEXT NOT NULL,
          original_label INTEGER,
          project_label INTEGER,
          relative_source_key TEXT,
          source_file_sha256 TEXT,
          decoded_pixel_sha256 TEXT,
          image_width INTEGER,
          image_height INTEGER,
          file_size_bytes BIGINT,
          identity_status TEXT NOT NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_dataset_source_records_key UNIQUE (dataset_id, source_record_key),
          CONSTRAINT chk_dataset_source_records_identity_status CHECK (
            identity_status IN ('VERIFIED','UNRESOLVED','CONFLICT')
          ),
          CONSTRAINT chk_dataset_source_records_source_sha256 CHECK (
            source_file_sha256 IS NULL OR source_file_sha256 ~ '^[0-9a-fA-F]{64}$'
          ),
          CONSTRAINT chk_dataset_source_records_pixel_sha256 CHECK (
            decoded_pixel_sha256 IS NULL OR decoded_pixel_sha256 ~ '^[0-9a-fA-F]{64}$'
          ),
          CONSTRAINT chk_dataset_source_records_dimensions CHECK (
            (image_width IS NULL OR image_width > 0)
            AND (image_height IS NULL OR image_height > 0)
            AND (file_size_bytes IS NULL OR file_size_bytes >= 0)
          ),
          CONSTRAINT chk_dataset_source_records_metadata_object CHECK (
            jsonb_typeof(metadata) = 'object'
          )
        );
        CREATE INDEX ix_dataset_source_records_dataset_id
          ON dataset_source_records(dataset_id);
        CREATE INDEX ix_dataset_source_records_clinical_identity_id
          ON dataset_source_records(clinical_identity_id);
        CREATE INDEX ix_dataset_source_records_source_file_sha256
          ON dataset_source_records(source_file_sha256)
          WHERE source_file_sha256 IS NOT NULL;
        CREATE INDEX ix_dataset_source_records_decoded_pixel_sha256
          ON dataset_source_records(decoded_pixel_sha256)
          WHERE decoded_pixel_sha256 IS NOT NULL;

        CREATE TABLE identity_evidence (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_record_id UUID NOT NULL REFERENCES dataset_source_records(id) ON DELETE RESTRICT,
          clinical_identity_id UUID NOT NULL REFERENCES clinical_identities(id) ON DELETE RESTRICT,
          evidence_type TEXT NOT NULL,
          evidence_level TEXT NOT NULL,
          mapping_method TEXT NOT NULL,
          evidence_reference TEXT,
          official_source_reference TEXT,
          evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT chk_identity_evidence_json_object CHECK (
            jsonb_typeof(evidence_json) = 'object'
          )
        );
        CREATE INDEX ix_identity_evidence_source_record_id
          ON identity_evidence(source_record_id);
        CREATE INDEX ix_identity_evidence_clinical_identity_id
          ON identity_evidence(clinical_identity_id);

        CREATE TABLE dataset_split_assignments (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          source_record_id UUID NOT NULL REFERENCES dataset_source_records(id) ON DELETE RESTRICT,
          clinical_identity_id UUID NOT NULL REFERENCES clinical_identities(id) ON DELETE RESTRICT,
          split_name TEXT NOT NULL,
          class_index INTEGER NOT NULL,
          class_name TEXT NOT NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_dataset_split_assignments_record UNIQUE (
            dataset_version_id, source_record_id
          ),
          CONSTRAINT chk_dataset_split_assignments_split CHECK (
            split_name IN ('train','val','test','external_validation')
          ),
          CONSTRAINT chk_dataset_split_assignments_metadata_object CHECK (
            jsonb_typeof(metadata) = 'object'
          )
        );
        CREATE INDEX ix_dataset_split_assignments_dataset_version_id
          ON dataset_split_assignments(dataset_version_id);
        CREATE INDEX ix_dataset_split_assignments_clinical_identity_id
          ON dataset_split_assignments(clinical_identity_id);

        CREATE TABLE dataset_split_statistics (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          scope TEXT NOT NULL,
          metric_name TEXT NOT NULL,
          numeric_value NUMERIC,
          text_value TEXT,
          details_json JSONB,
          computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT chk_dataset_split_statistics_value CHECK (
            numeric_value IS NOT NULL OR text_value IS NOT NULL OR details_json IS NOT NULL
          ),
          CONSTRAINT chk_dataset_split_statistics_details_object CHECK (
            details_json IS NULL OR jsonb_typeof(details_json) = 'object'
          )
        );
        CREATE INDEX ix_dataset_split_statistics_version_metric
          ON dataset_split_statistics(dataset_version_id, scope, metric_name);

        CREATE TABLE dataset_split_validation_checks (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          check_name TEXT NOT NULL,
          status TEXT NOT NULL,
          observed_value TEXT,
          expected_value TEXT,
          details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          blocking_for_validation BOOLEAN NOT NULL DEFAULT false,
          blocking_for_freeze BOOLEAN NOT NULL DEFAULT false,
          executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT chk_dataset_split_validation_checks_status CHECK (
            status IN ('PASS','FAIL','WARNING')
          ),
          CONSTRAINT chk_dataset_split_validation_checks_details_object CHECK (
            jsonb_typeof(details_json) = 'object'
          )
        );
        CREATE INDEX ix_dataset_split_validation_checks_version_name
          ON dataset_split_validation_checks(dataset_version_id, check_name, executed_at);

        CREATE TABLE dataset_materializations (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          attempt_number INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'NOT_MATERIALIZED',
          reconciliation_status TEXT NOT NULL DEFAULT 'PENDING',
          relative_root TEXT NOT NULL,
          record_count BIGINT NOT NULL DEFAULT 0,
          manifest_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          started_at TIMESTAMPTZ,
          completed_at TIMESTAMPTZ,
          failure_reason TEXT,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_dataset_materializations_attempt UNIQUE (
            dataset_version_id, attempt_number
          ),
          CONSTRAINT chk_dataset_materializations_attempt CHECK (attempt_number > 0),
          CONSTRAINT chk_dataset_materializations_status CHECK (
            status IN ('NOT_MATERIALIZED','MATERIALIZING','READY','FAILED')
          ),
          CONSTRAINT chk_dataset_materializations_reconciliation CHECK (
            reconciliation_status IN ('PENDING','PASS','FAIL')
          ),
          CONSTRAINT chk_dataset_materializations_record_count CHECK (record_count >= 0),
          CONSTRAINT chk_dataset_materializations_relative_root CHECK (
            relative_root <> '' AND relative_root !~ '^/'
          ),
          CONSTRAINT chk_dataset_materializations_manifest_object CHECK (
            jsonb_typeof(manifest_metadata) = 'object'
          ),
          CONSTRAINT chk_dataset_materializations_metadata_object CHECK (
            jsonb_typeof(metadata) = 'object'
          )
        );
        CREATE INDEX ix_dataset_materializations_dataset_version_id
          ON dataset_materializations(dataset_version_id);

        CREATE TABLE dataset_materialization_activations (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          materialization_id UUID NOT NULL REFERENCES dataset_materializations(id) ON DELETE RESTRICT,
          dataset_family TEXT NOT NULL,
          activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          deactivated_at TIMESTAMPTZ,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          CONSTRAINT chk_dataset_materialization_activations_interval CHECK (
            deactivated_at IS NULL OR deactivated_at >= activated_at
          ),
          CONSTRAINT chk_dataset_materialization_activations_metadata_object CHECK (
            jsonb_typeof(metadata) = 'object'
          )
        );
        CREATE INDEX ix_dataset_materialization_activations_dataset_version_id
          ON dataset_materialization_activations(dataset_version_id);
        CREATE INDEX ix_dataset_materialization_activations_materialization_id
          ON dataset_materialization_activations(materialization_id);
        CREATE UNIQUE INDEX uq_dataset_materialization_activations_current_family
          ON dataset_materialization_activations(dataset_family)
          WHERE deactivated_at IS NULL;

        ALTER TABLE dataset_split_images
          ADD COLUMN dataset_version_id UUID REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          ADD COLUMN dataset_materialization_id UUID REFERENCES dataset_materializations(id) ON DELETE RESTRICT;
        CREATE INDEX ix_dataset_split_images_dataset_version_id
          ON dataset_split_images(dataset_version_id);
        CREATE INDEX ix_dataset_split_images_dataset_materialization_id
          ON dataset_split_images(dataset_materialization_id);

        ALTER TABLE runs
          ADD COLUMN dataset_version_id UUID REFERENCES dataset_versions(id) ON DELETE RESTRICT;
        CREATE INDEX ix_runs_dataset_version_id ON runs(dataset_version_id);

        ALTER TABLE run_io_records
          ADD COLUMN dataset_version_id UUID REFERENCES dataset_versions(id) ON DELETE RESTRICT,
          ADD COLUMN dataset_materialization_id UUID REFERENCES dataset_materializations(id) ON DELETE RESTRICT;
        CREATE INDEX ix_run_io_records_dataset_version_id
          ON run_io_records(dataset_version_id);
        CREATE INDEX ix_run_io_records_dataset_materialization_id
          ON run_io_records(dataset_materialization_id);
        """
    )


def downgrade():
    raise RuntimeError(
        "Downgrade is intentionally prohibited for scientific lineage migrations"
    )
