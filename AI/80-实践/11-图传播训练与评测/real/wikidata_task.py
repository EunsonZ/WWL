"""Real Wikidata panel: provenance, supervised relation features and tail ranks.

One static transductive graph, not iid graph samples or temporal evaluation.
Only decoder heads train. Reuses published relation encode/score/loss/rank APIs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
sys.dont_write_bytecode=True


def load_modules(parent):
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    return module('wwl_real_core',Path(parent)/'graph_task.py'),module('wwl_real_relations',Path(parent)/'relations/relations.py')


def split_for(qid,protocol):
    bucket=int(hashlib.sha256((protocol['split_salt']+':'+qid).encode()).hexdigest(),16)%10
    return 'train'if bucket<6 else'val'if bucket<8 else'test'


def normalize(source,panel,protocol):
    qids=panel['entities'];continents=panel['candidate_continents']
    if len(qids)!=len(set(qids))or set(qids)&set(continents):raise ValueError('panel entity identity collision')
    records={};labels={};used=[];discarded=[];raw_facts={'P30':[],'P47':[]}
    for rec in source['responses']:
        if hashlib.sha256(rec['body'].encode()).hexdigest()!=rec['sha256']:raise ValueError('source body hash mismatch')
        key=(rec['entity'],rec['property'])
        if key in records:raise ValueError('duplicate source response key')
        records[key]=rec;data=json.loads(rec['body'])
        if rec['property']=='label':labels[rec['entity']]=data
    for qid in qids:
        for prop in ('P30','P47'):
            data=json.loads(records[qid,prop]['body']);statements=data.get(prop,[])
            best='preferred'if any(s['rank']=='preferred'for s in statements)else'normal'
            for statement in statements:
                value=statement['value'];reason=None
                if statement['rank']!=best:reason='not best nondeprecated rank'
                elif value['type']!='value'or not isinstance(value.get('content'),str)or not value['content'].startswith('Q'):reason='not concrete entity value'
                entry={'head':qid,'property':prop,'statement_id':statement['id'],'rank':statement['rank'],'value':value.get('content'),'qualifiers_present':bool(statement.get('qualifiers'))}
                if reason:discarded.append(dict(entry,reason=reason));continue
                raw_facts[prop].append((qid,value['content']));used.append(entry)
    targets=sorted(set(raw_facts['P30']));borders=sorted(set(raw_facts['P47']));eligible=[];excluded=[]
    for qid in qids:
        true=[tail for head,tail in targets if head==qid and tail in continents]
        if true:eligible.append(qid)
        else:excluded.append({'qid':qid,'reason':'no recorded best-rank P30 in fixed candidate set'})
    index={qid:i for i,qid in enumerate(eligible)};n=len(eligible);entities=eligible+continents
    direct={(s,t)for s,t in borders if s in index and t in index and s!=t};closure=direct|{(t,s)for s,t in direct}
    public={'country_qids':eligible,'continent_qids':continents,'entities':[{'id':i,'qid':qid,'label':labels.get(qid,qid),'type':'CountryPanel'if i<n else'Continent'}for i,qid in enumerate(entities)],
            'border_edges':[[index[s],index[t]]for s,t in sorted(closure)],'candidate_entities':list(range(n,n+len(continents)))}
    data={'public':public}
    for split in ('train','val','test'):
        heads=[index[qid]for qid in eligible if split_for(qid,protocol)==split]
        data[split]={'query_heads':heads,'positives':[[index[head],'P30',n+continents.index(tail)]for head,tail in targets if head in index and index[head]in heads and tail in continents]}
    audit={'panel_entities':len(qids),'eligible_entities':n,'excluded':excluded,'labels':labels,'raw_best_P30_count':len(raw_facts['P30']),'unique_best_P30_count':len(targets),'raw_best_P47_count':len(raw_facts['P47']),'unique_best_P47_count':len(borders),
           'duplicate_P30_statements':len(raw_facts['P30'])-len(targets),'duplicate_P47_statements':len(raw_facts['P47'])-len(borders),'used_statements':used,'discarded_statements':discarded,
           'P30_outside_candidates':[[s,t]for s,t in targets if t not in continents],'P47_outside_eligible_panel':[[s,t]for s,t in borders if s not in index or t not in index],
           'P47_self_removed':[[s,t]for s,t in borders if s==t and s in index],'direct_within_panel_edges':len(direct),'symmetric_closure_edges':len(closure),'added_reverse_edges':[[s,t]for s,t in sorted(closure-direct)],
           'multi_label_entities':[qid for qid in eligible if sum(s==qid and t in continents for s,t in targets)>1],
           'split_counts':{s:{'heads':len(data[s]['query_heads']),'positives':len(data[s]['positives'])}for s in ('train','val','test')},
           'collection_start':min(r['retrieved_at_utc']for r in source['responses']),'collection_end':max(r['retrieved_at_utc']for r in source['responses']),
           'warning':'separate property reads, not an atomic dump or event time; best-rank qualifier-free projection of recorded statements'}
    return data,audit


def feature_matrix(relations,public,train,model):
    n=len(public['country_qids']);k=len(public['continent_qids']);total=n+k
    x=np.zeros((total,k+1));x[:n,-1]=1;x[n:,:k]=np.eye(k)
    root=np.zeros((k+1,k+1));root[-1,-1]=1
    if model=='no_graph':
        h=x@root;h[n:]=x[n:];return h
    seeds=np.zeros((total,total))
    for head,relation,tail in train['positives']:
        if relation!='P30'or head not in train['query_heads']or tail not in public['candidate_entities']:raise ValueError('invalid training seed')
        seeds[head,tail]=1  # inverse fact: continent sender -> country receiver.
    count=seeds.sum(axis=1,keepdims=True);seed_mean=np.divide(seeds,count,out=np.zeros_like(seeds),where=count>0)
    pass_labels=np.eye(k+1);pass_labels[-1,-1]=0
    stage1=relations.encode(x,{'P30_train_inv':seed_mean},{'P30_train_inv':pass_labels},root)
    border=np.zeros((total,total))
    for source,target in public['border_edges']:
        if source==target or not(0<=source<n and 0<=target<n):raise ValueError('border support must be nonself country pairs')
        border[target,source]=1
    degree=border.sum(axis=1,keepdims=True);border_mean=np.divide(border,degree,out=np.zeros_like(border),where=degree>0)
    h=relations.encode(stage1,{'P47':border_mean},{'P47':pass_labels},root)
    # Tail-continent embeddings use the same padded space for mature bilinear API.
    h[n:]=x[n:];return h


def rows_for(public,part):
    positive={tuple(t)for t in part['positives']};rows=[]
    for head in part['query_heads']:
        for tail in public['candidate_entities']:rows.append((head,tail,int((head,'P30',tail)in positive)))
    return rows


def padded(params):return {'decoder':np.column_stack((params['decoder'],np.zeros(len(params['decoder']))))}


def objective(core,relations,params,h,rows,l2):
    loss,gradient=relations.objective(core,padded(params),h,rows,'bilinear',l2)
    return loss,{'decoder':gradient['decoder'][:,:-1]}


def train_one(core,relations,public,train,val,protocol,model,seed):
    h=feature_matrix(relations,public,train,model);tr=rows_for(public,train);va=rows_for(public,val);k=len(public['continent_qids'])
    rng=np.random.default_rng(seed+1871);params={'decoder':rng.normal(0,protocol['initialization_sd'],(k+1,k))};m=np.zeros_like(params['decoder']);v=m.copy()
    best=None;score=float('inf');epoch=None;trace=[]
    for step in range(1,protocol['epochs']+1):
        _,gradient=objective(core,relations,params,h,tr,protocol['l2']);g=gradient['decoder'];m=.9*m+.1*g;v=.999*v+.001*g*g
        params['decoder']-=protocol['learning_rate']*(m/(1-.9**step))/(np.sqrt(v/(1-.999**step))+1e-8)
        tc=objective(core,relations,params,h,tr,0)[0];vc=objective(core,relations,params,h,va,0)[0];trace.append({'epoch':step,'train_ce':tc,'val_ce':vc})
        if vc<score:best=copy.deepcopy(params);score=vc;epoch=step
    return {'seed':seed,'model':model,'epoch':epoch,'val_ce':score,'params':{key:value.tolist()for key,value in best.items()},'trace':trace}


def train_all(core,relations,public,train,val,protocol,destination):
    fitted=[train_one(core,relations,public,train,val,protocol,model,seed)for seed in protocol['seeds']for model in protocol['models']]
    fitted.append({'seed':None,'model':'neighbor_prior','epoch':None,'val_ce':None,'params':{},'trace':[]})
    core.dump(destination/'checkpoints.json',fitted);core.dump(destination/'selection.json',[{key:r[key]for key in ('seed','model','epoch','val_ce')}for r in fitted]);return fitted


def predict(core,relations,item,public,train,rows,protocol):
    if item['model']!='neighbor_prior':
        h=feature_matrix(relations,public,train,item['model']);params={key:np.asarray(value)for key,value in item['params'].items()};return relations.scores(padded(params),h,rows,'bilinear')
    h=feature_matrix(relations,public,train,'relational');k=len(public['continent_qids']);counts=np.zeros(k)
    for _,_,tail in train['positives']:counts[tail-len(public['country_qids'])]+=1
    a=protocol['prior_smoothing'];prior=(counts+a)/(len(train['query_heads'])+2*a);alpha=protocol['neighbor_prior_mixing'];prob=np.array([alpha*h[head,tail-len(public['country_qids'])]+(1-alpha)*prior[tail-len(public['country_qids'])]for head,tail,_ in rows]);return np.log(prob)-np.log1p(-prob)


def evaluate(core,relations,data,fitted,protocol,destination):
    public=data['public'];raw=[];queries=[];heads=[];summary=[]
    for item in fitted:
        for split in ('train','val','test'):
            part=data[split];rows=rows_for(public,part);logits=predict(core,relations,item,public,data['train'],rows,protocol);score_maps={head:{}for head in part['query_heads']}
            for (head,tail,y),score in zip(rows,logits):
                score_maps[head][tail]=float(score);raw.append({'seed':item['seed'],'model':item['model'],'split':split,'head':head,'head_qid':public['entities'][head]['qid'],'tail':tail,'tail_qid':public['entities'][tail]['qid'],'y':y,'logit':float(score),'cross_entropy':float(np.logaddexp(0,score)-y*score)})
            known=set()
            for visible in protocol['filter_policy'][split]:known.update(tuple(t)for t in data[visible]['positives'])
            local=[]
            for head,relation,tail in part['positives']:
                removed={t for s,r,t in known if s==head and r==relation and t!=tail};rr=relations.rank(score_maps[head],tail,set(),protocol['rank_tie_tolerance']);fr=relations.rank(score_maps[head],tail,removed,protocol['rank_tie_tolerance'])
                rec={'seed':item['seed'],'model':item['model'],'split':split,'head':head,'head_qid':public['entities'][head]['qid'],'tail':tail,'tail_qid':public['entities'][tail]['qid'],'raw_rank':rr,'filtered_rank':fr,'removed_tails':sorted(removed),'filter_truth_splits':protocol['filter_policy'][split]};queries.append(rec);local.append(rec)
            local_heads=[]
            for head in part['query_heads']:
                q=[row for row in local if row['head']==head];record={'seed':item['seed'],'model':item['model'],'split':split,'head':head,'head_qid':public['entities'][head]['qid'],'positive_queries':len(q),'raw_mrr':float(np.mean([1/r['raw_rank']for r in q])),'filtered_mrr':float(np.mean([1/r['filtered_rank']for r in q])),'filtered_hits1':float(np.mean([r['filtered_rank']<=1 for r in q]))};heads.append(record);local_heads.append(record)
            summary.append({'seed':item['seed'],'model':item['model'],'split':split,'heads':len(local_heads),'positive_queries':len(local),'candidate_pairs':len(rows),'cross_entropy':float(np.mean([r['cross_entropy']for r in raw[-len(rows):]])),'macro_raw_mrr':float(np.mean([r['raw_mrr']for r in local_heads])),'macro_filtered_mrr':float(np.mean([r['filtered_mrr']for r in local_heads])),'macro_filtered_hits1':float(np.mean([r['filtered_hits1']for r in local_heads])),'micro_raw_mrr':float(np.mean([1/r['raw_rank']for r in local])),'micro_filtered_mrr':float(np.mean([1/r['filtered_rank']for r in local]))})
    core.dump(destination/'raw_scores.json',raw);core.dump(destination/'query_ranks.json',queries);core.dump(destination/'head_metrics.json',heads);core.dump(destination/'summary.json',summary)


def run(core,relations,data,protocol,destination):
    start=time.monotonic();fitted=train_all(core,relations,data['public'],data['train'],data['val'],protocol,destination)
    # ONLY after every selection is committed do evaluation and test reads begin.
    evaluate(core,relations,{key:data[key]for key in ('public','train','val','test')},fitted,protocol,destination)
    h=feature_matrix(relations,data['public'],data['train'],'relational');core.dump(destination/'features.json',h.tolist())
    public=data['public'];train_heads=set(data['train']['query_heads']);audit=[]
    for head,qid in enumerate(public['country_qids']):
        neighbors=sorted({s for s,t in public['border_edges']if t==head});audit.append({'head':head,'qid':qid,'degree':len(neighbors),'training_seed_available':head in train_heads,'labeled_neighbor_qids':[public['country_qids'][j]for j in neighbors if j in train_heads],'own_label_direct_coefficient':0.0,'label_message':h[head,:-1].tolist()})
    core.dump(destination/'graph-audit.json',audit)
    core.dump(destination/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),'seconds':time.monotonic()-start,'gpu':False,'threads_requested':1})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=('prepare','train'));ap.add_argument('--parent',type=Path,default=Path(__file__).resolve().parent.parent);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--protocol',type=Path);ap.add_argument('--inputs',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();core,relations=load_modules(args.parent);protocol=core.load(args.protocol or args.root/'protocol.json')
    if args.output.exists():ap.error('output exists; choose new directory')
    args.output.mkdir(parents=True)
    if args.command=='prepare':
        data,audit=normalize(core.load(args.root/'source-responses.json'),core.load(args.root/'panel.json'),protocol);core.dump(args.output/'inputs.json',data);core.dump(args.output/'source-audit.json',audit)
    else:
        if args.inputs is None:ap.error('train requires --inputs')
        core.dump(args.output/'identity.json',{key:core.digest(file)for key,file in [('source_sha256',__file__),('inputs_sha256',args.inputs),('protocol_sha256',args.protocol or args.root/'protocol.json'),('parent_core_sha256',args.parent/'graph_task.py'),('parent_relations_sha256',args.parent/'relations/relations.py'),('raw_source_sha256',args.root/'source-responses.json'),('panel_sha256',args.root/'panel.json')]});core.dump(args.output/'protocol.json',protocol);run(core,relations,core.load(args.inputs),protocol,args.output)

if __name__=='__main__':main()
