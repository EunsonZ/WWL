"""One 11-MOS OTA/CMFB circuit. SI throughout; no PDK or intrinsic-capacitance claim.
Imports do no I/O. Run writes only a fresh directory outside the source directory.
"""
import argparse, csv, json, math, numbers
from dataclasses import dataclass, replace
from pathlib import Path

NAMES=('op','om','s','vb','sense','sc','vm','vc')

@dataclass(frozen=True)
class Config:
    vdd:float=3.3
    vic:float=1.5
    reference:float=1.65
    iref:float=50e-6
    detector_r:float=200e3
    beta_feedback:float=.1
    control_c:float=10e-9
    load_scale:float=1.
    plus_mismatch:float=1.
    plus_cap_scale:float=1.
    cmfb:bool=True
    fixed_gate:float=2.1


def validate(c):
    if type(c) is not Config or type(c.cmfb) is not bool:raise ValueError('native Config and bool switch required')
    for key,value in vars(c).items():
        if key=='cmfb':continue
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('finite real configuration required')
    if not (2<=c.vdd<=5 and 1<=c.vic<=2 and 1<=c.reference<=2 and 1e-6<=c.iref<=100e-6 and 1e3<=c.detector_r<=1e7 and 0<=c.beta_feedback<=.2 and 1e-12<=c.control_c<=1e-7 and .5<=c.load_scale<=1.5 and .8<=c.plus_mismatch<=1.2 and .1<=c.plus_cap_scale<=10 and 1<=c.fixed_gate<=3):raise ValueError('outside bounded OTA teaching domain')


def mos(vd,vg,vs,polarity,beta,vt,lam=.04):
    """Signed drain-to-source I plus exact terminal derivatives; gamma=0.
    Saturation and triode both use the explicit (1+lambda*|Vds|) factor.
    Reverse operation swaps d/s (allowed only because body effect is disabled).
    """
    if polarity*(vd-vs)<0:
        i,dd,dg,ds,region,ov,head=mos(vs,vg,vd,polarity,beta,vt,lam)
        return -i,-ds,-dg,-dd,'reverse_'+region,ov,head
    ov=polarity*(vg-vs)-vt;d=polarity*(vd-vs)
    if ov<=0:return 0.,0.,0.,0.,'cutoff',ov,d-ov
    if d>=ov:
        raw=.5*beta*ov*ov;gm=beta*ov*(1+lam*d);gd=raw*lam;region='saturation'
    else:
        raw=beta*(ov*d-.5*d*d);gm=beta*d*(1+lam*d)
        gd=beta*(ov-d)*(1+lam*d)+raw*lam;region='triode'
    i=polarity*raw*(1+lam*d)
    return i,gd,gm,-gm-gd,region,ov,d-ov


def finite_voltage(value,name):
    if isinstance(value,bool) or not isinstance(value,numbers.Real):raise ValueError(name+': finite real voltage required')
    try:value=float(value)
    except (OverflowError,ValueError):raise ValueError(name+': finite real voltage required') from None
    if not math.isfinite(value):raise ValueError(name+': finite real voltage required')
    return value


