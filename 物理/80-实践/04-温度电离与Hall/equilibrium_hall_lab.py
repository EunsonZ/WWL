"""Joint thermal equilibrium and conditional Drude/Hall teaching models.
No fit, material measurement, TCAD or external dependency. SI densities; eV energies.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path

H=6.62607015e-34  # J s, exact
HBAR=H/(2*math.pi)
Q=1.602176634e-19  # C; also J/eV conversion number
KB=1.380649e-23  # J/K, exact
M0=9.1093837139e-31  # kg, CODATA 2022
KB_EV=KB/Q


@dataclass(frozen=True)
class Material:
    eg_ev: float=1.12
    mn_m0: float=.20
    mp_m0: float=.50
    gd_c: int=2  # total spin*valley degeneracy of conduction states
    gd_v: int=2
    nd_m3: float=1e22
    na_m3: float=2e21
    donor_binding_ev: float=.045
    acceptor_binding_ev: float=.055
    donor_weight_ratio: float=2  # neutral/ionized microstate weights
    acceptor_weight_ratio: float=4  # neutral/ionized microstate weights

    def validate(self):
        vals=asdict(self)
        if not all(math.isfinite(x) for x in vals.values()):
            raise ValueError('Finite model parameters required')
        if self.eg_ev<=0 or self.mn_m0<=0 or self.mp_m0<=0:
            raise ValueError('Positive band gap and DOS masses required')
        if not (0<self.donor_binding_ev<self.eg_ev and 0<self.acceptor_binding_ev<self.eg_ev):
            raise ValueError('Impurity energies must lie strictly in the gap')
        if self.nd_m3<0 or self.na_m3<0:
            raise ValueError('Dopant concentrations must be nonnegative')
        if min(self.donor_weight_ratio,self.acceptor_weight_ratio)<=0:
            raise ValueError('Positive impurity degeneracy ratios required')
        if any(not isinstance(g,int) or isinstance(g,bool) or g<=0 for g in (self.gd_c,self.gd_v)):
            raise ValueError('Positive integer band degeneracies required')


def reciprocal_logistic(x):
    """1/(1+exp(x)); stable for finite large positive/negative x."""
    if x>=0:
        z=math.exp(-x)
        return z/(1+z)
    return 1/(1+math.exp(x))


def adaptive_simpson(func, lo, hi, tolerance=1e-9, max_depth=22):
    """Finite-budget adaptive integration, raises instead of silently accepting failure."""
    if (not math.isfinite(tolerance) or tolerance<=0
            or not isinstance(max_depth,int) or not 0<=max_depth<=30):
        raise ValueError('Finite positive tolerance and integer depth 0..30 required')
    calls=0
    def value(x):
        nonlocal calls
        calls+=1
        if calls>10000:raise RuntimeError('Quadrature evaluation budget exhausted')
        return func(x)
    a,b=value(lo),value(hi)
    mid=(lo+hi)/2
    m=value(mid)
    whole=(hi-lo)*(a+4*m+b)/6
    def split(l,r,fl,fm,fr,previous,eps,depth):
        center=(l+r)/2
        lm=value((l+center)/2); rm=value((center+r)/2)
        left=(center-l)*(fl+4*lm+fm)/6
        right=(r-center)*(fm+4*rm+fr)/6
        delta=left+right-previous
        if abs(delta)<=15*eps:return left+right+delta/15
        if depth==0:raise RuntimeError('Quadrature recursion budget exhausted')
        return (split(l,center,fl,lm,fm,left,eps/2,depth-1)+
                split(center,r,fm,rm,fr,right,eps/2,depth-1))
    return split(lo,hi,a,m,b,whole,tolerance,max_depth)


def fhalf(eta, tolerance=1e-9, tail_margin=40):
    """Normalized F_1/2=2/sqrt(pi) int sqrt(u)/(1+exp(u-eta)) du.
    Uses u=t^2 and scales out exp(eta) for eta<0. Finite upper cutoff.
    The public numerical domain is -700 <= eta <= 40.
    """
    if not math.isfinite(eta) or not -700<=eta<=40:
        raise ValueError('Fermi-integral numerical domain: -700 <= eta <= 40')
    if (not math.isfinite(tolerance) or tolerance<=0
            or not math.isfinite(tail_margin) or not 20<=tail_margin<=200):
        raise ValueError('Positive finite tolerance and finite tail margin 20..200 required')
    upper=math.sqrt(max(tail_margin,eta+tail_margin))
    factor=4/math.sqrt(math.pi)
    if eta<=0:
        z=math.exp(eta)
        integral=adaptive_simpson(lambda t:factor*t*t*math.exp(-t*t)/(1+z*math.exp(-t*t)),
                                  0,upper,tolerance)
        return z*integral
    return adaptive_simpson(lambda t:factor*t*t*reciprocal_logistic(t*t-eta),0,upper,tolerance)


def effective_density(mass_m0, degeneracy, temp_k):
    return degeneracy*(mass_m0*M0*KB*temp_k/(2*math.pi*HBAR**2))**1.5


def population(ef_ev,temp_k,mat: Material,mode='fd',tol=1e-9):
    """Ec=0, Ev=-Eg. Return n,p,ionized impurities per m^3."""
    if not math.isfinite(temp_k) or not 40<=temp_k<=1200:
        raise ValueError('Teaching sweep domain: 40 <= T <=1200 K')
    if not math.isfinite(ef_ev) or mode not in ('fd','mb'):
        raise ValueError('Finite EF and fd/mb occupation required')
    mat.validate()
    kt=KB_EV*temp_k
    nc=effective_density(mat.mn_m0,mat.gd_c,temp_k)
    nv=effective_density(mat.mp_m0,mat.gd_v,temp_k)
    eta_n=ef_ev/kt; eta_p=(-mat.eg_ev-ef_ev)/kt
    if not (-700<=eta_n<=40 and -700<=eta_p<=40):
        raise ValueError('Carrier reduced chemical potentials outside numerical domain')
    if mode=='fd':
        n=nc*fhalf(eta_n,tol); p=nv*fhalf(eta_p,tol)
    else:
        n=nc*math.exp(eta_n); p=nv*math.exp(eta_p)
    ed=-mat.donor_binding_ev
    ea=-mat.eg_ev+mat.acceptor_binding_ev
    ndp=mat.nd_m3*reciprocal_logistic(math.log(mat.donor_weight_ratio)+(ef_ev-ed)/kt)
    nam=mat.na_m3*reciprocal_logistic(math.log(mat.acceptor_weight_ratio)+(ea-ef_ev)/kt)
    return {'n_m3':n,'p_m3':p,'NDplus_m3':ndp,'NAminus_m3':nam,'Nc_m3':nc,'Nv_m3':nv,
            'eta_n':eta_n,'eta_p':eta_p,'balance_m3':p+ndp-n-nam}


def solve_neutral(temp_k,mat=Material(),mode='fd',tol=1e-9):
    """Bracket monotone neutrality root; width <=1e-10 eV plus scaled charge residual.
    Restricted bracket [Ev-0.05, Ec+0.05] eV; out-of-bracket model requests fail.
    """
    mat.validate()
    lo=-mat.eg_ev-.05; hi=.05
    initial=(lo,hi)
    fl=population(lo,temp_k,mat,mode,tol)['balance_m3']
    fh=population(hi,temp_k,mat,mode,tol)['balance_m3']
    if not fl>0>fh:raise ValueError('Neutrality root not bracketed in declared teaching EF interval')
    for step in range(80):
        mid=(lo+hi)/2
        state=population(mid,temp_k,mat,mode,tol)
        if state['balance_m3']>0:lo=mid
        else:hi=mid
        if hi-lo<=1e-10:
            scale=max(state['NDplus_m3'],state['NAminus_m3'],state['n_m3'],state['p_m3'],1)
            if abs(state['balance_m3'])/scale>1e-7:
                raise RuntimeError('Charge residual exceeds tolerance after energy convergence')
            return {'T_K':temp_k,'EF_eV':mid,**state,'scaled_charge_residual':abs(state['balance_m3'])/scale,
                    'final_bracket_width_eV':hi-lo,'iterations':step+1,'initial_bracket_eV':initial}
    raise RuntimeError('Neutrality bisection iteration budget exhausted')


def freeze_mb_density(temp_k,mat):
    """Independent closed form: negligible holes, fully ionized acceptors, MB electrons."""
    mat.validate()
    if not math.isfinite(temp_k) or not 40<=temp_k<=1200:
        raise ValueError('Teaching sweep domain: 40 <= T <=1200 K')
    kt=KB_EV*temp_k
    nc=effective_density(mat.mn_m0,mat.gd_c,temp_k)
    aa=mat.donor_weight_ratio*math.exp(mat.donor_binding_ev/kt)/nc
    bb=1+aa*mat.na_m3
    net=mat.nd_m3-mat.na_m3
    if net<=0:raise ValueError('This n-type closed form requires ND>NA')
    return 2*net/(bb+math.sqrt(bb*bb+4*aa*net))


def prescribed_mobility(temp_k):
    """Illustration only: a phonon-shaped T^-3/2 law, not a microscopic model."""
    return .135*(300/temp_k)**1.5,.045*(300/temp_k)**1.5


def hall_observables(n_m3,mu_n,p_m3=0,mu_p=0):
    """Weak-field isotropic two-carrier Drude model with Hall factors equal to one."""
    if not all(math.isfinite(x) for x in (n_m3,mu_n,p_m3,mu_p)):
        raise ValueError('Finite transport inputs required')
    if min(n_m3,mu_n,p_m3,mu_p)<0 or n_m3*mu_n+p_m3*mu_p<=0:
        raise ValueError('Nonnegative inputs and positive conductivity required')
    sigma=Q*(n_m3*mu_n+p_m3*mu_p)
    rh=(p_m3*mu_p**2-n_m3*mu_n**2)/(Q*(n_m3*mu_n+p_m3*mu_p)**2)
    return {'sigma_S_m':sigma,'RH_m3_C':rh}


def run(output_dir: Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    mat=Material()
    temperatures=[40+5*i for i in range(33)]+[220+20*i for i in range(50)]
    states=[]
    for t in temperatures:
        row=solve_neutral(t,mat)
        mun,mup=prescribed_mobility(t)
        ni=math.sqrt(row['Nc_m3']*row['Nv_m3'])*math.exp(-mat.eg_ev/(2*KB_EV*t))
        row.update(hall_observables(row['n_m3'],mun,row['p_m3'],mup))
        row.update({'mu_n_m2_Vs':mun,'mu_p_m2_Vs':mup,'ni_MB_reference_m3':ni})
        states.append(row)
    table=[solve_neutral(t,mat) for t in (40,50,100,300,600,1000,1200)]
    uncompensated=[solve_neutral(t,replace(mat,na_m3=0)) for t in (40,50,100,300)]
    # High-density stress case remains an isolated-impurity mathematical model only.
    degenerate=replace(mat,nd_m3=1e26,na_m3=0)
    deg_fd=solve_neutral(300,degenerate)
    deg_mb=solve_neutral(300,degenerate,mode='mb')
    pairs=[]
    for n,mu in ((1e21,.135),(2e21,.0675)):
        obs=hall_observables(n,mu)
        obs.update({'n_m3':n,'mu_m2_Vs':mu,'G_S':obs['sigma_S_m']*1e-12/1e-6,
                    'Ey_V_m_at_Jx100_Bz0p1':obs['RH_m3_C']*100*.1})
        pairs.append(obs)
    cancellation=hall_observables(1e21,.1,1e21,.1)
    result={'model':asdict(mat),'energy_reference':'Ec=0 eV; Ev=-Eg; EF is electron chemical potential',
            'statistics':'3D parabolic FD with isolated impurity charge-state weights',
            'temperature_model':'constant gap, DOS masses and binding energies; Nc,Nv proportional to T^1.5',
            'mobility_model':'prescribed mu_n=.135*(300/T)^1.5; mu_p=.045*(300/T)^1.5 m^2/(V s), illustrative',
            'Hall_sweep_model':'RH is the B->0 coefficient at each T; no common finite B asserted over the sweep',
            'solver':{'T_domain_K':[40,1200],'EF_bracket_eV':[-mat.eg_ev-.05,.05],
                      'fhalf_eta_domain':[-700,40],'quadrature_tolerance':1e-9,'tail_margin':40,
                      'root_width_eV':1e-10,'scaled_charge_tolerance':1e-7,'bisection_budget':80},
            'representative_states':table,'uncompensated_states':uncompensated,
            'degenerate_stress':{'ND_m3':degenerate.nd_m3,'fd':deg_fd,'mb':deg_mb,'material_validity':'not established'},
            'same_G_Hall_pairs':pairs,'two_carrier_zero_Hall_counterexample':cancellation,'sweep':states}
    checks=[]
    for row in (table[0],table[3],table[-1]):
        fine=solve_neutral(row['T_K'],mat,tol=1e-11)
        eta=row['eta_n']
        checks.append({'T_K':row['T_K'],'EF_refinement_change_eV':abs(fine['EF_eV']-row['EF_eV']),
                       'n_refinement_relative_change':abs(fine['n_m3']/row['n_m3']-1),
                       'Fhalf_tail40_to60_relative_change':abs(fhalf(eta,tail_margin=60)/fhalf(eta)-1)})
    result['numerical_refinement_checks']=checks
    (output_dir/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    result=run(Path(__file__).resolve().parent/'assets')
    print(json.dumps({k:v for k,v in result.items() if k!='sweep'},ensure_ascii=False,indent=2))
