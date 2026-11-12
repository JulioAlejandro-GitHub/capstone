BEGIN READ ONLY;
SELECT json_build_object('evaluations',(SELECT json_agg(to_jsonb(e)) FROM evaluations e WHERE training_run_id='db31b6af-c2a2-44f0-9316-8f8c3492c0f1'),'artifacts',(SELECT json_agg(json_build_object('attempt_id',a.attempt_id,'role',a.role,'payload',a.payload,'artifact',to_jsonb(t))) FROM assessment_artifacts a JOIN artifacts t ON t.id=a.artifact_id WHERE a.attempt_id IN ('1ea90a63-65ea-41d9-97a0-1469fe671e47','7956a4c2-f65a-4e45-848a-499376b3e61f') AND a.sample_id IS NULL));
COMMIT;