def circuit(x,c=Config(),*,ud=0.,uc=0.,cut_dm=False,cut_cm=False):
    """F=outgoing KCL currents [A], J=dF/dx [S], Fu=dF/d(ud,uc) [S].
    Cut flags hold the branch gate at its CURRENT value while removing its
    small-signal feedback derivative; the DC circuit/value is unchanged.
    """
    import numpy as np
    validate(c);ud=finite_voltage(ud,'ud');uc=finite_voltage(uc,'uc');x=np.asarray(x,dtype=float)
    if x.shape!=(8,) or not np.isfinite(x).all():raise ValueError('eight finite node voltages required')
    eye=np.eye(8);zero=np.zeros(8)
    def node(n):return (x[NAMES.index(n)],eye[NAMES.index(n)],np.zeros(2)) if n in NAMES else (float(n),zero,np.zeros(2))
    def gate(sign):
        value=c.vic+uc+sign*.5*(ud+c.beta_feedback*(x[0]-x[1]))
        gradient=zero if cut_dm else sign*.5*c.beta_feedback*(eye[0]-eye[1])
        return value,gradient,np.array([sign*.5,1.])
    loadgate=node('vc') if c.cmfb else node(c.fixed_gate)
    if cut_cm:loadgate=(loadgate[0],zero,np.zeros(2))
    # name, drain, gate, source, polarity, KP*W/L, |VTO|; all L/W in netlist.
    devices=[('M1',node('op'),gate(1),node('s'),1,400e-6,.6),
             ('M2',node('om'),gate(-1),node('s'),1,400e-6,.6),
             ('M3',node('op'),loadgate,node(c.vdd),-1,200e-6*c.load_scale*c.plus_mismatch,.7),
             ('M4',node('om'),loadgate,node(c.vdd),-1,200e-6*c.load_scale,.7),
             ('M5',node('s'),node('vb'),node(0),1,1000e-6,.6),
             ('M6',node('vb'),node('vb'),node(0),1,1000e-6,.6),
             ('M7',node('vm'),node('sense'),node('sc'),1,2e-6,.6),
             ('M8',node('vc'),node(c.reference),node('sc'),1,2e-6,.6),
             ('M9',node('sc'),node('vb'),node(0),1,10e-6,.6),
             ('M10',node('vm'),node('vm'),node(c.vdd),-1,1e-6,.7),
             ('M11',node('vc'),node('vm'),node(c.vdd),-1,1e-6,.7)]
    F=np.zeros(8);J=np.zeros((8,8));Fu=np.zeros((8,2));diag=[]
    for name,d,g,s,pol,beta,vt in devices:
        i,dd,dg,ds,region,ov,head=mos(d[0],g[0],s[0],pol,beta,vt)
        incidence=d[1]-s[1];gradient=dd*d[1]+dg*g[1]+ds*s[1]
        F+=incidence*i;J+=np.outer(incidence,gradient)
        Fu+=np.outer(incidence,dd*d[2]+dg*g[2]+ds*s[2])
        diag.append(dict(name=name,Id_A=i,gm_S=dg,gds_S=dd,ro_ohm=None if dd==0 else 1/dd,
                         Vd_V=d[0],Vg_V=g[0],Vs_V=s[0],overdrive_V=ov,saturation_headroom_V=head,region=region))
    for a,b in ((0,4),(1,4)):
        delta=eye[a]-eye[b];F+=delta*(x[a]-x[b])/c.detector_r;J+=np.outer(delta,delta)/c.detector_r
    F[3]-=c.iref
    return F,J,Fu,diag


def capacitances(c):
    import numpy as np
    return np.array([20e-12*c.plus_cap_scale,20e-12,5e-12,5e-12,5e-12,5e-12,5e-12,c.control_c])


def operating_point(c=Config(),guess=None):
    import numpy as np
    validate(c);x=np.array([1.65,1.65,.55,.91,1.65,.55,1.9,2.1] if guess is None else guess,dtype=float)
    for iteration in range(80):
        f,j,_,diag=circuit(x,c)
        if np.max(abs(f))<2e-14:return x,dict(iterations=iteration,residual_A=float(np.max(abs(f))),devices=diag)
        step=np.linalg.solve(j,-f)
        for shrink in range(32):
            candidate=x+step*2**(-shrink)
            if np.all(candidate>=-1e-12) and np.all(candidate<=c.vdd+1e-12):
                candidate=np.clip(candidate,0,c.vdd)
                if np.linalg.norm(circuit(candidate,c)[0])<np.linalg.norm(f):
                    x=candidate;break
        else:break
    # A disconnected controller may settle at a rail; a bounded trust-region
    # solve handles that boundary without inventing a saturated small-signal Q.
    from scipy.optimize import least_squares
    solved=least_squares(lambda y:circuit(y,c)[0]/1e-6,x,jac=lambda y:circuit(y,c)[1]/1e-6,
        bounds=(np.zeros(8),np.full(8,c.vdd)),xtol=1e-14,ftol=1e-14,gtol=1e-14,max_nfev=2000,x_scale='jac')
    f,_,_,diag=circuit(solved.x,c)
    if np.max(abs(f))>2e-14:raise RuntimeError('DC residual failed after bounded solve')
    return solved.x,dict(iterations=80+solved.nfev,residual_A=float(np.max(abs(f))),devices=diag)


