"""Small independent-graph node classification; NumPy only, CPU, no downloads.

Generation and evaluation possess labels; forward() accepts only A and X.
Run generate before train. All figures derive from saved inputs and raw predictions.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import platform
import time
from pathlib import Path
import numpy as np


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def load(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(protocol):
    """Latent z generates y, edges and a noisy measurement, independently per graph.

    IDs and RNG seeds are bookkeeping and never input features. No cross-graph edges.
    """
    rows = []
    for seed in protocol['seeds']:
        for regime, (p_same, p_other) in protocol['regimes'].items():
            for split, count in protocol['splits'].items():
                split_code = {'train': 0, 'val': 1, 'test': 2}[split]
                regime_code = {'homophily': 0, 'heterophily': 1}[regime]
                for index in range(count):
                    rng_key = [seed, regime_code, split_code, index]
                    rng = np.random.default_rng(np.random.SeedSequence(rng_key))
                    n = protocol['nodes']
                    z = np.r_[np.ones(n // 2), -np.ones(n - n // 2)]
                    rng.shuffle(z)
                    x = np.column_stack((z + rng.normal(0, protocol['noise_sd'], n),
                                         rng.normal(0, protocol['noise_sd'], n)))
                    x = np.clip(x, -protocol['clip'], protocol['clip']) / protocol['clip']
                    a = np.zeros((n, n), dtype=int)
                    for i in range(n):
                        for j in range(i + 1, n):
                            a[i, j] = a[j, i] = int(rng.random() < (p_same if z[i] == z[j] else p_other))
                    rows.append({'id': f'{seed}-{regime}-{split}-{index}', 'seed': seed,
                                 'regime': regime, 'split': split, 'rng_key': rng_key,
                                 'A': a.tolist(), 'X': x.tolist(), 'y': (z > 0).astype(int).tolist()})
    return {'schema': 'wwl-graph-input-v1', 'graphs': rows}


def arrays(rows):
    a = np.asarray([g['A'] for g in rows], dtype=float)
    x = np.asarray([g['X'] for g in rows], dtype=float)
    if a.ndim != 3 or a.shape[1] != a.shape[2] or x.ndim != 3 or x.shape[:2] != a.shape[:2]:
        raise ValueError('A must be G,N,N and X must be G,N,d')
    if not np.isfinite(a).all() or not np.isfinite(x).all() or not np.isin(a, [0, 1]).all():
        raise ValueError('finite features and binary adjacency required')
    if not np.array_equal(a, a.transpose(0, 2, 1)) or np.diagonal(a, axis1=1, axis2=2).any():
        raise ValueError('undirected graph without input self loops required')
    return a, x


def row_operator(a):
    b = a + np.eye(a.shape[-1])
    return b / b.sum(axis=-1, keepdims=True)


def initialize(family, depth, width, input_dim, seed):
    if family not in ('no_graph', 'fixed', 'joint') or depth not in (0, 1, 2, 4):
        raise ValueError('unsupported family or depth')
    rng = np.random.default_rng(seed + 1009 * depth)
    if family == 'fixed':
        return {'out': rng.normal(0, .1, (input_dim, 1)), 'out_b': np.zeros(1)}
    params = {'in': rng.normal(0, 1 / math.sqrt(input_dim), (input_dim, width)), 'in_b': np.zeros(width)}
    for k in range(depth):
        params[f'w{k}'] = rng.normal(0, 1 / math.sqrt(width), (width, width))
        params[f'b{k}'] = np.zeros(width)
    params['out'] = rng.normal(0, 1 / math.sqrt(width), (width, 1))
    params['out_b'] = np.zeros(1)
    return params


def forward(params, family, depth, a, x):
    """No labels, graph IDs, split labels or RNG keys may enter this interface."""
    p = row_operator(a)
    cache = []
    if family == 'fixed':
        h = x.copy()
        for _ in range(depth):
            h = p @ h
    else:
        h = np.tanh(x @ params['in'] + params['in_b'])
        cache.append((x, h))
        for k in range(depth):
            m = p @ h if family == 'joint' else h
            h = np.tanh(m @ params[f'w{k}'] + params[f'b{k}'])
            cache.append((m, h))
    logits = (h @ params['out'] + params['out_b'])[..., 0]
    return logits, h, cache, p


def sigmoid(logits):
    return np.exp(-np.logaddexp(0, -logits))


def objective(params, family, depth, a, x, y, l2):
    """Mean of per-graph node means, plus .5*l2*sum squared weight entries."""
    logits, h, cache, p = forward(params, family, depth, a, x)
    if y.shape != logits.shape or not np.isin(y, [0, 1]).all():
        raise ValueError('binary labels must match G,N logits')
    weight_names = [k for k in params if not k.endswith('_b') and not k.startswith('b')]
    loss = float(np.mean(np.logaddexp(0, logits) - y * logits))
    loss += .5 * l2 * sum(float((params[k] ** 2).sum()) for k in weight_names)
    dz = ((sigmoid(logits) - y) / y.size)[..., None]
    grad = {'out': np.einsum('gni,gnj->ij', h, dz), 'out_b': dz.sum(axis=(0, 1))}
    dh = dz @ params['out'].T
    if family != 'fixed':
        for k in reversed(range(depth)):
            m, activated = cache[k + 1]
            du = dh * (1 - activated ** 2)
            grad[f'w{k}'] = np.einsum('gni,gnj->ij', m, du)
            grad[f'b{k}'] = du.sum(axis=(0, 1))
            dm = du @ params[f'w{k}'].T
            # Row mean is generally NOT symmetric: backward uses P transpose.
            dh = p.transpose(0, 2, 1) @ dm if family == 'joint' else dm
        inp, activated = cache[0]
        du = dh * (1 - activated ** 2)
        grad['in'] = np.einsum('gni,gnj->ij', inp, du)
        grad['in_b'] = du.sum(axis=(0, 1))
    for k in weight_names:
        grad[k] += l2 * params[k]
    return loss, grad


def metrics(y, logits):
    pred = (logits >= 0).astype(int)
    ce = np.logaddexp(0, logits) - y * logits
    return [{'accuracy': float((pp == yy).mean()), 'cross_entropy': float(cc.mean()),
             'correct': int((pp == yy).sum()), 'nodes': int(yy.size)}
            for yy, pp, cc in zip(y, pred, ce)]


def train_one(train_rows, val_rows, family, depth, protocol, seed):
    a, x = arrays(train_rows)
    y = np.asarray([r['y'] for r in train_rows])
    va, vx = arrays(val_rows)
    vy = np.asarray([r['y'] for r in val_rows])
    params = initialize(family, depth, protocol['hidden'], x.shape[-1], seed)
    m = {k: np.zeros_like(v) for k, v in params.items()}
    v = copy.deepcopy(m)
    best, best_val, best_epoch = None, math.inf, None
    trace = []
    for epoch in range(1, protocol['epochs'] + 1):
        _, grad = objective(params, family, depth, a, x, y, protocol['l2'])
        for k in params:
            m[k] = .9 * m[k] + .1 * grad[k]
            v[k] = .999 * v[k] + .001 * grad[k] ** 2
            params[k] -= protocol['learning_rate'] * (m[k] / (1 - .9 ** epoch)) / (np.sqrt(v[k] / (1 - .999 ** epoch)) + 1e-8)
        train_logits = forward(params, family, depth, a, x)[0]
        val_logits = forward(params, family, depth, va, vx)[0]
        train_ce = float(np.mean(np.logaddexp(0, train_logits) - y * train_logits))
        val_ce = float(np.mean(np.logaddexp(0, val_logits) - vy * val_logits))
        trace.append({'epoch': epoch, 'train_ce': train_ce, 'val_ce': val_ce})
        if val_ce < best_val:
            best, best_val, best_epoch = copy.deepcopy(params), val_ce, epoch
    return best, best_epoch, best_val, trace


def run(inputs, protocol, destination):
    """Complete ALL validation decisions before evaluating any test label."""
    start = time.monotonic()
    trained, selection = [], []
    for seed in protocol['seeds']:
        for regime in protocol['regimes']:
            group = [g for g in inputs['graphs'] if g['seed'] == seed and g['regime'] == regime]
            tr = [g for g in group if g['split'] == 'train']
            va = [g for g in group if g['split'] == 'val']
            for family in protocol['families']:
                candidates = []
                for depth in protocol['depths']:
                    params, epoch, score, trace = train_one(tr, va, family, depth, protocol, seed)
                    item = {'seed': seed, 'regime': regime, 'family': family, 'depth': depth,
                            'epoch': epoch, 'val_ce': score, 'params': {k: v.tolist() for k, v in params.items()}, 'trace': trace}
                    candidates.append(item)
                    trained.append(item)
                chosen = min(candidates, key=lambda item: (item['val_ce'], item['depth']))
                selection.append({k: chosen[k] for k in ('seed', 'regime', 'family', 'depth', 'epoch', 'val_ce')})
    # This file is written before test evaluation. Test is never passed to train_one.
    dump(destination / 'selection.json', selection)
    dump(destination / 'checkpoints.json', trained)
    raw, summaries = [], []
    for item in trained:
        group = [g for g in inputs['graphs'] if g['seed'] == item['seed'] and g['regime'] == item['regime']]
        params = {k: np.asarray(v) for k, v in item['params'].items()}
        for split in ('train', 'val', 'test'):
            rows = [g for g in group if g['split'] == split]
            # Forward receives an explicit label-free copy, including for evaluation.
            visible = [{'A': g['A'], 'X': g['X']} for g in rows]
            a, x = arrays(visible)
            logits, h, _, _ = forward(params, item['family'], item['depth'], a, x)
            y = np.asarray([g['y'] for g in rows])
            by_graph = metrics(y, logits)
            for g, lg, stat in zip(rows, logits, by_graph):
                raw.append({k: item[k] for k in ('seed', 'regime', 'family', 'depth')} | {
                    'graph_id': g['id'], 'split': split, 'y': g['y'], 'logits': lg.tolist(), **stat})
            summaries.append({k: item[k] for k in ('seed', 'regime', 'family', 'depth', 'epoch')} | {
                'split': split, 'accuracy': float(np.mean([r['accuracy'] for r in by_graph])),
                'cross_entropy': float(np.mean([r['cross_entropy'] for r in by_graph])),
                'graph_accuracy_min': min(r['accuracy'] for r in by_graph),
                'graph_accuracy_max': max(r['accuracy'] for r in by_graph),
                'hidden_within_graph_norm': float(np.mean(np.linalg.norm(h - h.mean(axis=1, keepdims=True), axis=(1, 2))))})
    dump(destination / 'raw_predictions.json', raw)
    dump(destination / 'summary.json', summaries)
    dump(destination / 'environment.json', {'python': platform.python_version(), 'numpy': np.__version__,
         'platform': platform.platform(), 'seconds': time.monotonic() - start, 'gpu': False})


def spectral():
    out = {}
    for name, edges in [('cycle6', [(i, (i + 1) % 6) for i in range(6)]),
                        ('two_triangles', [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])]:
        a = np.zeros((6, 6))
        for i, j in edges:
            a[i, j] = a[j, i] = 1
        p = (a + np.eye(6)) / 3
        h = np.eye(6)[:, 0]
        limit = np.ones(6) / 6 if name == 'cycle6' else np.array([1, 1, 1, 0, 0, 0]) / 3
        history = []
        for k in range(13):
            history.append({'k': k, 'h': h.tolist(), 'distance_to_limit': float(np.linalg.norm(h - limit)),
                            'global_centered_norm': float(np.linalg.norm(h - h.mean()))})
            h = p @ h
        out[name] = {'A': a.tolist(), 'P': p.tolist(), 'eigenvalues': np.linalg.eigvalsh(p).tolist(),
                     'limit': limit.tolist(), 'history': history}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('generate', 'train', 'spectral'))
    parser.add_argument('--protocol', default=str(Path(__file__).with_name('protocol.json')))
    parser.add_argument('--inputs')
    parser.add_argument('--output', required=True, help='new path; never overwrite')
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        parser.error('output already exists')
    protocol = load(args.protocol)
    if args.command == 'generate':
        dump(target, generate(protocol))
    elif args.command == 'spectral':
        dump(target, spectral())
    else:
        if not args.inputs:
            parser.error('train needs --inputs')
        target.mkdir(parents=True)
        dump(target / 'protocol.json', protocol)
        dump(target / 'identity.json', {'source_sha256': digest(__file__), 'inputs_sha256': digest(args.inputs),
                                      'protocol_sha256': digest(args.protocol)})
        run(load(args.inputs), protocol, target)


if __name__ == '__main__':
    main()
