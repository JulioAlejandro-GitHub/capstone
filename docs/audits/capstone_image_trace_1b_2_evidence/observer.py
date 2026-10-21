"""Experimental fingerprint side channel. Synthetic-only; no production activation.

Tokens travel alongside tensors through maps, then a lookup connects the exact
step input to its token. Prepared entries never count as completed receipts.
The table grows with distinct augmented tensors: this candidate is NOT scalable.
"""
import hashlib
import json
import time
import types
import numpy as np
import tensorflow as tf


def keys(images):
    fingerprint = tf.raw_ops.Fingerprint(data=tf.reshape(images, [tf.shape(images)[0], -1]), method='farmhash64')
    return tf.strings.reduce_join(tf.strings.as_string(fingerprint), axis=1, separator=':')


class Observer:
    def __init__(self, fixture, manifest, output):
        self.output = output
        self.rows = []
        self.epoch = 0
        self.phase = 0
        raw_keys = []
        for entry in manifest:
            # Synthetic fixture is exactly model input size; no second inference.
            pixels = tf.cast(tf.io.decode_png(tf.io.read_file(str(fixture/entry['path'])), channels=3), tf.float32)
            raw_keys.append(keys(pixels[None])[0].numpy())
        if len(set(raw_keys)) != len(raw_keys):
            raise ValueError('AMBIGUOUS_SYNTHETIC_IDENTITY')
        self.raw = tf.lookup.StaticHashTable(tf.lookup.KeyValueTensorInitializer(raw_keys, tf.range(len(raw_keys), dtype=tf.int64)), -1)
        self.prepared = tf.lookup.experimental.MutableHashTable(tf.string, tf.int64, -1)

    def preprocess(self, dataset, preprocessing_mode, augment=False):
        from src.malaria_dl.data import loaders
        mode = loaders.resolve_preprocessing_mode(requested=preprocessing_mode)
        augmentation = loaders.build_augmentation()
        def attach(x,y):
            token = self.raw.lookup(keys(x))
            tf.debugging.assert_greater_equal(token, tf.constant(0, tf.int64))
            return x, tf.cast(tf.reshape(y, [-1]), tf.float32), token
        def pre(x,y,t): return loaders.apply_model_preprocessing(x, mode), y,t
        def aug(x,y,t): return augmentation(x, training=True), y,t
        dataset = dataset.map(attach, num_parallel_calls=tf.data.AUTOTUNE)
        if augment and mode == loaders.PREPROCESSING_VGG16_IMAGENET:
            dataset = dataset.map(aug, num_parallel_calls=tf.data.AUTOTUNE).map(pre, num_parallel_calls=tf.data.AUTOTUNE)
        else:
            dataset = dataset.map(pre, num_parallel_calls=tf.data.AUTOTUNE)
            if augment: dataset = dataset.map(aug, num_parallel_calls=tf.data.AUTOTUNE)
        def detach(x,y,t):
            k=keys(x)
            prior=self.prepared.lookup(k)
            tf.debugging.assert_equal(tf.reduce_all(tf.logical_or(prior < 0, prior == t)), True, message='AMBIGUOUS_AUGMENTED_IDENTITY')
            with tf.control_dependencies([self.prepared.insert(k,t)]): return tf.identity(x),y
        return dataset.map(detach,num_parallel_calls=tf.data.AUTOTUNE).prefetch(tf.data.AUTOTUNE)

    def install(self, model):
        if model.steps_per_execution != 1:
            raise ValueError('ONE_STEP_PER_EXECUTION_REQUIRED')
        original_make = model._make_function
        observer=self
        for method,purpose in [('train_step','weight_optimization'),('test_step','keras_validation')]:
            original=getattr(model,method)
            def step(data, original=original, purpose=purpose):
                x,y=data
                result=original(data)
                token=observer.prepared.lookup(keys(x))
                tf.debugging.assert_greater_equal(token,tf.constant(0,tf.int64))
                return {**result, '_trace_tokens':token, '_trace_tensor':x, '_trace_labels':y}
            setattr(model,method,step)
        def make(step):
            function=original_make(step)
            purpose='weight_optimization' if step == model.train_step else 'keras_validation'
            def execute(iterator):
                start=time.perf_counter()
                result=function(iterator)
                if '_trace_tokens' not in result: return result
                # Materialize original metric outputs before recording completion.
                for value in result.values():
                    if hasattr(value,'numpy'): value.numpy()
                tokens=result.pop('_trace_tokens').numpy().tolist()
                x=result.pop('_trace_tensor').numpy()
                y=result.pop('_trace_labels').numpy()
                observer.rows.append(dict(purpose=purpose, tokens=tokens,
                    tensor_sha256=hashlib.sha256(x.tobytes()).hexdigest(),
                    labels=y.tolist(), seconds=time.perf_counter()-start))
                return result
            return execute
        model._make_function=make

    def save(self):
        (self.output/'receipts.json').write_text(json.dumps(self.rows,indent=2)+'\n')
        (self.output/'observer_summary.json').write_text(json.dumps(dict(
            confirmed_batches=len(self.rows), prepared_entries=int(self.prepared.size().numpy()),
            warning='Unbounded experimental table; fingerprint collision risk; no production approval'),indent=2)+'\n')
