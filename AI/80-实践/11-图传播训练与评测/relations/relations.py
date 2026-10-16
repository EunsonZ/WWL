"""Typed directed multigraph messages and finite tail completion; NumPy only.

The formal encoder is fixed; only decoder parameters are trained. Target facts
never enter message adjacency, even at validation/test time.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
from pathlib import Path
import platform
import sys
import time
import numpy as np
sys.dont_write_bytecode=True


def load_core(parent):
    spec=importlib.util.spec_from_file_location('wwl_relations_core',Path(parent)/'graph_task.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);return core


def generate(protocol):
    n=protocol['persons'];assert n==protocol['sites']==8
    entities=[{'id':i,'name':f'P{i}','type':'Person'}for i in range(n)]+[{'id':n+i,'name':f'S{i}','type':'Site'}for i in range(n)]
    x=np.zeros((2*n,3));x[:n,2]=1
    theta=2*np.pi*np.arange(n)/n;x[n:,:2]=np.column_stack((np.cos(theta),np.sin(theta)))
    support=[[i,'at',n+i]for i in range(n)];support+= [[t,'at_inv',s]for s,_,t in support.copy()]
    public={'entities':entities,'X':x.tolist(),'message_edges':support,'candidate_entities':list(range(n)),
            'schema':{'at':['Person','Site'],'at_inv':['Site','Person'],'next':['Person','Person']}}
    data={'public':public}
    for split,heads in protocol['query_heads'].items():
        data[split]={'query_heads':heads,'positives':[[head,'next',(head+offset)%n]for head in heads for offset in protocol['positive_clockwise_offsets']]}
    return data


def relation_matrices(public):
    entities=public['entities'];n=len(entities);types=[e['type']for e in entities]
    if [e['id']for e in entities]!=list(range(n)):raise ValueError('entity rows must match consecutive IDs')
    matrices={r:np.zeros((n,n))for r in ('at','at_inv')}
    for source,relation,target in public['message_edges']:
        if relation not in matrices:raise ValueError('only declared support relations may enter messages')
        if not(0<=source<n and 0<=target<n):raise ValueError('entity outside message domain')
        if [types[source],types[target]]!=public['schema'][relation]:raise ValueError('relation violates type schema')
        matrices[relation][target,source]+=1  # receiver row, sender column; multiplicity counts.
    normalized={}
    for relation,b in matrices.items():
        count=b.sum(axis=1,keepdims=True);normalized[relation]=np.divide(b,count,out=np.zeros_like(b),where=count>0)
    return matrices,normalized


def encode(x,normalized,weights,root):
    pre=x@root
    for relation,b in normalized.items():pre+=b@x@weights[relation]
    return pre  # identity activation; generic smooth example, not hidden ReLU.


def encode_backward(x,normalized,weights,root,upstream):
    grads={'root':x.T@upstream};dx=upstream@root.T
    for relation,b in normalized.items():
        grads[relation]=(b@x).T@upstream;dx+=b.T@upstream@weights[relation].T
    return grads,dx


def fixed_embeddings(public,model):
    x=np.asarray(public['X'],float)
    if x.shape!=(len(public['entities']),3)or not np.isfinite(x).all():raise ValueError('expected finite n x 3 features')
    _,b=relation_matrices(public)
    root=np.diag([0.,0.,1.]);weights={'at':np.zeros((3,3)),'at_inv':np.diag([1.,1.,0.])}
    if model=='no_graph':return x@root
    return encode(x,b,weights,root)


def candidates(public,head):
    people=public['candidate_entities']
    if head not in people or any(public['entities'][i]['type']!='Person'for i in people):raise ValueError('Person query/candidates required')
    return [tail for tail in people if tail!=head]


def query_rows(public,part):
    # This function receives only ONE split. Negatives never consult future truth.
    positives={tuple(t)for t in part['positives']};rows=[]
    heads=part['query_heads']
    if len(set(heads))!=len(heads):raise ValueError('duplicate query head')
    for head in heads:
        for tail in candidates(public,head):rows.append((head,tail,int((head,'next',tail)in positives)))
    if any(r!='next'or s not in heads or t not in candidates(public,s)for s,r,t in positives):raise ValueError('invalid target fact')
    return rows


def scores(params,h,rows,model):
    left=h[[row[0]for row in rows]];right=h[[row[1]for row in rows]]
    if model=='distmult':return np.sum(left*params['decoder']*right,axis=1)
    return np.einsum('bi,ij,bj->b',left,params['decoder'],right)


def objective(core,params,h,rows,model,l2):
    logits=scores(params,h,rows,model);y=np.asarray([row[2]for row in rows]);ds=(core.sigmoid(logits)-y)/len(y)
    left=h[[row[0]for row in rows]];right=h[[row[1]for row in rows]]
    if model=='distmult':gradient=np.sum(ds[:,None]*left*right,axis=0)
    else:gradient=np.einsum('b,bi,bj->ij',ds,left,right)
    w=params['decoder'];loss=float(np.mean(np.logaddexp(0,logits)-y*logits)+.5*l2*np.sum(w*w))
    return loss,{'decoder':gradient+l2*w}


def train_one(core,public,train,val,model,protocol,seed):
    h=fixed_embeddings(public,model);tr=query_rows(public,train);va=query_rows(public,val)
    rng=np.random.default_rng(seed+1261);shape=(3,)if model=='distmult'else(3,3)
    params={'decoder':rng.normal(0,protocol['initialization_sd'],shape)};m=np.zeros(shape);v=np.zeros(shape)
    best=None;best_ce=float('inf');epoch=None;trace=[]
    for k in range(1,protocol['epochs']+1):
        _,grad=objective(core,params,h,tr,model,protocol['l2']);g=grad['decoder'];m=.9*m+.1*g;v=.999*v+.001*g*g
        params['decoder']-=protocol['learning_rate']*(m/(1-.9**k))/(np.sqrt(v/(1-.999**k))+1e-8)
        train_ce=objective(core,params,h,tr,model,0)[0];val_ce=objective(core,params,h,va,model,0)[0]
        trace.append({'epoch':k,'train_ce':train_ce,'val_ce':val_ce})
        if val_ce<best_ce:best_ce=val_ce;best=copy.deepcopy(params);epoch=k
    return {'seed':seed,'model':model,'epoch':epoch,'val_ce':best_ce,'params':{k:v.tolist()for k,v in best.items()},'trace':trace}


def train_all(core,public,train,val,protocol,destination):
    # No test parameter, no all-known truth parameter.
    fitted=[train_one(core,public,train,val,model,protocol,seed)for seed in protocol['seeds']for model in protocol['models']]
    core.dump(destination/'checkpoints.json',fitted)
    core.dump(destination/'selection.json',[{k:r[k]for k in ('seed','model','epoch','val_ce')}for r in fitted]);return fitted


def rank(score_map,tail,removed,tolerance):
    target=score_map[tail];others=[value for key,value in score_map.items()if key!=tail and key not in removed]
    greater=sum(value>target+tolerance for value in others);ties=sum(abs(value-target)<=tolerance for value in others)
    return 1+greater+.5*ties


def evaluate(core,public,parts,fitted,protocol,destination):
    raw=[];queries=[];summary=[];barrier=[]
    for item in fitted:
        model=item['model'];h=fixed_embeddings(public,model);params={k:np.asarray(v)for k,v in item['params'].items()}
        for split in ('train','val','test'):
            part=parts[split];rows=query_rows(public,part);logits=scores(params,h,rows,model)
            known=set()
            for visible_split in protocol['filter_policy'][split]:known.update(tuple(t)for t in parts[visible_split]['positives'])
            score_by_head={head:{}for head in part['query_heads']}
            for (head,tail,y),logit in zip(rows,logits):
                score_by_head[head][tail]=float(logit)
                raw.append({'seed':item['seed'],'model':model,'split':split,'head':head,'relation':'next','tail':tail,'y':y,'logit':float(logit),'cross_entropy':float(np.logaddexp(0,logit)-y*logit)})
            local=[]
            for head,relation,tail in part['positives']:
                removed={t for s,r,t in known if s==head and r==relation and t!=tail and t in score_by_head[head]}
                raw_rank=rank(score_by_head[head],tail,set(),protocol['rank_tie_tolerance']);filtered_rank=rank(score_by_head[head],tail,removed,protocol['rank_tie_tolerance'])
                rec={'seed':item['seed'],'model':model,'split':split,'head':head,'relation':relation,'tail':tail,'raw_rank':raw_rank,'filtered_rank':filtered_rank,'removed_tails':sorted(removed),'filter_truth_splits':protocol['filter_policy'][split]};queries.append(rec);local.append(rec)
            summary.append({'seed':item['seed'],'model':model,'split':split,'heads':len(part['query_heads']),'positive_queries':len(local),'candidate_pairs':len(rows),'cross_entropy':float(np.mean([r['cross_entropy']for r in raw[-len(rows):]])),
                'raw_mrr':float(np.mean([1/r['raw_rank']for r in local])),'filtered_mrr':float(np.mean([1/r['filtered_rank']for r in local])),
                'filtered_hits1':float(np.mean([r['filtered_rank']<=1 for r in local])),'filtered_hits3':float(np.mean([r['filtered_rank']<=3 for r in local]))})
    target_edges={tuple(edge)for split in ('train','val','test')for edge in parts[split]['positives']}
    support={tuple(edge)for edge in public['message_edges']}
    for head,relation,tail in sorted(target_edges):barrier.append({'target':[head,relation,tail],'target_in_messages':(head,relation,tail)in support,'inverse_in_messages':(tail,relation+'_inv',head)in support})
    core.dump(destination/'raw_scores.json',raw);core.dump(destination/'query_ranks.json',queries);core.dump(destination/'summary.json',summary);core.dump(destination/'message_barrier.json',barrier)


def run(core,data,protocol,destination):
    start=time.monotonic();fitted=train_all(core,data['public'],data['train'],data['val'],protocol,destination)
    # Test data is first indexed after ALL model/epoch selections have been written.
    evaluate(core,data['public'],{split:data[split]for split in ('train','val','test')},fitted,protocol,destination)
    core.dump(destination/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),'seconds':time.monotonic()-start,'gpu':False,'threads_requested':1})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=('generate','train'));ap.add_argument('--parent',type=Path,default=Path(__file__).resolve().parent.parent);ap.add_argument('--protocol',type=Path,default=Path(__file__).with_name('protocol.json'));ap.add_argument('--inputs',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    core=load_core(args.parent);protocol=core.load(args.protocol)
    if args.output.exists():ap.error('output exists; choose a new path')
    if args.command=='generate':core.dump(args.output,generate(protocol))
    else:
        if args.inputs is None:ap.error('train requires --inputs')
        args.output.mkdir(parents=True);core.dump(args.output/'identity.json',{'source_sha256':core.digest(__file__),'inputs_sha256':core.digest(args.inputs),'protocol_sha256':core.digest(args.protocol),'parent_core_sha256':core.digest(args.parent/'graph_task.py')});core.dump(args.output/'protocol.json',protocol);run(core,core.load(args.inputs),protocol,args.output)

if __name__=='__main__':main()
