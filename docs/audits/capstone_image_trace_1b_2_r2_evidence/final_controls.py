"""Additional isolated controls and bounded-state measurement; no training."""
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tracemalloc
from ledger import Aggregator, Store, deep_size

ROOT = Path(__file__).resolve().parent
results = {}
for arch in ['custom_cnn', 'vgg16', 'densenet121']:
    subprocess.run([sys.executable, str(ROOT/'compare_reference.py'), str(ROOT/f'{arch}_reference_a'),
                    str(ROOT/f'{arch}_reference_b'), str(ROOT/f'{arch}_reference_exact.json')], check=True)
for case in ['no-augment', 'no-shuffle_verified', 'duplicate']:
    subprocess.run([sys.executable, str(ROOT/'compare_reference.py'), str(ROOT/f'{case}_a'),
                    str(ROOT/f'{case}_b'), str(ROOT/f'{case}_reference_exact.json')], check=True)

# No retained telemetry history in the measured process; periodic GC makes
# cyclic serializer garbage distinguishable from reachable aggregator state.
store = Store(ROOT/'memory_gc_journal')
agg = Aggregator(store)
tracemalloc.start()
with (ROOT/'memory_gc.jsonl').open('x') as stream:
    for epoch in range(1000):
        agg.open(dict(run_id='synthetic-gc', epoch_local=epoch + 1))
        for batch in range(8):
            agg.add(list(range(batch * 8, (batch + 1) * 8)))
        agg.close()
        if epoch % 25 == 24:
            gc.collect()
            current, peak = tracemalloc.get_traced_memory()
            stream.write(json.dumps(dict(epoch=epoch+1, live_bytes=current, peak_bytes=peak,
                reachable_aggregator_bytes=deep_size(agg.__dict__), bound_bytes=agg.peak_bytes))+'\n')
            stream.flush()
tracemalloc.stop()
results['memory_recovery'] = store.verify()

# Capacity probes are receipt-only; no model step is executed for an oversize batch.
store = Store(ROOT/'capacity_journal')
agg = Aggregator(store)
agg.open(dict(run_id='capacity', epoch_local=1))
agg.add(list(range(8192)))
agg.add([8192])
agg.close()
results['capacity'] = dict(verification=store.verify(), max_event_bytes=store.max_bytes,
                           aggregator_peak_bound_bytes=agg.peak_bytes)
(ROOT/'final_controls.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))

# Preparation/prefetch is deliberately exercised without invoking a model.
import tensorflow as tf
from contextlib import ExitStack
from observer import Observer
sys.path.insert(0, str(ROOT.parents[2]/'malaria_dl_local_project'))
from src.malaria_dl.data import loaders
if not tf.config.list_physical_devices('GPU'):
    raise RuntimeError('METAL_UNAVAILABLE: no CPU fallback')
tf.config.set_soft_device_placement(False)
with tf.device('/GPU:0'):
    probe = tf.matmul(tf.ones((2,2)), tf.ones((2,2)))
    probe.numpy()
fixture = ROOT/'custom_cnn_aa1'/'fixture'
manifest = json.loads((ROOT/'custom_cnn_aa1'/'manifest.json').read_text())
output = ROOT/'preparation_control'
output.mkdir(exist_ok=False)
observer = Observer(fixture, manifest, output)
with ExitStack() as stack:
    observer.patch_loading(stack)
    dataset = loaders.make_image_dataset_from_directory(fixture/'train', 32, 8, True, seed=42)
    dataset = observer.preprocess(dataset, loaders.PREPROCESSING_RESCALE_0_1, augment=False)
    images, labels = next(iter(dataset))
    prepared_tokens = images['token'].numpy().tolist()
    assert observer.store.events == 0 and observer.aggregator.batches == []
(output/'result.json').write_text(json.dumps(dict(prepared_tokens=prepared_tokens,
    prepared_images=len(prepared_tokens), confirmed_batches=0, durable_events=0, gpu_device=probe.device), indent=2))
