"""Small explicit teaching models. Import never writes files. SI internally."""
import argparse
import json
import math
import numbers
from pathlib import Path
import numpy as np


def positive(value, name):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')
    return value


def incidence(n, edges):
    if not isinstance(n, int) or n < 1:
        raise ValueError('n must be positive integer; ground is 0')
    a = np.zeros((n, len(edges)))
    for col, (start, end) in enumerate(edges):
        if any(not isinstance(v, int) or v < 0 or v > n for v in (start, end)) or start == end:
            raise ValueError('edge endpoint invalid or self-loop')
        if start: a[start-1, col] += 1
        if end: a[end-1, col] -= 1
    return a


def resistor_network(n, edges, conductance, injection):
    a = incidence(n, edges)
    g = np.asarray(conductance, dtype=float)
    b = np.asarray(injection, dtype=float)
    if g.shape != (len(edges),) or b.shape != (n,) or not np.isfinite(g).all() or not np.isfinite(b).all() or (g <= 0).any():
        raise ValueError('conductance/injection shape or domain invalid')
    y = (a*g) @ a.T
    v = np.linalg.solve(y, b)  # singular inputs are deliberately not patched
    u = a.T @ v
    i = g*u
    return a, y, v, i, float(np.dot(u, i))


def mna(y, b, source_columns, voltages):
    y = np.asarray(y, dtype=float); b = np.asarray(b, dtype=float)
    B = np.asarray(source_columns, dtype=float); e = np.asarray(voltages, dtype=float)
    n = len(b)
    if y.shape != (n,n) or B.ndim != 2 or B.shape[0] != n or e.shape != (B.shape[1],):
        raise ValueError('MNA shapes incompatible')
    if not all(np.isfinite(z).all() for z in [y,b,B,e]):
        raise ValueError('MNA requires finite values')
    k = np.block([[y,B],[B.T,np.zeros((len(e),len(e)))]])
    rhs = np.r_[b,e]
    return k, rhs, np.linalg.solve(k,rhs)


def constraint_ranks(y, e):
    """Parallel sources: exact constructive model, ranks use explicit float scale."""
    e = np.asarray(e,dtype=float)
    k = np.zeros((1+len(e),1+len(e))); k[0,0]=y
    k[0,1:]=1; k[1:,0]=1
    rhs=np.r_[0.,e]
    return int(np.linalg.matrix_rank(k)),int(np.linalg.matrix_rank(np.column_stack((k,rhs))))


def cv_source(c, times, values, v0):
    # Reject a changed physical input before any complex-to-float coercion.
    def real_array(value, name):
        raw = np.asarray(value)
        if np.iscomplexobj(raw) or raw.dtype.kind not in 'iufO':
            raise ValueError(f'{name} requires real numeric input')
        if raw.dtype.kind == 'O' and any(
                not isinstance(x, numbers.Real) or isinstance(x, (bool, np.bool_))
                for x in raw.flat):
            raise ValueError(f'{name} object elements must be real numbers')
        return np.asarray(raw, dtype=float)
    c_array=real_array(c,'C');v0_array=real_array(v0,'v0')
    if c_array.ndim != 0 or v0_array.ndim != 0:
        raise ValueError('C and v0 require real scalars')
    c=float(c_array);v0=float(v0_array);positive(c,'C')
    t=real_array(times,'times');u=real_array(values,'values')
    if t.ndim!=1 or len(t)<2 or u.shape!=t.shape or not np.isfinite(t).all() or not np.isfinite(u).all() or not math.isfinite(v0) or (np.diff(t)<=0).any():
        raise ValueError('ordered finite time/source arrays required')
    if not math.isclose(v0,float(u[0]),rel_tol=0,abs_tol=1e-12):
        raise ValueError('inconsistent capacitor voltage initial condition')
    return u.copy(), -c*np.diff(u)/np.diff(t)


def rc_backward(r,c,u,h,steps,v0=0):
    positive(r,'R');positive(c,'C');positive(h,'h')
    if not isinstance(steps,int) or steps<1 or not all(math.isfinite(z) for z in (u,v0)):
        raise ValueError('finite input/initial value and positive step count required')
    vs=[v0]
    for _ in range(steps):vs.append((vs[-1]+h*u/(r*c))/(1+h/(r*c)))
    return np.arange(steps+1)*h,np.array(vs)


def diode_residual(v, supply=5., r=1000., Is=1e-12, thermal=.025):
    positive(r,'R');positive(Is,'Is');positive(thermal,'nVT')
    if not math.isfinite(v) or not math.isfinite(supply) or v/thermal>700:
        raise ValueError('voltage outside finite exponential model range')
    expv=math.exp(v/thermal)
    return (v-supply)/r+Is*math.expm1(v/thermal),1/r+Is*expv/thermal


