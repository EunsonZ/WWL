#!/usr/bin/env python3
"""1D equilibrium MB Poisson with split interface control volume. Standard library."""
import argparse
import copy
import csv
import json
import math
from pathlib import Path

Q = 1.602176634e-19
KB_EV = 8.617333262145e-5
EPS0 = 8.8541878188e-12  # CODATA 2022, F/m


def validate(card):
    for key in ('temperature_K', 'half_length_m'):
        if not math.isfinite(card[key]) or card[key] <= 0:
            raise ValueError('positive finite '+key+' required')
    settings=card['newton']
    for key in ('scaled_residual_tolerance','max_step_V'):
        if not math.isfinite(settings[key]) or settings[key]<=0:
            raise ValueError('positive finite Newton '+key+' required')
    for key,cap in [('max_iterations',80),('max_backtracks',24)]:
        if isinstance(settings[key],bool) or not isinstance(settings[key],int) or not 0<=settings[key]<=cap:
            raise ValueError('Newton '+key+' outside finite budget')
    if not math.isfinite(card['fermi_eV']):
        raise ValueError('finite Fermi energy required')
    for m in card['materials'].values():
        for key in ('Eg_eV', 'Nc_m-3', 'Nv_m-3', 'epsilon_r'):
            if not math.isfinite(m[key]) or m[key] <= 0:
                raise ValueError('positive finite '+key+' required')
        for key in ('ND_m-3', 'NA_m-3'):
            if not math.isfinite(m[key]) or m[key] < 0:
                raise ValueError('nonnegative finite doping required')
        if not math.isfinite(m['Ec0_eV']):
            raise ValueError('finite band offset required')


def carriers(m, phi, card):
    vt = KB_EV*card['temperature_K']
    eta_n = (card['fermi_eV']-m['Ec0_eV']+phi)/vt
    eta_p = (m['Ec0_eV']-m['Eg_eV']-phi-card['fermi_eV'])/vt
    if max(abs(eta_n), abs(eta_p)) > 100:
        raise ValueError('exponent outside declared numeric range [-100,100]')
    n, p = m['Nc_m-3']*math.exp(eta_n), m['Nv_m-3']*math.exp(eta_p)
    rho = Q*(p-n+m['ND_m-3']-m['NA_m-3'])
    drho = -Q*(n+p)/vt
    if not all(math.isfinite(v) for v in (n,p,rho,drho)):
        raise ValueError('nonfinite carrier or charge arithmetic')
    return n, p, rho, drho


def neutral_phi(m, card):
    """Stable quadratic root of n-p=ND-NA, np=ni^2; no forced local neutrality."""
    vt = KB_EV*card['temperature_K']
    ni2 = m['Nc_m-3']*m['Nv_m-3']*math.exp(-m['Eg_eV']/vt)
    net = m['ND_m-3']-m['NA_m-3']
    root = math.hypot(net, 2*math.sqrt(ni2))
    if net >= 0:
        n = (net+root)/2
    else:
        n = 2*ni2/(root-net)
    return m['Ec0_eV']-card['fermi_eV']+vt*math.log(n/m['Nc_m-3'])


