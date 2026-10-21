"""Intrusive synchronization boundaries on ORIGINAL calls, never extra science.

These host marker intervals include dispatch and host/GPU synchronization.
They are not isolated GPU kernel times and never acceptance measurements.
"""
import json
from pathlib import Path
import runpy
import sys
import time
from unittest.mock import patch
from campaign import HERE, R1

arch,arm=sys.argv[1:]
OUT=HERE/f'phase_profile_{arch}_{arm}'
sys.path.insert(0,str(R1))
sys.path.insert(0,str(HERE.parents[2]/'malaria_dl_local_project'))
import tensorflow as tf
from src.malaria_dl.models import adapters

events=[]
origin=time.perf_counter()
phase='uncompiled'
original_calls={}

def marker(label, position, dependencies=()):
    current_phase=phase
    def mark():
        value=time.perf_counter()-origin
        events.append(dict(component=label,position=position,phase=phase,traced_phase=current_phase,seconds=value))
        return 0
    with tf.control_dependencies(list(dependencies)):
        return tf.py_function(mark,[],tf.int64)

def completed(value, end):
    with tf.control_dependencies([end]):
        return tf.nest.map_structure(lambda v:tf.identity(v) if v is not None else None,value)

compile_original=adapters.compile_phase
gradient_original=tf.GradientTape.gradient
def gradient(self,target,sources,*args,**kwargs):
    begin=marker('backward','begin',tf.nest.flatten(target))
    with tf.control_dependencies([begin]):
        result=gradient_original(self,target,sources,*args,**kwargs)
    end=marker('backward','end',[v for v in tf.nest.flatten(result) if v is not None])
    return completed(result,end)

def compile_instrumented(*args,**kwargs):
    global phase
    runtime=compile_original(*args,**kwargs)
    phase=args[3]
    model=args[1].model
    if id(model) not in original_calls: original_calls[id(model)]=model.call
    call=original_calls[id(model)]
    def forward(*a,**kw):
        label='forward_train' if kw.get('training',False) else 'forward_inference'
        begin=marker(label,'begin',tf.nest.flatten(a))
        with tf.control_dependencies([begin]): result=call(*a,**kw)
        end=marker(label,'end',tf.nest.flatten(result))
        return completed(result,end)
    model.call=forward
    optimizer=model.optimizer
    apply=optimizer.apply_gradients
    def apply_gradients(pairs):
        pairs=list(pairs)
        begin=marker('apply_gradients','begin',[g for g,v in pairs if g is not None])
        with tf.control_dependencies([begin]):
            result=apply(pairs)
            iteration=tf.identity(optimizer.iterations)
        end=marker('apply_gradients','end',[iteration])
        with tf.control_dependencies([end]): return tf.identity(result)
    optimizer.apply_gradients=apply_gradients
    return runtime

sys.argv=['experiment_benchmarked.py',str(OUT),'--architecture',arch,'--deterministic']
if arm=='b':sys.argv+=['--observer']
if arch!='custom_cnn':sys.argv+=['--two-phases']
with patch.object(adapters,'compile_phase',compile_instrumented),patch.object(tf.GradientTape,'gradient',gradient):
    try:
        runpy.run_path(str(R1/'experiment_benchmarked.py'),run_name='__main__')
    finally:
        if OUT.exists():
            (OUT/'phase_timeline.json').write_text(json.dumps(events,indent=2))
            (OUT/'profile_limitations.json').write_text(json.dumps(dict(acceptance=False,
                mechanism='tf.py_function host markers, GPU data/control dependencies on original calls',
                limitation='Intrusive dispatch/synchronization intervals, not pure GPU kernel durations'),indent=2))
