---
type: code
stage: 1
aliases: []
sources: []
prerequisites:
  - "[[控制论/80-实践/04-辨识与MRAC/README]]"
---

# 辨识与MRAC代码镜像

真源为相邻目录的 [identification_mrac_lab.py](../identification_mrac_lab.py)。本镜像逐字保留完整代码；运行、条件与结果见 [[控制论/80-实践/04-辨识与MRAC/README|实践入口]]。

<!-- code-sync: ../identification_mrac_lab.py -->

```python
#!/usr/bin/env python3
"""Scalar identification, continuous ideal MRAC, leakage, and a digital local test.
Standard library only. Time tau is normalized by 10 s; y by 1 K; v by 1 W.
The simulator knows a=-1 for independent checks; the adaptive law does not.
No hardware output. All runs and active arithmetic are serial.
"""
import argparse
import csv
from fractions import Fraction as F
import html
import json
import math
from pathlib import Path
import random
import resource
import sys

TRUE_A, AM, GAMMA = -1.0, 1.0, 2.0
CENTER, PARAM_RADIUS, DISTURBANCE_BOUND = -0.8, 0.25, 0.1
SIGMA = 0.2


def solve2(matrix, vector):
    determinant = matrix[0][0]*matrix[1][1]-matrix[0][1]*matrix[1][0]
    assert determinant != 0
    return [(vector[0]*matrix[1][1]-matrix[0][1]*vector[1])/determinant,
            (matrix[0][0]*vector[1]-vector[0]*matrix[1][0])/determinant]


def exact_identification():
    alpha,beta,kappa=F(9,10),F(1,10),F(2)
    closed=alpha-beta*kappa
    x=F(1); rank_one=[]
    for _ in range(4):
        rank_one.append([x,-kappa*x,closed*x]);x*=closed
    assert F(23,25)-kappa*F(11,100)==closed
    phi=[[F(0),F(1)],[F(1,10),F(-1,5)]]
    target=[F(1,10),F(7,100)]
    recovered=solve2(phi,target)
    assert recovered == [alpha,beta]
    ref_var,noise_var=F(1),F(1,100)
    state_var=(beta**2*ref_var+(beta*kappa)**2*noise_var)/(1-closed**2)
    measured_var=state_var+noise_var
    moment=[[measured_var,-kappa*measured_var],[-kappa*measured_var,kappa*kappa*measured_var+ref_var]]
    error_moment=[-alpha*noise_var,kappa*alpha*noise_var]
    bias=solve2(moment,error_moment)
    ols=[alpha+bias[0],beta+bias[1]]
    instrument=[[beta,-kappa*beta],[F(0),ref_var]]
    instrument_target=[closed*beta,beta*ref_var]
    iv=solve2(instrument,instrument_target)
    assert ols == [F(468,775),beta] and iv==[alpha,beta]
    designed_gain=(ols[0]-F(4,5))/ols[1]
    true_new_pole=alpha-beta*designed_gain
    assert designed_gain==F(-304,155) and true_new_pole==F(1699,1550)>1
    return {'alpha':str(alpha),'beta_K_per_W':str(beta),'feedback_W_per_K':str(kappa),
            'closed_pole':str(closed),'rank_one_records':[[str(v) for v in row] for row in rank_one],
            'two_row_phi':[[str(v) for v in row] for row in phi],
            'two_row_target':[str(v) for v in target], 'recovered':[str(v) for v in recovered],
            'stationary_state_variance_K2':str(state_var),'stationary_y_variance_K2':str(measured_var),
            'regressor_moment':[[str(v) for v in row] for row in moment],
            'regressor_error_moment':[str(v) for v in error_moment],
            'population_ols':[str(v) for v in ols], 'population_iv':[str(v) for v in iv],
            'instrument_moment':[[str(v) for v in row] for row in instrument],
            'instrument_target':[str(v) for v in instrument_target],
            'estimated_pole_target':str(F(4,5)), 'certainty_equivalent_gain_W_per_K':str(designed_gain),
            'actual_new_closed_pole':str(true_new_pole)}


def finite_identification():
    rng=random.Random(24612011)
    alpha,beta,kappa=0.9,0.1,2.0
    normal=[[0.0,0.0],[0.0,0.0]]; cross=[[0.0,0.0],[0.0,0.0]]
    target=[0.0,0.0]; instrument_target=[0.0,0.0]; corr=[0.0,0.0]
    x=0.0; noise=rng.choice((-0.1,0.1)); previous_ref=0.0
    data=[]; estimates=[]
    for index in range(12200):
        reference=rng.choice((-1.0,1.0))
        y=x+noise
        u=-kappa*y+reference
        next_x=alpha*x+beta*u
        next_noise=rng.choice((-0.1,0.1))
        next_y=next_x+next_noise
        if index>=200:
            phi=[y,u]; instrument=[previous_ref,reference]
            residual=next_noise-alpha*noise
            for i in range(2):
                target[i]+=phi[i]*next_y
                instrument_target[i]+=instrument[i]*next_y
                corr[i]+=phi[i]*residual
                for j in range(2):
                    normal[i][j]+=phi[i]*phi[j]
                    cross[i][j]+=instrument[i]*phi[j]
            count=index-199
            data.append([index, x, y, u, reference, previous_ref, next_y, noise, next_noise])
            if count%500==0:
                ols=solve2(normal,target);iv=solve2(cross,instrument_target)
                estimates.append([count,*ols,*iv])
        x,noise,previous_ref=next_x,next_noise,reference
    ols=solve2(normal,target);iv=solve2(cross,instrument_target)
    assert abs(ols[0]-468/775)<0.04 and abs(ols[1]-0.1)<0.015
    assert abs(iv[0]-0.9)<0.05 and abs(iv[1]-0.1)<0.015
    return {'seed':24612011,'burn_steps':200,'samples':12000,'OLS':ols,'IV':iv,
            'empirical_regressor_error_moment':[v/12000 for v in corr]},data,estimates


def rhs(state, reference, disturbance, sigma):
    y,yr,ahat,integral=state
    error=y-yr
    control=-(ahat+AM)*y+reference
    return [TRUE_A*y+control+disturbance, -AM*yr+reference,
            GAMMA*error*y-sigma*(ahat-CENTER), error*error]


def rk4_step(state,h,reference,disturbance,sigma):
    k1=rhs(state,reference,disturbance,sigma)
    k2=rhs([x+h*v/2 for x,v in zip(state,k1)],reference,disturbance,sigma)
    k3=rhs([x+h*v/2 for x,v in zip(state,k2)],reference,disturbance,sigma)
    k4=rhs([x+h*v for x,v in zip(state,k3)],reference,disturbance,sigma)
    return [x+h*(v1+2*v2+2*v3+v4)/6 for x,v1,v2,v3,v4 in zip(state,k1,k2,k3,k4)]


def storage(state):
    y,yr,ahat,_=state
    return (y-yr)**2/2+(ahat-TRUE_A)**2/(2*GAMMA)


def simulate(name,horizon,h,reference=1.0,disturbance=0.0,sigma=0.0,
             initial_y=0.0,initial_yr=0.0,initial_ahat=0.5):
    steps=round(horizon/h);assert abs(steps*h-horizon)<1e-9
    state=[initial_y,initial_yr,initial_ahat,0.0]
    initial_storage=storage(state)
    invariant0=initial_y**2/2+(initial_ahat-TRUE_A+AM)**2/(2*GAMMA)
    defects=[]; invariant_defect=0.0; bound_margin=math.inf
    max_control=0.0; max_error=0.0; traces=[]
    stride=round(0.1/h);assert abs(stride*h-0.1)<1e-12
    decay=min(AM,sigma) if sigma else None
    forcing=DISTURBANCE_BOUND**2/(2*AM)+sigma*PARAM_RADIUS**2/(2*GAMMA)
    for index in range(steps+1):
        tau=index*h;y,yr,ahat,integral=state;error=y-yr
        v=-(ahat+AM)*y+reference
        value=storage(state)
        max_control=max(max_control,abs(v));max_error=max(max_error,abs(error))
        if not sigma and not disturbance:
            defects.append(abs(value+AM*integral-initial_storage))
        if reference==0 and initial_yr==0 and not disturbance and not sigma:
            invariant=y*y/2+(ahat-TRUE_A+AM)**2/(2*GAMMA)
            invariant_defect=max(invariant_defect,abs(invariant-invariant0))
        envelope=math.nan
        if sigma:
            envelope=math.exp(-decay*tau)*initial_storage+forcing/decay*(1-math.exp(-decay*tau))
            bound_margin=min(bound_margin,envelope-value)
            assert value<=envelope+1e-8
        if index%stride==0 or index==steps:
            traces.append([tau*10,y,yr,error,ahat,v,value,envelope])
        if index<steps:state=rk4_step(state,h,reference,disturbance,sigma)
    reference_exact=reference/AM+(initial_yr-reference/AM)*math.exp(-AM*horizon)
    assert abs(state[1]-reference_exact)<2e-8
    return {'name':name,'horizon_tau':horizon,'horizon_s':10*horizon,'step_tau':h,'steps':steps,
            'reference':reference,'disturbance':disturbance,'sigma':sigma,
            'initial_y':initial_y,'initial_yr':initial_yr,'initial_ahat':initial_ahat,
            'final_y':state[0],'final_yr':state[1],'final_error':state[0]-state[1],
            'final_ahat':state[2],'max_abs_control_W':max_control,'max_abs_error_K':max_error,
            'energy_balance_max_defect':max(defects) if defects else None,
            'zero_reference_invariant_max_defect':invariant_defect,
            'minimum_comparison_margin':bound_margin if sigma else None},traces


def digital_local(delta,steps=50):
    """Sample -> old parameter control -> hold plant -> explicit parameter update.
    Reference is exactly propagated; y_r(0)=1, r=1, y(0)=1.0001, a_hat(0)=-1.
    """
    y,yr,ahat=1.0001,1.0,-1.0
    exp_a=math.exp(TRUE_A*delta)
    hold=(exp_a-1)/TRUE_A
    matrix=[[1-AM*hold,-hold],[delta*GAMMA,1.0]]
    trace=matrix[0][0]+matrix[1][1]
    determinant=matrix[0][0]*matrix[1][1]-matrix[0][1]*matrix[1][0]
    assert trace*trace-4*determinant<0
    radius=math.sqrt(determinant)
    records=[]
    for index in range(steps+1):
        error=y-yr;theta=ahat-TRUE_A
        records.append([index,index*delta*10,error,theta])
        if index==steps:break
        old_control=-(ahat+AM)*y+1.0
        next_ahat=ahat+delta*GAMMA*error*y
        y=exp_a*y+hold*old_control
        yr=math.exp(-AM*delta)*yr+(1-math.exp(-AM*delta))/AM
        ahat=next_ahat
    def perturbation_map(e,theta):
        value=1+e;parameter=TRUE_A+theta
        u=-(parameter+AM)*value+1
        return [exp_a*value+hold*u-1,theta+delta*GAMMA*e*value]
    eps=1e-6
    derivative=[[0.0,0.0],[0.0,0.0]]
    for j in range(2):
        plus=[0.0,0.0];minus=[0.0,0.0];plus[j]=eps;minus[j]=-eps
        fp,fm=perturbation_map(*plus),perturbation_map(*minus)
        for i in range(2):derivative[i][j]=(fp[i]-fm[i])/(2*eps)
    assert max(abs(derivative[i][j]-matrix[i][j]) for i in range(2) for j in range(2))<1e-9
    return {'delta_tau':delta,'sample_period_s':delta*10,'linearization':matrix,
            'determinant':determinant,'local_complex_eigenvalue_radius':radius,
            'first_step_error':records[1][2],'first_step_parameter_error':records[1][3],
            'last_error':records[-1][2],'last_parameter_error':records[-1][3],
            'linearization_centered_difference_max_error':max(abs(derivative[i][j]-matrix[i][j]) for i in range(2) for j in range(2))},records


def plot(path,title,panels):
    width,height=960,70+250*len(panels)
    pieces=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#fafafa"/>',
            f'<text x="65" y="28" font-family="sans-serif" font-size="18">{html.escape(title)}</text>']
    for index,(label,bounds,curves,lines) in enumerate(panels):
        top,h=65+250*index,165
        xmin,xmax,ymin,ymax=bounds
        def point(x,y):return (80+800*(x-xmin)/(xmax-xmin),top+h-h*(y-ymin)/(ymax-ymin))
        pieces += [f'<text x="80" y="{top-12}" font-family="sans-serif" font-size="13">{html.escape(label)}</text>',
                   f'<defs><clipPath id="panel{index}"><rect x="80" y="{top}" width="800" height="{h}"/></clipPath></defs>',
                   f'<rect x="80" y="{top}" width="800" height="{h}" fill="white" stroke="#b4b4b4"/>']
        for value in (ymin,0,ymax):
            if not ymin<=value<=ymax:continue
            _,yp=point(xmin,value)
            pieces += [f'<line x1="80" x2="880" y1="{yp:.3f}" y2="{yp:.3f}" stroke="#dedede"/>',
                       f'<text x="23" y="{yp+4:.3f}" font-family="sans-serif" font-size="12">{value:.3g}</text>']
        for value in lines:
            _,yp=point(xmin,value)
            pieces += [f'<line x1="80" x2="880" y1="{yp:.3f}" y2="{yp:.3f}" stroke="#777" stroke-dasharray="5 4"/>']
        for j,(name,color,rows) in enumerate(curves):
            dash=('','7 5','2 4')[j%3]
            style=f' stroke-dasharray="{dash}"' if dash else ''
            pts=' '.join(f'{xp:.3f},{yp:.3f}' for xp,yp in (point(x,y) for x,y in rows))
            pieces += [f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"{style} clip-path="url(#panel{index})"/>',
                       f'<line x1="{80+270*j}" x2="{103+270*j}" y1="{top+h+20}" y2="{top+h+20}" stroke="{color}" stroke-width="2"{style}/>',
                       f'<text x="{110+270*j}" y="{top+h+24}" font-family="sans-serif" font-size="12" fill="{color}">{html.escape(name)}</text>']
        pieces += [f'<text x="80" y="{top+h+44}" font-family="sans-serif" font-size="12">{xmin:g}</text>',
                   f'<text x="855" y="{top+h+44}" font-family="sans-serif" font-size="12">{xmax:g}</text>']
    pieces.append('</svg>');path.write_text('\n'.join(pieces)+'\n',encoding='utf-8')


def write_csv(path,header,rows):
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle);writer.writerow(header)
        writer.writerows([[str(v) if isinstance(v,(str,int)) else ('' if math.isnan(v) else f'{v:.12g}') for v in row] for row in rows])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent/'assets')
    args=parser.parse_args();assets=args.output_dir;assets.mkdir(parents=True,exist_ok=True)
    exact=exact_identification();finite,data,estimates=finite_identification()
    cases=[('ideal_reference',30,{'reference':1}),
           ('zero_exact',30,{'reference':0,'initial_y':0,'initial_yr':0}),
           ('zero_transient',30,{'reference':0,'initial_y':0.6}),
           ('bad_initial_gain',30,{'reference':1,'initial_y':0.2,'initial_ahat':-3}),
           ('sigma_reference_no_disturbance',50,{'reference':1,'sigma':SIGMA,'initial_ahat':CENTER}),
           ('sigma_reference_with_disturbance',50,{'reference':1,'disturbance':0.1,'sigma':SIGMA,'initial_ahat':CENTER}),
           ('drift_zero_reference',300,{'reference':0,'disturbance':0.1,'initial_ahat':CENTER}),
           ('sigma_zero_reference',300,{'reference':0,'disturbance':0.1,'sigma':SIGMA,'initial_ahat':CENTER})]
    observed=[]; all_traces={}; refinement=[]
    for name,horizon,parameters in cases:
        runs=[]; traces=[]
        for step in (0.02,0.01,0.005):
            result,trace=simulate(name,horizon,step,**parameters)
            runs.append(result);traces.append(trace)
        comparison=[]
        for left,right in [(0,1),(1,2)]:
            comparison.append(max(abs(row1[j]-row2[j]) for row1,row2 in zip(traces[left],traces[right]) for j in (1,2,4)))
        assert comparison[1]<1e-7
        if comparison[0]>1e-10:assert comparison[1]<comparison[0]/5
        refinement.append({'case':name,'steps_tau':[0.02,0.01,0.005],'max_y_yr_ahat_difference_on_0_1_tau_grid':comparison,
                           'energy_balance_defects':[item['energy_balance_max_defect'] for item in runs]})
        observed.append(runs[-1]);all_traces[name]=traces[-1]
    zero=next(item for item in observed if item['name']=='zero_exact')
    assert zero['final_error']==0 and zero['final_ahat']==0.5
    transient=next(item for item in observed if item['name']=='zero_transient')
    transient_oracle=TRUE_A-AM+math.sqrt((0.5-TRUE_A+AM)**2+GAMMA*0.6**2)
    assert abs(transient['final_ahat']-transient_oracle)<1e-9
    assert transient['zero_reference_invariant_max_defect']<1e-9
    ideal=next(item for item in observed if item['name']=='ideal_reference')
    assert abs(ideal['final_error'])<2e-6 and abs(ideal['final_ahat']-TRUE_A)<2e-6
    decay=min(AM,SIGMA)
    forcing=DISTURBANCE_BOUND**2/(2*AM)+SIGMA*PARAM_RADIUS**2/(2*GAMMA)
    final_storage_bound=forcing/decay
    digital_results=[];digital_rows=[]
    for delta in (0.1,0.6):
        result,rows=digital_local(delta)
        digital_results.append(result);digital_rows.extend([[delta,*row] for row in rows])
    assert digital_results[0]['local_complex_eigenvalue_radius']<1
    assert digital_results[1]['local_complex_eigenvalue_radius']>1
    # Independently solve the steady-state leakage equation near y=1.
    equilibrium=[]
    for disturbance in (0.0,0.1):
        lo,hi=0.8,1.1
        def steady(y):
            theta=GAMMA/SIGMA*(y-1)*y+CENTER-TRUE_A
            return -(y-1)-theta*y+disturbance
        assert steady(lo)>0 and steady(hi)<0
        for _ in range(80):
            mid=(lo+hi)/2
            if steady(mid)>0:lo=mid
            else:hi=mid
        y=(lo+hi)/2
        ahat=CENTER+GAMMA/SIGMA*(y-1)*y
        equilibrium.append({'disturbance':disturbance,'y':y,'tracking_error':y-1,'ahat':ahat})
        result=next(item for item in observed if item['name']==('sigma_reference_no_disturbance' if disturbance==0 else 'sigma_reference_with_disturbance'))
        assert abs(result['final_y']-y)<1e-8 and abs(result['final_ahat']-ahat)<1e-8
    summary={'normalization':{'time_s':10,'temperature_K':1,'power_W':1,'true_a':TRUE_A,'a_m':AM,'gamma':GAMMA},
             'exact_identification':exact,'finite_identification':finite,
             'continuous_cases':observed,'refinement':refinement,
             'zero_transient_final_parameter_oracle':transient_oracle,
             'sigma_certificate':{'center':CENTER,'parameter_radius':PARAM_RADIUS,'disturbance_bound':DISTURBANCE_BOUND,
                                  'sigma':SIGMA,'mu':decay,'C':forcing,'V_ultimate_bound':final_storage_bound,
                                  'tracking_error_limsup_bound_K':math.sqrt(2*final_storage_bound),
                                  'parameter_error_limsup_bound':math.sqrt(2*GAMMA*final_storage_bound)},
             'sigma_steady_state_oracle':equilibrium,'digital_local_cases':digital_results}
    (assets/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_csv(assets/'identification.csv',['sample_k','true_x_K','measured_y_K','input_u_W','reference_r_W','previous_reference_W','next_measured_y_K','noise_K','next_noise_K'],data)
    write_csv(assets/'estimates.csv',['samples','OLS_alpha','OLS_beta_K_per_W','IV_alpha','IV_beta_K_per_W'],estimates)
    rows=[]
    for name,trace in all_traces.items():rows.extend([[name,*row] for row in trace])
    write_csv(assets/'mrac.csv',['case','time_s','y_K','reference_model_y_K','tracking_error_K','ahat_dimensionless','control_W','V_dimensionless','comparison_envelope'],rows)
    write_csv(assets/'digital.csv',['sample_delta_tau','sample_k','time_s','tracking_error_K','parameter_error'],digital_rows)
    colors=['#15688e','#a44d20','#247347']
    plot(assets/'identification.svg','Measured-state feedback: full-rank data can still bias OLS',[
        ('Discrete alpha estimate; samples N; true alpha=0.9',(500,12000,0.4,1.0),
         [('OLS from measured y',colors[0],[(row[0],row[1]) for row in estimates]),
          ('IV from past/current r',colors[1],[(row[0],row[3]) for row in estimates]),
          ('Population OLS=468/775',colors[2],[(500,468/775),(12000,468/775)])],[0.9]),
        ('Discrete beta [K/W]; samples N; true beta=0.1',(500,12000,0.08,0.12),
         [('OLS',colors[0],[(row[0],row[2]) for row in estimates]),
          ('IV',colors[1],[(row[0],row[4]) for row in estimates])],[0.1])])
    names=['ideal_reference','zero_exact','zero_transient'];labels=['r=1: excited scalar','r=0: y(0)=0','r=0: y(0)=0.6 K']
    plot(assets/'mrac.svg','Continuous ideal MRAC: tracking and parameter learning are different',[
        ('Tracking error e [K]; physical time [s]',(0,300,-0.6,0.65),
         [(label,color,[(row[0],row[3]) for row in all_traces[name]]) for name,label,color in zip(names,labels,colors)],[]),
        ('Parameter a_hat [dimensionless]; true a=-1; physical time [s]',(0,300,-1.3,0.8),
         [(label,color,[(row[0],row[4]) for row in all_traces[name]]) for name,label,color in zip(names,labels,colors)],[-1])])
    drift=all_traces['drift_zero_reference'];leak=all_traces['sigma_zero_reference']
    plot(assets/'leakage.svg','r=0, d=0.1: drift versus fixed leakage sigma=0.2',[
        ('Parameter a_hat [dimensionless]; physical time [s]',(0,3000,-1,max(0.5,1.1*drift[-1][4])),
         [('No leakage',colors[0],[(row[0],row[4]) for row in drift]),
          ('Leakage to a0=-0.8',colors[1],[(row[0],row[4]) for row in leak])],[-1]),
        ('Tracking error e=y [K]; physical time [s]',(0,3000,0,0.1),
         [('No leakage',colors[0],[(row[0],row[3]) for row in drift]),
          ('Fixed leakage',colors[1],[(row[0],row[3]) for row in leak])],[]),
        ('V and its comparison envelope [dimensionless]; leakage case; physical time [s]',(0,3000,0,0.05),
         [('Actual V',colors[0],[(row[0],row[6]) for row in leak]),
          ('Comparison envelope',colors[1],[(row[0],row[7]) for row in leak])],[final_storage_bound])])
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print('PASS: exact identification moments, finite OLS/IV, RK4 refinement, ideal invariants, leakage comparison, digital local derivative')
    print(f'PYTHON={sys.version.split()[0]}; SERIAL=True; RU_MAXRSS_BYTES={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}')


if __name__=='__main__':
    main()
```
