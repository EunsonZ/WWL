#!/usr/bin/env python3
"""Finite quasi-static PB + dynamic sheet occupations, stdlib only.

External spatially uniform Fn/Fp clamps are inputs. This does not solve DD.
08 owns the material card and linear solver; 09 owns the frozen-sheet BVP.
"""
import argparse
import copy
import csv
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def dependencies(directory):
    base = module(directory/'08-异质结与Poisson自洽'/'heterojunction_lab.py', 'dynamic_pb_base')
    static = module(directory/'09-界面态与平衡电荷'/'interface_charge_lab.py', 'dynamic_static_sheet')
    card = json.loads((directory/'08-异质结与Poisson自洽'/'inputs.json').read_text())
    # Proxy avoids modifying either imported source module or their globals.
    proxy = SimpleNamespace(**vars(base))
    def carriers(material, phi, current):
        vt = base.KB_EV*current['temperature_K']
        eta_n = (current.get('Fn_eV', current['fermi_eV'])-material['Ec0_eV']+phi)/vt
        eta_p = (material['Ec0_eV']-material['Eg_eV']-phi-current.get('Fp_eV', current['fermi_eV']))/vt
        if not all(math.isfinite(x) and abs(x)<=100 for x in (eta_n, eta_p)):
            raise ValueError('carrier exponent outside finite arithmetic domain')
        n, p = material['Nc_m-3']*math.exp(eta_n), material['Nv_m-3']*math.exp(eta_p)
        rho = base.Q*(p-n+material['ND_m-3']-material['NA_m-3'])
        return n, p, rho, -base.Q*(n+p)/vt
    proxy.carriers = carriers
    return proxy, static, card


def validate(base, static, card, data):
    base.validate(card)
    static.validate_states(data['states'], data['fixed_sheet_C_m-2'])
    if not data['states']: raise ValueError('at least one state required')
    for state in data['states']:
        for key in ('cn_m3_s-1', 'cp_m3_s-1'):
            if not math.isfinite(state[key]) or state[key]<=0: raise ValueError('positive finite capture coefficients required')
    for key in ('dt_s', 'duration_s', 'half_length_m', 'density_factor'):
        if not math.isfinite(data[key]) or data[key]<=0: raise ValueError('positive finite '+key+' required')
    cells = data['half_cells']
    if isinstance(cells, bool) or not isinstance(cells, int) or not 4<=cells<=1000:
        raise ValueError('half_cells integer in [4,1000] required')
    if not 1<=data['duration_s']/data['dt_s']<=20000: raise ValueError('time-step budget outside [1,20000]')
    if abs(data['duration_s']/data['dt_s']-round(data['duration_s']/data['dt_s']))>1e-8:
        raise ValueError('duration must be an integer multiple of dt for aligned convergence comparisons')
    for key in ('initial_F_eV', 'final_Fn_eV', 'final_Fp_eV'):
        if not math.isfinite(data[key]): raise ValueError('finite reservoir energy required')
    if len(data['capture_factors'])!=2 or any(not math.isfinite(x) or x<=0 for x in data['capture_factors']):
        raise ValueError('two positive finite capture factors required')
    bins = data['dos_bin_centers_eV']
    if not 1<=len(bins)<=20 or any(not math.isfinite(x) for x in bins): raise ValueError('finite DOS bins required')


def profile_vector(result):
    return [r['phi_V'] for r in result['profile'] if r['x_m']!=0 or r['material']=='A']


def frozen_solve(base, static, card, states, occupations, fixed, cells, boundaries, initial):
    frozen = [dict(state, frozen_f=f) for state, f in zip(states, occupations)]
    if len(occupations)!=len(states): raise ValueError('occupation/state shape mismatch')
    return static.solve(base, card, frozen, fixed, cells, boundaries=boundaries, initial=initial)


def rates(base, card, state, phi):
    """Only the A-side carrier bath couples to these synthetic traps."""
    a = card['materials']['A']; vt = base.KB_EV*card['temperature_K']
    n, p, _, _ = base.carriers(a, phi, card)
    z_n = (state['Et0_eV']-a['Ec0_eV'])/vt
    z_p = (a['Ec0_eV']-a['Eg_eV']-state['Et0_eV'])/vt
    if max(abs(z_n), abs(z_p))>100: raise ValueError('emission exponent outside finite arithmetic domain')
    n1, p1 = a['Nc_m-3']*math.exp(z_n), a['Nv_m-3']*math.exp(z_p)
    cn, cp, beta = state['cn_m3_s-1'], state['cp_m3_s-1'], state['empty_over_filled_weight']
    capture_n, capture_p = cn*n, cp*p
    emission_n, emission_p = beta*cn*n1, cp*p1/beta
    total = capture_n+capture_p+emission_n+emission_p
    if not math.isfinite(total) or total<=0: raise ValueError('positive finite total rate required')
    return capture_n, emission_n, capture_p, emission_p