def diode_newton(start=.5, residual_tol=1e-12, voltage_tol=1e-10, max_iter=100):
    positive(residual_tol,'residual_tol');positive(voltage_tol,'voltage_tol')
    if not isinstance(max_iter,int) or max_iter<1:raise ValueError('max_iter invalid')
    v=float(start);trace=[]
    for k in range(max_iter):
        f,j=diode_residual(v);trace.append({'k':k,'v_V':v,'residual_A':f})
        if abs(f)<=residual_tol:
            # Bound follows from F' >= 1/R, independent of tiny damping steps.
            if 1000*abs(f)<=voltage_tol:return v,trace
        delta=-f/j;lam=1.
        while lam>=2**-24:
            trial=v+lam*delta
            try: ft,_=diode_residual(trial)
            except ValueError: ft=float('inf')
            if math.isfinite(ft) and abs(ft)<abs(f):break
            lam/=2
        else:raise ArithmeticError('line search failed to lower original residual')
        trace[-1]['lambda']=lam;trace[-1]['step_V']=lam*delta
        v=trial
    raise ArithmeticError('iteration limit')


def diode_bisection(a=0.,b=.6,voltage_tol=1e-12,max_iter=256):
    positive(voltage_tol,'voltage_tol')
    if not isinstance(max_iter,int) or isinstance(max_iter,bool) or max_iter<1:
        raise ValueError('max_iter must be a positive integer')
    fa,_=diode_residual(a);fb,_=diode_residual(b)
    if not (a<b and fa<0<fb):raise ValueError('requires strict increasing-model bracket')
    for _ in range(max_iter):
        if (b-a)/2<=voltage_tol:return (a+b)/2,(b-a)/2
        mid=(a+b)/2
        if not a<mid<b:
            raise ArithmeticError('bisection stagnation: no representable interior midpoint')
        fm,_=diode_residual(mid)
        if fm==0:return mid,(b-a)/2
        if fm<0:a=mid
        else:b=mid
    raise ArithmeticError('bisection iteration limit')


def cubic_step(u):
    if not math.isfinite(u):raise ValueError('finite u required')
    jac=3*u*u-1
    if abs(jac)<1e-14:raise ArithmeticError('zero cubic Jacobian')
    return u-(u**3-u)/jac


def z_parameters(ra=1000.,rb=2000.,rc=3000.):
    for x,n in [(ra,'Ra'),(rb,'Rb'),(rc,'Rc')]:positive(x,n)
    z=np.array([[ra+rc,rc],[rc,rb+rc]])
    det=float(np.linalg.det(z));z21=z[1,0];z22=z[1,1]
    y=np.linalg.solve(z,np.eye(2))
    h=np.array([[det/z22,z[0,1]/z22],[-z21/z22,1/z22]])
    T=np.array([[z[0,0]/z21,det/z21],[1/z21,z22/z21]])
    return z,y,h,T


def transfer(ra,rb,rc,rl):
    for x,n in zip((ra,rb,rc,rl),('Ra','Rb','Rc','RL')):positive(x,n)
    d=ra*rc+ra*rb+ra*rl+rc*rb+rc*rl
    return rc*rl/d


def results():
    a,y,v,i,p=resistor_network(2,[(1,0),(2,0),(1,2)],[.001,.002,.003],[.001,0])
    k,rhs,x=mna([[.001]],[0],[[1]],[1])
    vn,tr=diode_newton();vb,half=diode_bisection()
    z,yp,h,T=z_parameters()
    r,c=1000.,1e-6;t,vr=rc_backward(r,c,1,.00025,20)
    return {'units':'SI unless keys state otherwise','incidence':a.tolist(),'Y_S':y.tolist(),'node_V':v.tolist(),'branch_A':i.tolist(),'resistor_W':p,'mna_K':k.tolist(),'mna_x_V_A':x.tolist(),'parallel_5_3_ranks':constraint_ranks(.001,[5,3]),'parallel_5_5_ranks':constraint_ranks(.001,[5,5]),'diode_V':vn,'diode_bisection_V':vb,'bisection_halfwidth_V':half,'diode_trace':tr,'Z_ohm':z.tolist(),'Yport_S':yp.tolist(),'h_mixed_units':h.tolist(),'ABCD_mixed_units':T.tolist(),'loaded_gain':transfer(1000,2000,3000,1000),'gain_Ra_plus1percent':transfer(1010,2000,3000,1000),'rc_time_s':t.tolist(),'rc_backward_V':vr.tolist(),'rc_exact_V':(1-np.exp(-t/(r*c))).tolist(),'rc_noise_rms_V':math.sqrt(1.380649e-23*300/c),'rc_noise_dc_V_per_sqrtHz':math.sqrt(4*1.380649e-23*300*r)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='explicit directory outside main vault')
    args=parser.parse_args()
    out=args.output.resolve()
    vault=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if out==vault or vault in out.parents:parser.error('generated results must remain outside main vault')
    data=results()  # complete calculation before filesystem mutations
    out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(out/'results.json')

if __name__=='__main__':main()
