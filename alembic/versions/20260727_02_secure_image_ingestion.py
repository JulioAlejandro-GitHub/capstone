"""Secure patient/sample microscopy image ingestion."""

from alembic import op


revision = "20260727_02"
down_revision = "20260727_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      ALTER TABLE research_subjects
        ADD COLUMN source_system VARCHAR(120),
        ADD COLUMN external_patient_id VARCHAR(240);
      CREATE UNIQUE INDEX uq_research_subjects_external_identity
        ON research_subjects(source_system, external_patient_id)
        WHERE external_patient_id IS NOT NULL;

      ALTER TABLE blood_samples
        ADD COLUMN source_system VARCHAR(120),
        ADD COLUMN external_sample_id VARCHAR(240),
        ADD COLUMN sample_identity_origin VARCHAR(40) NOT NULL DEFAULT 'generated_by_capstone',
        ADD COLUMN source_group_key VARCHAR(240),
        ADD COLUMN ingestion_status VARCHAR(20),
        ADD COLUMN expected_image_count INTEGER,
        ADD CONSTRAINT ck_blood_samples_identity_origin CHECK (
          sample_identity_origin IN ('external_system','generated_by_capstone','derived_import_profile')
        ),
        ADD CONSTRAINT ck_blood_samples_ingestion_status CHECK (
          ingestion_status IS NULL OR ingestion_status IN ('pending','incomplete','complete','inconsistent','rejected')
        ),
        ADD CONSTRAINT ck_blood_samples_expected_count CHECK (
          expected_image_count IS NULL OR expected_image_count > 0
        );
      CREATE UNIQUE INDEX uq_blood_samples_external_identity
        ON blood_samples(case_id, source_system, external_sample_id)
        WHERE external_sample_id IS NOT NULL;

      CREATE TABLE image_ingestion_batches (
        id UUID PRIMARY KEY,
        subject_id UUID NOT NULL REFERENCES research_subjects(id) ON DELETE RESTRICT,
        case_id UUID NOT NULL REFERENCES scientific_cases(id) ON DELETE RESTRICT,
        sample_id UUID NOT NULL REFERENCES blood_samples(id) ON DELETE RESTRICT,
        slide_id UUID NOT NULL REFERENCES smear_slides(id) ON DELETE RESTRICT,
        acquisition_origin VARCHAR(40) NOT NULL CHECK (
          acquisition_origin IN ('manual_upload','research_dataset_import','external_capture_system')
        ),
        source_system VARCHAR(120),
        source_group_key VARCHAR(240),
        expected_image_count INTEGER CHECK (expected_image_count IS NULL OR expected_image_count > 0),
        received_image_count INTEGER NOT NULL DEFAULT 0 CHECK (received_image_count >= 0),
        status VARCHAR(20) NOT NULL DEFAULT 'pending'
          CHECK (status IN ('pending','incomplete','complete','inconsistent','failed')),
        created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        completed_at TIMESTAMPTZ,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
          CHECK (jsonb_typeof(metadata_json) = 'object')
      );
      CREATE UNIQUE INDEX uq_ingestion_batches_source_group
        ON image_ingestion_batches(source_system, source_group_key)
        WHERE source_system IS NOT NULL AND source_group_key IS NOT NULL;
      CREATE INDEX ix_ingestion_batches_sample ON image_ingestion_batches(sample_id, created_at DESC);

      ALTER TABLE microscopy_images
        ADD COLUMN acquisition_origin VARCHAR(40) NOT NULL DEFAULT 'manual_upload',
        ADD COLUMN source_system VARCHAR(120),
        ADD COLUMN source_component_id VARCHAR(240),
        ADD COLUMN source_image_name VARCHAR(500),
        ADD COLUMN source_relative_path TEXT,
        ADD COLUMN image_sequence_number INTEGER,
        ADD COLUMN detected_format VARCHAR(20),
        ADD COLUMN channel_count INTEGER,
        ADD COLUMN color_space VARCHAR(80),
        ADD COLUMN orientation VARCHAR(80),
        ADD COLUMN ingestion_batch_id UUID REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT,
        ADD CONSTRAINT ck_microscopy_images_acquisition_origin CHECK (
          acquisition_origin IN ('manual_upload','research_dataset_import','external_capture_system')
        ),
        ADD CONSTRAINT ck_microscopy_images_sequence CHECK (
          image_sequence_number IS NULL OR image_sequence_number > 0
        ),
        ADD CONSTRAINT ck_microscopy_images_channels CHECK (
          channel_count IS NULL OR channel_count > 0
        );
      CREATE UNIQUE INDEX uq_microscopy_images_external_path
        ON microscopy_images(source_system, source_relative_path)
        WHERE source_system IS NOT NULL AND source_relative_path IS NOT NULL;
      CREATE INDEX ix_microscopy_images_ingestion_batch ON microscopy_images(ingestion_batch_id);
    """)


def downgrade():
    op.execute("""
      DROP INDEX ix_microscopy_images_ingestion_batch;
      DROP INDEX uq_microscopy_images_external_path;
      ALTER TABLE microscopy_images
        DROP COLUMN ingestion_batch_id, DROP COLUMN orientation, DROP COLUMN color_space,
        DROP COLUMN channel_count, DROP COLUMN detected_format, DROP COLUMN image_sequence_number,
        DROP COLUMN source_relative_path, DROP COLUMN source_image_name, DROP COLUMN source_component_id,
        DROP COLUMN source_system, DROP COLUMN acquisition_origin;
      DROP TABLE image_ingestion_batches;
      DROP INDEX uq_blood_samples_external_identity;
      ALTER TABLE blood_samples
        DROP COLUMN expected_image_count, DROP COLUMN ingestion_status, DROP COLUMN source_group_key,
        DROP COLUMN sample_identity_origin, DROP COLUMN external_sample_id, DROP COLUMN source_system;
      DROP INDEX uq_research_subjects_external_identity;
      ALTER TABLE research_subjects DROP COLUMN external_patient_id, DROP COLUMN source_system;
    """)
