"""Intrusive diagnostic only: R1 science, host timeline, cProfile and XPlane.

No diagnostic duration is admissible as a clean acceptance benchmark.
"""
import cProfile
import functools
import json
import os
from pathlib import Path
import pstats
import resource
import runpy
import subprocess
import sys
import time
from unittest.mock import patch
from contextlib import ExitStack

HERE = Path(__file__).resolve().parent
R1 = HERE.parent/'capstone_image_trace_1b_2_r1_evidence'
arch, mode = sys.argv[1:3]
OUT = HERE/f'diagnostic_{arch}_{mode}'
# All diagnostic variants use precisely the archived R1 implementation.
sys.path.insert(0, str(R1))
import tensorflow as tf
from tensorflow.python.framework.ops import EagerTensor
from tensorflow.python.eager.polymorphic_function.polymorphic_function import Function
from keras.src.backend.tensorflow.trainer import TensorFlowTrainer
import ledger
from observer import Observer

events = []
origin = time.perf_counter()
origin_unix_ns = time.time_ns()
def event(name, start, **fields):
    events.append(dict(name=name, start=start-origin, seconds=time.perf_counter()-start, **fields))

def timed(function, name):
    @functools.wraps(function)
    def call(*args, **kwargs):
        start = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            event(name, start)
    return call

numpy_original = EagerTensor.numpy
def numpy_timed(self, *args, **kwargs):
    caller = sys._getframe(1)
    location = Path(caller.f_code.co_filename).name+':'+caller.f_code.co_name+':'+str(caller.f_lineno)
    start = time.perf_counter()
    result = numpy_original(self, *args, **kwargs)
    event('numpy', start, caller=location, device=self.device, shape=str(self.shape))
    return result

function_call = Function.__call__
def traced(self, *args, **kwargs):
    before = self.experimental_get_tracing_count()
    start = time.perf_counter()
    result = function_call(self, *args, **kwargs)
    elapsed = time.perf_counter()-start
    after = self.experimental_get_tracing_count()
    if elapsed > .001 or before != after:
        event('tf_function', start, function=self.name, traces_before=before, traces_after=after)
    return result

original_install = Observer.install
def install(self, model, record=True):
    return original_install(self, model, record=record and mode != 'tokens')

def nondurable_put(self, payload):
    # Diagnostics ONLY: memory still includes Aggregator.emit hashing and
    # capacity serialization. These residual costs are explicitly retained.
    if mode == 'serialization':
        data = ledger.canonical(dict(payload, receipt_sha256=ledger.digest(payload)))
        self.max_bytes = max(self.max_bytes, len(data))
    self.events += 1
    return True

def nondurable_verify(self):
    return dict(diagnostic_only=True, durable=False, events=self.events)

profile = cProfile.Profile()
def host_snapshot():
    result = dict(loadavg=os.getloadavg(),rss_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    for key, command in [('vm_stat',['/usr/bin/vm_stat']),('thermal',['/usr/bin/pmset','-g','therm'])]:
        process = subprocess.run(command,capture_output=True,text=True)
        result[key] = dict(returncode=process.returncode,stdout=process.stdout,stderr=process.stderr)
    return result
host_before = host_snapshot()
sys.argv = ['experiment_benchmarked.py', str(OUT), '--architecture', arch, '--deterministic']
if arch != 'custom_cnn': sys.argv += ['--two-phases']
if mode != 'baseline': sys.argv += ['--observer']
profiler_started = False
errors = []
original_make = TensorFlowTrainer._make_function
function_number = 0
def measured_make(model, step):
    global function_number
    function = original_make(model, step)
    number = function_number
    function_number += 1
    purpose = 'train' if step == model.train_step else 'test'
    batch = 0
    def execute(iterator):
        nonlocal batch
        start = time.perf_counter()
        result = function(iterator)
        event('scientific_function',start,function_number=number,purpose=purpose,batch=batch,
              element_spec=str(getattr(iterator,'element_spec',None)),
              devices={k:getattr(v,'device',None) for k,v in result.items()})
        batch += 1
        return result
    return execute

with ExitStack() as stack:
    stack.enter_context(patch.object(TensorFlowTrainer,'_make_function',measured_make))
    stack.enter_context(patch.object(EagerTensor, 'numpy', numpy_timed))
    stack.enter_context(patch.object(Function, '__call__', traced))
    stack.enter_context(patch.object(Observer, 'install', install))
    if mode in ('memory','serialization'):
        stack.enter_context(patch.object(ledger.Store,'put',nondurable_put))
        stack.enter_context(patch.object(ledger.Store,'verify',nondurable_verify))
    for owner, methods in [(ledger.Aggregator,['add','emit','flush','open','close']),
                           (ledger.Store,['put','verify']), (ledger,['canonical','digest']),
                           (os,['fsync','rename'])]:
        for method in methods:
            label = (owner.__name__ if hasattr(owner,'__name__') else str(owner))+'.'+method
            stack.enter_context(patch.object(owner,method,timed(getattr(owner,method),label)))
    # XPlane kept outside OUT: the original harness owns output mkdir.
    trace_dir = HERE/(OUT.name+'_xplane')
    try:
        tf.profiler.experimental.start(str(trace_dir), options=tf.profiler.experimental.ProfilerOptions(
            host_tracer_level=2, python_tracer_level=0, device_tracer_level=1))
        profiler_started = True
    except Exception as exc:
        errors.append(repr(exc))
    profile.enable()
    try:
        runpy.run_path(str(R1/'experiment_benchmarked.py'),run_name='__main__')
    finally:
        profile.disable()
        if profiler_started:
            tf.profiler.experimental.stop()
        if OUT.exists():
            (OUT/'host_timeline.json').write_text(json.dumps(events))
            profile.dump_stats(str(OUT/'cpu_profile.pstats'))
            with (OUT/'cpu_profile.txt').open('x') as f:
                pstats.Stats(profile,stream=f).sort_stats('cumulative').print_stats(150)
            try:
                gpu_memory = tf.config.experimental.get_memory_info('GPU:0')
                gpu_note = 'Allocator API only; zero does not establish physical GPU usage.'
            except Exception as exc:
                gpu_memory, gpu_note = None, repr(exc)
            (OUT/'diagnostic_metadata.json').write_text(json.dumps(dict(
                mode=mode, diagnostic_only=True, acceptance_timings=False,
                timeline_origin_monotonic=origin,timeline_origin_unix_ns=origin_unix_ns,
                durable=mode=='full', host_before=host_before, host_after=host_snapshot(),
                gpu_allocator=gpu_memory,gpu_allocator_limitation=gpu_note,profiler_errors=errors),indent=2))
