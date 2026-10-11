"""SI teaching rates and exact finite-base solutions; Python standard library only.
No material fit, DD-Poisson solve, device or optical measurement.
"""
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path

Q=1.602176634e-19
KB=1.380649e-23

@dataclass(frozen=True)
class Rates:
    temp_k: float=300.
    ni_m3: float=1e16
    p0_m3: float=1e22
    nc_m3: float=1e26
    nv_m3: float=1e26
    nt_m3: float=1e19
    tau_n_s: float=1e-6
    tau_p_s: float=2e-6
    trap_offset_ev: float=0.  # Et-Ei; unit degeneracy, MB emission
    b_m3_s: float=1e-16
    cn_m6_s: float=1e-40  # Auger electron-assisted coefficient, not trap capture
    cp_m6_s: float=1e-40

    def validate(self):
        values=asdict(self)
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError('Finite model inputs required')
        if min(self.temp_k,self.ni_m3,self.p0_m3,self.nc_m3,self.nv_m3,self.nt_m3,self.tau_n_s,self.tau_p_s)<=0:
            raise ValueError('Positive temperature, densities and trap times required')
        if min(self.b_m3_s,self.cn_m6_s,self.cp_m6_s)<0:
            raise ValueError('Nonnegative band recombination coefficients required')
        if abs(self.trap_offset_ev/(KB*self.temp_k/Q))>40:
            raise ValueError('Declared trap energy range: abs((Et-Ei)/kT)<=40')

    @property
    def n0_m3(self):return self.ni_m3**2/self.p0_m3

    def aux(self):
        self.validate()
        exponent=self.trap_offset_ev/(KB*self.temp_k/Q)
        return self.ni_m3*math.exp(exponent),self.ni_m3*math.exp(-exponent)

    def linear_tau(self):
        n1,p1=self.aux()
        s=self.n0_m3+self.p0_m3
        inv=s/(self.tau_p_s*(self.n0_m3+n1)+self.tau_n_s*(self.p0_m3+p1))
        inv+=self.b_m3_s*s+(self.cn_m6_s*self.n0_m3+self.cp_m6_s*self.p0_m3)*s
        return 1/inv


def trap_state(n_m3,p_m3,model=Rates()):
    """Stationary one-level trap: independent electron/hole net capture rates.
    Numerical density domain 0<=n,p<=1e25 /m^3; MB detailed-balance emission.
    """
    model.validate()
    if not all(math.isfinite(v) and 0<=v<=1e25 for v in (n_m3,p_m3)):
        raise ValueError('Declared trap density range: 0<=n,p<=1e25 /m^3')
    n1,p1=model.aux()
    cap_n=1/(model.tau_n_s*model.nt_m3);cap_p=1/(model.tau_p_s*model.nt_m3)
    emission_n=cap_n*n1;emission_p=cap_p*p1
    denominator=cap_n*n_m3+emission_n+cap_p*p_m3+emission_p
    f=(cap_n*n_m3+emission_p)/denominator
    un=model.nt_m3*(cap_n*n_m3*(1-f)-emission_n*f)
    up=model.nt_m3*(cap_p*p_m3*f-emission_p*(1-f))
    return {'f':f,'relaxation_s':1/denominator,'U_n_m3_s':un,'U_p_m3_s':up,
            'U_closed_m3_s':(n_m3*p_m3-model.ni_m3**2)/
              (model.tau_p_s*(n_m3+n1)+model.tau_n_s*(p_m3+p1))}


