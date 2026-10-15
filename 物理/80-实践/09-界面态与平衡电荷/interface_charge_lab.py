#!/usr/bin/env python3
"""Equilibrium interface occupation coupled to finite 1D PB, Python stdlib only.

Practice 08 owns the material card, carrier law, neutral boundary and linear solver.
This module owns the charge-state law and its nonlinear interface Jacobian.
"""
import argparse
import copy
import csv
import importlib.util
import json
import math
from pathlib import Path


def load_base(directory):
    spec = importlib.util.spec_from_file_location('wwl_heterojunction_base', directory/'heterojunction_lab.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_states(states, fixed):
    if not math.isfinite(fixed): raise ValueError('finite fixed sheet required')
    if not isinstance(states, list) or len(states) > 100:
        raise ValueError('at most 100 discrete states required')
    names = []
    for s in states:
        if s['type'] not in ('acceptor', 'donor'): raise ValueError('unknown charge type')
        if not isinstance(s['name'], str) or not s['name'] or s['name'] in names:
            raise ValueError('distinct nonempty state names required')
        names.append(s['name'])
        if not math.isfinite(s['N_m-2']) or s['N_m-2'] < 0: raise ValueError('nonnegative finite sheet density required')
        if not math.isfinite(s['Et0_eV']): raise ValueError('finite common-reference energy required')
        if not math.isfinite(s['empty_over_filled_weight']) or s['empty_over_filled_weight'] <= 0:
            raise ValueError('positive finite state weight ratio required')
        if 'frozen_f' in s and (not math.isfinite(s['frozen_f']) or not 0 <= s['frozen_f'] <= 1):
            raise ValueError('frozen probability in [0,1] required')


def sheet_state(base, card, states, fixed, phi0):
    """Et=eV Et0 - numerical volts phi0; beta = w_empty/w_filled.

    Returns C/m2, derivative C/(m2 V), and occupied electron numbers per m2.
    """
    vt = base.KB_EV*card['temperature_K']
    if not math.isfinite(vt) or vt<=0: raise ValueError('thermal voltage outside finite arithmetic domain')
    charge, derivative, rows = fixed, 0.0, []
    for s in states:
        z = math.log(s['empty_over_filled_weight'])+(s['Et0_eV']-phi0-card['fermi_eV'])/vt
        if not math.isfinite(z): raise ValueError('trap exponent outside finite arithmetic domain')
        if 'frozen_f' in s: f = s['frozen_f']
        elif z >= 0:
            ez = math.exp(-z); f = ez/(1+ez)
        else:
            ez = math.exp(z); f = 1/(1+ez)
        number = s['N_m-2']; occupied = number*f
        contribution = base.Q*((number-occupied) if s['type']=='donor' else -occupied)
        slope = 0.0 if 'frozen_f' in s else -base.Q*number*f*(1-f)/vt
        charge += contribution; derivative += slope
        rows.append({'name':s['name'], 'type':s['type'], 'f':f, 'N_m-2':number,
                     'Et_eV':s['Et0_eV']-phi0, 'Et_minus_EF_eV':s['Et0_eV']-phi0-card['fermi_eV'],
                     'occupied_number_m-2':occupied, 'charge_C_m-2':contribution,
                     'charge_derivative_C_m-2_V-1':slope, 'frozen':'frozen_f' in s})
    if not all(math.isfinite(v) for v in (charge,derivative)):
        raise ValueError('nonfinite interface charge arithmetic')
    return charge, derivative, rows


def solve(base, card, states, fixed, half_cells, boundaries=None, initial=None, max_iterations=None):
    base.validate(card); validate_states(states, fixed)
    if isinstance(half_cells,bool) or not isinstance(half_cells,int) or not 4<=half_cells<=5000:
        raise ValueError('half_cells integer in [4,5000] required')
    if max_iterations is not None and (isinstance(max_iterations,bool) or not isinstance(max_iterations,int) or not 0<=max_iterations<=80):
        raise ValueError('iteration override integer in [0,80] required')
    a,b = card['materials']['A'],card['materials']['B']
    lo_gap=max(m['Ec0_eV']-m['Eg_eV'] for m in (a,b));hi_gap=min(m['Ec0_eV'] for m in (a,b))
    if any(not lo_gap < s['Et0_eV'] < hi_gap for s in states):
        raise ValueError('this teaching model requires trap levels in the common gap')
    length=card['half_length_m']; h=length/half_cells; count=2*half_cells
    eps=[base.EPS0*(a if i<half_cells else b)['epsilon_r'] for i in range(count)]
    pl,pr=boundaries if boundaries is not None else (base.neutral_phi(a,card),base.neutral_phi(b,card))
    if not all(math.isfinite(v) for v in (pl,pr)): raise ValueError('finite Dirichlet potentials required')
    if initial is None:
        # Fixed zero-state solve supplies a good profile; no iteration treats this as final.
        seed=base.solve(card,0.0,half_cells)
        seed_phi=[r['phi_V'] for r in seed['profile'] if r['x_m']!=0 or r['material']=='A']
        sl,sr=seed['phiL_V'],seed['phiR_V']
        phi=[v+(pl-sl)*(1-i/count)+(pr-sr)*i/count for i,v in enumerate(seed_phi)]
    else:
        if len(initial)!=count+1 or not all(math.isfinite(v) for v in initial): raise ValueError('finite matching initial vector required')
        phi=list(initial)
    phi[0],phi[-1]=pl,pr
    settings=card['newton']; budget=settings['max_iterations'] if max_iterations is None else max_iterations
    scale=max(base.Q*max(m[k] for m in (a,b) for k in ('ND_m-3','NA_m-3'))*length,
              abs(fixed)+sum(base.Q*s['N_m-2'] for s in states),
              max(eps)*base.KB_EV*card['temperature_K']/length,1e-30)
    if not math.isfinite(scale) or scale<=0: raise ValueError('nonfinite residual scale')
    def state(v):
        charges,residual,diag=[],[],[]
        sheet,dsheet,_=sheet_state(base,card,states,fixed,v[half_cells])
        for i in range(1,count):
            weights=[(a,h/2),(b,h/2)] if i==half_cells else [(a if i<half_cells else b,h)]
            charge=slope=0.0
            for m,w in weights:
                _,_,rho,drho=base.carriers(m,v[i],card);charge+=w*rho;slope+=w*drho
            charges.append(charge)
            residual.append(eps[i-1]*(v[i]-v[i-1])/h+eps[i]*(v[i]-v[i+1])/h-charge-(sheet if i==half_cells else 0))
            diag.append((eps[i-1]+eps[i])/h-slope-(dsheet if i==half_cells else 0))
        if not all(math.isfinite(v) for row in (charges,residual,diag) for v in row):
            raise ValueError('nonfinite control-volume arithmetic')
        return charges,residual,diag
    history=[]
    for iteration in range(budget+1):
        charges,residual,diag=state(phi);norm=max(abs(v) for v in residual)/scale
        if norm<settings['scaled_residual_tolerance']: break
        if iteration==budget: raise RuntimeError('Newton iteration budget exhausted')
        off=[-eps[i]/h for i in range(1,count-1)]
        step=base.tridiagonal(off,diag,off,[-v for v in residual])
        alpha=min(1.0,settings['max_step_V']/max(abs(v) for v in step))
        for backtrack in range(settings['max_backtracks']+1):
            trial=[pl]+[phi[i+1]+alpha*step[i] for i in range(count-1)]+[pr]
            try: trial_norm=max(abs(v) for v in state(trial)[1])/scale
            except ValueError: trial_norm=math.inf
            if trial_norm <= (1-1e-4*alpha)*norm: break
            alpha*=.5
        else: raise RuntimeError('Newton line search exhausted')
        history.append({'iteration':iteration,'scaled_residual_before':norm,'alpha':alpha,'backtracks':backtrack})
        phi=trial
    sheet,dsheet,trap_rows=sheet_state(base,card,states,fixed,phi[half_cells])
    flux=[-eps[i]*(phi[i+1]-phi[i])/h for i in range(count)]
    ra=base.carriers(a,phi[half_cells],card)[2];rb=base.carriers(b,phi[half_cells],card)[2]
    dl=flux[half_cells-1]+ra*h/2;dr=flux[half_cells]-rb*h/2
    end_l=base.carriers(a,pl,card)[2]*h/2;end_r=base.carriers(b,pr,card)[2]*h/2
    bl,br=flux[0]-end_l,flux[-1]+end_r
    volume=sum(charges)+end_l+end_r
    integrated={'electron_number_m-2':0.0,'hole_number_m-2':0.0,'dopant_net_number_m-2':0.0}
    rows=[];max_fraction=0.0
    for i,v in enumerate(phi):
        names=['A','B'] if i==half_cells else ['A' if i<half_cells else 'B']
        for name in names:
            m=card['materials'][name];n,p,rho,_=base.carriers(m,v,card)
            weight=h/2 if i in (0,half_cells,count) else h
            integrated['electron_number_m-2']+=weight*n
            integrated['hole_number_m-2']+=weight*p
            integrated['dopant_net_number_m-2']+=weight*(m['ND_m-3']-m['NA_m-3'])
            max_fraction=max(max_fraction,n/m['Nc_m-3'],p/m['Nv_m-3'])
            rows.append({'x_m':(i-half_cells)*h,'material':name,'phi_V':v,'Ec_eV':m['Ec0_eV']-v,
                         'Ev_eV':m['Ec0_eV']-m['Eg_eV']-v,'n_m-3':n,'p_m-3':p,'rho_C_m-3':rho,
                         'quadrature_weight_m':weight})
    number_volume=base.Q*(integrated['hole_number_m-2']-integrated['electron_number_m-2']+integrated['dopant_net_number_m-2'])
    return {'half_cells':half_cells,'h_m':h,'phiL_V':pl,'phiR_V':pr,'phi0_V':phi[half_cells],
            'fermi_eV':card['fermi_eV'],'sheet_C_m-2':sheet,'sheet_derivative_C_m-2_V-1':dsheet,
            'traps':trap_rows,'scaled_residual':norm,'residual_scale_C_m-2':scale,'iterations':len(history),
            'D0minus_C_m-2':dl,'D0plus_C_m-2':dr,'sheet_jump_error_C_m-2':dr-dl-sheet,
            'boundary_D_left_C_m-2':bl,'boundary_D_right_C_m-2':br,'volume_charge_C_m-2':volume,
            'global_gauss_error_C_m-2':br-bl-volume-sheet,
            'electrode_charge_left_C_m-2':bl,'electrode_charge_right_C_m-2':-br,
            'total_including_electrodes_C_m-2':bl-br+volume+sheet,
            'integrated_numbers':integrated,'number_vs_volume_error_C_m-2':number_volume-volume,
            'max_n_over_Nc_or_p_over_Nv':max_fraction,'MB_tail_check_eta_le_minus3':max_fraction<=math.exp(-3),
            'profile':rows,'history':history,
            'edges':[{'x_mid_m':(i-half_cells+.5)*h,'D_C_m-2':flux[i],'E_V_m-1':flux[i]/eps[i]} for i in range(count)]}


def continuum_oracle(base,card,states,fixed):
    """Signed first-integral interface root on semi-infinite neutral bulks.

    No finite-volume rows or Newton matrices; compare with long finite device only.
    """
    pl=base.neutral_phi(card['materials']['A'],card);pr=base.neutral_phi(card['materials']['B'],card)
    vt=base.KB_EV*card['temperature_K']
    def flux(m,v,pb,left):
        n,p,_,_=base.carriers(m,pb,card);z=(v-pb)/vt
        excess=base.Q*vt*(n*(math.expm1(z)-z)+p*(math.expm1(-z)+z))
        sign=1 if v>pb else -1 if v<pb else 0
        return (-1 if left else 1)*sign*math.sqrt(max(0,2*base.EPS0*m['epsilon_r']*excess))
    def residual(v):
        return flux(card['materials']['B'],v,pr,False)-flux(card['materials']['A'],v,pl,True)-sheet_state(base,card,states,fixed,v)[0]
    lo,hi=pl,pr
    if not residual(lo)<=0<=residual(hi): raise ValueError('oracle root outside declared neutral-bulk bracket')
    for _ in range(100):
        mid=(lo+hi)/2
        if residual(mid)<0:lo=mid
        else:hi=mid
    v=(lo+hi)/2
    return {'phi0_V':v,'root_residual_C_m-2':residual(v),'scope':'semi-infinite equilibrium first integral; not exact finite Dirichlet'}


def summary(result): return {k:v for k,v in result.items() if k not in ('profile','edges','history')}


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run(base,card,inputs,out):
    grids=inputs['half_cells'];states=inputs['states'];fixed=inputs['fixed_sheet_C_m-2']
    validate_states(states,fixed)
    if len(grids)!=3 or any(isinstance(n,bool) or not isinstance(n,int) or not 4<=n<=5000 for n in grids): raise ValueError('exactly three finite integer grids required')
    if any(b!=2*a for a,b in zip(grids,grids[1:])): raise ValueError('grid refinement must double')
    if grids[-1]*3//2>5000: raise ValueError('extension grid exceeds finite budget')
    for key in ('density_factor','short_half_length_m'):
        if not math.isfinite(inputs[key]) or inputs[key]<=0: raise ValueError('positive finite '+key+' required')
    if not math.isfinite(inputs['fermi_change_eV']): raise ValueError('finite EF change required')
    out.mkdir(parents=True,exist_ok=True)
    meshes=[solve(base,card,states,fixed,n) for n in grids];fine=meshes[-1]
    cases={'equilibrium':fine,'zero_states':solve(base,card,[],fixed,grids[-1])}
    doubled=copy.deepcopy(states)
    for s in doubled:s['N_m-2']*=inputs['density_factor']
    cases['density_changed']=solve(base,card,doubled,fixed,grids[-1])
    frozen=copy.deepcopy(states)
    for s,r in zip(frozen,fine['traps']):s['frozen_f']=r['f']
    cases['frozen_at_solution']=solve(base,card,frozen,fixed,grids[-1])
    # An often-used one-shot approximation evaluates f on the zero-sheet profile.
    one_shot=copy.deepcopy(states)
    zero_traps=sheet_state(base,card,states,fixed,cases['zero_states']['phi0_V'])[2]
    for s,r in zip(one_shot,zero_traps):s['frozen_f']=r['f']
    cases['one_shot_fixed']=solve(base,card,one_shot,fixed,grids[-1])
    # Changing trap density while reusing the old actual sheet neglects new sites.
    old_sheet=solve(base,card,[],fine['sheet_C_m-2'],grids[-1])
    cases['old_sheet_density_change']=old_sheet
    gauge=copy.deepcopy(card);gauge['fermi_eV']+=inputs['fermi_change_eV']
    cases['EF_shift_neutral_ends']=solve(base,gauge,states,fixed,grids[-1])
    short=copy.deepcopy(card);short['half_length_m']=inputs['short_half_length_m']
    bc=(base.neutral_phi(card['materials']['A'],card),base.neutral_phi(card['materials']['B'],card))
    cases['short_clamp_before']=solve(base,short,states,fixed,grids[-1],boundaries=bc)
    changed=copy.deepcopy(short);changed['fermi_eV']+=inputs['fermi_change_eV']
    cases['short_clamp_EF_changed']=solve(base,changed,states,fixed,grids[-1],boundaries=bc)
    old_short=copy.deepcopy(states)
    for s,r in zip(old_short,cases['short_clamp_before']['traps']):s['frozen_f']=r['f']
    cases['short_clamp_frozen']=solve(base,changed,old_short,fixed,grids[-1],boundaries=bc)
    differences=[]
    for coarse,refined in zip(meshes,meshes[1:]):
        cp=[r for r in coarse['profile'] if r['x_m']!=0 or r['material']=='A'];rp=[r for r in refined['profile'] if r['x_m']!=0 or r['material']=='A']
        differences.append({'max_phi_difference_V':max(abs(r['phi_V']-rp[2*i]['phi_V']) for i,r in enumerate(cp)),
                            'phi0_difference_V':refined['phi0_V']-coarse['phi0_V']})
    base_zero=base.solve(card,fixed,grids[-1]);ref_phi=[r['phi_V'] for r in base_zero['profile']]
    zero_error=max(abs(r['phi_V']-ref_phi[i]) for i,r in enumerate(cases['zero_states']['profile']))
    freeze_error=max(abs(r['phi_V']-cases['frozen_at_solution']['profile'][i]['phi_V']) for i,r in enumerate(fine['profile']))
    gauge_error=max(abs(r['phi_V']-cases['EF_shift_neutral_ends']['profile'][i]['phi_V']-inputs['fermi_change_eV']) for i,r in enumerate(fine['profile']))
    failures={}
    prototype=states[0] if states else {'name':'domain_check','type':'acceptor','N_m-2':1.0,'Et0_eV':-0.27,'empty_over_filled_weight':1.0}
    for name,work in [('negative_N',lambda:validate_states([dict(prototype,**{'N_m-2':-1})],fixed)),
                      ('zero_weight',lambda:validate_states([dict(prototype,empty_over_filled_weight=0)],fixed)),
                      ('invalid_frozen',lambda:validate_states([dict(prototype,frozen_f=1.1)],fixed)),
                      ('zero_iteration_budget',lambda:solve(base,card,[],base.Q*1e14,grids[0],max_iterations=0))]:
        try:work()
        except (ValueError,RuntimeError) as e:failures[name]=str(e)
        else:raise AssertionError('expected failure '+name)
    for name,r in cases.items():
        if abs(r['global_gauss_error_C_m-2'])>1e-11 or abs(r['sheet_jump_error_C_m-2'])>1e-11:raise AssertionError('Gauss failed '+name)
        if abs(r['number_vs_volume_error_C_m-2'])>1e-11:raise AssertionError('charge number failed '+name)
        if not r['MB_tail_check_eta_le_minus3']:raise AssertionError('MB invalid '+name)
        if name not in ('frozen_at_solution','old_sheet_density_change','EF_shift_neutral_ends'):
            write_csv(out/(name+'-profile.csv'),r['profile'])
    write_csv(out/'equilibrium-edges.csv',fine['edges'])
    if not zero_error<1e-10 or not freeze_error<1e-10 or not gauge_error<1e-10:raise AssertionError('limiting equality failed')
    if not differences[1]['max_phi_difference_V']<differences[0]['max_phi_difference_V']:raise AssertionError('mesh trend failed')
    oracle=continuum_oracle(base,card,states,fixed)
    longer=copy.deepcopy(card);longer['half_length_m']*=1.5
    if grids[-1]*3//2 > 5000: raise ValueError('extension grid exceeds finite budget')
    extended=solve(base,longer,states,fixed,grids[-1]*3//2)
    density_curve=[]
    for factor in range(17):
        sweep=copy.deepcopy(states)
        for s in sweep:s['N_m-2']*=factor/8
        r=solve(base,card,sweep,fixed,grids[1])
        density_curve.append({'density_factor':factor/8,'total_state_N_m-2':sum(s['N_m-2'] for s in sweep),
                              'phi0_V':r['phi0_V'],'sheet_C_m-2':r['sheet_C_m-2']})
    ef_curve=[]
    for k in range(11):
        varied=copy.deepcopy(short);varied['fermi_eV']+=inputs['fermi_change_eV']*k/10
        coupled=solve(base,varied,states,fixed,grids[1],boundaries=bc)
        held=solve(base,varied,old_short,fixed,grids[1],boundaries=bc)
        ef_curve.append({'EF_eV':varied['fermi_eV'],'coupled_phi0_V':coupled['phi0_V'],
                         'frozen_phi0_V':held['phi0_V'],'coupled_sheet_C_m-2':coupled['sheet_C_m-2'],
                         'frozen_sheet_C_m-2':held['sheet_C_m-2'],'coupled_first_f':coupled['traps'][0]['f'] if coupled['traps'] else 0.0})
    write_csv(out/'density-sweep.csv',density_curve);write_csv(out/'EF-clamp-sweep.csv',ef_curve)
    charge_curve=[]
    for k in range(61):
        v=fine['phi0_V']-0.10+0.003*k
        sg,ds,trs=sheet_state(base,card,states,fixed,v)
        charge_curve.append({'phi0_V':v,'sheet_C_m-2':sg,'first_f':trs[0]['f'] if trs else 0.0,
                             'derivative_C_m-2_V-1':ds})
    write_csv(out/'occupation-sweep.csv',charge_curve)
    # Double-sided derivative and occupancy checks are useful implementation checks,
    # but independent acceptance must use an independently constructed route.
    delta=1e-6;sigma,dsigma,_=sheet_state(base,card,states,fixed,fine['phi0_V'])
    fd=(sheet_state(base,card,states,fixed,fine['phi0_V']+delta)[0]-sheet_state(base,card,states,fixed,fine['phi0_V']-delta)[0])/(2*delta)
    checks={'domain_extension_same_h_phi0_difference_V':extended['phi0_V']-fine['phi0_V'],
            'zero_states_vs_practice08_max_phi_error_V':zero_error,
            'frozen_at_solution_max_phi_error_V':freeze_error,'EF_neutral_shift_gauge_error_V':gauge_error,
            'sheet_derivative_vs_centered_relative_error':abs(fd-dsigma)/max(abs(dsigma),1e-30),
            'expected_failures':failures}
    report={'model':'finite 1D equilibrium MB bulks plus localized two-state equilibrium interface; fully ionized dopants; no dipole',
            'base_card':card,'interface_input':inputs,'cases':{k:summary(v) for k,v in cases.items()},
            'meshes':[summary(v) for v in meshes],'mesh_differences':differences,
            'density_sweep_old_sheet_phi0_V':solve(base,card,[],fine['sheet_C_m-2'],grids[1])['phi0_V'],
            'semi_infinite_oracle':oracle,'fine_minus_oracle_phi0_V':fine['phi0_V']-oracle['phi0_V'],'checks':checks}
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--base-dir',type=Path,help='practice 08 directory; default is the sibling practice directory')
    parser.add_argument('--out',type=Path,default=Path(__file__).with_name('results'))
    args=parser.parse_args();inputs=json.loads(args.input.read_text())
    base_dir=args.base_dir or (args.input.parent/inputs['base_card']).resolve().parent
    base=load_base(base_dir);card=json.loads((base_dir/'inputs.json').read_text())
    report=run(base,card,inputs,args.out)
    print(json.dumps({'cases':{k:{x:v[x] for x in ('phi0_V','sheet_C_m-2','traps')} for k,v in report['cases'].items()},
                      'checks':report['checks'],'mesh_differences':report['mesh_differences']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
