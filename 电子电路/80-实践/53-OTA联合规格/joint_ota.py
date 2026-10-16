"""Ten physical voltage states, the published 11-MOS law, and explicit capacitor incidences.
No import-side execution; no PDK. All quantities SI. Further CLI lives in run_joint.py.
"""
import hashlib,importlib.util,math
from dataclasses import dataclass,asdict,replace
from pathlib import Path
import numpy as np
NAMES=('op','om','s','vb','sense','sc','vm','vc','gp','gm')
KB=1.38064852e-23

@dataclass(frozen=True)
class Design:
    vdd:float=3.3
    vic:float=1.5
    reference:float=1.65
    iref:float=50e-6
    rdet:float=2e6
    rgate:float=20e3
    cgate:float=500e-12
    cout:float=20e-12
    ccontrol:float=10e-9
    cbridge:float=5e-12
    feedback:float=.1
    temperature_K:float=300.15
    kp_scale:float=1.
    threshold_shift:float=0.
    mismatch:float=1.


def load_base(path):
    spec=importlib.util.spec_from_file_location('published_mos_law',path);base=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=base;spec.loader.exec_module(base);return base


def validate(c):
    if type(c) is not Design:raise ValueError('native_design')
    for k,v in asdict(c).items():
        if type(v) not in (int,float) or not math.isfinite(v):raise ValueError('finite_design')
    if not (2.7<=c.vdd<=3.6 and 1<=c.vic<=2.6 and 1.3<=c.reference<=1.8 and 25e-6<=c.iref<=100e-6 and 1e5<=c.rdet<=4e6 and 1e3<=c.rgate<=1e5 and 1e-12<=c.cgate<=1e-9 and 10e-12<=c.cout<=3e-9 and 20e-12<=c.ccontrol<=100e-9 and 0<=c.cbridge<=50e-12 and .05<=c.feedback<=.2 and 250<=c.temperature_K<=400 and .5<=c.kp_scale<=1.5 and -.1<=c.threshold_shift<=.1 and .95<=c.mismatch<=1.05):raise ValueError('finite_design_budget')


def caps(c):
    validate(c);C=np.diag([c.cout,c.cout,5e-12,5e-12,5e-12,5e-12,5e-12,c.ccontrol,c.cgate,c.cgate])
    for i in (0,1):
        b=np.eye(10)[i]-np.eye(10)[7];C+=c.cbridge*np.outer(b,b)
    return C