def rate_state(delta_m3,model=Rates()):
    """n=n0+delta, p=p0+delta; paired-injection approximation, delta>=0.
    Finite numerical API: delta<=1e25 /m^3. Material validity is a separate input.
    Uses expanded np-ni^2 to retain tiny-injection precision.
    """
    model.validate()
    if not math.isfinite(delta_m3) or not 0<=delta_m3<=1e25:
        raise ValueError('Declared paired excess range: 0<=delta<=1e25 /m^3')
    d=delta_m3;n=model.n0_m3+d;p=model.p0_m3+d
    n1,p1=model.aux()
    capture_n=1/(model.tau_n_s*model.nt_m3)
    capture_p=1/(model.tau_p_s*model.nt_m3)
    denom=capture_n*(n+n1)+capture_p*(p+p1)
    f=(capture_n*n+capture_p*p1)/denom
    excess=d*(model.n0_m3+model.p0_m3+d)
    srh=excess/(model.tau_p_s*(n+n1)+model.tau_n_s*(p+p1))
    rad=model.b_m3_s*excess
    aug=(model.cn_m6_s*n+model.cp_m6_s*p)*excess
    total=srh+rad+aug
    # Analytic dU/ddelta distinguishes differential and secant lifetimes.
    den=model.tau_p_s*(n+n1)+model.tau_n_s*(p+p1)
    slope_excess=model.n0_m3+model.p0_m3+2*d
    slope_srh=(slope_excess*den-excess*(model.tau_n_s+model.tau_p_s))/den**2
    slope=slope_srh+model.b_m3_s*slope_excess
    slope+=(model.cn_m6_s+model.cp_m6_s)*excess+(model.cn_m6_s*n+model.cp_m6_s*p)*slope_excess
    splitting=(KB*model.temp_k/Q)*math.log1p(excess/(model.ni_m3**2))
    return {'delta_m3':d,'n_m3':n,'p_m3':p,'np_excess_m6':excess,'trap_f':f,
            'trap_relaxation_s':1/denom,'U_srh_m3_s':srh,'U_rad_m3_s':rad,
            'U_auger_m3_s':aug,'U_total_m3_s':total,
            'tau_secant_s':d/total if d else model.linear_tau(),
            'tau_differential_s':1/slope,'quasi_fermi_split_ev':splitting,'eta_n_mb':math.log(n/model.nc_m3),'eta_p_mb':math.log(p/model.nv_m3)}


def uniform_decay(initial_m3,step_s,end_s,model=Rates()):
    """RK4 for ddelta/dt=-U(delta), fixed finite budget, positivity checked.
    Returns all requested samples, not an unbounded interactive simulator.
    """
    rate_state(initial_m3,model)
    if initial_m3<=0 or not all(math.isfinite(v) and v>0 for v in (step_s,end_s)):
        raise ValueError('Positive initial excess, step and end time required')
    count=round(end_s/step_s)
    if not 1<=count<=100000 or abs(count*step_s-end_s)>1e-10*end_s:
        raise ValueError('Integer 1..100000 steps required')
    rows=[];d=initial_m3
    def rhs(x):return -rate_state(x,model)['U_total_m3_s']
    for i in range(count+1):
        state=rate_state(d,model)
        rows.append({'t_s':i*step_s,'delta_m3':d,'tau_secant_s':state['tau_secant_s']})
        if i==count:break
        k1=rhs(d);k2=rhs(d+step_s*k1/2);k3=rhs(d+step_s*k2/2);k4=rhs(d+step_s*k3)
        d+=step_s*(k1+2*k2+2*k3+k4)/6
        if not math.isfinite(d) or d<0:raise RuntimeError('RK4 positivity failure; reduce step')
    return rows


def base_point(x_m,length_m,diff_m2_s,tau_s,edge_m3,beta=None):
    """Exact steady solution with left Dirichlet injection.
    beta=None: right absorbing Dirichlet; beta>=0: Fn(L)=S*u(L), beta=S*Ln/D.
    API: 0<=x<=L incl endpoints, .001<=L/Ln<=20 (finite hyperbolic range).
    """
    vals=(x_m,length_m,diff_m2_s,tau_s,edge_m3)
    if not all(math.isfinite(v) for v in vals) or min(length_m,diff_m2_s,tau_s,edge_m3)<=0:
        raise ValueError('Finite x and positive length/D/tau/edge density required')
    ln=math.sqrt(diff_m2_s*tau_s);ell=length_m/ln;y=(length_m-x_m)/ln
    if not 0<=x_m<=length_m or not .001<=ell<=20:
        raise ValueError('0<=x<=L and .001<=L/Ln<=20 required')
    if beta is not None and (not math.isfinite(beta) or beta<0 or beta>1e8):
        raise ValueError('Finite 0<=beta<=1e8 or None absorbing limit required')
    scale=diff_m2_s*edge_m3/ln
    if beta is None:
        den=math.sinh(ell)
        u=edge_m3*math.sinh(y)/den
        flux=scale*math.cosh(y)/den
        cumulative=scale*(math.cosh(ell)-math.cosh(y))/den
    else:
        den=math.cosh(ell)+beta*math.sinh(ell)
        u=edge_m3*(math.cosh(y)+beta*math.sinh(y))/den
        flux=scale*(math.sinh(y)+beta*math.cosh(y))/den
        cumulative=scale*(math.sinh(ell)-math.sinh(y)+beta*(math.cosh(ell)-math.cosh(y)))/den
    return {'x_m':x_m,'delta_m3':u,'Fn_m2_s':flux,'Jn_A_m2':-Q*flux,
            'cumulative_bulk_m2_s':cumulative,'Ln_m':ln,'flux_scale_m2_s':scale}


