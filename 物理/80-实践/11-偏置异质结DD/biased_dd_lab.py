#!/usr/bin/env python3
"""Mixed 1D two-carrier DD/Poisson, ideal zero-resistance CQFL interface.

Source of truth. Only pure-material edges receive SG. Shared interface phi,a,b
implements a chosen infinite-transfer limit, not a general abrupt TE interface.
"""
import argparse
import copy
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
import numpy as np
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def read_json(path):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('duplicate JSON key '+key)
            out[key]=value
        return out
    def reject_constant(value):raise ValueError('nonfinite JSON constant '+value)
    return json.loads(path.read_text(),object_pairs_hook=pairs,parse_constant=reject_constant)


def exact_keys(obj,expected,label):
    if not isinstance(obj,dict) or set(obj)!=set(expected):raise ValueError('unsupported/missing keys in '+label)


def validate_overlay_schema(overlay):
    exact_keys(overlay,('description','transport','main_bias_V','half_cells','continuation_step_V','newton','teaching_low_field_scale_V_m'),'overlay')
    exact_keys(overlay['transport'],('A','B'),'transport')
    for name in ('A','B'):exact_keys(overlay['transport'][name],('mu_n_m2_Vs','mu_p_m2_Vs','tau_n_s','tau_p_s'),name+' transport')
    exact_keys(overlay['newton'],('max_iterations','max_backtracks','scaled_tolerance','max_phi_step_V','max_log_step'),'Newton')
    if not isinstance(overlay['description'],str):raise ValueError('description must be string')


def load_base(base_dir):
    path = base_dir / '08-异质结与Poisson自洽' / 'heterojunction_lab.py'
    spec = importlib.util.spec_from_file_location('equilibrium08', path)
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    card = read_json(path.with_name('inputs.json'))
    return base, card


def finite(value):
    if not isinstance(value,(int,float)) or isinstance(value,bool):return False
    try:return math.isfinite(value)
    except OverflowError:return False


def validate(base, card, overlay, half_cells, bias):
    base.validate(card)
    validate_overlay_schema(overlay)
    if not finite(bias) or abs(bias) > .10:
        raise ValueError('bias must be finite within [-.10,.10] V (declared numerical domain)')
    if isinstance(half_cells, bool) or not isinstance(half_cells, int) or not 8 <= half_cells <= 1000:
        raise ValueError('half_cells integer in [8,1000] required')
    for name in ('A', 'B'):
        for key in ('mu_n_m2_Vs', 'mu_p_m2_Vs', 'tau_n_s', 'tau_p_s'):
            if not finite(overlay['transport'][name][key]) or overlay['transport'][name][key] <= 0:
                raise ValueError('positive finite transport '+name+'/'+key+' required')
    s = overlay['newton']
    for key, hi in [('max_iterations', 80), ('max_backtracks', 24)]:
        if isinstance(s[key], bool) or not isinstance(s[key], int) or not 0 <= s[key] <= hi:
            raise ValueError('invalid Newton '+key)
    for key in ('scaled_tolerance', 'max_phi_step_V', 'max_log_step'):
        if not finite(s[key]) or s[key] <= 0:
            raise ValueError('positive finite Newton '+key+' required')
    for key in ('continuation_step_V', 'teaching_low_field_scale_V_m'):
        if not finite(overlay[key]) or overlay[key] <= 0:
            raise ValueError('positive finite '+key+' required')
    if overlay['continuation_step_V'] < .001:
        raise ValueError('continuation step below finite run budget .001 V')


def bernoulli(z):
    """B(z), d(log B)/dz. Small-z series avoids cancellation."""
    if abs(z) < 1e-4:
        val = 1-z/2+z*z/12-z**4/720+z**6/30240
        der = -.5+z/6-z**3/180+z**5/5040
        return val, der/val
    val = z/math.expm1(z)
    return val, 1/z-1/(-math.expm1(-z))