def exponential_step(f, channels, dt, number):
    if not math.isfinite(f) or not 0<=f<=1: raise ValueError('initial occupation outside [0,1]')
    if not math.isfinite(dt) or dt<=0: raise ValueError('positive finite time step required')
    if not math.isfinite(number) or number<0: raise ValueError('nonnegative finite state density required')
    if len(channels)!=4 or not all(math.isfinite(x) and x>=0 for x in channels): raise ValueError('four finite nonnegative rates required')
    cn, en, cp, ep = channels
    lam = cn+en+cp+ep
    if not math.isfinite(lam) or lam<=0: raise ValueError('positive finite total rate required')
    star = (cn+ep)/lam
    drop = -math.expm1(-lam*dt)
    new = f+(star-f)*drop
    integral_f = star*dt+(f-star)*drop/lam
    # Exact event integrals for rates frozen at the beginning of this step.
    events = (number*cn*(dt-integral_f), number*en*integral_f,
              number*cp*integral_f, number*ep*(dt-integral_f))
    if not 0<=new<=1 or not all(math.isfinite(x) and x>=0 for x in events):
        raise ValueError('probability/event positivity failure; no clipping permitted')
    return new, events


def trace_row(base, card, states, f, solution, t):
    r = {'t_s':t, 'phi0_V':solution['phi0_V'], 'sheet_C_m-2':solution['sheet_C_m-2'],
         'volume_C_m-2':solution['volume_charge_C_m-2'],
         'electrodes_C_m-2':solution['electrode_charge_left_C_m-2']+solution['electrode_charge_right_C_m-2'],
         'global_gauss_error_C_m-2':solution['global_gauss_error_C_m-2'],
         'sheet_jump_error_C_m-2':solution['sheet_jump_error_C_m-2'],
         'scaled_residual':solution['scaled_residual'],
         'MB_max_fraction':solution['max_n_over_Nc_or_p_over_Nv']}
    for s, value in zip(states, f):
        cn, en, cp, ep = rates(base, card, s, solution['phi0_V'])
        name = s['name']; un = s['N_m-2']*(cn*(1-value)-en*value)
        up = s['N_m-2']*(cp*value-ep*(1-value))
        r['f_'+name] = value; r['fstar_'+name] = (cn+ep)/(cn+en+cp+ep)
        r['tau_frozen_'+name+'_s'] = 1/(cn+en+cp+ep)
        r['Un_'+name+'_m-2_s-1'] = un; r['Up_'+name+'_m-2_s-1'] = up
    return r