def linearization(x,c=Config()):
    import numpy as np
    _,j,fu,_=circuit(x,c);cap=capacitances(c);A=-j/cap[:,None];B=-fu/cap[:,None]
    T=np.eye(8);T[0,:2]=[1,-1];T[1,:2]=[.5,.5];Ti=np.linalg.inv(T)
    Am=T@A@Ti;H=-T[:2]@np.linalg.solve(j,fu)
    # Actual two cuts: input differential feedback and load-gate CMFB actuation.
    _,jdm,_,_=circuit(x,c,cut_dm=True);_,jcm,_,_=circuit(x,c,cut_cm=True)
    cuts={'DM_other_CMFB_closed':-jdm/cap[:,None],'CMFB_other_DM_closed':-jcm/cap[:,None]}
    returns={}
    for name,opened in cuts.items():
        delta=A-opened
        # Rank-one branch closure; trace resolvent gives its single scalar return.
        frequencies=np.geomspace(1.,1e10,1001);L=[]
        for w in frequencies:L.append(-np.trace(np.linalg.solve(1j*w*np.eye(8)-opened,delta)))
        mag=np.abs(L);phase=np.unwrap(np.angle(L));cross=[]
        for k in range(len(frequencies)-1):
            if (mag[k]-1)*(mag[k+1]-1)<=0:
                weight=-math.log(mag[k])/math.log(mag[k+1]/mag[k])
                w=math.exp(math.log(frequencies[k])+weight*math.log(frequencies[k+1]/frequencies[k]))
                ph=phase[k]+weight*(phase[k+1]-phase[k]);cross.append(dict(omega_rad_s=w,phase_margin_deg=180+math.degrees(ph)))
        returns[name]=dict(crossings=cross,open_roots_s_inv=[[float(z.real),float(z.imag)] for z in np.linalg.eigvals(opened)],
                           cut_closure_rank=int(np.linalg.matrix_rank(delta,tol=1e-6)))
    return dict(J_S=j.tolist(),A_s_inv=A.tolist(),B_s_inv=B.tolist(),capacitances_F=cap.tolist(),
                transform_new_from_node=T.tolist(),A_modal_s_inv=Am.tolist(),H_DC_output_d_c_from_input_d_c=H.tolist(),
                roots_s_inv=[[float(z.real),float(z.imag)] for z in np.linalg.eigvals(A)],returns=returns,
                modal_cross_max_s_inv=float(max(np.max(abs(Am[0,1:])),np.max(abs(Am[1:,0])))))


def transient(c,x,perturbation,*,duration=.002,count=401):
    import numpy as np
    from scipy.integrate import solve_ivp
    cap=capacitances(c);start=np.asarray(x)+np.asarray(perturbation);times=np.linspace(0,duration,count)
    def fun(t,y):return -circuit(y,c)[0]/cap
    def jac(t,y):return -circuit(y,c)[1]/cap[:,None]
    result=solve_ivp(fun,(0,duration),start,method='Radau',jac=jac,t_eval=times,rtol=2e-9,atol=2e-11)
    if not result.success or len(result.t)!=count:raise RuntimeError('finite transient did not finish')
    if not np.isfinite(result.y).all():raise RuntimeError('nonfinite transient')
    return [dict(time_s=float(t),**{n:float(v) for n,v in zip(NAMES,y)}) for t,y in zip(result.t,result.y.T)]


