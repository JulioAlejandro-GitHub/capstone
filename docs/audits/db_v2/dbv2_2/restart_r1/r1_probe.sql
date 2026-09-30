\set ON_ERROR_STOP on
-- R1 minimal harness: real corrected function/triggers, synthetic row-shape dependencies.
-- Not installation of the design SQL; full contract certification follows separately.
BEGIN;
DO $$ BEGIN IF current_setting('server_version_num')<>'170009' OR inet_server_addr() IS NOT NULL THEN RAISE EXCEPTION 'UNSAFE_TARGET'; END IF; END $$;
CREATE EXTENSION pgcrypto;
CREATE TABLE public.xai_quantitative_evaluations(id uuid PRIMARY KEY,protocol_id uuid,membership_hash text,metric_value float8,reference_annotation_id uuid,reference_annotation_version integer);
CREATE TABLE public.xai_evaluation_protocols(id uuid PRIMARY KEY,metric_family text);
CREATE TABLE public.xai_evidence(id uuid PRIMARY KEY,input_sha256 text,input_contract_hash text,target_class smallint,explained_output text,processing_stage text,checkpoint_sha256 text);
CREATE TABLE public.xai_evaluation_members(evaluation_id uuid REFERENCES xai_quantitative_evaluations(id) ON DELETE RESTRICT,xai_evidence_id uuid REFERENCES xai_evidence(id) ON DELETE RESTRICT,member_role text,PRIMARY KEY(evaluation_id,xai_evidence_id));
CREATE TABLE public.scientific_validation_annotations(id uuid,version integer);
CREATE FUNCTION public.dbv21_xai_evaluation_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_catalog AS $$
DECLARE eid uuid; q public.xai_quantitative_evaluations%ROWTYPE; p public.xai_evaluation_protocols%ROWTYPE; n integer;
BEGIN
 IF TG_TABLE_NAME = 'xai_quantitative_evaluations' THEN
     eid := NEW.id;
 ELSIF TG_TABLE_NAME = 'xai_evaluation_members' THEN
     eid := NEW.evaluation_id;
 ELSE
     RAISE EXCEPTION
         'dbv21_xai_evaluation_complete invoked from unsupported table: %',
         TG_TABLE_NAME;
 END IF;
 SELECT * INTO STRICT q FROM public.xai_quantitative_evaluations WHERE id=eid;
 SELECT * INTO STRICT p FROM public.xai_evaluation_protocols WHERE id=q.protocol_id;
 SELECT count(*) INTO n FROM public.xai_evaluation_members WHERE evaluation_id=eid;
 IF q.membership_hash IS DISTINCT FROM (SELECT encode(digest(convert_to(coalesce(string_agg(xai_evidence_id::text || ':' || member_role, E'\n' ORDER BY xai_evidence_id::text COLLATE "C"),''),'UTF8'),'sha256'),'hex') FROM public.xai_evaluation_members WHERE evaluation_id=eid) THEN RAISE EXCEPTION 'XAI_MEMBERSHIP_HASH_MISMATCH'; END IF;
 IF n<1 OR (p.metric_family='agreement' AND n<2) THEN RAISE EXCEPTION 'XAI_EVALUATION_MEMBERS_REQUIRED'; END IF;
 IF p.metric_family='agreement' AND EXISTS (
 SELECT 1 FROM public.xai_evaluation_members ma JOIN public.xai_evidence a ON a.id=ma.xai_evidence_id
 JOIN public.xai_evaluation_members mb ON mb.evaluation_id=ma.evaluation_id JOIN public.xai_evidence b ON b.id=mb.xai_evidence_id
 WHERE ma.evaluation_id=eid AND (a.input_sha256 IS DISTINCT FROM b.input_sha256 OR a.input_contract_hash IS DISTINCT FROM b.input_contract_hash OR a.target_class IS DISTINCT FROM b.target_class OR a.explained_output IS DISTINCT FROM b.explained_output OR a.processing_stage IS DISTINCT FROM b.processing_stage OR a.checkpoint_sha256 IS DISTINCT FROM b.checkpoint_sha256)) THEN RAISE EXCEPTION 'XAI_AGREEMENT_INCOMPATIBLE'; END IF;
 IF p.metric_family='localization' AND q.metric_value IS NOT NULL AND q.reference_annotation_id IS NULL THEN RAISE EXCEPTION 'XAI_LOCALIZATION_REFERENCE_REQUIRED'; END IF;
 IF q.reference_annotation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.scientific_validation_annotations WHERE id=q.reference_annotation_id AND version=q.reference_annotation_version) THEN RAISE EXCEPTION 'XAI_REFERENCE_VERSION_MISMATCH'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER dbv21_xai_evaluation_complete AFTER INSERT ON public.xai_quantitative_evaluations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.dbv21_xai_evaluation_complete();
