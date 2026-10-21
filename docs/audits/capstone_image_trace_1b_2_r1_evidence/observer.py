"""Explicit path-bound tokens. All monkeypatches confined to synthetic harness."""
import hashlib
import json
import resource
import time
import tensorflow as tf
from ledger import Aggregator, Store, canonical, digest, deep_size


class Observer:
    def __init__(self, fixture, manifest, output):
        self.output = output
        self.fixture = fixture
        self.manifest = [dict(row, dataset_version='synthetic-r1-v1', materialization='synthetic-r1-m1',
                              split=row['path'].split('/')[0], source_record='synthetic:' + row['path'])
                         for row in sorted(manifest, key=lambda row: row['path'])]
        self.manifest_hash = digest(self.manifest)
        (output / 'token_manifest.json').write_bytes(canonical(self.manifest))
        paths = [str(fixture / row['path']) for row in self.manifest]
        if len(set(paths)) != len(paths):
            raise ValueError('AMBIGUOUS_PATH')
        self.lookup = tf.lookup.StaticHashTable(tf.lookup.KeyValueTensorInitializer(paths,
                                tf.range(len(paths), dtype=tf.int64)), -1)
        self.map_bytes = deep_size(self.manifest) + deep_size(paths) + len(paths) * 8
        self.store = Store(output / 'journal')
        self.aggregator = Aggregator(self.store)
        self.offset = 0
        self.epoch = 0
        self.phase = 'base'
        self.architecture = 'unknown'
        self.close_seconds = 0.

    def patch_loading(self, stack):
        from unittest.mock import patch
        from keras.src.utils import image_dataset_utils
        load = image_dataset_utils._load_image_tf
        def tagged(path, *args, **kwargs):
            token = self.lookup.lookup(path)
            with tf.control_dependencies([tf.debugging.assert_greater_equal(token, tf.constant(0, tf.int64))]):
                return {'image': load(path, *args, **kwargs), 'token': tf.identity(token)}
        stack.enter_context(patch.object(image_dataset_utils, '_load_image_tf', tagged))
        predict = tf.keras.Model.predict
        def predict_images(model, x, *args, **kwargs):
            return predict(model, x['image'] if isinstance(x, dict) and 'token' in x else x, *args, **kwargs)
        stack.enter_context(patch.object(tf.keras.Model, 'predict', predict_images))

    def preprocess(self, dataset, preprocessing_mode, augment=False):
        from src.malaria_dl.data import loaders
        mode = loaders.resolve_preprocessing_mode(requested=preprocessing_mode)
        augmentation = loaders.build_augmentation()
        def normalize(x, y):
            return x, tf.cast(tf.reshape(y, [-1]), tf.float32)
        def pre(x, y):
            return dict(image=loaders.apply_model_preprocessing(x['image'], mode), token=x['token']), y
        def aug(x, y):
            return dict(image=augmentation(x['image'], training=True), token=x['token']), y
        dataset = dataset.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)
        if augment and mode == loaders.PREPROCESSING_VGG16_IMAGENET:
            dataset = dataset.map(aug, num_parallel_calls=tf.data.AUTOTUNE).map(pre, num_parallel_calls=tf.data.AUTOTUNE)
        else:
            dataset = dataset.map(pre, num_parallel_calls=tf.data.AUTOTUNE)
            if augment:
                dataset = dataset.map(aug, num_parallel_calls=tf.data.AUTOTUNE)
        return dataset.prefetch(tf.data.AUTOTUNE)

    def scope(self, purpose):
        return dict(run_id='00000000-0000-4000-8000-000000000001',
                    session_run_id='00000000-0000-4000-8000-000000000001', campaign_attempt_id=None,
                    architecture=self.architecture, usage_purpose=purpose, phase=self.phase,
                    epoch_local=self.epoch, epoch_global=self.offset + self.epoch, pass_ordinal=1,
                    manifest_ref='token_manifest.json', manifest_sha256=self.manifest_hash)

    def install(self, model, record=True):
        if model.steps_per_execution != 1:
            raise ValueError('ONE_STEP_REQUIRED')
        original_make = model._make_function
        for method in ('train_step', 'test_step'):
            original = getattr(model, method)
            def step(data, original=original, method=method):
                x, y = data
                result = original((x['image'], y))
                dependencies = list(result.values())
                if method == 'train_step':
                    dependencies.append(tf.identity(model.optimizer.iterations))
                with tf.control_dependencies(dependencies):
                    return dict(result, _trace_tokens=tf.identity(x['token']))
            setattr(model, method, step)
        def make(step):
            function = original_make(step)
            def execute(iterator):
                result = function(iterator)
                if '_trace_tokens' in result:
                    tokens = result.pop('_trace_tokens').numpy().tolist()
                    for value in result.values():
                        if hasattr(value, 'numpy'):
                            value.numpy()
                    if record:
                        self.aggregator.add(tokens)
                return result
            return execute
        model._make_function = make
        if not record:
            return
        fit = model.fit
        observer = self
        class Boundaries(tf.keras.callbacks.Callback):
            def on_epoch_begin(self, epoch, logs=None):
                observer.epoch = epoch + 1
                observer.aggregator.open(observer.scope('weight_optimization'))
            def on_test_begin(self, logs=None):
                observer.aggregator.close()
                observer.aggregator.open(observer.scope('keras_validation'))
            def on_test_end(self, logs=None):
                observer.aggregator.close()
            def on_epoch_end(self, epoch, logs=None):
                with (observer.output / 'epoch_memory.jsonl').open('a') as stream:
                    stream.write(json.dumps(dict(phase=observer.phase, epoch=epoch + 1,
                        aggregator_live_bytes=deep_size(observer.aggregator.__dict__),
                        aggregator_peak_bound_bytes=observer.aggregator.peak_bytes,
                        rss_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)) + '\n')
        def observed_fit(*args, **kwargs):
            kwargs['callbacks'] = list(kwargs.get('callbacks', [])) + [Boundaries()]
            history = fit(*args, **kwargs)
            self.offset += len(history.epoch)
            return history
        model.fit = observed_fit

    def save(self):
        start = time.perf_counter()
        self.aggregator.close(exhaustive=False)
        self.close_seconds += time.perf_counter() - start
        result = self.store.verify()
        result.update(aggregator_peak_bound_bytes=self.aggregator.peak_bytes,
                      identity_python_and_payload_bytes=self.map_bytes,
                      identity_native_table_bytes='not_measured',
                      max_event_bytes=self.store.max_bytes, write_seconds=self.store.write_seconds,
                      close_seconds=self.aggregator.close_seconds, finish_seconds=self.close_seconds, max_drain_seconds=self.aggregator.max_drain_seconds)
        (self.output / 'observer_summary.json').write_text(json.dumps(result, indent=2))
