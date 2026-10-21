"""Aggregate native profiler intervals; nested/threaded durations are not additive."""
from collections import defaultdict
import json
from pathlib import Path
import re
import numpy as np
from tensorflow.tsl.profiler.protobuf.xplane_pb2 import XSpace
from analyze import stats, ROOT

results={}
for directory in sorted(ROOT.glob('diagnostic_*_xplane')):
    groups=defaultdict(list)
    named=defaultdict(list)
    planes=[]
    for path in directory.rglob('*.xplane.pb'):
        space=XSpace();space.ParseFromString(path.read_bytes())
        for plane in space.planes:
            planes.append(dict(name=plane.name,lines=len(plane.lines),events=sum(len(l.events) for l in plane.lines)))
            for line in plane.lines:
                for event in line.events:
                    name=plane.event_metadata[event.metadata_id].name
                    seconds=event.duration_ps/1e12
                    named[name].append(seconds)
                    for group, pattern in {
                        'read_decode':r'ReadFile|DecodePng|DecodeImage',
                        'lookup':r'LookupTableFind',
                        'preprocessing':r'ResizeBilinear|Rescaling|rescaling|preprocessing',
                        'augmentation':r'random_flip|random_rotation|random_translation|random_zoom|random_contrast',
                        'shuffle':r'Shuffle', 'batch':r'BatchDataset|::Batch',
                        'prefetch':r'Prefetch', 'delivery':r'IteratorGetNext',
                        'forward_backward':r'Conv2D|MatMul|Backprop|ReluGrad',
                        'apply_gradients':r'ResourceApply|Adam|SGD|AssignSub',
                        'compile_trace':r'Trac|Compil|GraphOptimization|GraphDef',
                        'synchronization':r'Sync|Wait|Memcpy|Copy.*(Host|Device)',
                    }.items():
                        if re.search(pattern,name): groups[group].append(seconds)
    results[directory.name]=dict(planes=planes,components={k:stats(v) for k,v in groups.items()},
        named_intervals={k:stats(v) for k,v in named.items()},
        limitation='Inclusive overlapping host intervals; op names are not proof of isolated GPU kernel duration. Missing groups are unobserved.')
(ROOT/'xplane_summary.json').write_text(json.dumps(results,indent=2))
print(json.dumps({k:dict(planes=v['planes'],components=v['components']) for k,v in results.items()},indent=2))
