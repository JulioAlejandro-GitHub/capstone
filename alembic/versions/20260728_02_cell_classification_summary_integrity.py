"""Enforce aggregate-summary consistency with immutable cell predictions."""

from alembic import op


revision = "20260728_02"
down_revision = "20260728_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE OR REPLACE FUNCTION validate_smear_analysis_summary()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      source_analysis_run_id UUID;
      source_detection_run_id UUID;
      source_eligible_count INTEGER;
      actual_classified_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_count INTEGER;
      actual_failed_count INTEGER;
      actual_maximum DOUBLE PRECISION;
      actual_mean DOUBLE PRECISION;
      actual_median DOUBLE PRECISION;
      expected_outcome VARCHAR(40);
      actual_per_image JSONB;
      expected_policy CONSTANT JSONB := '{
        "version":"cell-candidate-aggregation-v1",
        "scope":"candidate_cells",
        "suspicious_when_any_parasitized": true,
        "near_threshold_makes_negative_inconclusive": true,
        "partial_failure_makes_negative_inconclusive": true,
        "terminology":"experimental_screening_not_diagnosis"
      }'::jsonb;
    BEGIN
      SELECT analysis_run_id,detection_run_id,eligible_count
      INTO
        source_analysis_run_id,
        source_detection_run_id,
        source_eligible_count
      FROM cell_classification_runs
      WHERE id=NEW.classification_run_id
      FOR SHARE;

      SELECT
        count(*) FILTER (WHERE prediction_status='completed'),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='parasitized'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='uninfected'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed' AND near_threshold
        ),
        count(*) FILTER (WHERE prediction_status='failed'),
        max(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        avg(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        percentile_cont(0.5) WITHIN GROUP (
          ORDER BY probability_parasitized
        ) FILTER (WHERE prediction_status='completed')
      INTO
        actual_classified_count,
        actual_parasitized_count,
        actual_uninfected_count,
        actual_near_count,
        actual_failed_count,
        actual_maximum,
        actual_mean,
        actual_median
      FROM cell_predictions
      WHERE classification_run_id=NEW.classification_run_id;

      SELECT jsonb_build_object(
        'images',
        COALESCE(
          jsonb_agg(
            jsonb_build_object(
              'microscopy_image_id',per_image.microscopy_image_id::text,
              'image_sequence_number',per_image.image_sequence_number,
              'eligible_cell_count',per_image.eligible_cell_count,
              'classified_cell_count',per_image.classified_cell_count,
              'parasitized_candidate_count',
                per_image.parasitized_candidate_count,
              'uninfected_candidate_count',
                per_image.uninfected_candidate_count,
              'near_threshold_count',per_image.near_threshold_count,
              'failed_prediction_count',per_image.failed_prediction_count
            )
            ORDER BY
              per_image.image_sequence_number,
              per_image.microscopy_image_id
          ),
          '[]'::jsonb
        )
      )
      INTO actual_per_image
      FROM (
        SELECT
          input.microscopy_image_id,
          min(input.image_sequence_number) image_sequence_number,
          count(*)::INTEGER eligible_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
          )::INTEGER classified_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='parasitized'
          )::INTEGER parasitized_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='uninfected'
          )::INTEGER uninfected_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.near_threshold
          )::INTEGER near_threshold_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='failed'
          )::INTEGER failed_prediction_count
        FROM cell_classification_inputs input
        LEFT JOIN cell_predictions prediction
          ON prediction.classification_input_id=input.id
        WHERE input.classification_run_id=NEW.classification_run_id
          AND input.eligible
        GROUP BY input.microscopy_image_id
      ) per_image;

      IF actual_parasitized_count > 0 THEN
        expected_outcome := 'suspicious_cells_detected';
      ELSIF source_eligible_count > 0
        AND actual_classified_count=source_eligible_count
        AND actual_failed_count=0
        AND actual_near_count=0
      THEN
        expected_outcome := 'no_suspicious_cells_detected';
      ELSE
        expected_outcome := 'inconclusive';
      END IF;

      IF NEW.analysis_run_id IS DISTINCT FROM source_analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM source_detection_run_id
        OR NEW.eligible_cell_count IS DISTINCT FROM source_eligible_count
        OR NEW.classified_cell_count IS DISTINCT FROM actual_classified_count
        OR NEW.parasitized_candidate_count
          IS DISTINCT FROM actual_parasitized_count
        OR NEW.uninfected_candidate_count
          IS DISTINCT FROM actual_uninfected_count
        OR NEW.near_threshold_count IS DISTINCT FROM actual_near_count
        OR NEW.failed_prediction_count IS DISTINCT FROM actual_failed_count
        OR NEW.outcome IS DISTINCT FROM expected_outcome
        OR NEW.per_image_summary IS DISTINCT FROM actual_per_image
        OR NEW.aggregation_policy_snapshot IS DISTINCT FROM expected_policy
        OR (
          actual_classified_count > 0
          AND (
            NEW.maximum_probability_parasitized IS NULL
            OR NEW.mean_probability_parasitized IS NULL
            OR NEW.median_probability_parasitized IS NULL
            OR abs(
              NEW.maximum_probability_parasitized - actual_maximum
            ) > 1e-12
            OR abs(NEW.mean_probability_parasitized - actual_mean) > 1e-12
            OR abs(NEW.median_probability_parasitized - actual_median) > 1e-12
          )
        )
      THEN
        RAISE EXCEPTION
          'smear analysis summary does not match immutable predictions'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_smear_analysis_summaries_validate
      ON smear_analysis_summaries;
    CREATE TRIGGER trg_smear_analysis_summaries_validate
      BEFORE INSERT ON smear_analysis_summaries
      FOR EACH ROW EXECUTE FUNCTION validate_smear_analysis_summary();
    """)


def downgrade():
    # Revision 20260728_01 owns the baseline definition. This forward migration
    # reasserts it for databases migrated while Prompt 8 was being validated.
    pass