def simulate(base, static, material_card, data, states=None, dt=None, cells=None, rate_factor=1.0):
    if not math.isfinite(rate_factor) or rate_factor<=0: raise ValueError('positive finite rate factor required')
    states = copy.deepcopy(data['states'] if states is None else states)
    for s in states:
        s['cn_m3_s-1']*=rate_factor; s['cp_m3_s-1']*=rate_factor
    dt = data['dt_s'] if dt is None else dt
    cells = data['half_cells'] if cells is None else cells
    if not math.isfinite(dt) or dt<=0: raise ValueError('positive finite dt required')
    if data['duration_s']/dt>20000: raise ValueError('refinement exceeds step budget')
    card = copy.deepcopy(material_card); card['half_length_m']=data['half_length_m']
    card['fermi_eV']=data['initial_F_eV']
    boundaries = tuple(base.neutral_phi(card['materials'][name], card) for name in ('A','B'))
    initial = static.solve(base, card, states, data['fixed_sheet_C_m-2'], cells, boundaries=boundaries)
    f = [s['f'] for s in initial['traps']]
    card['Fn_eV'], card['Fp_eV'] = data['final_Fn_eV'], data['final_Fp_eV']
    # Carrier/field fast relaxation occurs before any trap occupation changes.
    solution = frozen_solve(base, static, card, states, f, data['fixed_sheet_C_m-2'], cells, boundaries, profile_vector(initial))
    start = solution; rows = [trace_row(base, card, states, f, solution, 0.0)]
    balances = []; elapsed = 0.0; channels_total = [0.0]*4
    while elapsed < data['duration_s']:
        step = min(dt, data['duration_s']-elapsed)
        if step < dt*1e-10: break
        new_f, events = [], [0.0]*4
        for state, value in zip(states, f):
            new, pieces = exponential_step(value, rates(base, card, state, solution['phi0_V']), step, state['N_m-2'])
            new_f.append(new)
            events = [a+b for a,b in zip(events,pieces)]
        next_solution = frozen_solve(base, static, card, states, new_f, data['fixed_sheet_C_m-2'], cells, boundaries, profile_vector(solution))
        un, up = events[0]-events[1], events[2]-events[3]
        delta_sheet = next_solution['sheet_C_m-2']-solution['sheet_C_m-2']
        ni, nf = solution['integrated_numbers'], next_solution['integrated_numbers']
        supply_n = nf['electron_number_m-2']-ni['electron_number_m-2']+un
        supply_p = nf['hole_number_m-2']-ni['hole_number_m-2']+up
        delta_volume = next_solution['volume_charge_C_m-2']-solution['volume_charge_C_m-2']
        balances.append({'t_end_s':elapsed+step, 'dt_s':step,
                         'capture_n_m-2':events[0], 'emission_n_m-2':events[1],
                         'capture_p_m-2':events[2], 'emission_p_m-2':events[3],
                         'delta_sheet_C_m-2':delta_sheet,
                         'trap_balance_error_C_m-2':delta_sheet-base.Q*(up-un),
                         'supplied_electron_number_m-2':supply_n, 'supplied_hole_number_m-2':supply_p,
                         'supply_balance_error_C_m-2':base.Q*(supply_p-supply_n)-delta_volume-delta_sheet})
        channels_total = [a+b for a,b in zip(channels_total,events)]
        elapsed += step; f = new_f; solution = next_solution
        rows.append(trace_row(base, card, states, f, solution, elapsed))
    # A separate static root is meaningful only for common Fn=Fp.
    equilibrium = None
    if card['Fn_eV']==card['Fp_eV']:
        ref = copy.deepcopy(card); ref['fermi_eV']=card['Fn_eV']
        equilibrium = static.solve(base, ref, states, data['fixed_sheet_C_m-2'], cells, boundaries=boundaries, initial=profile_vector(solution))
    result = {'rows':rows, 'balances':balances, 'initial':initial, 'start':start, 'end':solution,
              'equilibrium':equilibrium, 'boundaries_V':list(boundaries), 'events_m-2':channels_total,
              'states':states, 'dt_s':dt, 'half_cells':cells}
    return result


def summary(sim):
    rows = sim['rows']; e = sim['equilibrium']; s = sim['end']
    return {'dt_s':sim['dt_s'], 'half_cells':sim['half_cells'], 'steps':len(sim['balances']),
            'phi0_before_V':sim['initial']['phi0_V'], 'phi0_0plus_V':sim['start']['phi0_V'],
            'phi0_end_V':s['phi0_V'], 'occupations_end':[r['f'] for r in s['traps']],
            'equilibrium_phi0_V':None if e is None else e['phi0_V'],
            'end_minus_equilibrium_V':None if e is None else s['phi0_V']-e['phi0_V'],
            'max_trap_balance_error_C_m-2':max(abs(r['trap_balance_error_C_m-2']) for r in sim['balances']),
            'max_supply_balance_error_C_m-2':max(abs(r['supply_balance_error_C_m-2']) for r in sim['balances']),
            'max_gauss_error_C_m-2':max(abs(r['global_gauss_error_C_m-2']) for r in rows),
            'max_jump_error_C_m-2':max(abs(r['sheet_jump_error_C_m-2']) for r in rows),
            'max_scaled_residual':max(r['scaled_residual'] for r in rows),
            'max_MB_fraction':max(r['MB_max_fraction'] for r in rows),
            'max_end_f_minus_fstar':max(abs(rows[-1]['f_'+state['name']]-rows[-1]['fstar_'+state['name']]) for state in sim['states']),
            'channel_events_m-2':sim['events_m-2'], 'boundaries_V':sim['boundaries_V']}


