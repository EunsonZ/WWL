"""Finite-dimensional continuous LTI teaching models; no plant identification.

States and outputs are normalized amplitudes, time is seconds. NumPy only.
Results use floating point Taylor scaling/squaring, not certified intervals.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np

def real_array(x, ndim):
    # Object dtype hides NumPy complex scalars from np.iscomplexobj(raw).
    # Reject before float conversion, including zero imaginary part/subclasses.
    try:
        raw = np.asarray(x)
        if raw.ndim != ndim or np.iscomplexobj(raw) or (raw.dtype == object and any(
                isinstance(v, (complex, np.complexfloating)) or np.iscomplexobj(v)
                for v in raw.flat)):
            raise ValueError('finite real array with specified dimension required')
        a = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError('real numeric array required') from e
    if not np.all(np.isfinite(a)):
        raise ValueError('nonfinite array')
    return a

def square(A):
    A = real_array(A, 2)
    if A.shape[0] == 0 or A.shape[0] != A.shape[1]:
        raise ValueError('nonempty square A required')
    return A

def time_value(T):
    if isinstance(T, (bool, np.bool_)) or not np.isscalar(T) or np.iscomplexobj(T):
        raise ValueError('finite nonnegative time required')
    T = float(T)
    if not math.isfinite(T) or T < 0:
        raise ValueError('finite nonnegative time required')
    return T

def finite_result(a):
    if not np.all(np.isfinite(a)):
        raise ValueError('numerical result is not representable')
    return a

def model(A, B, C, D):
    A, B, C, D = square(A), real_array(B,2), real_array(C,2), real_array(D,2)
    n=A.shape[0]
    if B.shape[0]!=n or C.shape[1]!=n or B.shape[1]<1 or C.shape[0]<1 or D.shape!=(C.shape[0],B.shape[1]):
        raise ValueError('A:n*n B:n*m C:p*n D:p*m with n,m,p >= 1')
    return A,B,C,D

def expm(A):
    """Taylor at ||A/2**s||_inf <= .5, then square; handles Jordan blocks.

    Explicit finite range checks; no arbitrary ill-conditioned accuracy guarantee.
    """
    A=square(A)
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        norm=float(np.linalg.norm(A,np.inf))
        if not math.isfinite(norm):
            raise ValueError('matrix norm is not representable')
        s=max(0, int(math.ceil(math.log2(norm)+1))) if norm > .5 else 0
        scaled=np.ldexp(A,-s)
        result=term=np.eye(len(A))
        for k in range(1,81):
            term=term@scaled/k
            result=result+term
            if np.linalg.norm(term,np.inf) <= 2e-16*max(1.,float(np.linalg.norm(result,np.inf))):
                break
        else:
            raise ValueError('matrix series did not converge')
        for _ in range(s):
            result=finite_result(result@result)
    return finite_result(result)

def transition(A,t):
    A=square(A);t=time_value(t)
    with np.errstate(over='ignore',invalid='ignore'):
        At=finite_result(A*t)
    return expm(At)

def constant_response(A,B,C,D,t,x0,u):
    """Exact-form constant-input solution via an augmented matrix exponential.

    No A inverse; singular A including integrators is supported.
    """
    A,B,C,D=model(A,B,C,D);t=time_value(t)
    x0,u=real_array(x0,1),real_array(u,1)
    n,m=B.shape
    if x0.shape!=(n,) or u.shape!=(m,):
        raise ValueError('x0:n and u:m required')
    block=np.zeros((n+m,n+m));block[:n,:n]=A;block[:n,n:]=B
    E=transition(block,t)
    with np.errstate(over='ignore',invalid='ignore'):
        x=finite_result(E[:n,:n]@x0+E[:n,n:]@u)
        y=finite_result(C@x+D@u)
    return x,y

def structure(A,B,C):
    A,B,C=square(A),real_array(B,2),real_array(C,2)
    A,B,C,D=model(A,B,C,np.zeros((C.shape[0],B.shape[1])))
    n=len(A);power=np.eye(n);R=[];O=[]
    with np.errstate(over='ignore',invalid='ignore'):
        for k in range(n):
            R.append(finite_result(power@B));O.append(finite_result(C@power))
            power=finite_result(power@A)
    return np.hstack(R),np.vstack(O)

def rank_report(K, rtol=1e-10, atol=0.):
    K=real_array(K,2)
    if min(K.shape)<1 or not math.isfinite(rtol) or not math.isfinite(atol) or rtol<0 or atol<0:
        raise ValueError('nonempty matrix and finite nonnegative tolerances required')
    sv=np.linalg.svd(K,compute_uv=False)
    if not np.all(np.isfinite(sv)):
        raise ValueError('singular values are outside numerical support; rescale matrix')
    threshold=max(atol,rtol*float(sv[0]))
    if not math.isfinite(threshold):
        raise ValueError('rank threshold is outside numerical support')
    return dict(rank=int(np.count_nonzero(sv>threshold)),singular_values=sv.tolist(),
                threshold=threshold,rtol=rtol,atol=atol,
                evidence='numerical rank at declared coordinates/tolerance, not structural identification')

def gramian(A,B,T):
    """Finite reachability Gramian: exp [[A,BB^T],[0,-A^T]]T.

    Upper-right block times exp(A^T T) equals integral exp(A t)BB^T exp(A^T t)dt.
    """
    A=square(A);B=real_array(B,2);T=time_value(T);n=len(A)
    if B.shape[0]!=n or B.shape[1]<1:
        raise ValueError('B:n*m required')
    block=np.zeros((2*n,2*n))
    with np.errstate(over='ignore',invalid='ignore'):
        block[:n,:n]=A;block[:n,n:]=finite_result(B@B.T);block[n:,n:]=-A.T
        E=transition(block,T)
        W=finite_result(E[:n,n:]@E[:n,:n].T)
    return finite_result(W/2+W.T/2)

def observability_gramian(A,C,T):
    A=square(A);C=real_array(C,2)
    if C.shape[1]!=len(A) or C.shape[0]<1:
        raise ValueError('C:p*n required')
    return gramian(A.T,C.T,T)

def transfer(A,B,C,D,s):
    A,B,C,D=model(A,B,C,D)
    try:s=complex(s)
    except (TypeError,ValueError) as e:raise ValueError('finite complex s required') from e
    if not math.isfinite(s.real) or not math.isfinite(s.imag):raise ValueError('finite complex s required')
    try:
        with np.errstate(over='ignore',invalid='ignore'):
            return finite_result(C@np.linalg.solve(s*np.eye(len(A))-A,B)+D)
    except np.linalg.LinAlgError as e:
        raise ValueError('sI-A singular: use algebraically reduced transfer separately') from e

def markov(A,B,C,count=5):
    A,B,C=square(A),real_array(B,2),real_array(C,2)
    A,B,C,D=model(A,B,C,np.zeros((C.shape[0],B.shape[1])))
    if type(count) is not int or count<0:raise ValueError('nonnegative integer count required')
    terms=[];power=np.eye(len(A))
    with np.errstate(over='ignore',invalid='ignore'):
        for k in range(count):
            terms.append(finite_result(C@power@B))
            if k+1 < count:
                power=finite_result(power@A)
    return terms

def experiment():
    A=np.diag([-1.,1.]);B=np.array([[1.],[1.]]);C=np.array([[1.,0.]]);D=np.zeros((1,1))
    t=np.linspace(0,6,301)
    xs=[];ys=[];visible=[];ic=[]
    for ti in t:
        x,y=constant_response(A,B,C,D,ti,[0,0],[1]);xs.append(x);ys.append(y[0])
        _,v=constant_response(A,B,[[1,1e-3]],D,ti,[0,0],[1]);visible.append(v[0])
        _,z=constant_response(A,[[1],[0]],[[1,1]],D,ti,[0,1],[0]);ic.append(z[0])
    xs=np.array(xs);ys=np.array(ys)
    W=observability_gramian(np.diag([-1.,-2.]),[[1.,1.]],1.)
    W_hidden=observability_gramian(A,C,1.)
    r,o=structure(A,B,C)
    eps=1e-12;_,near=structure(A,B,[[1,eps]])
    _,scaled=structure(A,B,[[1,1]])
    S=np.diag([1.,1e12]);_,scaled=structure(S@A@np.linalg.inv(S),S@B,np.array([[1,1]])@np.linalg.inv(S))
    Q=np.linspace(-1,1,31);q1,q2=np.meshgrid(Q,Q)
    energy=W[0,0]*q1*q1+2*W[0,1]*q1*q2+W[1,1]*q2*q2
    results=dict(schema='wwl-state-v1',normalized_units=True,time_units='s',A=A.tolist(),B=B.tolist(),C=C.tolist(),
        R=rank_report(r),O=rank_report(o),near_O_loose=rank_report(near,rtol=1e-10),near_O_tight=rank_report(near,rtol=1e-14),scaled_O=rank_report(scaled),
        W_observable_T1=W.tolist(),W_hidden_T1=W_hidden.tolist(),
        W_observable_eigenvalues=np.linalg.eigvalsh(W).tolist(),
        hidden_t6=float(xs[-1,1]),output_t6=float(ys[-1]),near_visible_t6=float(visible[-1]),ic_visible_t6=float(ic[-1]),
        numerical_accuracy='floating point teaching checks; no interval enclosure',
        evidence='known-model CPU examples, not identification, plant or controller evidence')
    return dict(t=t,x=xs,y=ys,visible=np.array(visible),ic=np.array(ic),W=W,q1=q1,q2=q2,energy=energy,results=results)

def write_data(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);d=experiment()
    np.savetxt(output/'trajectories.csv',np.column_stack([d['t'],d['x'],d['y'],d['visible'],d['ic']]),delimiter=',',header='t_s,x1_normalized,x2_normalized,y_hidden,y_epsilon_0.001,y_IC_visible',comments='',fmt='%.17g')
    np.savetxt(output/'energy.csv',np.column_stack([d['q1'].ravel(),d['q2'].ravel(),d['energy'].ravel()]),delimiter=',',header='x01_normalized,x02_normalized,output_energy_normalized_squared_s',comments='',fmt='%.17g')
    np.savetxt(output/'gramians.csv',np.column_stack([np.arange(4),d['W'].ravel(),np.array(d['results']['W_hidden_T1']).ravel()]),delimiter=',',header='rowmajor_index,Wo_observable_T1,Wo_hidden_T1',comments='',fmt='%.17g')
    (output/'results.json').write_text(json.dumps(d['results'],ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return d

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    print(json.dumps(write_data(p.parse_args().output)['results'],sort_keys=True))