def base_summary(length_m,diff_m2_s,tau_s,edge_m3,beta=None):
    left=base_point(0,length_m,diff_m2_s,tau_s,edge_m3,beta)
    right=base_point(length_m,length_m,diff_m2_s,tau_s,edge_m3,beta)
    bulk=right['cumulative_bulk_m2_s']
    return {'L_m':length_m,'D_m2_s':diff_m2_s,'tau_s':tau_s,'edge_m3':edge_m3,
            'beta':beta,'S_m_s':None if beta is None else beta*diff_m2_s/left['Ln_m'],
            'Fn_left_m2_s':left['Fn_m2_s'],'Fn_right_m2_s':right['Fn_m2_s'],
            'bulk_integral_m2_s':bulk,'stored_per_area_m2':tau_s*bulk,
            'tau_storage_s':tau_s*bulk/left['Fn_m2_s'],
            'conservation_relative_error':abs(left['Fn_m2_s']-right['Fn_m2_s']-bulk)/left['Fn_m2_s']}


def mode_point(x_m,t_s,length_m,diff_m2_s,tau_s,amplitude_m3=1e18):
    """Prepared two-sine-mode decay; both boundaries zero after switch-off.
    This exact eigenmode example is not the previous steady profile switched off.
    """
    if not all(math.isfinite(v) for v in (x_m,t_s,length_m,diff_m2_s,tau_s,amplitude_m3)):
        raise ValueError('Finite mode inputs required')
    if min(length_m,diff_m2_s,tau_s,amplitude_m3)<=0 or t_s<0 or not 0<=x_m<=length_m:
        raise ValueError('Positive scales, t>=0 and 0<=x<=L required')
    u=0.;ut=0.;uxx=0.;flux=0.
    for j,weight in ((1,1.),(2,.25)):
        k=j*math.pi/length_m;rate=1/tau_s+diff_m2_s*k*k
        a=amplitude_m3*weight*math.exp(-rate*t_s)
        wave=a*math.sin(k*x_m)
        u+=wave;ut-=rate*wave;uxx-=k*k*wave;flux-=diff_m2_s*a*k*math.cos(k*x_m)
    return {'x_m':x_m,'t_s':t_s,'delta_m3':u,'d_dt_m3_s':ut,'d2_dx2_m5':uxx,'Fn_m2_s':flux}


def run():
    m=Rates();tau=m.linear_tau();diff=.003;ln=math.sqrt(diff*tau)
    states=[rate_state(d,m) for d in (0,1e18,1e20,1e22,1e24)]
    base_cases=[base_summary(ln,diff,tau,1e18,b) for b in (None,0.,1.,10.)]
    profiles={str(b):[base_point(ln*i/100,ln,diff,tau,1e18,b) for i in range(101)] for b in (None,0.,1.,10.)}
    sweep=[rate_state(10**(16+i/10),m) for i in range(91)]
    decay=uniform_decay(1e24,2e-11,2e-8,m)
    decay_half=uniform_decay(1e24,1e-11,2e-8,m)
    refinement=max(abs(a['delta_m3']/b['delta_m3']-1) for a,b in zip(decay,decay_half[::2]))
    modes=[mode_point(ln/4,t*1e-9,ln,diff,tau) for t in range(201)]
    return {'model':asdict(m),'effective_gap_ev':(KB*m.temp_k/Q)*math.log(m.nc_m3*m.nv_m3/m.ni_m3**2),'linear_tau_s':tau,'D_m2_s':diff,'Ln_m':ln,'states':states,
            'rate_sweep':sweep,'base_cases':base_cases,'base_profiles':profiles,
            'decay':decay[::10],'decay_refinement_max_relative':refinement,'two_mode_quarter':modes,
            'fundamental_tau_s':tau/(1+math.pi**2),
            'disclaimer':'Synthetic same-parameter models; no material/measurement/device calibration'}

if __name__=='__main__':
    result=run()
    destination=Path(__file__).parent/'assets/results.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('linear_tau_s','Ln_m','decay_refinement_max_relative','fundamental_tau_s')},indent=2))