def circuit(x,c,base,ud=0.,uc=0.,cut=None):
    validate(c);x=np.asarray(x,float)
    if x.shape!=(10,) or not np.isfinite(x).all() or not np.isfinite([ud,uc]).all() or abs(ud)>.5 or abs(uc)>.4:raise ValueError('finite_states_inputs')
    if cut not in (None,'dm','cm'):raise ValueError('cut')
    e=np.eye(10);zero=np.zeros(10)
    def node(n):return (float(x[NAMES.index(n)]),e[NAMES.index(n)]) if isinstance(n,str) else (float(n),zero)
    vg=node('vc')
    if cut=='cm':vg=(vg[0],zero)
    specs=[('M1','op','gp','s',1,400e-6,.6),('M2','om','gm','s',1,400e-6,.6),('M3','op',vg,c.vdd,-1,200e-6*c.mismatch,.7),('M4','om',vg,c.vdd,-1,200e-6,.7),('M5','s','vb',0,1,1000e-6,.6),('M6','vb','vb',0,1,1000e-6,.6),('M7','vm','sense','sc',1,2e-6,.6),('M8','vc',c.reference,'sc',1,2e-6,.6),('M9','sc','vb',0,1,10e-6,.6),('M10','vm','vm',c.vdd,-1,1e-6,.7),('M11','vc','vm',c.vdd,-1,1e-6,.7)]
    F=np.zeros(10);J=np.zeros((10,10));Fu=np.zeros((10,2));devices=[];sources=[]
    for name,d,g,s,pol,beta,vt in specs:
        d=node(d);s=node(s);g=g if isinstance(g,tuple) else node(g);vto=vt+c.threshold_shift
        cur,gd,gm,gs,region,ov,head=base.mos(d[0],g[0],s[0],pol,beta*c.kp_scale,vto)
        b=d[1]-s[1];F+=b*cur;J+=np.outer(b,gd*d[1]+gm*g[1]+gs*s[1]);devices.append(dict(name=name,Id_A=cur,gm_S=gm,gds_S=gd,gm_over_Id_V_inv=abs(gm/cur) if cur else None,region=region,overdrive_V=ov,headroom_V=head,Vd_V=d[0],Vg_V=g[0],Vs_V=s[0]));sources.append(dict(name=name,incidence=b.tolist(),psd_A2_Hz=4*KB*c.temperature_K*(2/3)*abs(gm)))
    for name,i,j,R in [('RDp',0,4,c.rdet),('RDm',1,4,c.rdet)]:
        b=e[i]-e[j];F+=b*(x[i]-x[j])/R;J+=np.outer(b,b)/R;sources.append(dict(name=name,incidence=b.tolist(),psd_A2_Hz=4*KB*c.temperature_K/R))
    for name,i,sign in [('RGp',8,1),('RGm',9,-1)]:
        drive=c.vic+uc+sign*.5*(ud+c.feedback*(x[0]-x[1]));gradient=e[i]-(0 if cut=='dm' else sign*.5*c.feedback)*(e[0]-e[1]);F[i]+=(x[i]-drive)/c.rgate;J[i]+=gradient/c.rgate;Fu[i]=[-sign*.5/c.rgate,-1/c.rgate];sources.append(dict(name=name,incidence=e[i].tolist(),psd_A2_Hz=4*KB*c.temperature_K/c.rgate))
    F[3]-=c.iref
    return F,J,Fu,devices,sources


def dc(c,base,ud=0.,uc=0.,guess=None):
    validate(c);x=np.array([1.65,1.65,.55,.91,1.65,.55,1.9,2.1,1.5,1.5] if guess is None else guess,float)
    for k in range(100):
        f,j,_,dev,_=circuit(x,c,base,ud,uc)
        if max(abs(f))<2e-14:return x,dict(residual_A=float(max(abs(f))),iterations=k,devices=dev)
        dx=np.linalg.solve(j,-f)
        for m in range(35):
            z=x+dx*2**(-m)
            if np.all(z>=0) and np.all(z<=c.vdd) and np.linalg.norm(circuit(z,c,base,ud,uc)[0])<np.linalg.norm(f):x=z;break
        else:break
    raise RuntimeError('dc_failed')