class Model:
    def __init__(self, base, card, overlay, half_cells, recombination=True):
        validate(base, card, overlay, half_cells, 0.)
        self.base, self.card, self.overlay = base, card, overlay
        self.half, self.N = half_cells, 2*half_cells+1
        self.E = self.N-1; self.h = card['half_length_m']/half_cells
        self.vt = base.KB_EV*card['temperature_K']; self.q = base.Q
        self.qscale = max(self.q*max(max(m['ND_m-3'],m['NA_m-3']) for m in card['materials'].values())*card['half_length_m'],abs(self.q*card['sheet_number_m-2']),1e-30)
        nis = [math.sqrt(m['Nc_m-3']*m['Nv_m-3'])*math.exp(-m['Eg_eV']/(2*self.vt)) for m in card['materials'].values()]
        tau = min(t['tau_n_s'] for t in overlay['transport'].values())
        self.jscale = max(self.q*max(nis)*card['half_length_m']/tau,1e-20)
        self.recombination = recombination
        self.size = 3*self.N+2*self.E
        self.eps = np.array([base.EPS0*card['materials']['A' if e<half_cells else 'B']['epsilon_r'] for e in range(self.E)])
        self.pl = base.neutral_phi(card['materials']['A'],card)
        self.pr = base.neutral_phi(card['materials']['B'],card)

    def species(self, name, phi, a, b):
        m = self.card['materials'][name]; t = self.overlay['transport'][name]
        en = (self.card['fermi_eV']-m['Ec0_eV']+phi)/self.vt
        ep = (m['Ec0_eV']-m['Eg_eV']-phi-self.card['fermi_eV'])/self.vt
        if max(abs(en),abs(ep),abs(a),abs(b),abs(en+a),abs(ep+b),abs(a+b)) > 100:
            raise ValueError('exponent outside declared [-100,100] domain')
        nb,pb = m['Nc_m-3']*math.exp(en),m['Nv_m-3']*math.exp(ep)
        n,p = nb*math.exp(a),pb*math.exp(b)
        ni = math.sqrt(m['Nc_m-3']*m['Nv_m-3'])*math.exp(-m['Eg_eV']/(2*self.vt))
        den = t['tau_p_s']*(n+ni)+t['tau_n_s']*(p+ni)
        U = ni*ni*math.expm1(a+b)/den if self.recombination else 0.0
        dU = np.array([-U*(t['tau_p_s']*n-t['tau_n_s']*p)/(self.vt*den),
                        ni*ni*math.exp(a+b)/den-U*t['tau_p_s']*n/den,
                        ni*ni*math.exp(a+b)/den-U*t['tau_n_s']*p/den]) if self.recombination else np.zeros(3)
        rho = self.q*(p-n+m['ND_m-3']-m['NA_m-3'])
        drho = self.q*np.array([-(n+p)/self.vt,-n,p])
        return nb,pb,n,p,rho,drho,U,dU

    def state(self, y, bias, jacobian=False):
        nodes = y[:3*self.N].reshape(self.N,3)
        currents = y[3*self.N:].reshape(self.E,2)*self.jscale
        residual = np.zeros(self.size); rows=[]; cols=[]; vals=[]
        def put(r,c,v):
            if jacobian and v != 0: rows.append(r); cols.append(c); vals.append(v)
        node_data=[]
        for i,(phi,a,b) in enumerate(nodes):
            names = ('A','B') if i==self.half else ('A',) if i<self.half else ('B',)
            node_data.append({name:self.species(name,phi,a,b) for name in names})
        # Dirichlet: one potential plus two related contact chemical potentials.
        for i,bc in [(0,(self.pl,0.,0.)),(self.N-1,(self.pr+bias,-bias/self.vt,bias/self.vt))]:
            for k in range(3):
                scale = self.vt if k==0 else 1.
                residual[3*i+k]=(nodes[i,k]-bc[k])/scale;put(3*i+k,3*i+k,1/scale)
        D=-self.eps*np.diff(nodes[:,0])/self.h
        cv=[]
        for i in range(1,self.N-1):
            weights = {name:self.h/(2 if i==self.half else 1) for name in node_data[i]}
            charge=sum(weights[k]*v[4] for k,v in node_data[i].items())
            Ucv=sum(weights[k]*v[6] for k,v in node_data[i].items())
            dcharge=sum((weights[k]*v[5] for k,v in node_data[i].items()),np.zeros(3))
            dUcv=sum((weights[k]*v[7] for k,v in node_data[i].items()),np.zeros(3))
            sheet=self.q*self.card['sheet_number_m-2'] if i==self.half else 0.
            r=3*i; residual[r]=(D[i]-D[i-1]-charge-sheet)/self.qscale
            residual[r+1]=(currents[i,0]-currents[i-1,0]-self.q*Ucv)/self.jscale
            residual[r+2]=(currents[i,1]-currents[i-1,1]+self.q*Ucv)/self.jscale
            for k in range(3):
                put(r,3*i+k,-dcharge[k]/self.qscale)
                put(r+1,3*i+k,-self.q*dUcv[k]/self.jscale)
                put(r+2,3*i+k,self.q*dUcv[k]/self.jscale)
            put(r,3*i,(self.eps[i]+self.eps[i-1])/self.h/self.qscale)
            put(r,3*(i-1),-self.eps[i-1]/self.h/self.qscale)
            put(r,3*(i+1),-self.eps[i]/self.h/self.qscale)
            for k in range(2):
                put(r+1+k,3*self.N+2*i+k,1.)
                put(r+1+k,3*self.N+2*(i-1)+k,-1.)
            cv.append((charge,Ucv))
        coeff=[]
        for e in range(self.E):
            name='A' if e<self.half else 'B'; t=self.overlay['transport'][name]
            z=(nodes[e+1,0]-nodes[e,0])/self.vt
            bm,lm=bernoulli(-z);bp,lp=bernoulli(z)
            nb,pb=node_data[e][name][:2]
            cn=self.q*t['mu_n_m2_Vs']*self.vt/self.h*nb*bm
            cp=self.q*t['mu_p_m2_Vs']*self.vt/self.h*pb*bp
            coeff.append((cn,cp))
            dn=np.array([(1+lm)/self.vt,-lm/self.vt])
            dp=np.array([(-1-lp)/self.vt,lp/self.vt])
            for k,C,dlog in [(0,cn,dn),(1,cp,dp)]:
                colk=k+1; L=nodes[e,colk]; delta=nodes[e+1,colk]-L
                ratio=currents[e,k]/(C*math.exp(L));sgn=-1 if k==0 else 1
                row=3*self.N+2*e+k
                residual[row]=math.expm1(delta)+sgn*ratio
                put(row,3*(e+1)+colk,math.exp(delta))
                put(row,3*e+colk,-math.exp(delta)-sgn*ratio)
                put(row,3*e,-sgn*ratio*dlog[0]);put(row,3*(e+1),-sgn*ratio*dlog[1])
                put(row,3*self.N+2*e+k,sgn*self.jscale/(C*math.exp(L)))
        if not np.all(np.isfinite(residual)):
            raise ArithmeticError('nonfinite mixed residual')
        jac=coo_matrix((vals,(rows,cols)),shape=(self.size,self.size)).tocsc() if jacobian else None
        return residual,jac,(nodes,currents,D,node_data,cv,coeff)

    def equilibrium(self):
        old=self.base.solve(self.card,self.q*self.card['sheet_number_m-2'],self.half)
        phi=[r['phi_V'] for r in old['profile'] if not (r['material']=='B' and r['x_m']==0)]
        y=np.zeros(self.size); y[:3*self.N:3]=phi
        return y,old

    def newton(self, y, bias, max_iterations=None):
        settings=self.overlay['newton'];budget=settings['max_iterations'] if max_iterations is None else max_iterations
        if isinstance(budget,bool) or not isinstance(budget,int) or not 0<=budget<=80:raise ValueError('Newton override integer in [0,80] required')
        history=[]
        for it in range(budget+1):
            residual,jac,_=self.state(y,bias,True);norm=float(np.max(np.abs(residual)))
            if norm<settings['scaled_tolerance']:return y,history,norm
            if it==budget:raise RuntimeError('coupled Newton iteration budget exhausted')
            step=spsolve(jac,-residual)
            if not np.all(np.isfinite(step)):raise ArithmeticError('nonfinite Newton step')
            dn=step[:3*self.N].reshape(self.N,3)
            alpha=min(1.,settings['max_phi_step_V']/max(np.max(np.abs(dn[:,0])),1e-300),settings['max_log_step']/max(np.max(np.abs(dn[:,1:])),1e-300))
            for back in range(settings['max_backtracks']+1):
                trial=y+alpha*step
                try:trial_norm=float(np.max(np.abs(self.state(trial,bias)[0])))
                except (ValueError,ArithmeticError,OverflowError):trial_norm=math.inf
                if trial_norm <= (1-1e-4*alpha)*norm:break
                alpha*=.5
            else:raise RuntimeError('coupled Newton line search exhausted')
            history.append({'iteration':it,'scaled_residual_before':norm,'scaled_residual_after':trial_norm,'alpha':alpha,'backtracks':back})
            y=trial
        raise RuntimeError('unreachable Newton exit')

    def solve(self,bias,max_iterations=None):
        validate(self.base,self.card,self.overlay,self.half,bias)
        y,old=self.equilibrium();history=[]
        count=max(1,math.ceil(abs(bias)/self.overlay['continuation_step_V']))
        previous=0.
        for V in np.linspace(0,bias,count+1)[1:]:
            ramp=np.linspace(0,1,self.N);delta=float(V)-previous
            y[:3*self.N:3]+=delta*ramp;y[1:3*self.N:3]-=delta/self.vt*ramp;y[2:3*self.N:3]+=delta/self.vt*ramp
            y,steps,norm=self.newton(y,float(V),max_iterations)
            history.append({'bias_V':float(V),'newton':steps});previous=float(V)
        return self.report(y,bias,history,old)

    def report(self,y,bias,history,old):
        residual,_,data=self.state(y,bias);nodes,J,D,nd,cv,coeff=data
        profiles=[];mb=0.;integrals={'A':0.,'B':0.}
        volume=0.
        for i,(phi,a,b) in enumerate(nodes):
            w=self.h/2 if i in (0,self.N-1,self.half) else self.h
            for name,v in nd[i].items():
                m=self.card['materials'][name];n,p,rho,U=v[2],v[3],v[4],v[6]
                integrals[name]+=U*w;volume+=rho*w
                mb=max(mb,n/m['Nc_m-3'],p/m['Nv_m-3'])
                profiles.append({'x_m':(i-self.half)*self.h,'material':name,'phi_V':float(phi),'Fn_eV':self.card['fermi_eV']+self.vt*float(a),'Fp_eV':self.card['fermi_eV']-self.vt*float(b),'Ec_eV':m['Ec0_eV']-float(phi),'Ev_eV':m['Ec0_eV']-m['Eg_eV']-float(phi),'n_m-3':n,'p_m-3':p,'rho_C_m-3':rho,'U_m-3_s-1':U,'quadrature_weight_m':w})
        ua,ub=nd[self.half]['A'][6],nd[self.half]['B'][6]
        jminus=J[self.half-1]+self.q*ua*self.h/2*np.array([1.,-1.])
        jplus=J[self.half]-self.q*ub*self.h/2*np.array([1.,-1.])
        jl=J[0]-self.q*nd[0]['A'][6]*self.h/2*np.array([1.,-1.])
        jr=J[-1]+self.q*nd[-1]['B'][6]*self.h/2*np.array([1.,-1.])
        dl=D[self.half-1]+nd[self.half]['A'][4]*self.h/2
        dr=D[self.half]-nd[self.half]['B'][4]*self.h/2
        dleft=D[0]-nd[0]['A'][4]*self.h/2;dright=D[-1]+nd[-1]['B'][4]*self.h/2
        balances={}
        for name,lo,hi in [('A',jl,jminus),('B',jplus,jr),('all',jl,jr)]:
            integ=integrals[name] if name!='all' else sum(integrals.values())
            balances[name]={'U_integral_m-2_s-1':integ,'electron_error_A_m-2':float(hi[0]-lo[0]-self.q*integ),'hole_error_A_m-2':float(hi[1]-lo[1]+self.q*integ)}
        interface=nd[self.half];ma=self.card['materials']['A'];mbmat=self.card['materials']['B']
        edge_rows=[{'x_mid_m':(e+.5-self.half)*self.h,'material':'A' if e<self.half else 'B','D_C_m-2':float(D[e]),'E_V_m-1':float(D[e]/self.eps[e]),'Jn_A_m-2':float(J[e,0]),'Jp_A_m-2':float(J[e,1]),'Jtotal_A_m-2':float(sum(J[e]))} for e in range(self.E)]
        maxfield=max(abs(v['E_V_m-1']) for v in edge_rows)
        summary={'bias_V':bias,'half_cells':self.half,'h_m':self.h,'scaled_residual':float(np.max(np.abs(residual))),'phi0_V':float(nodes[self.half,0]),'contact_J_left_A_m-2':jl.tolist(),'contact_J_right_A_m-2':jr.tolist(),'interface_J_A_minus_A_m-2':jminus.tolist(),'interface_J_B_plus_A_m-2':jplus.tolist(),'interface_J_jump_A_m-2':(jplus-jminus).tolist(),'edge_total_current_spread_A_m-2':float(np.ptp(np.sum(J,axis=1))),'contact_total_current_error_A_m-2':float(sum(jr)-sum(jl)),'SRH_balances':balances,'max_n_over_Nc_or_p_over_Nv':mb,'MB_tail_eta_le_minus3':mb<=math.exp(-3),'min_carrier_m-3':min(min(r['n_m-3'],r['p_m-3']) for r in profiles),'max_abs_field_V_m':maxfield,'field_over_teaching_scale':maxfield/self.overlay['teaching_low_field_scale_V_m'],'teaching_field_bound_pass':maxfield<self.overlay['teaching_low_field_scale_V_m'],'D0minus_C_m-2':float(dl),'D0plus_C_m-2':float(dr),'sheet_jump_error_C_m-2':float(dr-dl-self.q*self.card['sheet_number_m-2']),'global_Gauss_error_C_m-2':float(dright-dleft-volume-self.q*self.card['sheet_number_m-2']),'nB_over_nA':interface['B'][2]/interface['A'][2],'pB_over_pA':interface['B'][3]/interface['A'][3],'equilibrium08_phi_error_V':float(np.max(np.abs(nodes[:,0]-np.array([r['phi_V'] for r in old['profile'] if not(r['material']=='B' and r['x_m']==0)])))) if bias==0 else None,'current_scale_A_m-2':self.jscale,'poisson_scale_C_m-2':self.qscale}
        return {'summary':summary,'profile':profiles,'edges':edge_rows,'history':history,'state':y}


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'));p.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parent.parent);p.add_argument('--out',type=Path,required=True);p.add_argument('--prototype',action='store_true')
    args=p.parse_args();base,card=load_base(args.base_dir);overlay=read_json(args.input)
    if args.out.exists() and any(args.out.iterdir()):raise FileExistsError('output must be a new or empty directory')
    validate_overlay_schema(overlay)
    grids=overlay['half_cells']
    if len(grids)!=3 or any(isinstance(n,bool) or not isinstance(n,int) or not 8<=n<=1000 for n in grids) or any(b<=a or b%a for a,b in zip(grids,grids[1:])):raise ValueError('three increasing integer-ratio grids in [8,1000] required')
    validate(base,card,overlay,grids[0],overlay['main_bias_V'])
    cases={};full={};pending={}
    specs=[('equilibrium',0.,60),('forward',overlay['main_bias_V'],60)] if args.prototype else [('equilibrium',0.,overlay['half_cells'][-1])]+[(f'forward_n{n}',overlay['main_bias_V'],n) for n in overlay['half_cells']]+[('reverse',.02,overlay['half_cells'][-1]),('half_bias',-.01,overlay['half_cells'][-1])]
    for name,V,n in specs:
        r=Model(base,card,overlay,n).solve(V);full[name]=r;cases[name]=r['summary'];pending[name+'-profile.csv']=r['profile'];pending[name+'-edges.csv']=r['edges']
    changes={}
    if not args.prototype:
        band=copy.deepcopy(card);band['materials']['B']['Ec0_eV']+=.025
        mob=copy.deepcopy(overlay);mob['transport']['A']['mu_n_m2_Vs']*=.5
        for name,c,o,rec in [('band_step_plus_0.025eV',band,overlay,True),('A_electron_mobility_half',card,mob,True),('no_recombination',card,overlay,False)]:
            r=Model(base,c,o,overlay['half_cells'][-1],rec).solve(overlay['main_bias_V']);full[name]=r;cases[name]=r['summary'];pending[name+'-profile.csv']=r['profile'];pending[name+'-edges.csv']=r['edges']
        diffs=[]
        for n,m in zip(overlay['half_cells'],overlay['half_cells'][1:]):
            cr=full[f'forward_n{n}'];fr=full[f'forward_n{m}'];ratio=m//n
            cnode=cr['state'][:3*(2*n+1)].reshape(-1,3);fnode=fr['state'][:3*(2*m+1)].reshape(-1,3)[::ratio]
            diffs.append({'coarse_half_cells':n,'fine_half_cells':m,'max_phi_difference_V':float(np.max(np.abs(cnode[:,0]-fnode[:,0]))),'max_Fn_difference_eV':float(np.max(np.abs(cnode[:,1]-fnode[:,1])))*base.KB_EV*card['temperature_K'],'max_Fp_difference_eV':float(np.max(np.abs(cnode[:,2]-fnode[:,2])))*base.KB_EV*card['temperature_K'],'total_current_difference_A_m-2':sum(fr['summary']['contact_J_left_A_m-2'])-sum(cr['summary']['contact_J_left_A_m-2'])})
        changes['mesh_differences']=diffs
        failures={}
        bad=copy.deepcopy(overlay);bad['transport']['A']['mu_n_m2_Vs']=-1
        work=[('zero_newton_budget',lambda:Model(base,card,overlay,60).solve(-.02,max_iterations=0)),('negative_mobility',lambda:Model(base,card,bad,60).solve(-.02)),('out_of_range_bias',lambda:Model(base,card,overlay,60).solve(.2)),('fractional_grid',lambda:validate(base,card,overlay,12.5,.01))]
        for name,f in work:
            try:f()
            except (ValueError,RuntimeError) as e:failures[name]=str(e)
            else:raise AssertionError('expected rejection '+name)
        changes['expected_failures']=failures
        intrinsic=copy.deepcopy(card)
        for m in intrinsic['materials'].values():
            m.update(intrinsic['materials']['A']);m['ND_m-3']=m['NA_m-3']=0.
        intrinsic['sheet_number_m-2']=0.
        exact=Model(base,intrinsic,overlay,60).solve(0.)
        expected_phi=base.neutral_phi(intrinsic['materials']['A'],intrinsic)
        changes['exact_intrinsic']={'max_phi_error_V':max(abs(r['phi_V']-expected_phi) for r in exact['profile']),'max_current_A_m-2':max(abs(r[k]) for r in exact['edges'] for k in ('Jn_A_m-2','Jp_A_m-2'))}
        for name,summ in cases.items():
            if not summ['MB_tail_eta_le_minus3'] or summ['min_carrier_m-3']<=0:raise AssertionError('physical statistics check failed '+name)
            if summ['edge_total_current_spread_A_m-2']>1e-11 or abs(summ['sheet_jump_error_C_m-2'])>1e-11:raise AssertionError('balance failed '+name)
            if any(abs(v[k])>1e-11 for v in summ['SRH_balances'].values() for k in ('electron_error_A_m-2','hole_error_A_m-2')):raise AssertionError('SRH balance failed '+name)
        if changes['exact_intrinsic']['max_phi_error_V']>1e-12 or changes['exact_intrinsic']['max_current_A_m-2']!=0.:raise AssertionError('intrinsic exact limit failed')
    report={'model':'steady 1D two-carrier MB DD-Poisson, synthetic SRH, ideal zero interface resistance CQFL, fixed sheet, Ohmic Dirichlet','base_input':card,'transport_input':overlay,'cases':cases,'checks':changes,'histories':{name:r['history'] for name,r in full.items()},'environment':{'numpy':np.__version__,'scipy':scipy.__version__}}
    # All cases must finish before publishing any numeric result.
    if args.out.exists() and any(args.out.iterdir()):raise FileExistsError('output became nonempty during calculation')
    args.out.mkdir(parents=True,exist_ok=True)
    for filename,rows in pending.items():write_csv(args.out/filename,rows)
    (args.out/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'cases':{k:{s:v[s] for s in ('bias_V','phi0_V','contact_J_left_A_m-2','scaled_residual','edge_total_current_spread_A_m-2','MB_tail_eta_le_minus3')} for k,v in cases.items()},'checks':changes},indent=2,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,ArithmeticError,FileExistsError,KeyError,TypeError,OSError) as exc:
        print('FAILED: '+str(exc),file=sys.stderr);raise SystemExit(1)
