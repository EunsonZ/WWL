"""Graph labels, exact unlabeled identity grouping, readout and bounded fixed heads.

No old attention/SAGE retraining. Reuses only parent JSON/validation utilities.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import itertools
import math
from pathlib import Path
import platform
import sys
import time
import numpy as np
sys.dont_write_bytecode=True


def load_core(parent):
    spec=importlib.util.spec_from_file_location('wwl_graphlevel_core',Path(parent)/'graph_task.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def canonical(a,cap=10000):
    """Exact minimum adjacency code among degree-respecting orders, ignoring marks.

    Sorting degrees fixes the block order; every isomorphism preserves degrees.
    The cap rejects expensive candidates; it never substitutes a heuristic hash.
    """
    n=len(a);degrees=np.sum(a,axis=1).astype(int).tolist();groups=[]
    for degree in sorted(set(degrees)):groups.append([i for i,d in enumerate(degrees)if d==degree])
    count=math.prod(math.factorial(len(group))for group in groups)
    if count>cap:raise ValueError('exact canonical permutation cap exceeded')
    best=None
    for blocks in itertools.product(*(itertools.permutations(group)for group in groups)):
        order=tuple(i for block in blocks for i in block)
        code=''.join(str(int(a[order[i],order[j]]))for i in range(n)for j in range(i+1,n))
        if best is None or code<best:best=code
    return str(n)+':'+best


def connected(a):
    reached={0};pending=[0]
    while pending:
        i=pending.pop()
        for j in np.flatnonzero(a[i]):
            if int(j)not in reached:reached.add(int(j));pending.append(int(j))
    return len(reached)==len(a)


def generate(protocol):
    seen=set();rows=[];attempts=0;cap_rejections=0
    for seed in protocol['seeds']:
        rng=np.random.default_rng(seed)
        for n in protocol['nodes']:
            for split,count in protocol['graphs_per_size_and_seed'].items():
                for index in range(count):
                    desired=index%2
                    for _ in range(50000):
                        attempts+=1
                        upper=np.triu((rng.random((n,n))<protocol['edge_probability']).astype(int),1)
                        a=upper+upper.T
                        if not connected(a):continue
                        marked=rng.choice(n,2,replace=False);y=int(a[marked[0],marked[1]])
                        if y!=desired:continue
                        try:key=canonical(a,protocol['canonical_permutation_cap'])
                        except ValueError:cap_rejections+=1;continue
                        if key in seen:continue
                        seen.add(key);x=np.zeros((n,1));x[marked,0]=1
                        rows.append({'id':f'{seed}-{n}-{split}-{index}','group_id':key,'seed':seed,'split':split,
                                     'A':a.tolist(),'X':x.tolist(),'y':y,'nodes':n});break
                    else:raise RuntimeError('could not fill prescribed topology-distinct slot')
    return {'schema':'wwl-graphlevel-input-v1','graphs':rows,'generation':{'attempts':attempts,'cap_rejections':cap_rejections,
        'identity_scope':'unlabeled topology globally distinct across ALL seeds/splits; marks ignored',
        'sampling_warning':'class-balanced rejection and global exclusion do not produce an iid graph sample'}}


def visible(core,graph):
    a,x=core.arrays([{'A':graph['A'],'X':graph['X']}]);return a[0],x[0]


def local_features(a,x):
    return np.concatenate((x,a@x),axis=1)


def fixed_features(a,x,model,scale):
    if model=='bag':return np.array([len(x)/scale,float(x.mean()),float(x.max()),1.])
    if model=='fixed':
        # Task-specific constructive witness; no labels enter this function.
        q=a@x;psi=float(np.maximum(2*x+q-2.5,0).sum())
        return np.array([psi,1.])
    raise ValueError('unknown fixed model')


def pool(h,mode,scale):
    if mode=='sum':return h.sum(axis=0)/scale
    if mode=='mean':return h.mean(axis=0)
    if mode=='max':return h.max(axis=0)
    raise ValueError('readout must be sum/mean/max')


def pool_backward(h,upstream,mode,scale):
    if mode=='sum':return np.broadcast_to(upstream/scale,h.shape).copy()
    if mode=='mean':return np.broadcast_to(upstream/len(h),h.shape).copy()
    ties=(h==h.max(axis=0));return ties*upstream/ties.sum(axis=0)


def initialize(protocol,seed):
    rng=np.random.default_rng(seed+809)
    return {'w':rng.normal(0,.5,(2,protocol['hidden'])),'b':rng.normal(0,.05,protocol['hidden']),
            'head':rng.normal(0,.2,protocol['hidden']+1)}


def forward(params,graphs,model,protocol,core):
    logits=[];cache=[]
    for graph in graphs:
        a,x=visible(core,graph)
        if model in('bag','fixed'):
            features=fixed_features(a,x,model,protocol['sum_scale']);logits.append(features@params['head']);cache.append(features)
        else:
            c=local_features(a,x);pre=c@params['w']+params['b'];h=np.maximum(pre,0)
            r=pool(h,model,protocol['sum_scale']);features=np.r_[r,1.]
            logits.append(features@params['head']);cache.append((c,pre,h,features))
    return np.asarray(logits),cache


def objective(params,graphs,y,model,protocol,core):
    logits,cache=forward(params,graphs,model,protocol,core)
    if y.shape!=logits.shape or not np.isin(y,[0,1]).all():raise ValueError('one binary label per graph required')
    l2=protocol['l2'];loss=float(np.mean(np.logaddexp(0,logits)-y*logits))+.5*l2*sum(float((v*v).sum())for v in params.values())
    ds=(core.sigmoid(logits)-y)/len(y);grad={k:np.zeros_like(v)for k,v in params.items()}
    for derivative,record in zip(ds,cache):
        if model in('bag','fixed'):grad['head']+=derivative*record
        else:
            c,pre,h,features=record;grad['head']+=derivative*features
            dh=pool_backward(h,derivative*params['head'][:-1],model,protocol['sum_scale'])
            dq=dh*(pre>0);grad['w']+=c.T@dq;grad['b']+=dq.sum(axis=0)
    for key in params:grad[key]+=l2*params[key]
    return loss,grad


def project(value,bound):
    return value*min(1,bound/max(float(np.linalg.norm(value)),1e-300))


def solve_fixed(core,train,model,protocol):
    a,x=visible(core,train[0]);d=len(fixed_features(a,x,model,protocol['sum_scale']));params={'head':np.zeros(d)}
    visible_rows=[{'A':r['A'],'X':r['X']}for r in train];y=np.asarray([r['y']for r in train]);rmax=max(np.linalg.norm(fixed_features(*visible(core,g),model,protocol['sum_scale']))for g in train)
    step=1/(.25*rmax*rmax+protocol['l2']);gap=math.inf
    for iteration in range(1,protocol['fixed_solver_steps']+1):
        _,gradient=objective(params,visible_rows,y,model,protocol,core);g=gradient['head']
        gap=float(g@params['head']+protocol['head_norm_bound']*np.linalg.norm(g))
        if gap<=protocol['fixed_solver_gap_tolerance']:break
        params['head']=project(params['head']-step*g,protocol['head_norm_bound'])
    # Recompute certificate at the actual returned parameters, including limit exit.
    loss,gradient=objective(params,visible_rows,y,model,protocol,core);g=gradient['head']
    gap=float(g@params['head']+protocol['head_norm_bound']*np.linalg.norm(g))
    return params,{'steps':iteration,'regularized_train_loss':loss,'convex_gap_upper_bound':gap,'head_norm':float(np.linalg.norm(params['head']))}


def train_joint(core,train,val,model,protocol,seed):
    tr=[{'A':g['A'],'X':g['X']}for g in train];va=[{'A':g['A'],'X':g['X']}for g in val]
    y=np.asarray([g['y']for g in train]);vy=np.asarray([g['y']for g in val]);params=initialize(protocol,seed)
    m={k:np.zeros_like(v)for k,v in params.items()};v=copy.deepcopy(m)
    best,score,epoch=None,math.inf,None;trace=[]
    for k in range(1,protocol['epochs']+1):
        _,grad=objective(params,tr,y,model,protocol,core)
        for key in params:
            m[key]=.9*m[key]+.1*grad[key];v[key]=.999*v[key]+.001*grad[key]**2
            params[key]-=protocol['learning_rate']*(m[key]/(1-.9**k))/(np.sqrt(v[key]/(1-.999**k))+1e-8)
        params['head']=project(params['head'],protocol['head_norm_bound'])
        tl=forward(params,tr,model,protocol,core)[0];vl=forward(params,va,model,protocol,core)[0]
        tc=float(np.mean(np.logaddexp(0,tl)-y*tl));vc=float(np.mean(np.logaddexp(0,vl)-vy*vl))
        trace.append({'epoch':k,'train_ce':tc,'val_ce':vc})
        if vc<score:best,score,epoch=copy.deepcopy(params),vc,k
    return best,epoch,score,trace


def run(core,inputs,protocol,destination):
    start=time.monotonic();trained=[];selection=[]
    for seed in protocol['seeds']:
        rows=[g for g in inputs['graphs']if g['seed']==seed];tr=[g for g in rows if g['split']=='train'];va=[g for g in rows if g['split']=='val']
        for model in protocol['models']:
            if model in('bag','fixed'):
                p,certificate=solve_fixed(core,tr,model,protocol);epoch=None;trace=[]
                score=None
            else:p,epoch,score,trace=train_joint(core,tr,va,model,protocol,seed);certificate=None
            item={'seed':seed,'model':model,'epoch':epoch,'val_ce':score,'trace':trace,'certificate':certificate,'params':{k:v.tolist()for k,v in p.items()}}
            trained.append(item);selection.append({k:item[k]for k in('seed','model','epoch','val_ce','certificate')})
    core.dump(destination/'selection.json',selection);core.dump(destination/'checkpoints.json',trained)
    raw=[];summary=[];permutation=[]
    for item in trained:
        p={k:np.asarray(v)for k,v in item['params'].items()};model=item['model']
        for split in('train','val','test'):
            rows=[g for g in inputs['graphs']if g['seed']==item['seed']and g['split']==split]
            visible_rows=[{'A':g['A'],'X':g['X']}for g in rows];logits,_=forward(p,visible_rows,model,protocol,core)
            y=np.asarray([g['y']for g in rows]);correct=(logits>=0)==y;ce=np.logaddexp(0,logits)-y*logits
            for g,lg,ok,loss in zip(rows,logits,correct,ce):raw.append({'seed':item['seed'],'model':model,'graph_id':g['id'],'group_id':g['group_id'],'split':split,'nodes':g['nodes'],'y':g['y'],'logit':float(lg),'correct':int(ok),'cross_entropy':float(loss)})
            summary.append({'seed':item['seed'],'model':model,'split':split,'graphs':len(rows),'accuracy':float(correct.mean()),'cross_entropy':float(ce.mean()),'per_size':{str(n):{'graphs':sum(g['nodes']==n for g in rows),'accuracy':float(correct[[g['nodes']==n for g in rows]].mean())}for n in protocol['nodes']}})
            for g,lg in zip(rows,logits):
                order=list(reversed(range(g['nodes'])));a=np.asarray(g['A']);x=np.asarray(g['X'])
                moved={'A':a[order][:,order].tolist(),'X':x[order].tolist()}
                new=forward(p,[moved],model,protocol,core)[0][0]
                permutation.append({'seed':item['seed'],'model':model,'graph_id':g['id'],'split':split,'logit_difference':float(new-lg)})
    core.dump(destination/'raw_predictions.json',raw);core.dump(destination/'summary.json',summary);core.dump(destination/'permutation_audit.json',permutation)
    core.dump(destination/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),'seconds':time.monotonic()-start,'gpu':False,'threads_requested':1})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=('generate','train'));ap.add_argument('--parent',type=Path,default=Path(__file__).resolve().parent.parent);ap.add_argument('--protocol',type=Path,default=Path(__file__).with_name('protocol.json'));ap.add_argument('--inputs',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();core=load_core(args.parent);protocol=core.load(args.protocol)
    if args.output.exists():ap.error('output exists; choose a new path')
    if args.command=='generate':core.dump(args.output,generate(protocol))
    else:
        if args.inputs is None:ap.error('train requires --inputs')
        args.output.mkdir(parents=True)
        core.dump(args.output/'identity.json',{'source_sha256':core.digest(__file__),'inputs_sha256':core.digest(args.inputs),'protocol_sha256':core.digest(args.protocol),'parent_core_sha256':core.digest(args.parent/'graph_task.py')})
        core.dump(args.output/'protocol.json',protocol);run(core,core.load(args.inputs),protocol,args.output)


if __name__=='__main__':main()
