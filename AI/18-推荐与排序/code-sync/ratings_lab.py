"""Masked explicit-rating MF; finite teaching protocol, not an online recommender."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np


class DataAccess:
    """The test file is not even opened until all validation selection has finished."""
    def __init__(self,root):
        self.root=Path(root);self.selection_finished=False;self.events=[]

    def read(self,split):
        if split not in ['train','val','test']:raise ValueError('unknown split')
        if split=='test' and not self.selection_finished:raise RuntimeError('test before selection')
        self.events.append(dict(action='read',split=split,selection_finished=self.selection_finished))
        return json.loads((self.root/(split+'.json')).read_text())

    def finish_selection(self):
        self.selection_finished=True;self.events.append(dict(action='selection_finished'))


def rated(records):
    output=[]
    for row in records:
        if row['rating_observed']:
            if not row['exposed'] or row['rating'] is None or not 1<=row['rating']<=5:
                raise ValueError('observed rating requires exposure and a 1..5 rating')
            output.append(row)
        elif row['rating'] is not None:
            raise ValueError('unobserved rating must remain null, never zero filled')
    if not output:raise ValueError('no rating labels')
    return output


def arrays(records):
    rows=rated(records)
    return np.array([x['user'] for x in rows],int),np.array([x['item'] for x in rows],int),np.array([x['rating'] for x in rows],float)


def initialize(protocol):
    rng=np.random.default_rng(protocol['seed']);d=protocol['rank']
    return dict(P=rng.normal(0,protocol['initial_factor_std'],(len(protocol['users']),d)),
                Q=rng.normal(0,protocol['initial_factor_std'],(len(protocol['items']),d)),
                bu=np.zeros(len(protocol['users'])),bi=np.zeros(len(protocol['items'])))


def predict(parameters,users,items,mean):
    return mean+parameters['bu'][users]+parameters['bi'][items]+np.sum(parameters['P'][users]*parameters['Q'][items],axis=1)


def objective_gradient(parameters,records,mean,regularization):
    users,items,y=arrays(records);n=len(y)
    error=predict(parameters,users,items,mean)-y
    loss=.5*float(error@error)/n+.5*regularization*sum(float(np.sum(x*x)) for x in parameters.values())
    gradient={key:regularization*x.copy() for key,x in parameters.items()}
    np.add.at(gradient['P'],users,error[:,None]*parameters['Q'][items]/n)
    np.add.at(gradient['Q'],items,error[:,None]*parameters['P'][users]/n)
    np.add.at(gradient['bu'],users,error/n);np.add.at(gradient['bi'],items,error/n)
    return loss,gradient


def step(parameters,records,mean,regularization,learning_rate):
    loss,gradient=objective_gradient(parameters,records,mean,regularization)
    # All four parameter arrays use the same old parameter values.
    return {key:value-learning_rate*gradient[key] for key,value in parameters.items()},loss


def metrics(y,prediction):
    error=np.asarray(prediction)-np.asarray(y)
    return dict(n=len(error),mse=float(np.mean(error**2)),rmse=float(np.sqrt(np.mean(error**2))),mae=float(np.mean(np.abs(error))))


def baseline_parameters(train,protocol,mean):
    users,items,y=arrays(train);n=len(y);m=len(protocol['items'])
    totals=np.bincount(items,weights=y-mean,minlength=m);counts=np.bincount(items,minlength=m)
    return dict(mean=mean,item_bias=(totals/(counts+n*protocol['regularization'])).tolist(),counts=counts.tolist())


def predictions_for(model,parameters,baseline,records,mean):
    users,items,_=arrays(records)
    if model=='global_mean':return np.full(len(users),mean)
    if model=='item_bias':return mean+np.array(baseline['item_bias'])[items]
    if model=='mf':return predict(parameters,users,items,mean)
    raise ValueError('unknown model')


def analytic_examples():
    observed=np.array([[3.,0.],[4.,2.]])
    mask=np.array([[True,False],[True,True]])
    worlds=[np.array([[3.,x],[4.,2.]]) for x in [1.,5.]]
    u,s,vt=np.linalg.svd(observed,full_matrices=False)
    zero_svd=(u[:,:1]*s[:1])@vt[:1]
    exact=np.array([[3.,1.5],[4.,2.]])
    p,q,target,reg,lr=1.,2.,3.,.1,.1
    error=p*q-target;gp=error*q+reg*p;gq=error*p+reg*q
    newp,newq=p-lr*gp,q-lr*gq
    return dict(observed=observed.tolist(),observed_mask=mask.tolist(),
                candidate_items=[0,1],candidate_includes_already_rated_item=True,
                worlds=[dict(matrix=w.tolist(),best_item_user0=int(np.argmax(w[0])),observed_sse=float(np.sum((w-observed)[mask]**2))) for w in worlds],
                exact_rank1_completion=exact.tolist(),exact_rank1_observed_sse=float(np.sum((exact-observed)[mask]**2)),
                zero_filled_rank1_svd=zero_svd.tolist(),zero_svd_observed_sse=float(np.sum((zero_svd-observed)[mask]**2)),
                zero_svd_full_sse=float(np.sum((zero_svd-observed)**2)),singular_values=s.tolist(),
                manual_step=dict(p=p,q=q,target=target,regularization=reg,learning_rate=lr,error=error,gradient_p=gp,gradient_q=gq,
                                 new_p=newp,new_q=newq,new_prediction=newp*newq),
                origin_stationary=dict(gradient=[0.,0.],hessian=[[reg,-target],[-target,reg]],eigenvalues=[reg-target,reg+target]),
                zero_support_policy=dict(user=0,item=1,exposure_probability=0.,note='An additional declared policy assumption, not inferred from a single missing cell; IPS for a new policy choosing it is undefined.'))


def save_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def run(inputs,output,pre_run_steps=None,access=None):
    inputs,output=Path(inputs),Path(output);output.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((inputs/'protocol.json').read_text());access=access or DataAccess(inputs)
    train=access.read('train');u,i,y=arrays(train);mean=float(y.mean())
    if set(u)!=set(protocol['users']) or set(i)!=set(protocol['items']):raise ValueError('fixture promises warm user/item support')
    if max(x['time'] for x in train)>protocol['split_cutoffs']['train_through']:raise ValueError('future training record')
    parameters=initialize(protocol);baseline=baseline_parameters(train,protocol,mean)
    if pre_run_steps is not None:
        if not 0<pre_run_steps<=protocol['epochs']:raise ValueError('pre-run steps')
        for _ in range(pre_run_steps):parameters,_=step(parameters,train,mean,protocol['regularization'],protocol['learning_rate'])
        result=dict(mode='pre-run training only',steps=pre_run_steps,loss=objective_gradient(parameters,train,mean,protocol['regularization'])[0],access_events=access.events)
        save_json(output/'pre-run.json',result);return result
    val=access.read('val')
    if not all(protocol['split_cutoffs']['train_through']<x['time']<=protocol['split_cutoffs']['val_through'] for x in val):raise ValueError('validation time')
    checkpoint_rows=[];checkpoints={};train_curve=[]
    for epoch in range(protocol['epochs']+1):
        loss,_=objective_gradient(parameters,train,mean,protocol['regularization'])
        train_curve.append(dict(epoch=epoch,objective=loss,**metrics(y,predict(parameters,u,i,mean))))
        if epoch in protocol['checkpoints']:
            vu,vi,vy=arrays(val);vm=metrics(vy,predict(parameters,vu,vi,mean))
            checkpoint_rows.append(dict(epoch=epoch,validation=vm,training_objective=loss))
            checkpoints[epoch]={key:value.copy() for key,value in parameters.items()}
        if epoch<protocol['epochs']:parameters,_=step(parameters,train,mean,protocol['regularization'],protocol['learning_rate'])
    selected=min(checkpoint_rows,key=lambda row:(row['validation']['mse'],row['epoch']))['epoch']
    chosen=checkpoints[selected]
    # Frozen choice and baseline parameters precede even opening the test file.
    access.finish_selection();test=access.read('test')
    if not all(protocol['split_cutoffs']['val_through']<x['time']<=protocol['split_cutoffs']['test_through'] for x in test):raise ValueError('test time')
    pairs=[(row['user'],row['item']) for group in [rated(train),rated(val),rated(test)] for row in group]
    if len(pairs)!=len(set(pairs)):raise ValueError('fixture must not repeat a rated pair across splits')
    raw=[];summary=[];per_user=[]
    for model in ['global_mean','item_bias','mf']:
        for split,records in [('train',train),('val',val),('test',test)]:
            rows=rated(records);pred=predictions_for(model,chosen,baseline,rows,mean);truth=np.array([x['rating'] for x in rows])
            summary.append(dict(model=model,split=split,**metrics(truth,pred)))
            for row,score in zip(rows,pred):raw.append(dict(model=model,split=split,event=row['event'],user=row['user'],item=row['item'],time=row['time'],rating=row['rating'],prediction=float(score)))
            for user in protocol['users']:
                ids=[k for k,row in enumerate(rows) if row['user']==user]
                if ids:per_user.append(dict(model=model,split=split,user=user,**metrics(truth[ids],pred[ids])))
    with (output/'predictions.jsonl').open('w') as f:
        for row in raw:f.write(json.dumps(row,allow_nan=False)+'\n')
    save_json(output/'train-curve.json',train_curve);save_json(output/'validation.json',checkpoint_rows)
    save_json(output/'checkpoints.json',{str(epoch):{key:value.tolist() for key,value in pp.items()} for epoch,pp in checkpoints.items()})
    result=dict(selected_epoch=selected,mean=mean,baselines=baseline,summary=summary,per_user=per_user,examples=analytic_examples(),access_events=access.events,
                parameter_counts=dict(global_mean_fitted=1,item_bias_fitted=7,mf_fitted=43,mf_updated=42,mean_fixed_during_updates=True),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.glob('*.json'))},
                thread_limit_environment={x:os.environ.get(x) for x in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']})
    save_json(output/'results.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parents[1]/'inputs')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--pre-run-steps',type=int)
    args=parser.parse_args();result=run(args.inputs,args.output,args.pre_run_steps)
    print(json.dumps({key:result[key] for key in ['selected_epoch','summary']} if args.pre_run_steps is None else result,ensure_ascii=False))
