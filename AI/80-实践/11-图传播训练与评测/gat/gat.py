"""Dense classical GAT: masked row softmax, shared additive scores, multi-head.

Two-layer binary node task on published fixed independent graphs. NumPy only.
Uniform attention control shares value shapes/initialization, not effective budget.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import math
from pathlib import Path
import platform
import sys
import time
import numpy as np

sys.dont_write_bytecode=True


def load_core(parent):
    spec=importlib.util.spec_from_file_location('wwl_gat_core',Path(parent)/'graph_task.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def allowed_mask(a):
    if a.ndim!=3 or a.shape[1]!=a.shape[2] or not np.isin(a,[0,1]).all():
        raise ValueError('A must be batched binary square adjacency')
    if not np.array_equal(a,a.transpose(0,2,1)) or np.diagonal(a,axis1=1,axis2=2).any():
        raise ValueError('undirected input without self loops required')
    return (a+np.eye(a.shape[1]))>0


def masked_softmax(scores,mask):
    if scores.shape!=mask.shape or not mask.any(axis=-1).all():
        raise ValueError('matching nonempty row masks required')
    centered=np.where(mask,scores,-np.inf)
    centered=centered-centered.max(axis=-1,keepdims=True)
    exponent=np.exp(centered)
    return exponent/exponent.sum(axis=-1,keepdims=True)


def initialize(input_dim,protocol,seed):
    rng=np.random.default_rng(seed+1237);params={}
    shapes=[(input_dim,protocol['hidden_per_head'],protocol['hidden_heads']),
            (protocol['hidden_per_head']*protocol['hidden_heads'],1,protocol['output_heads'])]
    for layer,(d,width,heads)in enumerate(shapes):
        for k in range(heads):
            tag=f'{layer}_{k}'
            params['w'+tag]=rng.normal(0,1/math.sqrt(d),(d,width))
            params['l'+tag]=rng.normal(0,1/math.sqrt(width),width)
            params['r'+tag]=rng.normal(0,1/math.sqrt(width),width)
            params['b'+tag]=np.zeros(width)
    return params


def head_forward(x,params,tag,mask,variant,slope):
    z=x@params['w'+tag]
    raw=(z@params['l'+tag])[...,None]+(z@params['r'+tag])[:,None,:]
    if variant=='attention':
        scores=np.where(raw>0,raw,slope*raw)
        alpha=masked_softmax(scores,mask)
    elif variant=='uniform':
        alpha=mask/mask.sum(axis=-1,keepdims=True)
    else:
        raise ValueError('variant must be attention or uniform')
    output=alpha@z+params['b'+tag]
    return output,(z,raw,alpha)


def forward(params,a,x,variant,protocol):
    """No graph ID, labels, split or seed enters this deterministic interface."""
    mask=allowed_mask(a);h=x;cache=[]
    for layer,heads in enumerate((protocol['hidden_heads'],protocol['output_heads'])):
        blocks=[];head_cache=[]
        for k in range(heads):
            output,details=head_forward(h,params,f'{layer}_{k}',mask,variant,protocol['leaky_slope'])
            blocks.append(output);head_cache.append(details)
        if layer==0:
            pre=np.concatenate(blocks,axis=-1)
            # minimum avoids evaluating exp(large positive) in the unused branch.
            new_h=np.where(pre>0,pre,np.expm1(np.minimum(pre,0)))
        else:
            pre=np.mean(blocks,axis=0);new_h=pre
        cache.append((h,head_cache,pre));h=new_h
    return h[...,0],cache


def weight_names(params,variant):
    return [key for key in params if key.startswith('w')or(variant=='attention'and key[0]in('l','r'))]


def objective(params,a,x,y,variant,protocol):
    logits,cache=forward(params,a,x,variant,protocol)
    if y.shape!=logits.shape or not np.isin(y,[0,1]).all():
        raise ValueError('binary label shape must equal G,N logits')
    l2=protocol['l2'];weights=weight_names(params,variant)
    loss=float(np.mean(np.logaddexp(0,logits)-y*logits))+.5*l2*sum(float((params[k]**2).sum())for k in weights)
    dh=((np.exp(-np.logaddexp(0,-logits))-y)/y.size)[...,None]
    grad={k:np.zeros_like(v)for k,v in params.items()}
    for layer in (1,0):
        inp,heads,pre=cache[layer]
        if layer==0:
            dh=dh*np.where(pre>0,1,np.exp(np.minimum(pre,0)))
            widths=[details[0].shape[-1]for details in heads]
            pieces=np.split(dh,np.cumsum(widths)[:-1],axis=-1)
        else:
            pieces=[dh/len(heads)for _ in heads]
        upstream=np.zeros_like(inp)
        for k,((z,raw,alpha),u)in enumerate(zip(heads,pieces)):
            tag=f'{layer}_{k}';grad['b'+tag]=u.sum(axis=(0,1))
            dz=alpha.transpose(0,2,1)@u  # value path: collect all receiving rows.
            if variant=='attention':
                dalpha=np.einsum('gif,gjf->gij',u,z)
                de=alpha*(dalpha-np.sum(alpha*dalpha,axis=-1,keepdims=True))
                draw=de*np.where(raw>0,1,protocol['leaky_slope'])
                # Nonedges have alpha=0, hence exact zero draw despite dense storage.
                dleft=draw.sum(axis=-1);dright=draw.sum(axis=-2)
                grad['l'+tag]=np.einsum('gn,gnf->f',dleft,z)
                grad['r'+tag]=np.einsum('gn,gnf->f',dright,z)
                dz+=dleft[...,None]*params['l'+tag]+dright[...,None]*params['r'+tag]
            grad['w'+tag]=np.einsum('gni,gnj->ij',inp,dz)
            upstream+=dz@params['w'+tag].T
        dh=upstream
    for key in weights:grad[key]+=l2*params[key]
    return loss,grad


def train_one(core,train,val,protocol,seed,variant):
    a,x=core.arrays([{'A':g['A'],'X':g['X']}for g in train]);y=np.asarray([g['y']for g in train])
    va,vx=core.arrays([{'A':g['A'],'X':g['X']}for g in val]);vy=np.asarray([g['y']for g in val])
    p=initialize(x.shape[-1],protocol,seed);m={k:np.zeros_like(v)for k,v in p.items()};v=copy.deepcopy(m)
    best,score,epoch=None,math.inf,None;trace=[];start=time.monotonic()
    for step in range(1,protocol['epochs']+1):
        _,grad=objective(p,a,x,y,variant,protocol)
        for key in p:
            m[key]=.9*m[key]+.1*grad[key];v[key]=.999*v[key]+.001*grad[key]**2
            p[key]-=protocol['learning_rate']*(m[key]/(1-.9**step))/(np.sqrt(v[key]/(1-.999**step))+1e-8)
        tr=forward(p,a,x,variant,protocol)[0];vl=forward(p,va,vx,variant,protocol)[0]
        train_ce=float(np.mean(np.logaddexp(0,tr)-y*tr));val_ce=float(np.mean(np.logaddexp(0,vl)-vy*vl))
        trace.append({'epoch':step,'train_ce':train_ce,'val_ce':val_ce})
        if val_ce<score:best,score,epoch=copy.deepcopy(p),val_ce,step
    return best,score,epoch,trace,time.monotonic()-start


def fixtures():
    a=np.zeros((1,3,3));a[0,0,1]=a[0,1,0]=a[0,1,2]=a[0,2,1]=1
    x=np.array([[[1.],[0.],[2.]]]);p={'w0_0':np.ones((1,1)),'l0_0':np.ones(1),'r0_0':np.ones(1),'b0_0':np.zeros(1)}
    output,(z,raw,alpha)=head_forward(x,p,'0_0',allowed_mask(a),'attention',.2)
    # Finite static-ranking demonstration: queries -2,+2, common keys -1,+1.
    queries=np.array([-2.,2.]);keys=np.array([-1.,1.]);raw_rank=queries[:,None]+keys[None,:]
    scores=np.where(raw_rank>0,raw_rank,.2*raw_rank)
    rank_alpha=masked_softmax(scores,np.ones_like(scores,dtype=bool))
    return {'path':{'A':a[0].tolist(),'X':x[0].tolist(),'Z':z[0].tolist(),'raw_scores':raw[0].tolist(),
                    'alpha':alpha[0].tolist(),'head_output':output[0].tolist(),'self_included':True},
            'ranking':{'queries':queries.tolist(),'common_keys':keys.tolist(),'raw':raw_rank.tolist(),
                       'alpha_conditioned_on_common_two_keys':rank_alpha.tolist(),
                       'note':'conditional common-key softmax only; full GAT rows also include self; ranking among shared keys remains the same'}}


def run(core,parent,protocol,destination):
    inputs=core.load(parent/'inputs.json');trained=[];selection=[];start=time.monotonic()
    for seed in protocol['seeds']:
        for regime in protocol['regimes']:
            group=[g for g in inputs['graphs']if g['seed']==seed and g['regime']==regime]
            train=[g for g in group if g['split']=='train'];val=[g for g in group if g['split']=='val']
            for variant in protocol['variants']:
                p,score,epoch,trace,seconds=train_one(core,train,val,protocol,seed,variant)
                item={'seed':seed,'regime':regime,'variant':variant,'epoch':epoch,'val_ce':score,
                      'params':{k:v.tolist()for k,v in p.items()},'trace':trace,'train_seconds':seconds}
                trained.append(item);selection.append({k:item[k]for k in ('seed','regime','variant','epoch','val_ce')})
    core.dump(destination/'selection.json',selection);core.dump(destination/'checkpoints.json',trained)
    raw=[];summary=[]
    for item in trained:
        p={k:np.asarray(v)for k,v in item['params'].items()}
        for split in ('train','val','test'):
            rows=[g for g in inputs['graphs']if g['seed']==item['seed']and g['regime']==item['regime']and g['split']==split]
            a,x=core.arrays([{'A':g['A'],'X':g['X']}for g in rows])
            logits,_=forward(p,a,x,item['variant'],protocol);y=np.asarray([g['y']for g in rows]);stats=core.metrics(y,logits)
            for g,lg,stat in zip(rows,logits,stats):raw.append({k:item[k]for k in ('seed','regime','variant')}|{'graph_id':g['id'],'split':split,'y':g['y'],'logits':lg.tolist(),**stat})
            summary.append({k:item[k]for k in ('seed','regime','variant','epoch')}|{'split':split,
                'accuracy':float(np.mean([r['accuracy']for r in stats])),'cross_entropy':float(np.mean([r['cross_entropy']for r in stats])),
                'graph_accuracy_min':min(r['accuracy']for r in stats),'graph_accuracy_max':max(r['accuracy']for r in stats)})
    core.dump(destination/'raw_predictions.json',raw);core.dump(destination/'summary.json',summary)
    # Read both published controls only AFTER all new GAT decisions are frozen.
    no_graph=core.load(parent/'graphsage/results/baseline_reference.json')
    sage_selection=[r for r in core.load(parent/'graphsage/results/selection.json')if r['fanout']is None]
    sage_raw=[r for r in core.load(parent/'graphsage/results/raw_predictions.json')if r['fanout']is None and any(all(r[k]==s[k]for k in ('seed','regime','depth'))for s in sage_selection)]
    core.dump(destination/'baseline_reference.json',{'no_graph':no_graph,'sage_full':{'selection':sage_selection,'raw_predictions':sage_raw},'note':'published controls reused, not retrained; budgets differ'})
    core.dump(destination/'fixtures.json',fixtures())
    core.dump(destination/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),
        'seconds':time.monotonic()-start,'threads_requested':1,'gpu':False})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--parent',type=Path,default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--protocol',type=Path,default=Path(__file__).with_name('protocol.json'));ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False);core=load_core(args.parent);protocol=core.load(args.protocol)
    files={'gat_source':Path(__file__),'protocol':args.protocol,'inputs':args.parent/'inputs.json','core':args.parent/'graph_task.py',
           'published_no_graph':args.parent/'graphsage/results/baseline_reference.json','published_sage_selection':args.parent/'graphsage/results/selection.json','published_sage_raw':args.parent/'graphsage/results/raw_predictions.json'}
    core.dump(args.output/'identity.json',{key+'_sha256':core.digest(path)for key,path in files.items()});core.dump(args.output/'protocol.json',protocol)
    run(core,args.parent,protocol,args.output)


if __name__=='__main__':main()
