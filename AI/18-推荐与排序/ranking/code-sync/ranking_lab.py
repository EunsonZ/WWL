"""Finite BPR expected-sampling targets, candidate metrics, and explicit cold fallbacks."""
import argparse
import hashlib
import importlib.util
import json
from fractions import Fraction
from itertools import combinations
import os
from pathlib import Path
import numpy as np

_PARENT=None
_PARENT_PATH=None


def set_parent(path=None):
    global _PARENT,_PARENT_PATH
    path=Path(path) if path else Path(__file__).resolve().parents[2]/'code-sync/ratings_lab.py'
    spec=importlib.util.spec_from_file_location('published_ratings_lab',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    _PARENT,_PARENT_PATH=module,path.resolve()


def parent():
    if _PARENT is None:set_parent()
    return _PARENT


def history(events,config):
    h=np.zeros((len(config['users']),len(config['items'])))
    for row in events:
        if not row['exposed'] or row['click'] not in [0,1] or row['time']>config['train_through']:
            raise ValueError('training clicks need observed exposure and in-time binary label')
        if row['user'] not in config['train_users'] or row['item'] not in config['train_items']:raise ValueError('cold feedback leaked into training')
        if row['click']==1:h[row['user'],row['item']]=1.
    return h


def triples(h,config,sampler):
    if sampler not in config['samplers']:raise ValueError('sampler')
    counts=h.sum(axis=0);rows=[]
    for u in config['train_users']:
        pos=[i for i in config['train_items'] if h[u,i]>0]
        pool=[j for j in config['train_items'] if h[u,j]==0]
        if not pos or not pool:raise ValueError('need at least one training positive and eligible contrast item')
        q=np.ones(len(pool)) if sampler=='uniform' else counts[pool]+1.
        q=q/q.sum()
        for i in pos:
            for j,probability in zip(pool,q):
                rows.append(dict(user=u,positive=i,contrast=j,q=float(probability),weight=float(probability/(len(config['train_users'])*len(pos)))))
    return rows


def initialize(config):
    p=parent().initialize(config)
    p['P'][[u for u in config['users'] if u not in config['train_users']]]=0.
    p['Q'][[i for i in config['items'] if i not in config['train_items']]]=0.
    # User intercept and global mean cancel from pairwise differences; keep both fixed at zero.
    p['bu'][:]=0.;p['bi'][:]=0.
    return p


def objective_gradient(p,pairs,regularization):
    loss=.5*regularization*sum(float(np.sum(p[k]**2)) for k in ['P','Q','bi'])
    g={k:regularization*v.copy() if k!='bu' else np.zeros_like(v) for k,v in p.items()}
    for row in pairs:
        u,i,j,w=row['user'],row['positive'],row['contrast'],row['weight']
        score=parent().predict(p,np.array([u,u]),np.array([i,j]),0.)
        margin=float(score[0]-score[1]);loss+=w*float(np.logaddexp(0.,-margin))
        coefficient=-w*float(np.exp(-np.logaddexp(0.,margin)))
        g['P'][u]+=coefficient*(p['Q'][i]-p['Q'][j])
        g['Q'][i]+=coefficient*p['P'][u];g['Q'][j]-=coefficient*p['P'][u]
        g['bi'][i]+=coefficient;g['bi'][j]-=coefficient
    return loss,g


def rank_items(candidates,scores):
    if len(candidates)!=len(set(candidates)) or len(scores)!=len(candidates) or not np.isfinite(scores).all():raise ValueError('distinct candidates and finite scores')
    return [i for i,s in sorted(zip(candidates,scores),key=lambda pair:(-pair[1],pair[0]))]


def list_metrics(ranking,relevant,K,full_candidates):
    if K<1 or len(ranking)!=len(set(ranking)) or not set(ranking)<=set(full_candidates):raise ValueError('invalid ranking')
    relevant=set(relevant)
    if not relevant<=set(full_candidates):raise ValueError('relevance outside eligible catalogue')
    returned_relevant=relevant&set(ranking)
    top=ranking[:K];hit=sum(i in relevant for i in top)
    dcg=sum(1./np.log2(k+2) for k,i in enumerate(top) if i in relevant)
    ideal=lambda n:sum(1./np.log2(k+2) for k in range(min(K,n)))
    idcg=ideal(len(relevant));conditional_idcg=ideal(len(returned_relevant))
    return dict(relevant_n=len(relevant),returned_n=len(ranking),hits=hit,dcg=float(dcg),idcg=float(idcg),
                recall=hit/len(relevant) if relevant else None,ndcg=float(dcg/idcg) if idcg else None,
                candidate_recall=len(returned_relevant)/len(relevant) if relevant else None,
                conditional_recall=hit/len(returned_relevant) if returned_relevant else None,
                conditional_ndcg=float(dcg/conditional_idcg) if conditional_idcg else None)


def scores_for(model,p,h,config,user,candidates):
    counts=h.sum(axis=0)
    if model=='popularity':return counts[candidates]
    if model=='content':return np.array([float(config['user_group'][user]==config['item_group'][i]) for i in candidates])
    if model=='neighbors':
        norm=np.linalg.norm(h[user]);neighbors=[]
        for v in config['train_users']:
            if v==user:continue
            denom=norm*np.linalg.norm(h[v]);sim=float(h[user]@h[v]/denom) if denom else 0.
            if sim>0:neighbors.append((v,sim))
        neighbors=sorted(neighbors,key=lambda item:(-item[1],item[0]))[:config['neighbor_k']]
        denom=sum(s for v,s in neighbors)
        return np.array([sum(s*h[v,i] for v,s in neighbors)/denom for i in candidates]) if denom else counts[candidates]
    if model.startswith('bpr_'):
        if user not in config['train_users']:return counts[candidates]
        values=parent().predict(p,np.full(len(candidates),user),np.array(candidates),0.)
        return np.array([score if i in config['train_items'] else counts[i] for i,score in zip(candidates,values)])
    raise ValueError('model')


def evaluate(model,p,h,config,queries,split):
    rows=[];counts=h.sum(axis=0)
    for query in queries:
        u,C=query['user'],query['candidates'];scores=scores_for(model,p,h,config,u,C)
        if set(C)&set(np.where(h[u]>0)[0]):raise ValueError('training consumed item in serving candidates')
        retrieved=rank_items(C,counts[C])[:config['retriever_size']]
        score_map=dict(zip(C,scores))
        for mode,candidates in [('full',C),('retrieved',retrieved)]:
            ranking=rank_items(candidates,[score_map[i] for i in candidates])
            rows.append(dict(model=model,split=split,query=query['query'],user=u,group=query['group'],time=query['time'],candidate_mode=mode,
                             full_candidates=C,candidates=candidates,scores=[float(score_map[i]) for i in candidates],ranking=ranking,
                             relevant=query['relevant'],**list_metrics(ranking,query['relevant'],config['K'],C)))
    return rows


def summarize(rows,K):
    summaries=[]
    keys=sorted(set((r['model'],r['split'],r['group'],r['candidate_mode']) for r in rows))
    for model,split,group,mode in keys:
        subset=[r for r in rows if (r['model'],r['split'],r['group'],r['candidate_mode'])==(model,split,group,mode)]
        record=dict(model=model,split=split,group=group,candidate_mode=mode,queries=len(subset))
        for metric in ['recall','ndcg','candidate_recall','conditional_recall','conditional_ndcg']:
            values=[r[metric] for r in subset if r[metric] is not None]
            record[metric+'_valid_queries']=len(values);record[metric]=float(np.mean(values)) if values else None
        record['topK_coverage']=len(set(i for r in subset for i in r['ranking'][:K]))/len(set(i for r in subset for i in r['full_candidates']))
        summaries.append(record)
    return summaries


def finite_examples():
    gamma=float(1/(1+np.exp(1.)));loss=np.logaddexp(0.,-np.array([0.,2.]))
    softmax=np.exp(np.array([2.,1.,0.])-2);softmax/=softmax.sum()
    # Same history timeline, different train eligibility; no ranking model is refit here.
    timeline=[dict(time=1,item=0,click=1),dict(time=2,item=0,click=1),dict(time=3,item=1,click=1),dict(time=4,item=1,click=1)]
    query_time=2.5;release=[0.,3.]
    random_indices=sorted(np.random.default_rng(17).permutation(4)[:3].tolist())
    random_train=[timeline[i] for i in random_indices];time_train=[r for r in timeline if r['time']<query_time]
    def audit(events):
        counts=[sum(r['click'] for r in events if r['item']==i) for i in range(2)]
        bad=[r for r in events if r['time']>=query_time]
        return dict(counts=counts,future_training_events=bad,unfiltered_top_item=int(np.argmax(counts)),available_at_query=[i for i,t in enumerate(release) if t<=query_time])
    point_scores=np.array([2.,1.,0.]);point_labels=np.array([1.,0.,0.])
    return dict(pointwise=dict(scores=point_scores.tolist(),labels=point_labels.tolist(),loss=float(np.sum(np.logaddexp(0.,point_scores)-point_labels*point_scores)),gradient=(1/(1+np.exp(-point_scores))-point_labels).tolist()),manual_bpr=dict(gamma=gamma,gradient=[-gamma,-gamma,gamma],new_p=1+.1*gamma,new_q_positive=1+.1*gamma,new_q_contrast=-.1*gamma),
                sampler_loss=dict(margins=[0.,2.],uniform=float(np.array([.5,.5])@loss),skew=float(np.array([.9,.1])@loss),importance_weights=[.5/.9,.5/.1]),
                listwise=dict(scores=[2.,1.,0.],one_hot_target=[1.,0.,0.],loss=float(np.logaddexp.reduce([2.,1.,0.])-2),gradient=(softmax-[1.,0.,0.]).tolist()),
                candidate_example=dict(full=list_metrics([1,0,2,3],[0,3],2,[0,1,2,3]),retrieved=list_metrics([1,0],[0,3],2,[0,1,2,3])),
                timeline=dict(events=timeline,random_seed=17,random_train_indices=random_indices,query_time=query_time,item_release_times=release,random_train=audit(random_train),time_train=audit(time_train)))


def randomization_example(binary_truth):
    # Fixed single-opportunity potential responses; not dynamic deployment or human evidence.
    yA=[int(row[0]) for row in binary_truth];yB=[int(row[4]) for row in binary_truth]
    if len(yA)!=8:raise ValueError('fixed 8-user randomization fixture')
    rows=[];effects=[]
    for treated in combinations(range(8),4):
        control=[u for u in range(8) if u not in treated]
        meanA=Fraction(sum(yA[u] for u in control),4);meanB=Fraction(sum(yB[u] for u in treated),4)
        effect=meanB-meanA;effects.append(effect)
        rows.append(dict(treated_B=list(treated),control_A=control,mean_A=float(meanA),mean_B=float(meanB),difference=float(effect)))
    ate=Fraction(sum(yB)-sum(yA),8);expectation=sum(effects,Fraction(0))/len(effects)
    variance=sum(((x-expectation)**2 for x in effects),Fraction(0))/len(effects)
    return dict(policy_A_item=0,policy_B_item=4,potential_A=yA,potential_B=yB,allocations=rows,
                population_ATE=float(ate),expected_difference=float(expectation),variance=float(variance),
                expectation_exact=str(expectation),variance_exact=str(variance),minimum=float(min(effects)),maximum=float(max(effects)),
                interpretation='All 70 balanced assignments of one fixed synthetic population; not 70 human trials or deployment-effect evidence.')


def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def run(inputs,output,pre_run_steps=None,reader=None):
    inputs,output=Path(inputs),Path(output);output.mkdir(parents=True,exist_ok=True)
    config=json.loads((inputs/'protocol.json').read_text());reader=reader or parent().DataAccess(inputs)
    events=reader.read('train');h=history(events,config);pairsets={s:triples(h,config,s) for s in config['samplers']}
    if pre_run_steps is not None:
        if not 0<pre_run_steps<=config['epochs']:raise ValueError('pre-run steps')
        p=initialize(config)
        for _ in range(pre_run_steps):
            loss,g=objective_gradient(p,pairsets['uniform'],config['regularization']);p={k:v-config['learning_rate']*g[k] for k,v in p.items()}
        loss=objective_gradient(p,pairsets['uniform'],config['regularization'])[0]
        value=dict(mode='train-only pre-run',steps=pre_run_steps,objective=loss,access_events=reader.events);save(output/'pre-run.json',value);return value
    val=reader.read('val')
    if not all(q['time']>config['train_through'] for q in val):raise ValueError('validation must follow training')
    parameters={};checkpoints={};curves=[];decisions=[];validation_rows=[]
    for sampler,pairs in pairsets.items():
        p=initialize(config);model='bpr_'+sampler;choices=[];checkpoints[model]={}
        for epoch in range(config['epochs']+1):
            loss,g=objective_gradient(p,pairs,config['regularization']);curves.append(dict(model=model,epoch=epoch,objective=loss))
            if epoch in config['checkpoints']:
                vr=evaluate(model,p,h,config,val,'val');full=[r['ndcg'] for r in vr if r['candidate_mode']=='full']
                choices.append(dict(epoch=epoch,macro_ndcg=float(np.mean(full)),objective=loss));validation_rows.extend(dict(epoch=epoch,**r) for r in vr)
                checkpoints[model][str(epoch)]={k:v.tolist() for k,v in p.items()}
            if epoch<config['epochs']:p={k:v-config['learning_rate']*g[k] for k,v in p.items()}
        selected=min(choices,key=lambda r:(-r['macro_ndcg'],r['epoch']))['epoch']
        parameters[model]={k:np.array(v) for k,v in checkpoints[model][str(selected)].items()}
        decisions.append(dict(model=model,selected_epoch=selected,validation_choices=choices))
    # Both sampler choices and all train-only baselines are frozen before test/diagnostic truth.
    reader.finish_selection();test=reader.read('test')
    if not all(q['time']>max(v['time'] for v in val) for q in test):raise ValueError('test must follow validation')
    diagnostic=json.loads((inputs/'diagnostic-truth.json').read_text());reader.events.append(dict(action='read_diagnostic_truth',selection_finished=reader.selection_finished))
    randomization=randomization_example(diagnostic['binary_relevance'])
    save(output/'randomization.json',randomization)
    rows=[]
    for model in ['popularity','neighbors','content',*parameters]:
        for split,queries in [('val',val),('test',test)]:rows.extend(evaluate(model,parameters.get(model),h,config,queries,split))
    with (output/'query-predictions.jsonl').open('w') as stream:
        for row in rows:stream.write(json.dumps(row,allow_nan=False)+'\n')
    pairs_out={}
    for sampler,pairs in pairsets.items():
        pairs_out[sampler]=[dict(r,contrast_observed_nonclick=any(e['user']==r['user'] and e['item']==r['contrast'] and e['click']==0 for e in events),
                                 diagnostic_contrast_relevant=bool(diagnostic['binary_relevance'][r['user']][r['contrast']])) for r in pairs]
    save(output/'pairs.json',pairs_out);save(output/'checkpoints.json',checkpoints);save(output/'training-curves.json',curves);save(output/'validation-queries.json',validation_rows)
    result=dict(selection=decisions,summary=summarize(rows,config['K']),history=h.tolist(),training_counts=h.sum(axis=0).tolist(),examples=finite_examples(),access_events=reader.events,
                randomization_summary={k:v for k,v in randomization.items() if k!='allocations'},
                updated_parameters_per_bpr=24,stored_parameters_per_bpr=42,side_information_baseline_extra_input=True,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parent_source_sha256=hashlib.sha256(_PARENT_PATH.read_bytes()).hexdigest(),
                input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.glob('*.json'))},
                thread_limit_environment={x:os.environ.get(x) for x in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']})
    save(output/'results.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parent',type=Path);parser.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parents[1]/'inputs')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--pre-run-steps',type=int)
    args=parser.parse_args();set_parent(args.parent);r=run(args.inputs,args.output,args.pre_run_steps)
    print(json.dumps(r['selection'] if args.pre_run_steps is None else r,ensure_ascii=False))
