#!/usr/bin/env python3
"""Finite long-boundary experiments, reusing published db2 and convolution sources.
Continuous existence is proved in lesson 08, never inferred from this computation.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(x):
    return type(x) in (int, float) and math.isfinite(x)


def validate(c):
    require(type(c) is dict, 'object required')
    x = c.get('samples_V')
    require(type(x) is list and 6 <= len(x) <= 64 and len(x) % 2 == 0 and
            all(number(t) and abs(t) <= 1e6 for t in x), 'even 6..64 finite samples within 1e6 required')
    require(number(c.get('sample_rate_Hz')) and 0 < c['sample_rate_Hz'] <= 1e6, 'positive finite sample rate required')
    ns = c.get('basis_lengths')
    require(type(ns) is list and 1 <= len(ns) <= 12 and all(type(n) is int and 4 <= n <= 64 and n % 2 == 0 for n in ns)
            and len(set(ns)) == len(ns), 'distinct even basis lengths 4..64 required')
    require(number(c.get('mix_a')) and abs(c['mix_a']) < 1, 'finite abs(mix_a)<1 required')
    js = c.get('cascade_levels')
    require(type(js) is list and 1 <= len(js) <= 5 and all(type(j) is int and 1 <= j <= 12 for j in js)
            and len(set(js)) == len(js), 'distinct integer cascade levels 1..12 required')
    require(type(c.get('display_grid_denominator')) is int and 16 <= c['display_grid_denominator'] <= 256,
            'integer display denominator 16..256 required')
    require(type(c.get('dual_last_shift')) is int and 1 <= c['dual_last_shift'] <= 16, 'integer dual_last_shift 1..16 required')
    ms = c.get('instability_lengths')
    require(type(ms) is list and 1 <= len(ms) <= 8 and len(set(ms)) == len(ms) and
            all(type(m) is int and 2 <= m <= 256 and m % 2 == 0 for m in ms), 'distinct even instability lengths 2..256 required')


def load_published(root):
    root = Path(root).resolve()
    src = root / '信号与系统/80-实践/02-流式音频重采样/resample_lab.py'
    mask = root / '信号与系统/80-实践/14-Haar函数空间与消失矩/results/results.json'
    require(src.is_file() and mask.is_file(), 'published source and mask JSON required')
    spec = importlib.util.spec_from_file_location('published_resample', src)
    mod = importlib.util.module_from_spec(spec)
    old_no_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True  # Published source is read-only, including cache files.
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = old_no_bytecode
    masks = json.loads(mask.read_text())['filters']
    d = next(t for t in masks if t['name'] == 'db2_mask')
    h, g = np.array(d['h']), np.array(d['g'])
    require(h.shape == (4,) and g.shape == (4,) and np.isfinite(h).all() and np.isfinite(g).all(), 'four finite db2 taps required')
    refs = [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (src, mask)]
    return h, g, mod.offline, refs


def analysis(x, h, g, offline, mode):
    x = np.asarray(x, dtype=float)
    if mode == 'periodic':
        xx = np.r_[x, x[:3]]
        return tuple(offline(xx, z[::-1], 2, 1)[1:1 + len(x)//2] for z in (h, g))
    require(mode == 'zero_full', 'unknown boundary mode')
    return tuple(offline(x, z[::-1], 2, 1) for z in (h, g))


def synthesis(a, d, h, g, offline, n, mode):
    require(len(a) == len(d) and len(a) > 0, 'equal nonempty subbands required')
    u, v = np.zeros(2*len(a)-1), np.zeros(2*len(d)-1)
    u[::2], v[::2] = a, d
    full = offline(u, h, 1, 0) + offline(v, g, 1, 0)
    if mode == 'periodic':
        out = np.zeros(n)
        for i, value in enumerate(full):
            out[i % n] += value
        return out, full
    if mode == 'zero_full':
        return full[2:2+n], full
    require(mode == 'zero_dropped', 'unknown boundary mode')
    return full[:n], full


def mix(q, a):
    return q + a*np.roll(q, 1)


def unmix(d, a):
    # On a length M circle S^M=I. This differs from the infinite geometric inverse.
    m = len(d)
    return sum(((-a)**r)*np.roll(d, r) for r in range(m)) / (1-(-a)**m)


def sq(x):
    return float(np.dot(x, x))


def record(x, h, g, offline, a):
    n = len(x)
    out = {}
    for mode in ('periodic', 'zero_full'):
        aa, dd = analysis(x, h, g, offline, mode)
        restored, full = synthesis(aa, dd, h, g, offline, n, mode)
        out[mode] = {'a': aa.tolist(), 'd': dd.tolist(), 'restored': restored.tolist(),
                     'synthesis_full': full.tolist(), 'input_squared_sum_V2': sq(x),
                     'coefficient_squared_sum_V2': sq(aa)+sq(dd), 'error_squared_sum_V2': sq(restored-x)}
    aa, dd = analysis(x, h, g, offline, 'zero_full')
    bad, full = synthesis(aa[1:], dd[1:], h, g, offline, n, 'zero_dropped')
    out['zero_dropped'] = {'a': aa[1:].tolist(), 'd': dd[1:].tolist(), 'restored': bad.tolist(),
                           'synthesis_full': full.tolist(), 'error_squared_sum_V2': sq(bad-x)}
    aa, dd = analysis(x, h, g, offline, 'periodic')
    q = unmix(dd, a)
    restored, _ = synthesis(aa, mix(q, a), h, g, offline, n, 'periodic')
    out['biorth_periodic'] = {'a': aa.tolist(), 'q': q.tolist(), 'orthogonal_d': dd.tolist(),
                             'restored': restored.tolist(), 'coefficient_squared_sum_V2': sq(aa)+sq(q),
                             'error_squared_sum_V2': sq(restored-x)}
    return out


def basis_check(n, h, g, offline, a):
    eye = np.eye(n)
    results = {'length': n, 'vectors': n}
    for mode in ('periodic', 'zero_full'):
        cols = [np.r_[*analysis(x, h, g, offline, mode)] for x in eye]
        E = np.column_stack(cols)
        restored = [synthesis(*analysis(x, h, g, offline, mode), h, g, offline, n, mode)[0] for x in eye]
        RE = np.column_stack(restored)
        results[mode] = {'rows': len(E), 'max_RE_minus_I': float(np.max(np.abs(RE-eye))),
                         'max_EtE_minus_I': float(np.max(np.abs(E.T@E-eye)))}
    restored, eco = [], []
    for x in eye:
        aa, dd = analysis(x, h, g, offline, 'periodic')
        q = unmix(dd, a)
        eco.append(np.r_[aa, q])
        restored.append(synthesis(aa, mix(q, a), h, g, offline, n, 'periodic')[0])
    E = np.column_stack(eco)
    results['biorth_periodic'] = {'max_RE_minus_I': float(np.max(np.abs(np.column_stack(restored)-eye))),
                                  'max_EtE_minus_I': float(np.max(np.abs(E.T@E-eye)))}
    return results


def cascade(h, g, levels, denominator, last, a):
    c = math.sqrt(2)*h
    prev = np.ones(1)
    curves, diagnostics = [], []
    grid = np.arange(-last*denominator, 4*denominator+1, dtype=float)/denominator
    for j in range(1, max(levels)+1):
        shift = 2**(j-1)
        v = np.zeros(len(prev)+3*shift)
        w = np.zeros_like(v)
        for k in range(4):
            v[k*shift:k*shift+len(prev)] += c[k]*prev
            w[k*shift:k*shift+len(prev)] += math.sqrt(2)*g[k]*prev
        if j in levels:
            def ev(values, t):
                indices = np.floor(np.asarray(t)*2**j).astype(int)
                good = (indices >= 0) & (indices < len(values))
                out = np.zeros(len(indices))
                out[good] = values[indices[good]]
                return out
            psi = ev(w, grid)
            b = psi+a*ev(w, grid-1)
            dual = sum(((-a)**r)*ev(w, grid+r) for r in range(last+1))
            curves.append({'level': j, 'tau': grid.tolist(), 'phi_cascade': ev(v, grid).tolist(),
                           'psi_cascade': psi.tolist(), 'b_cascade': b.tolist(), 'dual_partial_cascade': dual.tolist()})
            corr = {str(k): float(np.dot(v[k*2**j:], v[:-k*2**j])/2**j) if k*2**j < len(v) else 0. for k in (1, 2)}
            diagnostics.append({'level': j, 'cell_width': 2.**(-j), 'cell_count': len(v),
                                'integral': float(sum(v)/2**j), 'norm_squared': sq(v)/2**j,
                                'integer_shift_correlations': corr})
        prev = v
    return {'curves': curves, 'finite_iterate_checks': diagnostics,
            'last_dual_shift': last, 'dual_tail_L2_bound_for_exact_psi': abs(a)**(last+1)/math.sqrt(1-a*a),
            'warning': 'piecewise-constant finite iterates at grid positions, not exact continuous scaling samples'}


def run(c, root):
    validate(c)
    h, g, offline, refs = load_published(root)
    x = np.array(c['samples_V'], dtype=float)
    a = c['mix_a']
    result = {'model': 'db2-long-boundaries-and-continuous-proof-companion-v1', 'inputs': c,
              'published_sources': refs, 'h': h.tolist(), 'g': g.tolist(), 'record': record(x,h,g,offline,a),
              'basis': [basis_check(n,h,g,offline,a) for n in c['basis_lengths']]}
    # Independent analytic boundary null direction, not obtained by numerical SVD.
    null = np.zeros(len(x)); null[:2] = [math.sqrt(3)/2, -.5]
    result['boundary_null'] = {'input': null.tolist(), 'outputs': record(null,h,g,offline,a)}
    result['boundary_prediction'] = {'unit_null': null.tolist(), 'dot_with_input_V': float(null@x),
                                      'predicted_dropped_SSE_V2': float(null@x)**2}
    result['instability_a_equal_1'] = []
    for m in c['instability_lengths']:
        q = np.array([(-1.)**k/math.sqrt(m) for k in range(m)])
        # Finite-support sequence on Z: retain both endpoints, no wrap.
        y = np.r_[q, 0.] + np.r_[0., q]
        result['instability_a_equal_1'].append({'M':m,'input_norm_squared':sq(q), 'output_norm_squared':sq(y), 'analytic_expected':2/m,
                                               'circular_output_norm_squared':sq(mix(q,1.))})
    result['biorth_exact_example'] = {'a':a, 'f_norm_squared':1., 'analysis_squared_sum':1/(1-a*a),
                                     'keep_q0_reconstruction_error_squared':a*a,
                                     'discarded_squared_sum':a*a/(1-a*a),
                                     'primal_Riesz_bounds':[(1-abs(a))**2,(1+abs(a))**2]}
    result['cascade'] = cascade(h,g,c['cascade_levels'],c['display_grid_denominator'],c['dual_last_shift'],a)
    # Fail rather than silently publish a violated numerical contract.
    scale = max(1., float(np.max(np.abs(x))))
    tol = 2e-11*scale/max(1e-10,1-abs(a))
    for mode in ('periodic','zero_full','biorth_periodic'):
        require(np.max(np.abs(np.array(result['record'][mode]['restored'])-x)) < tol, 'restoration failure: '+mode)
    for b in result['basis']:
        for mode in ('periodic','zero_full','biorth_periodic'):
            require(b[mode]['max_RE_minus_I'] < 2e-10/max(1e-10,1-abs(a)), 'basis restoration failed')
    require(abs(result['record']['zero_dropped']['error_squared_sum_V2']-result['boundary_prediction']['predicted_dropped_SSE_V2']) < 2e-10*scale*scale,
            'analytic boundary failure prediction mismatch')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--vault-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();start=time.monotonic()
    try:
        c=json.loads(args.inputs.read_text()); r=run(c,args.vault_root)
        r['environment']={'python':platform.python_version(),'numpy':np.__version__, 'platform':platform.platform(),
                          'threads':{k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}}
        r['elapsed_seconds']=time.monotonic()-start
        require(not args.out.exists(),'output directory already exists')
        args.out.mkdir(parents=True)
        (args.out/'results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        with (args.out/'samples.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['n','time_s','input_V','periodic_V','zero_full_V','zero_dropped_V','biorth_periodic_V'])
            for i,v in enumerate(c['samples_V']):w.writerow([i,i/c['sample_rate_Hz'],v]+[r['record'][k]['restored'][i] for k in ('periodic','zero_full','zero_dropped','biorth_periodic')])
        print(json.dumps({'out':str(args.out),'basis_vectors':sum(b['vectors'] for b in r['basis']),
                          'dropped_SSE_V2':r['record']['zero_dropped']['error_squared_sum_V2'],'seconds':r['elapsed_seconds']}))
    except (ValueError,KeyError,TypeError,IndexError,OSError,StopIteration) as e:
        print('error: '+str(e),file=sys.stderr);return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
