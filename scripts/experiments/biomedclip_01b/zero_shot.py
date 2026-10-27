from common import *
import platform,importlib.metadata as meta
seeds()
(model,transform,tokenizer),load_seconds=timed(load)
(x,rows),preprocess_seconds=timed(lambda:images(transform))
tokens=tokenizer(PROMPTS,context_length=256)
result=dict(seed=SEED,prompts=PROMPTS,class_order=['uninfected','parasitized'],threshold=0.5,score_meaning='relative prompt softmax, not clinically calibrated probability',load_seconds=load_seconds,preprocess_seconds=preprocess_seconds,transform=repr(transform),tokens=tokens.tolist(),parameter_count=sum(p.numel() for p in model.parameters()),dtype=str(next(model.parameters()).dtype),environment={p:meta.version(p) for p in ['torch','torchvision','open_clip_torch','transformers','timm','huggingface-hub','tokenizers','numpy']},devices={},benchmarks=[])
outputs={}
for device in ['cpu','mps']:
    _,transfer=timed(lambda:model.to(device),device)
    inputs=x[:8].to(device);text=tokens.to(device)
    def forward():
        with torch.no_grad():
            v,t,scale=model(inputs,text)
            cosine=v@t.T;logits=scale*cosine;scores=logits.softmax(-1)
        return v,t,cosine,logits,scores,scale
    out,elapsed=timed(forward,device)
    outputs[device]=[v.detach().cpu().numpy() for v in out]
    result['devices'][device]=dict(transfer_seconds=transfer,inference_seconds=elapsed,images_per_second=8/elapsed,image_device=str(out[0].device),text_device=str(out[1].device),logits_device=str(out[3].device),scale=float(out[5].item()),scores=outputs[device][4].tolist(),predictions=(outputs[device][4][:,1]>=.5).astype(int).tolist(),memory=memory() if device=='mps' else None)
    for batch in [1,4,8]:
        inp=x[:batch].to(device)
        def visual():
            with torch.no_grad():return model.encode_image(inp,normalize=True)
        for _ in range(2):timed(visual,device)
        times=[timed(visual,device)[1] for _ in range(5)]
        result['benchmarks'].append(dict(device=device,batch=batch,seconds=times,median=float(np.median(times)),p95=float(np.percentile(times,95)),images_per_second=batch/float(np.median(times)),memory=memory() if device=='mps' else None))
result['parity']={key:parity(a,b) for key,a,b in zip(['image_embeddings','text_embeddings','cosine','logits','scores','logit_scale'],outputs['cpu'],outputs['mps'])}
result['class_changes']=int(np.sum((outputs['cpu'][4][:,1]>=.5)!=(outputs['mps'][4][:,1]>=.5)))
result['threshold_margins']=np.abs(outputs['mps'][4][:,1]-.5).tolist()
# Actual MPS image/token gradients for positive text similarity.
model.requires_grad_(False)
captured={}
def hook(module,inputs,output):
    captured['tokens']=output;output.retain_grad()
handle=model.visual.trunk.blocks[-1].norm1.register_forward_hook(hook)
img=x[:1].to('mps').detach().requires_grad_(True)
v=model.encode_image(img,normalize=True);v.retain_grad()
with torch.no_grad(): t=model.encode_text(tokens.to('mps'),normalize=True)
objective=(v@t[1:2].T).sum()
_,backward=timed(lambda:objective.backward(),'mps')
result['xai']=dict(objective='positive prompt cosine similarity',layer='visual.trunk.blocks.11.norm1',input_grad_finite=bool(torch.isfinite(img.grad).all()),input_grad_abs_sum=float(img.grad.abs().sum().item()),embedding_grad_abs_sum=float(v.grad.abs().sum().item()),tokens_shape=list(captured['tokens'].shape),token_grad_abs_sum=float(captured['tokens'].grad.abs().sum().item()),backward_seconds=backward,device=str(img.grad.device))
handle.remove()
model.zero_grad(set_to_none=True)
# Extract all governed rows in batches, frozen original.
before=digest_state(model)
def extract():
    with torch.no_grad():return torch.cat([model.encode_image(x[i:i+4].to('mps'),normalize=True).cpu() for i in range(0,len(x),4)]).numpy()
features,seconds=timed(extract,'mps')
assert np.isfinite(features).all() and features.shape==(len(rows),512)
assert before==digest_state(model)
np.save(WORK/'original_embeddings.npy',features,allow_pickle=False)
result['represent']=dict(shape=list(features.shape),finite=bool(np.isfinite(features).all()),norm_range=[float(np.linalg.norm(features,axis=1).min()),float(np.linalg.norm(features,axis=1).max())],seconds=seconds,encoder_unchanged=True)
write('zero_shot.json',result)
print(json.dumps({'parity':result['parity'],'xai':result['xai'],'represent':result['represent']},indent=2))
