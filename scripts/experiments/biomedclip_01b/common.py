"""Experimental only; no production imports or database writes."""
import os
os.environ['PYTORCH_ENABLE_MPS_FALLBACK']='0'
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
import hashlib,json,time,random
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[3]
E=Path(os.environ.get('BIOMEDCLIP_EVIDENCE_DIR',str(ROOT/'docs/audits/evidence/biomedclip_01b')))
E.mkdir(parents=True,exist_ok=True)
WORK=Path(os.environ.get('BIOMEDCLIP_WORK_DIR','/Users/julio/.cache/capstone-biomedclip-01b'))
WORK.mkdir(parents=True,exist_ok=True)
SEED=20261026
PROMPTS=['a microscopy image of an uninfected red blood cell.','a microscopy image of a red blood cell infected with malaria parasites.']
def write(name,obj): (E/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def seeds():
    random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED);torch.set_num_threads(4)
def sync(device):
    if str(device).startswith('mps'):torch.mps.synchronize()
def timed(fn,device='cpu'):
    sync(device);t=time.perf_counter();out=fn();sync(device)
    return out,time.perf_counter()-t
def memory():
    import psutil
    return dict(allocated=torch.mps.current_allocated_memory(),driver=torch.mps.driver_allocated_memory(),recommended=torch.mps.recommended_max_memory(),rss=psutil.Process().memory_info().rss)
def digest_state(model):
    return {n:hashlib.sha256(v.detach().cpu().contiguous().numpy().tobytes()).hexdigest() for n,v in model.state_dict().items()}
def load():
    import copy,open_clip
    from open_clip.factory import _MODEL_CONFIGS
    assets=json.loads((E/'original_assets.json').read_text())
    for a in assets:
        for f in a['files']: assert sha(f['path'])==f['sha256'],f['name']
    clip,text=assets
    config=json.loads((Path(clip['directory'])/'open_clip_config.json').read_text())
    cfg=copy.deepcopy(config['model_cfg'])
    cfg['text_cfg']['hf_model_name']=text['directory']
    cfg['text_cfg']['hf_tokenizer_name']=text['directory']
    cfg['text_cfg']['hf_model_pretrained']=False
    _MODEL_CONFIGS['biomedclip_01b']=cfg
    model,_,transform=open_clip.create_model_and_transforms('biomedclip_01b',pretrained=str(Path(clip['directory'])/'open_clip_pytorch_model.bin'),pretrained_text=False,device='cpu',precision='fp32',**{'image_'+k:v for k,v in config['preprocess_cfg'].items()})
    tokenizer=open_clip.get_tokenizer('biomedclip_01b')
    model.eval()
    return model,transform,tokenizer

def images(transform):
    from PIL import Image
    rows=json.loads((E/'samples.json').read_text())['samples']
    tensors=[]
    for r in rows:
        p=ROOT/r['path'];assert sha(p)==r['sha256']
        assert r['split_name'] in ('train','val')
        with Image.open(p) as im:tensors.append(transform(im.convert('RGB')))
    return torch.stack(tensors),rows

def parity(a,b):
    a=np.asarray(a);b=np.asarray(b);d=np.abs(a-b)
    return dict(max_abs=float(d.max()),mean_abs=float(d.mean()),allclose=bool(np.allclose(a,b,atol=1e-4,rtol=1e-3)),atol=1e-4,rtol=1e-3)