def linear(x,c,base,frequencies=None):
    _,J,Fu,devices,sources=circuit(x,c,base);C=caps(c);A=-np.linalg.solve(C,J);B=-np.linalg.solve(C,Fu);obs=np.zeros((2,10));obs[0,:2]=[1,-1];obs[1,:2]=[.5,.5];T=np.eye(10);T[:2]=obs;T[8,8:]=[1,-1];T[9,8:]=[.5,.5];modal=T@A@np.linalg.inv(T)
    cuts={};omega=np.geomspace(1,1e9,1001)
    for name in ('dm','cm'):
        opened=-np.linalg.solve(C,circuit(x,c,base,cut=name)[1]);delta=A-opened;vals=np.array([-np.trace(np.linalg.solve(1j*w*np.eye(10)-opened,delta)) for w in omega]);phase=np.unwrap(np.angle(vals));mags=abs(vals);cross=[]
        for k in range(len(omega)-1):
            if (mags[k]-1)*(mags[k+1]-1)<0:
                t=-math.log(mags[k])/math.log(mags[k+1]/mags[k]);cross.append(dict(omega_rad_s=float(omega[k]*(omega[k+1]/omega[k])**t),phase_margin_deg=float(180+np.degrees(phase[k]+t*(phase[k+1]-phase[k])))))
        cuts[name]=dict(crossings=cross,open_roots=[[float(z.real),float(z.imag)] for z in np.linalg.eigvals(opened)],rank=int(np.linalg.matrix_rank(delta,tol=1e-5)))
    f=np.geomspace(1,1e5,401) if frequencies is None else np.asarray(frequencies);inc=np.array([s['incidence'] for s in sources]).T;psd=np.array([s['psd_A2_Hz'] for s in sources]);rows=[]
    for hz in f:
        Y=J+2j*np.pi*hz*C;H=-obs@np.linalg.solve(Y,Fu);N=-obs@np.linalg.solve(Y,inc);pieces=abs(N)**2*psd
        rows.append(dict(frequency_Hz=float(hz),signal=[[[float(z.real),float(z.imag)] for z in row] for row in H],dm_source_psd=pieces[0].tolist(),cm_source_psd=pieces[1].tolist(),dm_psd=float(pieces[0].sum()),cm_psd=float(pieces[1].sum()),input_equivalent_psd=float(pieces[0].sum()/abs(H[0,0])**2)))
    signal=-obs@np.linalg.solve(J,Fu);supply=c.iref+sum(abs(d['Id_A']) for d in devices if d['name'] in ('M3','M4','M10','M11'));return dict(J_S=J.tolist(),C_F=C.tolist(),A_s_inv=A.tolist(),B_s_inv=B.tolist(),transform=T.tolist(),modal_A=modal.tolist(),dm_state_indices=[0,8],cm_state_indices=[1,2,3,4,5,6,7,9],modal_cross_max_s_inv=float(max(np.max(abs(modal[np.ix_([0,8],[1,2,3,4,5,6,7,9])])),np.max(abs(modal[np.ix_([1,2,3,4,5,6,7,9],[0,8])])))),roots=[[float(z.real),float(z.imag)] for z in np.linalg.eigvals(A)],H_DC=signal.tolist(),cuts=cuts,sources=sources,spectrum=rows,noise_dm_rms_V=float(np.sqrt(np.trapezoid([r['dm_psd'] for r in rows],f))),noise_cm_rms_V=float(np.sqrt(np.trapezoid([r['cm_psd'] for r in rows],f))),input_equivalent_rms_V=float(np.sqrt(np.trapezoid([r['input_equivalent_psd'] for r in rows],f))),supply_current_A=float(supply),supply_power_W=float(c.vdd*supply))


def step(c,base,ud0,ud1,duration=.002,count=2001):
    from scipy.integrate import solve_ivp
    if type(count)!=int or not 101<=count<=4001 or not math.isfinite(duration) or not .0001<=duration<=.005:raise ValueError('step_work_budget')
    x0,_=dc(c,base,ud=ud0);target,_=dc(c,base,ud=ud1,guess=x0);C=caps(c);Ci=np.linalg.inv(C);times=np.linspace(0,duration,count)
    def rhs(t,y):return -Ci@circuit(y,c,base,ud=ud1)[0]
    def jac(t,y):return -Ci@circuit(y,c,base,ud=ud1)[1]
    r=solve_ivp(rhs,(0,duration),x0,method='Radau',jac=jac,t_eval=times,rtol=2e-8,atol=2e-10)
    if not r.success or len(r.t)!=count:raise RuntimeError('step_failed')
    d=r.y[0]-r.y[1];cm=(r.y[0]+r.y[1])/2;d0=x0[0]-x0[1];d1=target[0]-target[1];delta=d1-d0;fraction=(d-d0)/delta;first=lambda q:next((float(t) for t,v in zip(r.t,fraction) if v>=q),None);a=first(.1);b=first(.9);band=.01*abs(delta);outside=np.flatnonzero(abs(d-d1)>band);settle=None if len(outside) and outside[-1]==len(d)-1 else float(times[outside[-1]+1]) if len(outside) else 0.;derivatives=np.array([rhs(t,y) for t,y in zip(r.t,r.y.T)]);return dict(initial=x0.tolist(),target=target.tolist(),input_step=[ud0,ud1],time_s=r.t.tolist(),states_V=r.y.T.tolist(),differential_V=d.tolist(),common_V=cm.tolist(),differential_derivative_V_s=(derivatives[:,0]-derivatives[:,1]).tolist(),settling_1pct_s=settle,average_10_90_slew_V_s=None if a is None or b is None or b<=a else .8*abs(delta)/(b-a),max_differential_slope_V_s=float(max(abs(derivatives[:,0]-derivatives[:,1]))),peak_cm_error_V=float(max(abs(cm-c.reference))))


