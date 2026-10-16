#!/usr/bin/env python3
"""Haar joint analysis/synthesis, reusing the vault's canonical resample offline().

Analysis is full causal convolution retained at phase 1; synthesis upsamples at
phase 0. Infinite exact PR has zero index delay, but a pair waits for odd input.
This is real linear floating point Haar, not integer-rounded nonlinear lifting.
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

KAPPA=1/math.sqrt(2)


def require(ok,message):
    if not ok:raise ValueError(message)


def vector(x):
    require(type(x) in (list,tuple,np.ndarray),'real vector required')
    require(not any(isinstance(v,(bool,np.bool_)) for v in x),'bool is not a sample')
    a=np.asarray(x)
    require(a.ndim==1 and a.size>0 and not np.iscomplexobj(a),'nonempty real vector')
    require(all(type(v) in (int,float,np.float64,np.int64) for v in list(a)),
            'real numeric samples required')
    a=np.asarray(a,dtype=float)
    require(np.all(np.isfinite(a)),'finite samples required')
    return a


def load_source(path):
    path=Path(path).resolve()
    require(path.is_file(),'canonical resample source missing: '+str(path))
    spec=importlib.util.spec_from_file_location('wwl_resample_canonical',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(module.offline),'source must provide offline')
    return module


def source_default():
    return Path(os.environ.get('WWL_RESAMPLE_SOURCE',
                str(Path(__file__).parent.parent/'02-流式音频重采样/resample_lab.py')))


def validate(c):
    keys={'samples_V','odd_samples_V','fs_Hz','boundary_modes','basis_lengths','shear_lambda'}
    require(type(c) is dict and set(c)==keys,'unexpected/missing input fields')
    for key in ('samples_V','odd_samples_V'):
        a=vector(c[key]);require(len(a)<=32,'record budget 32 samples')
        require(np.max(np.abs(a))<=1e6,'input sample amplitude budget 1e6 V')
    require(len(c['samples_V'])==4 and len(c['odd_samples_V'])%2==1,
            'four-point first record and odd second record required')
    require(type(c['fs_Hz']) in (int,float) and math.isfinite(c['fs_Hz'])
            and 0<c['fs_Hz']<=1e6,'positive finite fs')
    modes=c['boundary_modes']
    require(type(modes) is list and modes and len(set(modes))==len(modes)
            and set(modes)<={'zero','repeat'},'invalid boundary modes')
    lengths=c['basis_lengths']
    require(type(lengths) is list and 1<=len(lengths)<=16
            and all(type(n) is int and 1<=n<=32 for n in lengths)
            and len(set(lengths))==len(lengths),'distinct basis lengths within 1..32')
    lam=c['shear_lambda']
    require(type(lam) in (int,float) and math.isfinite(lam) and abs(lam)<=1,'shear budget')
    return c


def extend(samples,mode):
    x=vector(samples)
    require(mode in ('zero','repeat'),'invalid boundary')
    if len(x)%2:x=np.append(x,0 if mode=='zero' else x[-1])
    return x


def analysis(samples,mode,source,phase=1):
    original=vector(samples)
    x=extend(original,mode)
    require(type(phase) is int and phase in (0,1),'analysis phase must be 0 or 1')
    a=source.offline(x,[KAPPA,KAPPA],factor=2,phase=phase)
    d=source.offline(x,[-KAPPA,KAPPA],factor=2,phase=phase)
    return {'a':a,'d':d,'original_length':len(original),'extended_length':len(x),
            'boundary':mode,'phase':phase}


def synthesis(a,d,source,detail_sign=1):
    a,d=vector(a),vector(d)
    require(len(a)==len(d) and detail_sign in (-1,1),'matching bands/sign required')
    ua=np.zeros(2*len(a)-1);ud=ua.copy()
    ua[::2]=a;ud[::2]=d
    low=source.offline(ua,[KAPPA,KAPPA],factor=1,phase=0)
    high=source.offline(ud,[detail_sign*KAPPA,-detail_sign*KAPPA],factor=1,phase=0)
    return low+high


def reconstruct(packet,source,drop_detail=False):
    require(packet['phase']==1,'this inverse crop requires odd analysis phase')
    y=synthesis(packet['a'],np.zeros_like(packet['d']) if drop_detail else packet['d'],source)
    require(len(y)==packet['extended_length'],'full synthesis length drift')
    return y[:packet['original_length']]


def record(samples,mode,source,lam):
    x=vector(samples);p=analysis(x,mode,source)
    full=synthesis(p['a'],p['d'],source)
    restored=reconstruct(p,source);low=reconstruct(p,source,True)
    wrong=synthesis(p['a'],p['d'],source,detail_sign=-1)[:len(x)]
    bi_a=p['a']+lam*p['d']
    bi_full=synthesis(bi_a-lam*p['d'],p['d'],source)[:len(x)]
    bi_low=synthesis(bi_a,np.zeros_like(p['d']),source)[:len(x)]
    # Same four causal filters with phase 0 implement a full-rate delay of one.
    p0=analysis(x,mode,source,phase=0)
    y0=synthesis(p0['a'],p0['d'],source)
    out={'samples_V':x.tolist(),'boundary':mode,'original_length':len(x),
         'extended_samples_V':extend(x,mode).tolist(),'a_V':p['a'].tolist(),'d_V':p['d'].tolist(),
         'a_source_fullrate_indices':list(range(1,len(extend(x,mode)),2)),
         'restored_extended_V':full.tolist(),'restored_crop_V':restored.tolist(),
         'low_only_crop_V':low.tolist(),'wrong_detail_sign_crop_V':wrong.tolist(),
         'input_squared_norm_V2':float(x@x),
         'extended_squared_norm_V2':float(extend(x,mode)@extend(x,mode)),
         'coefficient_squared_norm_V2':float(p['a']@p['a']+p['d']@p['d']),
         'detail_squared_norm_V2':float(p['d']@p['d']),
         'low_only_crop_error_V2':float((x-low)@(x-low)),
         'wrong_detail_sign_error_V2':float((x-wrong)@(x-wrong)),
         'sheared_a_V':bi_a.tolist(),'shear_full_crop_V':bi_full.tolist(),
         'shear_low_only_crop_V':bi_low.tolist(),
         'shear_coefficient_squared_norm_V2':float(bi_a@bi_a+p['d']@p['d']),
         'shear_low_only_error_V2':float((x-bi_low)@(x-bi_low)),
         'phase0_full_output_V':y0.tolist(),'phase0_correct_delay_crop_V':y0[1:1+len(x)].tolist(),
         'phase0_wrong_crop_V':y0[:len(x)].tolist()}
    tolerance=2e-12*max(1,float(np.max(np.abs(x))))
    require(np.max(np.abs(restored-x))<=tolerance,'finite record PR failure')
    require(np.max(np.abs(bi_full-x))<=tolerance,'shear PR failure')
    require(np.max(np.abs(y0[1:1+len(x)]-x))<=tolerance,'phase0 delay failure')
    return out


def finite_basis(length,mode,source,lam):
    # This exposes every column of the exact linear model at THIS finite N.
    # Floating point runs are finite diagnostics, not formal proof over all floats.
    restored=[];low=[];sheared=[]
    for j in range(length):
        e=np.zeros(length);e[j]=1
        p=analysis(e,mode,source)
        restored.append(reconstruct(p,source))
        low.append(reconstruct(p,source,True))
        ba=p['a']+lam*p['d']
        sheared.append(synthesis(ba,np.zeros_like(p['d']),source)[:length])
    Q=np.array(restored).T;P=np.array(low).T;B=np.array(sheared).T
    maximum=float(np.max(np.abs(Q-np.eye(length))))
    require(maximum<=2e-12,'basis PR failure')
    return {'length':length,'boundary':mode,'basis_count':length,
            'max_PR_matrix_error':maximum,
            'low_operator_idempotence_error':float(np.max(np.abs(P@P-P))),
            'low_operator_symmetry_error':float(np.max(np.abs(P-P.T))),
            'shear_low_idempotence_error':float(np.max(np.abs(B@B-B))),
            'shear_low_symmetry_error':float(np.max(np.abs(B-B.T)))}


def run(c,source_path,output):
    validate(c);source=load_source(source_path)
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    records=[record(samples,mode,source,c['shear_lambda'])
             for samples in (c['samples_V'],c['odd_samples_V']) for mode in c['boundary_modes']]
    basis=[finite_basis(n,mode,source,c['shear_lambda'])
           for n in c['basis_lengths'] for mode in c['boundary_modes']]
    p=analysis(c['samples_V'],'zero',source)
    p2=analysis(p['a'],'zero',source)
    constant=analysis([3]*8,'zero',source)['d']
    ramp=analysis(list(range(8)),'zero',source)['d']
    result={'model':'causal-Haar-phase1-full-convolution-explicit-extension', 'inputs':c,
            'environment':{'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
                           'processes':1,'threads':1,'executable':sys.executable},
            'canonical_resample_source':str(Path(source_path).resolve()),
            'canonical_source_sha256':hashlib.sha256(Path(source_path).read_bytes()).hexdigest(),
            'records':records,'finite_basis_checks':basis,
            'two_level_coefficients':{'a2_V':p2['a'].tolist(),'d2_V':p2['d'].tolist(),'d1_V':p['d'].tolist()},
            'constant_detail_V':constant.tolist(),'ramp_detail_V':ramp.tolist(),
            'elapsed_s':time.monotonic()-start,'checks':'PASS'}
    (output/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    with (output/'samples.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['original_length','boundary','n','input_V','full_crop_V','low_crop_V','shear_low_crop_V','wrong_high_sign_V'])
        for r in records:
            for n,x in enumerate(r['samples_V']):
                w.writerow([r['original_length'],r['boundary'],n,x,r['restored_crop_V'][n],r['low_only_crop_V'][n],r['shear_low_only_crop_V'][n],r['wrong_detail_sign_crop_V'][n]])
    with (output/'basis.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(basis[0]));w.writeheader();w.writerows(basis)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resample-source',type=Path,default=source_default())
    args=parser.parse_args()
    try:r=run(json.loads(args.inputs.read_text()),args.resample_source,args.output)
    except (ValueError,OSError,ImportError) as e:parser.exit(2,str(e)+'\n')
    print(json.dumps({'checks':r['checks'],'elapsed_s':r['elapsed_s'],
                      'basis_vectors':sum(v['basis_count'] for v in r['finite_basis_checks']),
                      'output':str(args.output)}))


if __name__=='__main__':main()
