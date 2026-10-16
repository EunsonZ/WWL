"""GraphSAGE mean + self/neighbor concat + guarded L2 normalization.

Reuse the published fixed inputs/loader/metrics; no downloads or new dataset.
The dense full-node implementation demonstrates sampling, NOT scalable minibatches.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import itertools
import json
import math
from pathlib import Path
import platform
import sys
import time
import numpy as np

sys.dont_write_bytecode = True


def load_core(parent):
    spec = importlib.util.spec_from_file_location('wwl_graph_task_core', Path(parent) / 'graph_task.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_operator(a, fanout, rng):
    """A[G,N,N] -> row means over min(fanout, degree) DISTINCT external neighbors.

    None means all neighbors. Empty rows remain zero, never include self.
    Uniform sampling is in distribution equivariant; replay a remapped mask for
    pathwise equivariance. The same integer seed after relabeling is not a coupling.
    """
    if isinstance(fanout, bool) or (fanout is not None and (not isinstance(fanout, int) or fanout < 1)):
        raise ValueError('fanout must be positive integer or None')
    if a.ndim != 3 or a.shape[1] != a.shape[2] or not np.isin(a, [0, 1]).all():
        raise ValueError('binary batched square adjacency required')
    if not np.array_equal(a, a.transpose(0, 2, 1)) or np.diagonal(a, axis1=1, axis2=2).any():
        raise ValueError('undirected zero-diagonal adjacency required')
    result = np.zeros_like(a, dtype=float)
    for graph in range(len(a)):
        for i in range(a.shape[1]):
            neighbors = np.flatnonzero(a[graph, i])
            count = len(neighbors) if fanout is None else min(fanout, len(neighbors))
            if count:
                selected = neighbors if count == len(neighbors) else rng.choice(neighbors, count, replace=False)
                result[graph, i, selected] = 1 / count
    return result


def operators(a, depth, fanout, key):
    rng = np.random.default_rng(np.random.SeedSequence(key))
    return [sample_operator(a, fanout, rng) for _ in range(depth)]


def initialize(depth, width, input_dim, seed):
    rng = np.random.default_rng(seed + 701 * depth)
    p = {}
    for layer in range(depth):
        d = input_dim if layer == 0 else width
        p[f'w{layer}'] = rng.normal(0, 1 / math.sqrt(2*d), (2*d, width))
        p[f'b{layer}'] = np.zeros(width)
    p['out'] = rng.normal(0, 1/math.sqrt(width), (width, 1))
    p['out_b'] = np.zeros(1)
    return p


def normalize(value, epsilon):
    norm = np.linalg.norm(value, axis=-1, keepdims=True)
    scale = np.maximum(norm, epsilon)
    return value / scale, norm, scale


def forward(params, x, ops, epsilon=1e-8):
    """Only node features and label-free sampled neighbor operators enter forward."""
    h = x
    cache = []
    for layer, op in enumerate(ops):
        neighbor = op @ h
        joined = np.concatenate((h, neighbor), axis=-1)
        activated = np.tanh(joined @ params[f'w{layer}'] + params[f'b{layer}'])
        new_h, norm, scale = normalize(activated, epsilon)
        cache.append((joined, activated, new_h, norm, scale, op))
        h = new_h
    return (h @ params['out'] + params['out_b'])[..., 0], cache


def objective(params, x, y, ops, l2=.001, epsilon=1e-8):
    logits, cache = forward(params, x, ops, epsilon)
    if y.shape != logits.shape or not np.isin(y, [0, 1]).all():
        raise ValueError('binary label shape must equal G,N logits')
    loss = float(np.mean(np.logaddexp(0, logits) - y*logits))
    weights = [k for k in params if k.startswith('w') or k == 'out']
    loss += .5*l2*sum(float(np.sum(params[k]**2)) for k in weights)
    dz = ((np.exp(-np.logaddexp(0, -logits)) - y)/y.size)[..., None]
    h = cache[-1][2]
    grad = {'out': np.einsum('gni,gnj->ij', h, dz), 'out_b': dz.sum(axis=(0,1))}
    dh = dz @ params['out'].T
    for layer in reversed(range(len(ops))):
        joined, activated, normalized, norm, scale, op = cache[layer]
        # For norm>epsilon: (I-hh^T)/norm. Below epsilon: I/epsilon.
        # At norm==epsilon use the lower branch; derivative there is not unique.
        tangent = dh - normalized*np.sum(normalized*dh, axis=-1, keepdims=True)
        da = np.where(norm > epsilon, tangent/scale, dh/scale)
        du = da*(1-activated**2)
        grad[f'w{layer}'] = np.einsum('gni,gnj->ij', joined, du)
        grad[f'b{layer}'] = du.sum(axis=(0,1))
        dc = du @ params[f'w{layer}'].T
        d = dc.shape[-1]//2
        dh = dc[..., :d] + op.transpose(0,2,1) @ dc[..., d:]
    for k in weights:
        grad[k] += l2*params[k]
    return loss, grad


def prediction(params, x, plans, epsilon):
    # Ensemble target: average LOGITS; not average sigmoid probabilities.
    return np.mean([forward(params, x, plan, epsilon)[0] for plan in plans], axis=0)


def train_one(core, train_rows, val_rows, depth, fanout, protocol, seed, regime_code):
    a,x = core.arrays([{'A':r['A'], 'X':r['X']} for r in train_rows])
    y = np.asarray([r['y'] for r in train_rows])
    va,vx = core.arrays([{'A':r['A'], 'X':r['X']} for r in val_rows])
    vy = np.asarray([r['y'] for r in val_rows])
    p = initialize(depth, protocol['hidden'], x.shape[-1], seed)
    m = {k:np.zeros_like(v)for k,v in p.items()};v=copy.deepcopy(m)
    draws = 1 if fanout is None else protocol['evaluation_draws']
    # RNG keys never use labels. Plans fixed across epochs for model selection.
    val_plans = [operators(va,depth,fanout,[seed,regime_code,1,draw])for draw in range(draws)]
    best, best_val, best_epoch = None, math.inf, None
    trace=[];start=time.monotonic()
    for epoch in range(1,protocol['epochs']+1):
        plan=operators(a,depth,fanout,[seed,regime_code,0,epoch])
        loss,grad=objective(p,x,y,plan,protocol['l2'],protocol['normalization_epsilon'])
        for k in p:
            m[k]=.9*m[k]+.1*grad[k];v[k]=.999*v[k]+.001*grad[k]**2
            p[k]-=protocol['learning_rate']*(m[k]/(1-.9**epoch))/(np.sqrt(v[k]/(1-.999**epoch))+1e-8)
        val_logits=prediction(p,vx,val_plans,protocol['normalization_epsilon'])
        val_ce=float(np.mean(np.logaddexp(0,val_logits)-vy*val_logits))
        trace.append({'epoch':epoch,'train_sample_objective_before_update':loss,'val_ce':val_ce})
        if val_ce < best_val:
            best,best_val,best_epoch=copy.deepcopy(p),val_ce,epoch
    return best,best_epoch,best_val,trace,time.monotonic()-start


def enumeration():
    values=[-1,0,1,2];n=len(values);population=sum(values)/n
    sample_variance=sum((v-population)**2 for v in values)/(n-1)
    rows=[]
    for count in range(1,n+1):
        subsets=list(itertools.combinations(range(n),count))
        means=[sum(values[j]for j in subset)/count for subset in subsets]
        expectation=sum(means)/len(means)
        variance=sum((value-population)**2 for value in means)/len(means)
        relu_after=[max(0,value-.5)for value in means]
        rows.append({'fanout':count,'subsets':[list(s)for s in subsets], 'sample_means':means,
                     'mean':expectation,'variance':variance,'theory_variance':(1-count/n)*sample_variance/count,
                     'mean_relu_of_centered_sample':sum(relu_after)/len(relu_after),
                     'relu_of_centered_population':max(0,population-.5)})
    return {'neighbor_values':values,'population_mean':population,'sample_variance_D_minus_1':sample_variance,'rows':rows}


def run(core, parent, protocol, destination):
    inputs=core.load(parent/'inputs.json');trained=[];selection=[];start=time.monotonic()
    for seed in protocol['seeds']:
        for regime_code,regime in enumerate(protocol['regimes']):
            group=[r for r in inputs['graphs']if r['seed']==seed and r['regime']==regime]
            train=[r for r in group if r['split']=='train'];val=[r for r in group if r['split']=='val']
            for fanout in protocol['fanouts']:
                candidates=[]
                for depth in protocol['depths']:
                    p,epoch,score,trace,seconds=train_one(core,train,val,depth,fanout,protocol,seed,regime_code)
                    item={'seed':seed,'regime':regime,'fanout':fanout,'depth':depth,'epoch':epoch,'val_ce':score,
                          'params':{k:v.tolist()for k,v in p.items()},'trace':trace,'train_seconds':seconds}
                    trained.append(item);candidates.append(item)
                chosen=min(candidates,key=lambda r:(r['val_ce'],r['depth']))
                selection.append({k:chosen[k]for k in ('seed','regime','fanout','depth','epoch','val_ce')})
    # Freeze ALL selection before any test labels or baseline test results are read.
    core.dump(destination/'selection.json',selection);core.dump(destination/'checkpoints.json',trained)
    raw=[];summary=[]
    for item in trained:
        seed,regime,fanout,depth=(item[k]for k in ('seed','regime','fanout','depth'))
        rc=protocol['regimes'].index(regime);p={k:np.asarray(v)for k,v in item['params'].items()}
        for sc,split in enumerate(('train','val','test')):
            rows=[r for r in inputs['graphs']if r['seed']==seed and r['regime']==regime and r['split']==split]
            a,x=core.arrays([{'A':r['A'],'X':r['X']}for r in rows])
            draws=1 if fanout is None else protocol['evaluation_draws']
            # Train reporting uses a fixed evaluation ensemble, distinct from SGD draws.
            key_split=3 if split=='train'else sc
            plans=[operators(a,depth,fanout,[seed,rc,key_split,draw])for draw in range(draws)]
            logits=prediction(p,x,plans,protocol['normalization_epsilon'])
            y=np.asarray([r['y']for r in rows]);metrics=core.metrics(y,logits)
            for graph,lg,stat in zip(rows,logits,metrics):
                raw.append({k:item[k]for k in ('seed','regime','fanout','depth')}|{'graph_id':graph['id'],'split':split,'y':graph['y'],'logits':lg.tolist(),**stat})
            summary.append({k:item[k]for k in ('seed','regime','fanout','depth','epoch')}|{'split':split,
                'accuracy':float(np.mean([r['accuracy']for r in metrics])),
                'cross_entropy':float(np.mean([r['cross_entropy']for r in metrics])),
                'graph_accuracy_min':min(r['accuracy']for r in metrics),'graph_accuracy_max':max(r['accuracy']for r in metrics),
                'neighbor_entries_per_layer_per_draw':sum(int(np.count_nonzero(op))for op in plans[0])/depth,
                'evaluation_draws':draws})
    core.dump(destination/'raw_predictions.json',raw);core.dump(destination/'summary.json',summary)
    # Baseline is a frozen previously evaluated control, never used to select new SAGE.
    base_selection=[r for r in core.load(parent/'results/selection.json')if r['family']=='no_graph']
    base_raw=[r for r in core.load(parent/'results/raw_predictions.json')if r['family']=='no_graph' and any(all(r[k]==q[k]for k in ('seed','regime','depth'))for q in base_selection)]
    core.dump(destination/'baseline_reference.json',{'selection':base_selection,'raw_predictions':base_raw,
        'note':'published no_graph validation-selected control; reused, not retrained; parameter budget differs'})
    core.dump(destination/'enumeration.json',enumeration())
    core.dump(destination/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,
        'platform':platform.platform(),'seconds':time.monotonic()-start,'gpu':False,'threads_requested':1})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--parent',type=Path,default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--protocol',type=Path,default=Path(__file__).with_name('protocol.json'))
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    core=load_core(args.parent);protocol=core.load(args.protocol)
    core.dump(args.output/'protocol.json',protocol)
    core.dump(args.output/'identity.json',{'sage_source_sha256':core.digest(__file__),'protocol_sha256':core.digest(args.protocol),
        'inputs_sha256':core.digest(args.parent/'inputs.json'),'core_sha256':core.digest(args.parent/'graph_task.py'),
        'baseline_raw_sha256':core.digest(args.parent/'results/raw_predictions.json'),
        'baseline_selection_sha256':core.digest(args.parent/'results/selection.json')})
    run(core,args.parent,protocol,args.output)


if __name__=='__main__':main()