def deck(c,commands,*,ud=0.,uc=0.,extra=None,initial=None):
    validate(c);temp=c.temperature_K-273.15
    lines=['11 MOS plus explicit gate RC and bridge capacitors; no PDK','.options reltol=1e-8 abstol=1e-15 vntol=1e-10 gmin=1e-18',f'.temp {temp:.16g}']
    for name,pol,kp,vt in [('NN','NMOS',100e-6,.6),('PP','PMOS',50e-6,.7)]:
        vto=(vt+c.threshold_shift)*(1 if pol=='NMOS' else -1);lines.append(f'.model {name} {pol} LEVEL=1 KP={kp*c.kp_scale:.16g} VTO={vto:.16g} LAMBDA=.04 GAMMA=0 PHI=.6 TNOM={temp:.16g} TOX=1e3 IS=1e-30 CGSO=0 CGDO=0 CGBO=0 CBD=0 CBS=0 NLEV=2 KF=0')
    lines += [f'VDD vdd 0 {c.vdd:.16g}',f'VREF ref 0 {c.reference:.16g}',f'IREF vdd vb {c.iref:.16g}',f'VD ud 0 DC {ud:.16g} AC 1',f'VCIN uc 0 DC {uc:.16g} AC 0',f'BGP dp 0 V={{{c.vic:.16g}+v(uc)+.5*(v(ud)+{c.feedback:.16g}*(v(op)-v(om)))}}',f'BGM dm 0 V={{{c.vic:.16g}+v(uc)-.5*(v(ud)+{c.feedback:.16g}*(v(op)-v(om)))}}',f'RGp gp dp {c.rgate:.16g}',f'RGm gm dm {c.rgate:.16g}','M1 op gp s 0 NN W=4u L=1u','M2 om gm s 0 NN W=4u L=1u',f'M3 op vc vdd vdd PP W={4e-6*c.mismatch:.16g} L=1u','M4 om vc vdd vdd PP W=4u L=1u','M5 s vb 0 0 NN W=10u L=1u','M6 vb vb 0 0 NN W=10u L=1u','M7 vm sense sc 0 NN W=1u L=50u','M8 vc ref sc 0 NN W=1u L=50u','M9 sc vb 0 0 NN W=1u L=10u','M10 vm vm vdd vdd PP W=1u L=50u','M11 vc vm vdd vdd PP W=1u L=50u',f'RDp op sense {c.rdet:.16g}',f'RDm om sense {c.rdet:.16g}']
    capvalues=[c.cout,c.cout,5e-12,5e-12,5e-12,5e-12,5e-12,c.ccontrol,c.cgate,c.cgate]
    for n,val in zip(NAMES,capvalues):lines.append(f'C_{n} {n} 0 {val:.16g}')
    for n in ('op','om'):lines.append(f'CB_{n} {n} vc {c.cbridge:.16g}')
    if extra:lines+=extra
    if initial is not None:lines.append('.ic '+' '.join(f'v({n})={v:.16g}' for n,v in zip(NAMES,initial)))
    lines += ['.control','set noaskquit','set numdgt=15','set wr_vecnames','set wr_singlescale']+commands+['quit','.endc','.end'];return '\n'.join(lines)+'\n'
