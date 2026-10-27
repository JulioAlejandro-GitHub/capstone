from common import *
import tensorflow as tf
from PIL import Image
seeds();tf.keras.utils.set_random_seed(SEED)
tf.config.optimizer.set_experimental_options({'disable_meta_optimizer':True})
gpus=tf.config.list_physical_devices('GPU')
assert gpus,'TensorFlow Metal required for this experiment'
(model,transform,tokenizer),load_seconds=timed(load)
model.to('mps').eval().requires_grad_(False)
before=digest_state(model)
features=np.load(WORK/'original_embeddings.npy',allow_pickle=False)
rows=json.loads((E/'samples.json').read_text())['samples']
train=np.array([r['split_name']=='train' for r in rows]);val=~train
y=np.array([r['label'] for r in rows],dtype=np.float32)[:,None]
head=tf.keras.Sequential([tf.keras.Input(shape=(512,)),tf.keras.layers.Dense(1,activation='sigmoid')])
head.compile(optimizer=tf.keras.optimizers.SGD(learning_rate=.1),loss='binary_crossentropy')
history=[];best=float('inf');selected=None
start=time.perf_counter()
for epoch in range(1,4):
    head.reset_metrics()
    train_loss=float(head.train_on_batch(features[train],y[train]))
    p=head(features[val],training=False).numpy()
    val_loss=float(tf.keras.losses.binary_crossentropy(y[val],p).numpy().mean())
    record=dict(epoch=epoch,loss=train_loss,val_loss=val_loss,val_accuracy=float(((p>=.5)==y[val]).mean()),learning_rate=.1)
    history.append(record)
    checkpoint=WORK/f'linear_epoch_{epoch}.keras'
    if checkpoint.exists():raise FileExistsError(checkpoint)
    head.save(checkpoint)
    if val_loss<best:best=val_loss;selected=checkpoint
elapsed=time.perf_counter()-start
selected_head=tf.keras.models.load_model(selected,compile=False)
pre=selected_head(features[val],training=False).numpy()
assert before==digest_state(model)
# Independent encoder reconstruction from fixed local original and head checkpoint.
(model2,transform2,_),encoder_reload=timed(load)
model2.to('mps').eval().requires_grad_(False)
(x,rows2),preprocessing=timed(lambda:images(transform2))
with torch.no_grad():f2=torch.cat([model2.encode_image(x[i:i+4].to('mps'),normalize=True).cpu() for i in range(0,len(x),4)]).numpy()
(reloaded,head_reload)=timed(lambda:tf.keras.models.load_model(selected,compile=False))
post=reloaded(f2[val],training=False).numpy()
# Actual black-box LIME call through image -> Torch -> numpy -> Keras.
from lime.lime_image import LimeImageExplainer
from skimage.segmentation import slic
calls=[]
def predict_images(batch):
    tensors=torch.stack([transform2(Image.fromarray(np.clip(im,0,255).astype('uint8'))) for im in batch]).to('mps')
    with torch.no_grad():z=model2.encode_image(tensors,normalize=True)
    arr=z.cpu().numpy()
    out=reloaded(arr,training=False).numpy().reshape(-1)
    calls.append(dict(batch=len(batch),torch_device=str(z.device),numpy_detached=not z.requires_grad,finite=bool(np.isfinite(out).all())))
    return np.stack([1-out,out],axis=1)
index=int(np.where(val)[0][0])
with Image.open(ROOT/rows[index]['path']) as im:rgb=np.array(im.convert('RGB').resize((224,224)))
explanation,lime_seconds=timed(lambda:LimeImageExplainer(random_state=SEED).explain_instance(rgb,predict_images,labels=(1,),top_labels=None,num_samples=32,batch_size=4,random_seed=SEED,segmentation_fn=lambda im:slic(im,n_segments=16,compactness=10,start_label=0)),'mps')
# Explicitly show numpy boundary does not preserve graph, while a direct torch graph does.
probe=torch.ones((1,512),device='mps',requires_grad=True)
converted=probe.detach().cpu().numpy();_ = reloaded(converted).numpy()
result=dict(seed=SEED,head='Dense(1,sigmoid), no hidden layers',input_shape=list(head.input_shape),train_count=int(train.sum()),val_count=int(val.sum()),optimizer='Keras SGD',learning_rate=.1,history=history,training_and_epoch_saves_seconds=elapsed,selected_checkpoint=str(selected),checkpoint_sha256=sha(selected),checkpoint_bytes=selected.stat().st_size,load_seconds=load_seconds,encoder_reload_seconds=encoder_reload,head_reload_seconds=head_reload,parity=parity(pre,post),scores_before=pre.tolist(),scores_after=post.tolist(),embeddings_reload_parity=parity(features,f2),encoder_unchanged=before==digest_state(model),gpu_devices=[d.name for d in gpus],head_variable_device=head.weights[0].value.device,lime=dict(perturbations=32,seconds=lime_seconds,calls=calls,weights=[[int(k),float(v)] for k,v in explanation.local_exp[1]],sample_id=rows[index]['sample_id']),autograd_boundary=dict(torch_input_grad_is_none=probe.grad is None,description='detach().cpu().numpy() loses autograd; LIME does not require it'),memory=memory())
write('linear.json',result)
write('linear_composite_manifest.json',dict(original_assets='original_assets.json',original_manifest_sha256=sha(E/'original_assets.json'),head=dict(path=str(selected),sha256=sha(selected),bytes=selected.stat().st_size),embedding=dict(dimension=512,normalization='L2',source='OpenCLIP encode_image projection'),transform=repr(transform2),positive_class=1,class_mapping={'0':'uninfected','1':'parasitized'},decision=dict(threshold=.5,comparison='>='),experimental_only=True))
print(json.dumps({k:result[k] for k in ['history','parity','head_variable_device','encoder_unchanged']},indent=2))
