"""Scientific case, sample, slide, and microscopy image foundation."""

from alembic import op


revision = "20260727_01"
down_revision = "20260726_02"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      CREATE TABLE research_subjects (
        id UUID PRIMARY KEY,
        subject_code VARCHAR(120) NOT NULL UNIQUE CHECK (btrim(subject_code) <> ''),
        study_reference VARCHAR(200),
        age_group VARCHAR(80),
        biological_sex VARCHAR(80),
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
          CHECK (jsonb_typeof(metadata_json) = 'object'),
        status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        archived_at TIMESTAMPTZ,
        archived_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        CONSTRAINT ck_research_subject_archive_state CHECK (
          (status = 'active' AND archived_at IS NULL AND archived_by IS NULL) OR
          (status = 'archived' AND archived_at IS NOT NULL)
        )
      );
      CREATE INDEX ix_research_subjects_status_created
        ON research_subjects(status, created_at DESC);

      CREATE TABLE scientific_cases (
        id UUID PRIMARY KEY,
        case_code VARCHAR(120) NOT NULL UNIQUE CHECK (btrim(case_code) <> ''),
        subject_id UUID REFERENCES research_subjects(id) ON DELETE RESTRICT,
        title VARCHAR(240),
        description TEXT,
        source_type VARCHAR(30) NOT NULL CHECK (
          source_type IN ('physical_microscope','imported_image','research_dataset','synthetic')
        ),
        status VARCHAR(20) NOT NULL DEFAULT 'draft'
          CHECK (status IN ('draft','registered','ready','archived')),
        priority VARCHAR(10) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high')),
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
          CHECK (jsonb_typeof(metadata_json) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        archived_at TIMESTAMPTZ,
        archived_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        CONSTRAINT ck_scientific_case_archive_state CHECK (
          (status <> 'archived' AND archived_at IS NULL AND archived_by IS NULL) OR
          (status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL)
        )
      );
      CREATE INDEX ix_scientific_cases_subject ON scientific_cases(subject_id);
      CREATE INDEX ix_scientific_cases_status_created ON scientific_cases(status, created_at DESC);

      CREATE TABLE blood_samples (
        id UUID PRIMARY KEY,
        case_id UUID NOT NULL REFERENCES scientific_cases(id) ON DELETE RESTRICT,
        sample_code VARCHAR(120) NOT NULL CHECK (btrim(sample_code) <> ''),
        specimen_type VARCHAR(80) NOT NULL DEFAULT 'peripheral_blood',
        collection_method VARCHAR(120),
        anticoagulant VARCHAR(120),
        collected_at TIMESTAMPTZ,
        received_at TIMESTAMPTZ,
        status VARCHAR(20) NOT NULL DEFAULT 'registered'
          CHECK (status IN ('registered','received','prepared','archived')),
        notes TEXT,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
          CHECK (jsonb_typeof(metadata_json) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        archived_at TIMESTAMPTZ,
        archived_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        CONSTRAINT uq_blood_samples_case_code UNIQUE(case_id, sample_code),
        CONSTRAINT ck_blood_sample_chronology CHECK (
          collected_at IS NULL OR received_at IS NULL OR received_at >= collected_at
        ),
        CONSTRAINT ck_blood_sample_archive_state CHECK (
          (status <> 'archived' AND archived_at IS NULL AND archived_by IS NULL) OR
          (status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL)
        )
      );
      CREATE INDEX ix_blood_samples_case ON blood_samples(case_id);
      CREATE INDEX ix_blood_samples_status_created ON blood_samples(status, created_at DESC);

      CREATE TABLE smear_slides (
        id UUID PRIMARY KEY,
        sample_id UUID NOT NULL REFERENCES blood_samples(id) ON DELETE RESTRICT,
        slide_code VARCHAR(120) NOT NULL CHECK (btrim(slide_code) <> ''),
        smear_type VARCHAR(20) NOT NULL CHECK (smear_type IN ('thin','thick','combined','unknown')),
        stain_type VARCHAR(120),
        preparation_method VARCHAR(160),
        prepared_at TIMESTAMPTZ,
        status VARCHAR(30) NOT NULL DEFAULT 'registered'
          CHECK (status IN ('registered','prepared','ready_for_capture','archived')),
        notes TEXT,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
          CHECK (jsonb_typeof(metadata_json) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        archived_at TIMESTAMPTZ,
        archived_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        CONSTRAINT uq_smear_slides_sample_code UNIQUE(sample_id, slide_code),
        CONSTRAINT ck_smear_slide_archive_state CHECK (
          (status <> 'archived' AND archived_at IS NULL AND archived_by IS NULL) OR
          (status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL)
        )
      );
      CREATE INDEX ix_smear_slides_sample ON smear_slides(sample_id);
      CREATE INDEX ix_smear_slides_status_created ON smear_slides(status, created_at DESC);

      CREATE TABLE microscopy_images (
        id UUID PRIMARY KEY,
        slide_id UUID NOT NULL REFERENCES smear_slides(id) ON DELETE RESTRICT,
        image_code VARCHAR(120) NOT NULL CHECK (btrim(image_code) <> ''),
        storage_provider VARCHAR(40) NOT NULL DEFAULT 'local',
        storage_key TEXT NOT NULL CHECK (btrim(storage_key) <> ''),
        original_filename TEXT,
        mime_type VARCHAR(120) NOT NULL CHECK (btrim(mime_type) <> ''),
        file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
        sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-fA-F]{64}$'),
        width_px INTEGER NOT NULL CHECK (width_px > 0),
        height_px INTEGER NOT NULL CHECK (height_px > 0),
        bit_depth INTEGER CHECK (bit_depth IS NULL OR bit_depth > 0),
        magnification NUMERIC CHECK (magnification IS NULL OR magnification > 0),
        objective_lens VARCHAR(120),
        microscope_reference VARCHAR(160),
        camera_reference VARCHAR(160),
        captured_at TIMESTAMPTZ,
        status VARCHAR(20) NOT NULL DEFAULT 'registered'
          CHECK (status IN ('registered','available','unavailable','rejected','archived')),
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
          CHECK (jsonb_typeof(metadata_json) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        archived_at TIMESTAMPTZ,
        archived_by UUID REFERENCES users(id) ON DELETE RESTRICT,
        CONSTRAINT uq_microscopy_images_slide_code UNIQUE(slide_id, image_code),
        CONSTRAINT uq_microscopy_images_slide_sha256 UNIQUE(slide_id, sha256),
        CONSTRAINT ck_microscopy_image_archive_state CHECK (
          (status <> 'archived' AND archived_at IS NULL AND archived_by IS NULL) OR
          (status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL)
        )
      );
      CREATE INDEX ix_microscopy_images_sha256 ON microscopy_images(sha256);
      CREATE INDEX ix_microscopy_images_slide ON microscopy_images(slide_id);
      CREATE INDEX ix_microscopy_images_status_created
        ON microscopy_images(status, created_at DESC);
    """)


def downgrade():
    op.execute("""
      DROP TABLE microscopy_images;
      DROP TABLE smear_slides;
      DROP TABLE blood_samples;
      DROP TABLE scientific_cases;
      DROP TABLE research_subjects;
    """)