def depletion(card, sigma):
    """Neutral-edge, carrier-free approximation. This is not the nonlinear solve."""
    a, b = card['materials']['A'], card['materials']['B']
    if a['ND_m-3'] or b['NA_m-3'] or not a['NA_m-3'] or not b['ND_m-3']:
        raise ValueError('depletion oracle requires pure p-A / n-B')
    na, nd = a['NA_m-3'], b['ND_m-3']
    ea, eb = EPS0*a['epsilon_r'], EPS0*b['epsilon_r']
    pl, pr = neutral_phi(a, card), neutral_phi(b, card)
    delta = pr-pl
    if delta <= 0:
        raise ValueError('no positive depletion drop')
    def wl(wr): return (nd*wr+sigma/Q)/na
    def drop(wr): return Q*na*wl(wr)**2/(2*ea)+Q*nd*wr**2/(2*eb)
    lo, hi = max(0, -sigma/(Q*nd)), card['half_length_m']
    if drop(lo) > delta or drop(hi) < delta:
        raise ValueError('no two-sided depletion solution within this finite card')
    for _ in range(100):
        mid = (lo+hi)/2
        if drop(mid) < delta: lo = mid
        else: hi = mid
    wr = (lo+hi)/2
    left = wl(wr)
    if left > card['half_length_m']:
        raise ValueError('left depletion width exceeds domain')
    pi = pl+Q*na*left**2/(2*ea)
    dl, dr = -Q*na*left, -Q*nd*wr
    return {'wA_m': left, 'wB_m': wr, 'phi0_V': pi, 'phiL_V': pl, 'phiR_V': pr,
            'D0minus_C_m-2': dl, 'D0plus_C_m-2': dr,
            'sheet_jump_error_C_m-2': dr-dl-sigma,
            'charge_sum_C_m-2': -Q*na*left+Q*nd*wr+sigma,
            'potential_drop_error_V': drop(wr)-delta}


def depletion_phi(x, d, card):
    a, b = card['materials']['A'], card['materials']['B']
    if x < 0:
        z = max(0, x+d['wA_m'])
        return d['phiL_V']+Q*a['NA_m-3']*z*z/(2*EPS0*a['epsilon_r'])
    z = max(0, d['wB_m']-x)
    return d['phiR_V']-Q*b['ND_m-3']*z*z/(2*EPS0*b['epsilon_r'])


def semi_infinite_oracle(card, sigma):
    """Independent first integral of continuum PB on each semi-infinite side."""
    a, b = card['materials']['A'], card['materials']['B']
    vt = KB_EV*card['temperature_K']
    pl, pr = neutral_phi(a, card), neutral_phi(b, card)
    if pl >= pr: raise ValueError('oracle branch requires increasing potential')
    def flux(m, phi, pb):
        # Difference of F avoids subtracting large constants; expm1 retains small bend.
        n0, p0, _, _ = carriers(m, pb, card)
        z = (phi-pb)/vt
        excess = Q*vt*(n0*(math.expm1(z)-z)+p0*(math.expm1(-z)+z))
        return -math.sqrt(max(0, 2*EPS0*m['epsilon_r']*excess))
    def residual(pi): return flux(b, pi, pr)-flux(a, pi, pl)-sigma
    lo, hi = pl, pr
    if residual(lo)*residual(hi) > 0:
        raise ValueError('sheet needs a different semi-infinite monotone branch')
    for _ in range(100):
        mid = (lo+hi)/2
        if residual(mid) < 0: lo = mid
        else: hi = mid
    pi = (lo+hi)/2
    return {'phi0_V': pi, 'D0minus_C_m-2': flux(a, pi, pl),
            'D0plus_C_m-2': flux(b, pi, pr), 'jump_error_C_m-2': residual(pi),
            'scope': 'continuum semi-infinite monotone equilibrium, not finite Dirichlet'}


def tridiagonal(lower, diag, upper, rhs):
    n = len(diag)
    d, r = diag[:], rhs[:]
    for i in range(1, n):
        if d[i-1] <= 0: raise ArithmeticError('nonpositive pivot')
        factor = lower[i-1]/d[i-1]
        d[i] -= factor*upper[i-1]
        r[i] -= factor*r[i-1]
    if d[-1] <= 0: raise ArithmeticError('nonpositive pivot')
    x = [0.0]*n
    x[-1] = r[-1]/d[-1]
    for i in range(n-2, -1, -1): x[i] = (r[i]-upper[i]*x[i+1])/d[i]
    return x