def netlist(c=Config(),*,analysis='op',initial=None,title='11 MOS OTA and resistor-sensed CMFB'):
    import numpy as np
    validate(c)
    if initial is not None:
        if not isinstance(initial,(list,tuple,np.ndarray)) or np.asarray(initial,dtype=object).shape!=(8,):
            raise ValueError('eight finite initial capacitor voltages in [0,VDD] required')
        initial=[finite_voltage(v,'initial') for v in initial]
        if any(v<0 or v>c.vdd for v in initial):raise ValueError('eight finite initial capacitor voltages in [0,VDD] required')
    elif analysis=='tran':raise ValueError('eight finite initial capacitor voltages in [0,VDD] required')
    lines=[title,'.options reltol=1e-8 abstol=1e-15 vntol=1e-10 gmin=1e-18', '.temp 27',
           '.model NN NMOS LEVEL=1 KP=100u VTO=.6 LAMBDA=.04 GAMMA=0 PHI=.6 TNOM=27 TOX=1e3 IS=1e-30 CGSO=0 CGDO=0 CGBO=0 CBD=0 CBS=0',
           '.model PP PMOS LEVEL=1 KP=50u VTO=-.7 LAMBDA=.04 GAMMA=0 PHI=.6 TNOM=27 TOX=1e3 IS=1e-30 CGSO=0 CGDO=0 CGBO=0 CBD=0 CBS=0',
           f'VDD vdd 0 {c.vdd:.16g}',f'VREF ref 0 {c.reference:.16g}',f'IREF vdd vb {c.iref:.16g}',
           f'VD ud 0 DC 0 AC 1', 'VCIN uc 0 DC 0 AC 0',
           f'BGP gp 0 V={{{c.vic:.16g}+v(uc)+.5*(v(ud)+{c.beta_feedback:.16g}*(v(op)-v(om)))}}',
           f'BGM gm 0 V={{{c.vic:.16g}+v(uc)-.5*(v(ud)+{c.beta_feedback:.16g}*(v(op)-v(om)))}}']
    gate='vc' if c.cmfb else 'hold'
    if not c.cmfb:lines.append(f'VHOLD hold 0 {c.fixed_gate:.16g}')
    lines += ['M1 op gp s 0 NN W=4u L=1u','M2 om gm s 0 NN W=4u L=1u',
              f'M3 op {gate} vdd vdd PP W={4e-6*c.load_scale*c.plus_mismatch:.16g} L=1u',
              f'M4 om {gate} vdd vdd PP W={4e-6*c.load_scale:.16g} L=1u',
              'M5 s vb 0 0 NN W=10u L=1u','M6 vb vb 0 0 NN W=10u L=1u',
              'M7 vm sense sc 0 NN W=1u L=50u','M8 vc ref sc 0 NN W=1u L=50u',
              'M9 sc vb 0 0 NN W=1u L=10u','M10 vm vm vdd vdd PP W=1u L=50u','M11 vc vm vdd vdd PP W=1u L=50u',
              f'R1 op sense {c.detector_r:.16g}',f'R2 om sense {c.detector_r:.16g}']
    for n,cap in zip(NAMES,capacitances(c)):lines.append(f'C_{n} {n} 0 {cap:.16g}')
    lines += ['.control','set noaskquit','set numdgt=15']
    if analysis=='op':
        lines += ['op','print v(op) v(om) v(s) v(vb) v(sense) v(sc) v(vm) v(vc)',
                  'print @m1[id] @m2[id] @m3[id] @m4[id] @m5[id] @m6[id] @m7[id] @m8[id] @m9[id] @m10[id] @m11[id]',
                  'print @m1[gm] @m1[gds] @m3[gm] @m3[gds]']
    elif analysis=='ac':
        lines += ['ac dec 60 1 100Meg','set wr_vecnames','set wr_singlescale','wrdata ac-dm.txt v(op) v(om) v(sense) v(vc)',
                  'alter VD AC=0','alter VCIN AC=1','ac dec 60 1 100Meg','wrdata ac-cm.txt v(op) v(om) v(sense) v(vc)']
    elif analysis=='tran':
        lines += ['tran .2u 2m uic','set wr_vecnames','set wr_singlescale','wrdata transient.txt v(op) v(om) v(s) v(vb) v(sense) v(sc) v(vm) v(vc)']
    else:raise ValueError('known analysis required')
    lines += ['quit','.endc']
    if initial is not None:lines.append('.ic '+' '.join(f'v({n})={v:.16g}' for n,v in zip(NAMES,initial)))
    lines.append('.end');return '\n'.join(lines)+'\n'


def generate(output):
    import numpy as np
    out=Path(output).resolve();here=Path(__file__).resolve().parent
    if out.exists():raise FileExistsError('fresh results directory required')
    if out==here or here in out.parents:raise ValueError('results outside source directory required')
    base=Config();q,dc=operating_point(base);hold=float(q[7])
    cases={'nominal':base,'no_CMFB_nominal':replace(base,cmfb=False,fixed_gate=hold),
           'no_CMFB_load10pct':replace(base,cmfb=False,fixed_gate=hold,load_scale=1.1),
           'CMFB_load10pct':replace(base,load_scale=1.1),
           'single_load_2pct':replace(base,plus_mismatch=1.02),
           'small_control_cap':replace(base,control_c=20e-12)}
    result={'kind':'MOS_LEVEL1_teaching_OTA_bias_CMFB','temperature_C':27,'state_order':NAMES,'cases':{}}
    decks={}
    for name,cfg in cases.items():
        x,d=operating_point(cfg,guess=q);lin=linearization(x,cfg)
        result['cases'][name]={'configuration':vars(cfg),'Q_V':x.tolist(),'DC':d,'linear':lin}
        decks[name+'-op.cir']=netlist(cfg)
    delta=np.array([.0105,.0095,0,0,0,0,0,0]);trace=transient(base,q,delta)
    result['transient_initial_perturbation_V']=delta.tolist()
    result['nominal_finite_perturbation']=trace
    decks['nominal-ac.cir']=netlist(base,analysis='ac')
    decks['nominal-tran.cir']=netlist(base,analysis='tran',initial=q+delta)
    encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    out.mkdir(parents=True);(out/'results.json').write_text(encoded)
    for name,body in decks.items():(out/name).write_text(body)
    with (out/'nominal-transient.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
    return result


def main():
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args();generate(args.output)
if __name__=='__main__':main()