def write_csv(path, rows):
    with path.open('w', newline='') as file:
        writer=csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def compare(a, b, factor):
    return {'max_phi0_difference_V':max(abs(r['phi0_V']-b['rows'][i*factor]['phi0_V']) for i,r in enumerate(a['rows'])),
            'max_first_f_difference':max(abs(r['f_'+a['states'][0]['name']]-b['rows'][i*factor]['f_'+b['states'][0]['name']]) for i,r in enumerate(a['rows']))}


def run(base, static, card, data, out):
    validate(base, static, card, data)
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError('output must be absent or an empty nonsymlink directory; existing bytes are preserved')
    out.mkdir(parents=True,exist_ok=True)
    coarse = simulate(base, static, card, data)
    half = simulate(base, static, card, data, dt=data['dt_s']/2)
    quarter = simulate(base, static, card, data, dt=data['dt_s']/4)
    mesh = simulate(base, static, card, data, cells=data['half_cells']*2)
    doubled = copy.deepcopy(data['states'])
    for s in doubled: s['N_m-2']*=data['density_factor']
    bins = [dict(data['states'][0], name='bin'+str(i), **{'Et0_eV':energy, 'N_m-2':data['states'][0]['N_m-2']/len(data['dos_bin_centers_eV'])})
            for i,energy in enumerate(data['dos_bin_centers_eV'])]
    cases={'step':coarse, 'half_dt':half, 'quarter_dt':quarter, 'fine_mesh':mesh,
           'density':simulate(base,static,card,data,states=doubled),
           'slow':simulate(base,static,card,data,rate_factor=data['capture_factors'][0]),
           'fast':simulate(base,static,card,data,rate_factor=data['capture_factors'][1]),
           'finite_dos':simulate(base,static,card,data,states=bins)}
    split=copy.deepcopy(data); split['final_Fp_eV']=data['initial_F_eV']
    cases['split']=simulate(base,static,card,split)
    # Frozen-field exact exponential is a deliberately different limit.
    state=coarse['states'][0]; f0=coarse['rows'][0]['f_'+state['name']]
    after=copy.deepcopy(card); after['Fn_eV']=data['final_Fn_eV'];after['Fp_eV']=data['final_Fp_eV']
    ch=rates(base,after,state,coarse['start']['phi0_V']);lam=sum(ch);star=(ch[0]+ch[3])/lam
    f=f0; max_error=0.0
    for row in coarse['rows']:
        exact=star+(f0-star)*math.exp(-lam*row['t_s'])
        if row['t_s']>0: f,_=exponential_step(f,ch,data['dt_s'],state['N_m-2'])
        max_error=max(max_error,abs(f-exact))
    analytic=[{'t_s':r['t_s'],'f_frozen_exact':star+(f0-star)*math.exp(-lam*r['t_s'])} for r in coarse['rows']]
    failures={}
    for name, work in [('negative_capture',lambda:validate(base,static,card,dict(data,states=[dict(state,**{'cn_m3_s-1':-1})]))),
                       ('invalid_f',lambda:exponential_step(1.1,ch,data['dt_s'],state['N_m-2'])),
                       ('zero_step',lambda:validate(base,static,card,dict(data,dt_s=0)))]:
        try: work()
        except (ValueError,RuntimeError) as error: failures[name]=type(error).__name__
        else: raise RuntimeError('guard failed: '+name)
    for name, sim in cases.items():
        write_csv(out/(name+'-time.csv'),sim['rows'])
    write_csv(out/'step-balance.csv',coarse['balances'])
    for name,sol in [('before',coarse['initial']),('0plus',coarse['start']),('end',coarse['end'])]:
        write_csv(out/(name+'-profile.csv'),sol['profile'])
    write_csv(out/'frozen-analytic.csv',analytic)
    result={'inputs':copy.deepcopy(data), 'material_card':copy.deepcopy(card),
            'scope':'Finite quasi-static electrostatic feedback with external uniform Fn/Fp clamps; no DD continuity solve',
            'cases':{name:summary(sim) for name,sim in cases.items()},
            'time_refinement':[compare(coarse,half,2),compare(half,quarter,2)],
            'mesh_refinement':compare(coarse,mesh,1),
            'frozen_analytic_max_error':max_error,'guards':failures}
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-dir', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--out',type=Path,default=Path(__file__).with_name('results'))
    args=parser.parse_args();base,static,card=dependencies(args.base_dir)
    run(base,static,card,json.loads(args.inputs.read_text()),args.out)

if __name__=='__main__': main()