def solve(card, sigma, half_cells, right_shift=0.0, max_iterations=None):
    validate(card)
    if isinstance(half_cells, bool) or not isinstance(half_cells, int) or not 4 <= half_cells <= 5000:
        raise ValueError('half_cells integer in [4,5000] required')
    if not math.isfinite(sigma) or not math.isfinite(right_shift):
        raise ValueError('finite sheet and boundary shift required')
    if max_iterations is not None and (isinstance(max_iterations,bool) or not isinstance(max_iterations,int) or not 0<=max_iterations<=80):
        raise ValueError('iteration override must be integer in [0,80]')
    a, b = card['materials']['A'], card['materials']['B']
    length = card['half_length_m']; h = length/half_cells; count = 2*half_cells
    x = [(i-half_cells)*h for i in range(count+1)]
    eps = [EPS0*(a if i < half_cells else b)['epsilon_r'] for i in range(count)]
    pl, pr = neutral_phi(a, card), neutral_phi(b, card)+right_shift
    try:
        dep = depletion(card, sigma)
        phi = [depletion_phi(xx, dep, card)+right_shift*(xx+length)/(2*length) for xx in x]
    except ValueError:
        phi = [pl+(pr-pl)*i/count for i in range(count+1)]
    phi[0], phi[-1] = pl, pr
    settings = card['newton']; budget = settings['max_iterations'] if max_iterations is None else max_iterations
    scale = max(Q*max(a['NA_m-3'], a['ND_m-3'], b['NA_m-3'], b['ND_m-3'])*length,
                abs(sigma), EPS0*max(a['epsilon_r'], b['epsilon_r'])*KB_EV*card['temperature_K']/length, 1e-30)
    def state(v):
        charge, derivative, resid, diag = [], [], [], []
        for i in range(1, count):
            weights = [(a, h/2), (b, h/2)] if i == half_cells else [(a if i < half_cells else b, h)]
            cvq = cvd = 0.0
            for m, w in weights:
                _, _, rho, drho = carriers(m, v[i], card)
                cvq += w*rho; cvd += w*drho
            charge.append(cvq)
            derivative.append(cvd)
            sheet = sigma if i == half_cells else 0.0
            resid.append(eps[i-1]*(v[i]-v[i-1])/h+eps[i]*(v[i]-v[i+1])/h-cvq-sheet)
            diag.append((eps[i-1]+eps[i])/h-cvd)
        return charge, derivative, resid, diag
    history = []
    last_step = 0.0
    for iteration in range(budget+1):
        charges, _, residual, diag = state(phi)
        norm = max(abs(z) for z in residual)/scale
        if norm < settings['scaled_residual_tolerance']:
            break
        if iteration == budget: raise RuntimeError('Newton iteration budget exhausted')
        off = [-eps[i]/h for i in range(1, count-1)]
        step = tridiagonal(off, diag, off, [-z for z in residual])
        alpha = min(1.0, settings['max_step_V']/max(abs(z) for z in step))
        accepted = False
        for backtrack in range(settings['max_backtracks']+1):
            trial = [pl]+[phi[i+1]+alpha*step[i] for i in range(count-1)]+[pr]
            try: trial_norm = max(abs(z) for z in state(trial)[2])/scale
            except ValueError: trial_norm = math.inf
            if trial_norm <= (1-1e-4*alpha)*norm:
                accepted = True; break
            alpha *= 0.5
        if not accepted: raise RuntimeError('Newton line search exhausted')
        last_step = alpha*max(abs(z) for z in step)
        history.append({'iteration': iteration, 'scaled_residual_before': norm,
                        'alpha': alpha, 'accepted_step_V': last_step, 'backtracks': backtrack})
        phi = trial
    flux = [-eps[i]*(phi[i+1]-phi[i])/h for i in range(count)]
    interface_charge = charges[half_cells-1]
    # Correct mid-face D to the interface using the declared half-cell quadrature.
    _, _, ra, _ = carriers(a, phi[half_cells], card)
    _, _, rb, _ = carriers(b, phi[half_cells], card)
    dl = flux[half_cells-1]+ra*h/2
    dr = flux[half_cells]-rb*h/2
    # Endpoint half-volumes are prescribed-density quadrature, not unknown CV rows.
    end_l = carriers(a, pl, card)[2]*h/2
    end_r = carriers(b, pr, card)[2]*h/2
    boundary_l, boundary_r = flux[0]-end_l, flux[-1]+end_r
    qfull = sum(charges)+end_l+end_r
    rows = []
    maximum_fraction = 0.0
    for i, xx in enumerate(x):
        for name in (['A','B'] if i == half_cells else ['A' if i < half_cells else 'B']):
            m = card['materials'][name]; n, p, rho, _ = carriers(m, phi[i], card)
            maximum_fraction = max(maximum_fraction, n/m['Nc_m-3'], p/m['Nv_m-3'])
            rows.append({'x_m': xx, 'material': name, 'phi_V': phi[i], 'Ec_eV': m['Ec0_eV']-phi[i],
                         'Ev_eV': m['Ec0_eV']-m['Eg_eV']-phi[i], 'n_m-3': n, 'p_m-3': p,
                         'rho_C_m-3': rho})
    return {'half_cells': half_cells, 'h_m': h, 'sigma_C_m-2': sigma, 'phiL_V': pl, 'phiR_V': pr,
            'phi0_V': phi[half_cells], 'iterations': len(history), 'last_step_V': last_step,
            'scaled_residual': norm, 'residual_scale_C_m-2': scale,
            'max_row_residual_C_m-2': max(abs(z) for z in residual),
            'D0minus_C_m-2': dl, 'D0plus_C_m-2': dr,
            'sheet_jump_error_C_m-2': dr-dl-sigma,
            'interface_half_volume_charge_C_m-2': interface_charge,
            'boundary_D_left_C_m-2': boundary_l, 'boundary_D_right_C_m-2': boundary_r,
            'volume_charge_C_m-2': qfull, 'global_charge_error_C_m-2': boundary_r-boundary_l-qfull-sigma,
            'max_n_over_Nc_or_p_over_Nv': maximum_fraction,
            'MB_tail_check_eta_le_minus3': maximum_fraction <= math.exp(-3),
            'history': history, 'profile': rows,
            'edges': [{'x_mid_m': (x[i]+x[i+1])/2, 'D_C_m-2': flux[i], 'E_V_m-1': flux[i]/eps[i]} for i in range(count)]}


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def run(card, out):
    validate(card)
    grids=card['half_cells']
    if len(grids)!=3 or any(isinstance(n,bool) or not isinstance(n,int) or not 4<=n<=5000 for n in grids):
        raise ValueError('run requires exactly three integer grids in [4,5000]')
    if any(b<=a or b%a for a,b in zip(grids,grids[1:])) or grids[-1]%2:
        raise ValueError('run grids must increase by integer ratios; finest must be even')
    if grids[-1]*3//2>5000:
        raise ValueError('domain-extension grid exceeds 5000 per side')
    out.mkdir(parents=True, exist_ok=True)
    sigma = Q*card['sheet_number_m-2']
    cases = {}
    for name, sheet in [('zero',0.0),('positive',sigma),('negative',-sigma)]:
        meshes = [solve(card, sheet, n) for n in card['half_cells']]
        fine = meshes[-1]
        diff = []
        for coarse, refined in zip(meshes, meshes[1:]):
            cp = [r for r in coarse['profile'] if r['material'] != 'B' or r['x_m'] != 0]
            rp = [r for r in refined['profile'] if r['material'] != 'B' or r['x_m'] != 0]
            ratio = refined['half_cells']//coarse['half_cells']
            diff.append({'h_coarse_m': coarse['h_m'], 'h_refined_m': refined['h_m'],
                         'max_phi_difference_V': max(abs(r['phi_V']-rp[i*ratio]['phi_V']) for i,r in enumerate(cp)),
                         'phi0_difference_V': refined['phi0_V']-coarse['phi0_V']})
        dep, oracle = depletion(card, sheet), semi_infinite_oracle(card, sheet)
        summary = [{k:v for k,v in r.items() if k not in ('profile','edges','history')} for r in meshes]
        write_csv(out/(name+'-profile.csv'), fine['profile']); write_csv(out/(name+'-edges.csv'), fine['edges'])
        cases[name] = {'depletion': dep, 'semi_infinite_PB': oracle, 'meshes': summary,
                       'mesh_differences': diff, 'fine_minus_semi_infinite_phi0_V': fine['phi0_V']-oracle['phi0_V'],
                       'newton_history': fine['history']}
    changed = copy.deepcopy(card); changed['materials']['B']['ND_m-3'] *= 2
    doping = solve(changed, sigma, card['half_cells'][-1])
    boundary = solve(card, sigma, card['half_cells'][-1], right_shift=.05)
    write_csv(out/'doping-profile.csv', doping['profile']); write_csv(out/'boundary-profile.csv', boundary['profile'])
    cases['doping_double'] = {k:v for k,v in doping.items() if k not in ('profile','edges','history')}
    cases['right_boundary_plus_0.05V'] = {k:v for k,v in boundary.items() if k not in ('profile','edges','history')}
    # Exact nonlinear equilibrium limit: identical intrinsic media, zero sheet/BC.
    intrinsic = copy.deepcopy(card)
    for m in intrinsic['materials'].values():
        m.update(intrinsic['materials']['A']); m['ND_m-3']=m['NA_m-3']=0.0
    exact = solve(intrinsic, 0, 60)
    exact_error = max(abs(r['phi_V']-neutral_phi(intrinsic['materials']['A'], intrinsic)) for r in exact['profile'])
    failures = {}
    for name, work in [('iteration_budget_zero', lambda: solve(card,sigma,120,max_iterations=0)),
                        ('invalid_temperature', lambda: solve(dict(card,temperature_K=0),sigma,120)),
                        ('fractional_grid', lambda: solve(card,sigma,120.5))]:
        try: work()
        except (ValueError,RuntimeError) as e: failures[name] = str(e)
        else: raise AssertionError('expected failure did not occur: '+name)
    # Numerical convergence can survive a physically invalid MB contact.
    bad_mb = solve(card, sigma, 120, right_shift=.3)
    if bad_mb['MB_tail_check_eta_le_minus3']: raise AssertionError('expected MB violation')
    longer = copy.deepcopy(card); longer['half_length_m'] *= 1.5
    long_solution = solve(longer, sigma, card['half_cells'][-1]*3//2)  # same spacing, different physical domain
    checks = {'domain_extension_same_h_phi0_difference_V': long_solution['phi0_V']-cases['positive']['meshes'][-1]['phi0_V'],
              'exact_intrinsic_phi_error_V': exact_error,
              'exact_intrinsic_scaled_residual': exact['scaled_residual'],
              'expected_failures': failures,
              'converged_but_MB_invalid': {k:bad_mb[k] for k in ('scaled_residual','max_n_over_Nc_or_p_over_Nv','MB_tail_check_eta_le_minus3')},
              'assertions': ['all five physical teaching cases eta<=-3', 'mesh refinement decreases potential discrepancy',
                             'interface and global Gauss balance', 'exact intrinsic constant solution', 'budget/domain failures visible']}
    for name in ('zero','positive','negative'):
        c=cases[name]
        assert c['mesh_differences'][1]['max_phi_difference_V'] < c['mesh_differences'][0]['max_phi_difference_V']
        for r in c['meshes']:
            assert r['MB_tail_check_eta_le_minus3']
            assert abs(r['global_charge_error_C_m-2']) < 1e-10
            assert abs(r['sheet_jump_error_C_m-2']) < 1e-12
    assert doping['MB_tail_check_eta_le_minus3'] and boundary['MB_tail_check_eta_le_minus3']
    assert exact_error < 1e-12
    report = {'model':'equilibrium 1D nondegenerate MB, fully ionized dopants, fixed sheet, Dirichlet',
              'constants': {'q_C':Q,'kB_eV_K-1':KB_EV,'epsilon0_F_m-1':EPS0}, 'input':card,'cases':cases,'checks':checks}
    (out/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--out',type=Path,default=Path(__file__).with_name('results'))
    args=parser.parse_args(); report=run(json.loads(args.input.read_text()),args.out)
    print(json.dumps({'case_phi0_V': {k: v['meshes'][-1]['phi0_V'] if 'meshes' in v else v['phi0_V'] for k,v in report['cases'].items()},
                      'checks':report['checks']},indent=2,ensure_ascii=False))

if __name__=='__main__': main()