CREATE CONSTRAINT TRIGGER dbv21_xai_evaluation_complete AFTER INSERT ON public.xai_evaluation_members DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.dbv21_xai_evaluation_complete();
INSERT INTO xai_evaluation_protocols VALUES ('00000000-0000-0000-0000-000000000001','stability');
INSERT INTO xai_evidence(id) VALUES ('00000000-0000-0000-0000-000000000002');
COMMIT;
-- Evaluation alone is accepted while deferred, and rejected when forced.
BEGIN;
DO $$ BEGIN
 BEGIN
 INSERT INTO xai_quantitative_evaluations VALUES ('00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001',encode(digest('','sha256'),'hex'),NULL,NULL,NULL);
 RAISE NOTICE 'PASS evaluation INSERT is deferred (no 42703)';
 SET CONSTRAINTS ALL IMMEDIATE;
 RAISE EXCEPTION 'EXPECTED_REJECTION_MISSING';
 EXCEPTION WHEN raise_exception THEN
 IF SQLERRM <> 'XAI_EVALUATION_MEMBERS_REQUIRED' THEN RAISE; END IF;
 RAISE NOTICE 'PASS incomplete evaluation rejected: % %',SQLSTATE,SQLERRM;
 END;
END $$;
ROLLBACK;
-- Both trigger paths execute at COMMIT on a coherent pair.
BEGIN;
INSERT INTO xai_quantitative_evaluations VALUES ('00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001',encode(digest('00000000-0000-0000-0000-000000000002:candidate','sha256'),'hex'),NULL,NULL,NULL);
INSERT INTO xai_evaluation_members VALUES ('00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002','candidate');
COMMIT;
SELECT 'PASS coherent evaluation + member COMMIT; both trigger paths; no 42703' AS result;
-- The evidence can belong to a second evaluation: N:M preserved.
BEGIN;
INSERT INTO xai_quantitative_evaluations VALUES ('00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000001',encode(digest('00000000-0000-0000-0000-000000000002:candidate','sha256'),'hex'),NULL,NULL,NULL);
INSERT INTO xai_evaluation_members VALUES ('00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002','candidate');
COMMIT;
SELECT 'PASS second evaluation shares evidence; immediate FKs and deferred trigger COMMIT' AS result;
BEGIN;
DO $$ BEGIN
 BEGIN
 INSERT INTO xai_quantitative_evaluations VALUES ('00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000001',repeat('a',64),NULL,NULL,NULL);
 INSERT INTO xai_evaluation_members VALUES ('00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000002','candidate');
 SET CONSTRAINTS ALL IMMEDIATE;
 RAISE EXCEPTION 'EXPECTED_REJECTION_MISSING';
 EXCEPTION WHEN raise_exception THEN
 IF SQLERRM <> 'XAI_MEMBERSHIP_HASH_MISMATCH' THEN RAISE; END IF;
 RAISE NOTICE 'PASS invalid membership rejected: % %',SQLSTATE,SQLERRM;
 END;
END $$;
ROLLBACK;
