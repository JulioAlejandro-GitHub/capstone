"""Balanced VAL parity, persisted arrays and separate hybrid timings."""
from common import *
seeds()
(model,transform,tokenizer),load_seconds=timed(load)
(x,rows),preprocess_seconds=timed(lambda:images(transform))
ids=[i for i,r in enumerate(rows) if r['split_name']=='val']
inputs=x[ids];tokens=tokenizer(PROMPTS,context_length=256)
outputs={};timings={};arrays={}
for device in ['cpu','mps']:
    model.to(device);vinputs=inputs.to(device);texts=tokens.to(device)
    with torch.no_grad():
        v,visual=timed(lambda:model.encode_image(vinputs,normalize=True),device)
        t,text_seconds=timed(lambda:model.encode_text(texts,normalize=True),device)
        def sim():
            cosine=v@t.T;logits=model.logit_scale.exp()*cosine
            return cosine,logits,logits.softmax(-1)
        (cosine,logits,scores),similarity=timed(sim,device)
    outputs[device]={k:a.cpu().numpy() for k,a in [('embeddings',v),('text_embeddings',t),('cosines',cosine),('logits',logits),('scores',scores)]}
    for k,a in outputs[device].items():arrays[device+'_'+k]=a
    timings[device]=dict(visual_seconds=visual,text_seconds=text_seconds,similarity_seconds=similarity,device=str(scores.device))
with torch.no_grad():
    original=model.encode_image(inputs.to('mps'),normalize=True).cpu().numpy()
    state=torch.load(WORK/'fine_tuning.pt',map_location='cpu',weights_only=True)
    model.visual.load_state_dict(state['visual'],strict=True)
    adjusted=model.encode_image(inputs.to('mps'),normalize=True).cpu().numpy()
arrays['adjusted_val_embeddings']=adjusted
array_path=WORK/'parity_and_representations.npz'
assert not array_path.exists()
np.savez(array_path,**arrays)
# Same CKA implementation already in Capstone; import pure module via file to avoid services.
import importlib.util,sys
sys.path.insert(0,str(ROOT/'malaria_dl_local_project'))
from src.malaria_dl.assessment.representation import linear_cka
cka=linear_cka(original,adjusted)
import tensorflow as tf
tf.config.optimizer.set_experimental_options({'disable_meta_optimizer':True})
tf.keras.utils.set_random_seed(SEED)
features=np.load(WORK/'original_embeddings.npy')
train=np.array([r['split_name']=='train' for r in rows]);labels=np.array([r['label'] for r in rows],dtype=np.float32)[:,None]
head=tf.keras.Sequential([tf.keras.Input(shape=(512,)),tf.keras.layers.Dense(1,activation='sigmoid')])
head.compile(optimizer=tf.keras.optimizers.SGD(.1),loss='binary_crossentropy')
loss,head_step=timed(lambda:float(head.train_on_batch(features[train],labels[train])))
path=WORK/'linear_timing_probe.keras';assert not path.exists()
_,save=timed(lambda:head.save(path))
_,reload=timed(lambda:tf.keras.models.load_model(path,compile=False))
try:tf_memory=tf.config.experimental.get_memory_info('GPU:0')
except Exception as exc:tf_memory={'unavailable':type(exc).__name__+': '+str(exc)}
result=dict(sample_ids=[rows[i]['sample_id'] for i in ids],split='val',class_counts={'0':4,'1':4},load_seconds=load_seconds,preprocess_seconds=preprocess_seconds,timings=timings,parity={k:parity(outputs['cpu'][k],outputs['mps'][k]) for k in outputs['cpu']},class_changes=int(np.sum((outputs['cpu']['scores'][:,1]>=.5)!=(outputs['mps']['scores'][:,1]>=.5))),scores=outputs['mps']['scores'].tolist(),cosines=outputs['mps']['cosines'].tolist(),logits=outputs['mps']['logits'].tolist(),logit_scale=float(model.logit_scale.exp().item()),arrays=dict(path=str(array_path),sha256=sha(array_path),bytes=array_path.stat().st_size),cka_original_adjusted=cka,adjusted_represent=dict(shape=list(adjusted.shape),finite=bool(np.isfinite(adjusted).all())),hybrid_timing_probe=dict(loss=loss,train_step_seconds=head_step,save_seconds=save,reload_seconds=reload,tf_memory=tf_memory),mps_memory=memory())
write('supplement.json',result)
print(json.dumps(result,indent=2))
