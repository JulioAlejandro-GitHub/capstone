from common import *
seeds()
(model,transform,_),load_seconds=timed(load)
(x,rows),preprocess_seconds=timed(lambda:images(transform))
ix=[i for i,r in enumerate(rows) if r['split_name']=='train']
# One image per class for the two controlled updates.
ix=[next(i for i in ix if rows[i]['label']==label) for label in [0,1]]
x=x[ix].to('mps');y=torch.tensor([rows[i]['label'] for i in ix],dtype=torch.float32,device='mps')[:,None]
model.to('mps').eval().requires_grad_(False)
head=torch.nn.Linear(512,1).to('mps')
original=digest_state(model);head_before=digest_state(head)
opt=torch.optim.AdamW(head.parameters(),lr=1e-3,weight_decay=0.0)
def update(optimizer):
    optimizer.zero_grad(set_to_none=True)
    logits,forward_seconds=timed(lambda:head(model.encode_image(x,normalize=True)),'mps')
    loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y)
    _,backward_seconds=timed(loss.backward,'mps')
    _,step_seconds=timed(optimizer.step,'mps')
    return dict(loss=float(loss.item()),forward_seconds=forward_seconds,backward_seconds=backward_seconds,step_seconds=step_seconds,device=str(logits.device),dtype=str(logits.dtype),memory=memory())
first=update(opt)
after_head=digest_state(model)
assert original==after_head and head_before!=digest_state(head)
block=model.visual.trunk.blocks[-1]
block.requires_grad_(True)
names=[n for n,p in model.named_parameters() if p.requires_grad]
opt=torch.optim.AdamW([{'params':head.parameters(),'lr':1e-3},{'params':block.parameters(),'lr':1e-5}],weight_decay=0.0)
second=update(opt)
after=digest_state(model)
changed=[n for n in original if original[n]!=after[n]]
assert changed and all(n in names for n in changed)
assert all(original[n]==after[n] for n in original if n not in names)
with torch.no_grad():pre=head(model.encode_image(x,normalize=True)).sigmoid().cpu().numpy()
checkpoint=WORK/'fine_tuning.pt'
assert not checkpoint.exists()
_,save_seconds=timed(lambda:torch.save({'visual':{n:v.cpu() for n,v in model.visual.state_dict().items()},'head':{n:v.cpu() for n,v in head.state_dict().items()},'seed':SEED,'trainable_names':names},checkpoint),'mps')
(reloaded,_,_),model_reload_seconds=timed(load)
state,checkpoint_load_seconds=timed(lambda:torch.load(checkpoint,map_location='cpu',weights_only=True))
reloaded.visual.load_state_dict(state['visual'],strict=True)
head2=torch.nn.Linear(512,1);head2.load_state_dict(state['head'],strict=True)
reloaded.to('mps').eval();head2.to('mps').eval()
with torch.no_grad():post=head2(reloaded.encode_image(x,normalize=True)).sigmoid().cpu().numpy()
# Gradient/activation feasibility after fine tuning.
reloaded.requires_grad_(False);head2.requires_grad_(False)
capture={}
def hook(m,args,out):capture['activation']=out;out.retain_grad()
h=reloaded.visual.trunk.blocks[-1].norm1.register_forward_hook(hook)
input_image=x[:1].detach().requires_grad_(True)
score=head2(reloaded.encode_image(input_image,normalize=True)).sum()
_,gradient_seconds=timed(score.backward,'mps')
xai=dict(layer='visual.trunk.blocks.11.norm1',activation_shape=list(capture['activation'].shape),activation_finite=bool(torch.isfinite(capture['activation']).all()),token_grad_abs_sum=float(capture['activation'].grad.abs().sum().item()),image_grad_abs_sum=float(input_image.grad.abs().sum().item()),gradient_device=str(input_image.grad.device),seconds=gradient_seconds)
h.remove()
with torch.no_grad():emb=reloaded.encode_image(x,normalize=True).cpu().numpy()
original_files=json.loads((E/'original_assets.json').read_text())
original_intact=all(sha(f['path'])==f['sha256'] for a in original_files for f in a['files'])
result=dict(seed=SEED,load_seconds=load_seconds,preprocess_seconds=preprocess_seconds,loss='BCEWithLogits',optimizer='torch.optim.AdamW',weight_decay=0.0,head_lr=.001,visual_block_lr=.00001,training_mode='eval tower (dropout disabled), gradients enabled for selected block; technical update only',head_update=first,block_update=second,encoder_unchanged_after_head=original==after_head,trainable_names=names,changed_names=changed,frozen_unchanged=True,head_changed=head_before!=digest_state(head),checkpoint=dict(path=str(checkpoint),sha256=sha(checkpoint),bytes=checkpoint.stat().st_size,save_seconds=save_seconds,model_reload_seconds=model_reload_seconds,checkpoint_load_seconds=checkpoint_load_seconds),parity=parity(pre,post),scores_before=pre.tolist(),scores_after=post.tolist(),xai=xai,represent=dict(shape=list(emb.shape),finite=bool(np.isfinite(emb).all())),original_files_intact=original_intact)
write('fine_tuning.json',result)
print(json.dumps({k:result[k] for k in ['head_update','block_update','parity','xai','original_files_intact']},indent=2))
