-- BiomedCLIP Linear Probing and Fine-tuning: catalog rows and run_configurations domain.
--
-- run_configurations enumerated the three Keras architectures, their weights and their
-- normalizations. public.models is the only catalog: an architecture is valid when it is a
-- registered model name, so the closed lists are replaced by a foreign key to models(name).
-- Optimizer, numeric, hash and immutability guards are unchanged; v2_configuration_guard still
-- binds every column to the frozen resolved configuration. One transaction, idempotent rows.
-- Apply with an owner role: psql -v ON_ERROR_STOP=1 -f scripts/sql/biomedclip_trainable_models.sql
BEGIN;

ALTER TABLE public.models ADD CONSTRAINT models_name_key UNIQUE (name);

ALTER TABLE public.run_configurations
  DROP CONSTRAINT v2_run_configurations_check_cf7585e198d6,  -- architecture IN (custom_cnn, vgg16, densenet121)
  DROP CONSTRAINT v2_run_configurations_check_4face7ed3946,  -- weights IN (none, imagenet)
  DROP CONSTRAINT v2_run_configurations_check_63e4a55e1de0,  -- architecture-specific normalization
  ADD CONSTRAINT run_configurations_architecture_catalog_fkey
    FOREIGN KEY (architecture) REFERENCES public.models(name) ON UPDATE RESTRICT ON DELETE RESTRICT;

INSERT INTO public.models(name, model_type, framework, architecture, description, pretrained, pretrained_source, metadata)
VALUES
  ('biomedclip_linear', 'linear_probe', 'pytorch_openclip', 'BiomedCLIP Linear Probing',
   'Frozen BiomedCLIP ViT-B/16 image encoder with a trained binary linear head: quality of the representations',
   true, 'microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224',
   jsonb_build_object(
     'task', 'binary_classification', 'target', 'parasitized_vs_uninfected',
     'architecture_family', 'vit', 'origin', 'pretrained_external', 'modality', 'linear_probe',
     'training_mode', 'computational', 'trainable_encoder', false,
     'base_model', jsonb_build_object('name', 'biomedclip_zero_shot',
       'model_version_id', '3fd16a84-b5c7-442b-916b-e0438bb0f3e5',
       'training_run_id', '31d27b2d-6e90-4530-a589-ae92c91281df'),
     'scientific_origin', jsonb_build_object('kind', 'pretrained_external',
       'repo_id', 'microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224',
       'revision', '9f341de24bfb00180f1b847274256e9b65a3a32e'))),
  ('biomedclip_fine_tuning', 'fine_tuning', 'pytorch_openclip', 'BiomedCLIP Fine-tuning',
   'BiomedCLIP ViT-B/16 image encoder partially or totally fine-tuned with a binary head: adaptation to malaria',
   true, 'microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224',
   jsonb_build_object(
     'task', 'binary_classification', 'target', 'parasitized_vs_uninfected',
     'architecture_family', 'vit', 'origin', 'pretrained_external', 'modality', 'fine_tuning',
     'training_mode', 'computational', 'trainable_encoder', true,
     'base_model', jsonb_build_object('name', 'biomedclip_zero_shot',
       'model_version_id', '3fd16a84-b5c7-442b-916b-e0438bb0f3e5',
       'training_run_id', '31d27b2d-6e90-4530-a589-ae92c91281df'),
     'scientific_origin', jsonb_build_object('kind', 'pretrained_external',
       'repo_id', 'microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224',
       'revision', '9f341de24bfb00180f1b847274256e9b65a3a32e')))
ON CONFLICT (name) DO NOTHING;

COMMIT;
