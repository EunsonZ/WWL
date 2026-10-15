"""SI teaching models: isotropic MB thermionic contact and uniform bar ports.
No material/process certification. Depletion B must be positive;
linear contact cards and barrier-width diagnostics are separate models.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import math
Q = 1.602176634e-19
KB = 1.380649e-23
H = 6.62607015e-34
HBAR = H / (2 * math.pi)
M0 = 9.1093837139e-31
EPS0 = 8.8541878128e-12

def positive(**values):
    for name, value in values.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be finite and positive')

@dataclass(frozen=True)
class Contact:
    temperature_K: float = 300.0
    donor_m3: float = 1e22
    electron_mass_m0: float = 0.26
    hole_mass_m0: float = 0.5
    epsilon_r: float = 11.7
    affinity_eV: float = 4.05
    metal_work_eV: float = 4.65
    gap_eV: float = 1.12
    def __post_init__(self):
        positive(**asdict(self))
        if self.barrier_V <= 0:
            raise ValueError('positive electron barrier required for this card')
    @property
    def vt(self): return KB * self.temperature_K / Q
    @property
    def mass(self): return self.electron_mass_m0 * M0
    @property
    def eps(self): return self.epsilon_r * EPS0
    def dos_density(self, mass_m0):
        positive(mass_m0=mass_m0)
        return 2 * (2 * math.pi * mass_m0 * M0 * KB * self.temperature_K / H**2)**1.5
    @property
    def nc(self): return self.dos_density(self.electron_mass_m0)
    @property
    def nv(self): return self.dos_density(self.hole_mass_m0)
    @property
    def xi_eV(self):
        # Full ionization, uncompensated doping and negligible holes: n ~ ND.
        return self.vt * math.log(self.nc / self.donor_m3)
    @property
    def barrier_V(self): return self.metal_work_eV - self.affinity_eV
    @property
    def vbi(self): return self.barrier_V - self.xi_eV
    @property
    def astar(self): return 4 * math.pi * Q * self.mass * KB**2 / H**3
    @property
    def js(self): return self.astar * self.temperature_K**2 * math.exp(-self.barrier_V / self.vt)
    def depletion(self, voltage_V):
        if not math.isfinite(voltage_V): raise ValueError('voltage_V must be finite')
        b = self.vbi - voltage_V
        positive(band_bending_V=b)
        w = math.sqrt(2 * self.eps * b / (Q * self.donor_m3))
        return {'B_V': b, 'W_m': w, 'E0_V_m': -Q * self.donor_m3 * w / self.eps,
                'Qsemi_C_m2': Q * self.donor_m3 * w, 'C_F_m2': self.eps / w}
    def spatial(self, x_m, voltage_V):
        if not math.isfinite(x_m) or x_m < 0: raise ValueError('x_m must be finite and nonnegative')
        d = self.depletion(voltage_V); z = max(d['W_m'] - x_m, 0.0)
        phi = -Q * self.donor_m3 * z*z / (2 * self.eps)
        return {'phi_V': phi, 'E_V_m': -Q * self.donor_m3 * z / self.eps,
                'Ec_eV': -phi, 'Ev_eV': -phi - self.gap_eV,
                'rho_C_m3': Q * self.donor_m3 if x_m < d['W_m'] else 0.0}
    def current(self, voltage_V):
        if not math.isfinite(voltage_V) or abs(voltage_V / self.vt) > 500:
            raise ValueError('finite voltage with abs(V/VT)<=500 required')
        return self.js * math.expm1(voltage_V / self.vt)
    def summary(self):
        ni = math.sqrt(self.nc*self.nv) * math.exp(-self.gap_eV/(2*self.vt))
        return {'VT_V': self.vt, 'Nc_m3': self.nc, 'Nv_m3': self.nv, 'ni_m3': ni,
                'eta_bulk': -self.xi_eV/self.vt, 'xi_eV': self.xi_eV,
                'work_semiconductor_eV': self.affinity_eV+self.xi_eV,
                'barrier_V': self.barrier_V, 'Vbi_V': self.vbi,
                'Astar_A_m2_K2': self.astar, 'Js_A_m2': self.js,
                'rho_c0_ohm_m2': self.vt/self.js}

def linear_error(voltage_V, vt):
    """Exact TE J / tangent J minus 1; continuous at zero."""
    positive(VT=vt)
    if not math.isfinite(voltage_V) or abs(voltage_V/vt) > 500:
        raise ValueError('finite voltage with abs(V/VT)<=500 required')
    z = voltage_V / vt
    return math.expm1(z)/z-1 if z else 0.0

def barrier_diagnostic(donor_m3, bending_V, mass_kg, epsilon_F_m, temperature_K):
    """Fixed-bending parabolic barrier; no MB Fermi level or tunnel I-V.
    E00 is a leading zero-normal-kinetic-energy WKB scale. Transmission
    omits prefactors; WKB loses accuracy when the action is small.
    """
    positive(ND=donor_m3, B=bending_V, mass=mass_kg, eps=epsilon_F_m, T=temperature_K)
    w = math.sqrt(2*epsilon_F_m*bending_V/(Q*donor_m3))
    e00 = Q*HBAR/2*math.sqrt(donor_m3/(mass_kg*epsilon_F_m)); action = Q*bending_V/e00
    return {'ND_m3': donor_m3, 'fixed_B_V': bending_V, 'W_m': w,
            'E00_J': e00, 'E00_eV': e00/Q, 'E00_over_kT': e00/(KB*temperature_K),
            'WKB_action_zero_normal_energy': action, 'WKB_leading_transmission': math.exp(-action)}

def bar_resistance(length_m, area_m2, density_m3, mobility_m2_V_s, contact_area_m2, rho_c_ohm_m2):
    positive(L=length_m, A=area_m2, n=density_m3, mu=mobility_m2_V_s,
             Ac=contact_area_m2, rho_c=rho_c_ohm_m2)
    rc = rho_c_ohm_m2/contact_area_m2
    rb = length_m/(Q*density_m3*mobility_m2_V_s*area_m2)
    return {'L_m': length_m, 'Rc_each_ohm': rc, 'Rbulk_ohm': rb,
            'Rtotal_ohm': rb+2*rc, 'Gtotal_S': 1/(rb+2*rc)}

def recover_length_series(lengths, resistances):
    """Affine fit for identical uniform contacts and cross-section."""
    if len(lengths) != len(resistances) or len(lengths) < 2: raise ValueError('at least two paired samples required')
    positive(**{f'L{i}': x for i,x in enumerate(lengths)}); positive(**{f'R{i}': x for i,x in enumerate(resistances)})
    lm = sum(lengths)/len(lengths); rm = sum(resistances)/len(resistances)
    denom = sum((x-lm)**2 for x in lengths)
    if denom == 0: raise ValueError('distinct lengths required')
    slope = sum((x-lm)*(y-rm) for x,y in zip(lengths,resistances))/denom; intercept = rm-slope*lm
    return {'slope_ohm_m': slope, 'intercept_ohm': intercept, 'Rc_each_ohm': intercept/2}

def dataset():
    c = Contact(); spatial = []
    for v in [-0.2, 0.0, 0.2]:
        spatial.append({'V_V': v, 'EFmetal_eV': -c.xi_eV-v, 'EFbulk_eV': -c.xi_eV,
                        'depletion': c.depletion(v),
                        'profile': [{'x_m': i*4e-7/160, **c.spatial(i*4e-7/160,v)} for i in range(161)]})
    cvs = [{'V_V': -0.2+i*0.4/80, **c.depletion(-0.2+i*0.4/80)} for i in range(81)]
    iv = [{'V_V': -0.2+i*0.4/160, 'J_A_m2': c.current(-0.2+i*0.4/160)} for i in range(161)]
    diagnostics = [{**barrier_diagnostic(10**(22+i*3/60), c.vbi,c.mass,c.eps,c.temperature_K),
                    'ND_over_default_Nc': 10**(22+i*3/60)/c.nc} for i in range(61)]
    bc = {'n_m3': 1e21, 'mu_m2_V_s': .135, 'A_m2': 1e-12, 'Ac_m2': 1e-12, 'rho_c_ohm_m2': 1e-8}
    bars = [bar_resistance(l*1e-6,bc['A_m2'],bc['n_m3'],bc['mu_m2_V_s'],bc['Ac_m2'],bc['rho_c_ohm_m2']) for l in [1,2,4]]
    return {'model': 'ideal single-isotropic-valley MB Schottky plus separate uniform linear-contact bar',
            'contact_card': asdict(c), 'summary': c.summary(), 'spatial': spatial, 'cv': cvs, 'iv': iv,
            'linear_error': [{'V_V': v, 'relative_error':linear_error(v,c.vt)} for v in [-.01,-.0025,0,.0025,.01]],
            'fixed_bending_diagnostics': diagnostics, 'bar_card_independent_of_TE': bc,
            'bar_length_series': bars, 'bar_recovered': recover_length_series([d['L_m'] for d in bars],[d['Rtotal_ohm'] for d in bars])}

if __name__ == '__main__':
    Path('results.json').write_text(json.dumps(dataset(),ensure_ascii=False,indent=2,sort_keys=True)+'\n')
