---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# 反馈线性化与零动态实验源码

返回 [[控制论/80-实践/07-反馈线性化与零动态/README|复现说明]]。

<!-- code-sync: 控制论/80-实践/07-反馈线性化与零动态/zero_dynamics_lab.py -->

```python
#!/usr/bin/env python3
"""Finite smooth scalar-output example; explicit domains, events and references."""
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[_key]='1'
import argparse
import csv
import html
import json
import math
import platform
import resource
import time
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def to_normal(x):
    x1,x2,x3=x
    return x1,x2+x1*x3,x3


def to_original(z):
    y,s,eta=z
    return y,s-y*eta,eta


def reference(t, cfg, case):
    A=cfg['tracking']['amplitude'] if case['reference']=='sine' else 0.0
    w=cfg['tracking']['omega_per_tau']
    return A*math.sin(w*t), A*w*math.cos(w*t), -A*w*w*math.sin(w*t)


def command(t,z,cfg,case):
    y,s,eta=z
    beta=1-y*y
    require(beta>0, 'feedback undefined outside |y|<1; refusing continuation')
    r,dr,ddr=reference(t,cfg,case)
    nu=ddr-2*(y-r)-3*(s-dr)
    raw=(nu-eta)/beta
    limit=cfg['actuator_limit']
    applied=max(-limit,min(limit,raw)) if case['mode']=='saturated' else raw
    return raw,applied,nu,beta


def rhs_normal(t,z,cfg,case):
    y,s,eta=z
    _,u,_,beta=command(t,z,cfg,case)
    return s,eta+beta*u,case['sigma']*eta+y


def rhs_original(t,x,cfg,case):
    x1,x2,x3=x
    _,u,_,_=command(t,to_normal(x),cfg,case)
    sigma=case['sigma']
    return (x2+x1*x3,
            x3-x2*x3-x1*x3*x3-sigma*x1*x3-x1*x1+(1-x1*x1)*u,
            sigma*x3+x1)


def rk4(t,z,h,cfg,case,rhs):
    def add(z,v,scale):
        return tuple(a+scale*b for a,b in zip(z,v))
    k1=rhs(t,z,cfg,case)
    k2=rhs(t+h/2,add(z,k1,h/2),cfg,case)
    k3=rhs(t+h/2,add(z,k2,h/2),cfg,case)
    k4=rhs(t+h,add(z,k3,h),cfg,case)
    return tuple(x+h*(a+2*b+2*c+d)/6 for x,a,b,c,d in zip(z,k1,k2,k3,k4))


def analytic(t,cfg,case):
    y0,s0,eta0=case.get('initial_normal',cfg['initial_normal'])
    _,dr0,_=reference(0,cfg,case)
    p=2*y0+s0-dr0
    q=y0+s0-dr0
    r,dr,_=reference(t,cfg,case)
    e1,e2=math.exp(-t),math.exp(-2*t)
    y=r+p*e1-q*e2
    s=dr-p*e1+2*q*e2
    if case['sigma']==-1:
        eta=e1*(eta0+p*t-q*(1-e1))
    else:
        eta=math.exp(t)*(eta0+p/2*(1-e2)-q/3*(1-math.exp(-3*t)))
    A=cfg['tracking']['amplitude'] if case['reference']=='sine' else 0.0
    w=cfg['tracking']['omega_per_tau'];sigma=case['sigma']
    eta+=A/(1+w*w)*(-sigma*math.sin(w*t)-w*math.cos(w*t)+w*math.exp(sigma*t))
    return y,s,eta


def safe_bound(cfg,case):
    y0,s0,eta0=case.get('initial_normal',cfg['initial_normal'])
    _,dr0,_=reference(0,cfg,case)
    p,q=2*y0+s0-dr0,y0+s0-dr0
    S=abs(p)+abs(q)
    A=abs(cfg['tracking']['amplitude']) if case['reference']=='sine' else 0.0
    w=cfg['tracking']['omega_per_tau']
    B=A+S
    H=abs(eta0)+A+S/math.e
    N=A*w*w+abs(p)+4*abs(q)
    U=(N+H)/(1-B*B) if B<1 and case['sigma']==-1 else None
    if case['sigma']!= -1:H=None
    return {'p0':p,'q0':q,'ideal_output_bound':B,'internal_bound':H,
            'virtual_input_bound':N,'request_bound':U,
            'protected_minimum_case':case['sigma']==-1 and B<cfg['integration']['guard_y']
            and U is not None and U<cfg['actuator_limit']}


def integrate(cfg,case,substeps,original=False):
    init=tuple(case.get('initial_normal',cfg['initial_normal']))
    guard=cfg['integration']['guard_y'];dt=cfg['integration']['base_step_tau']
    if abs(init[0])>=guard:
        reason='initial_singular_stop' if abs(1-init[0]*init[0])<1e-12 else 'initial_guard_stop'
        return [(0.0,init)],reason
    rhs=rhs_original if original else rhs_normal
    z=to_original(init) if original else init
    result=[(0.0,init)]
    end=cfg['integration']['end_tau'];n=round(end/dt)
    t=0.0
    for index in range(n):
        for j in range(substeps):
            step=dt/substeps
            start_z,start_t=z,t
            trial=rk4(t,z,step,cfg,case,rhs)
            normal=to_normal(trial) if original else trial
            if abs(normal[0])>=guard:
                lo,hi=0.0,step
                for _ in range(48):
                    mid=(lo+hi)/2
                    candidate=rk4(start_t,start_z,mid,cfg,case,rhs)
                    nz=to_normal(candidate) if original else candidate
                    if abs(nz[0])<guard:lo=mid
                    else:hi=mid
                event_z=rk4(start_t,start_z,(lo+hi)/2,cfg,case,rhs)
                event_normal=to_normal(event_z) if original else event_z
                result.append((start_t+(lo+hi)/2,event_normal))
                return result,'guard_event_stop'
            z=trial;t=start_t+step
        # Export grid identity is exact index*dt, not an accumulated floating timestamp.
        t=(index+1)*dt
        result.append((t,to_normal(z) if original else z))
    return result,'completed'


def panel_svg(path,title,desc,panels):
    width,ph=950,355
    output=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{80+ph*len(panels)}" viewBox="0 0 {width} {80+ph*len(panels)}">',
            '<title>'+html.escape(title)+'</title><desc>'+html.escape(desc)+'</desc>',
            '<rect width="100%" height="100%" fill="white"/>',
            '<g font-family="sans-serif" font-size="13" fill="#173047">',
            '<text x="85" y="28" font-size="21">'+html.escape(title)+'</text>',
            '<text x="85" y="53">'+html.escape(desc)+'</text>']
    colors=['#126c9b','#b24b08','#763898','#286b30']
    for i,panel in enumerate(panels):
        subtitle,xlabel,ylabel,xmin,xmax,ymin,ymax,series,guides=panel
        top=80+i*ph
        def xy(x,y):
            return 85+770*(x-xmin)/(xmax-xmin),top+235-200*(y-ymin)/(ymax-ymin)
        output.append(f'<text x="85" y="{top+15}" font-size="16">{html.escape(subtitle)}</text>')
        for j in range(6):
            x=xmin+(xmax-xmin)*j/5;y=ymin+(ymax-ymin)*j/5
            px,_=xy(x,ymin);_,py=xy(xmin,y)
            output += [f'<path d="M {px:.2f} {top+35} V {top+235}" stroke="#dfe5eb"/>',
                       f'<text x="{px:.2f}" y="{top+255}" text-anchor="middle">{x:.3g}</text>',
                       f'<path d="M 85 {py:.2f} H 855" stroke="#dfe5eb"/>',
                       f'<text x="74" y="{py+4:.2f}" text-anchor="end">{y:.3g}</text>']
        for guide_index,(y,label) in enumerate(guides):
            _,py=xy(xmin,y)
            label_y=top+48+20*guide_index if len(guides)>1 else py-4
            output += [f'<path d="M 85 {py:.2f} H 855" stroke="#666" stroke-dasharray="3 5"/>',
                       f'<text x="850" y="{label_y:.2f}" text-anchor="end">{html.escape(label)}</text>']
        for j,(label,data,dash) in enumerate(series):
            color=colors[j%len(colors)];pts=' '.join(f'{xy(x,y)[0]:.3f},{xy(x,y)[1]:.3f}' for x,y in data)
            output += [f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',
                       f'<path d="M {85+(j%2)*395} {top+306+(j//2)*20} h 30" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',
                       f'<text x="{122+(j%2)*395}" y="{top+310+(j//2)*20}">{html.escape(label)}</text>']
        output += [f'<text x="470" y="{top+282}" text-anchor="middle">{html.escape(xlabel)}</text>',
                   f'<text transform="translate(22 {top+145}) rotate(-90)" text-anchor="middle">{html.escape(ylabel)}</text>']
    output.append('</g></svg>');path.write_text('\n'.join(output)+'\n',encoding='utf-8')


def main():
    start=time.monotonic();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('input.json'))
    parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    require(not args.output_dir.exists(),'output directory must be new; refusing overwrite')
    cfg=json.loads(args.input.read_text(encoding='utf-8'));grid=cfg['integration']
    require(all(math.isfinite(x) for x in list(grid.values())+list(cfg['tracking'].values())+
                cfg['initial_normal']+[cfg['time_scale_s'],cfg['actuator_limit']]),'all parameters must be finite')
    dt,end,guard=grid['base_step_tau'],grid['end_tau'],grid['guard_y']
    require(0.002<=dt<=0.02 and 0<end<=12 and abs(end/dt-round(end/dt))<1e-9,'invalid finite grid')
    require(0.2<=guard<=0.85 and 0<cfg['time_scale_s']<=10 and 0.1<=cfg['actuator_limit']<=10,
            'invalid domain/time/actuator bound')
    require(0<=cfg['tracking']['amplitude']<=0.2 and 0<cfg['tracking']['omega_per_tau']<=2,
            'invalid smooth reference')
    require(len(cfg['initial_normal'])==3 and all(abs(x)<=0.2 for x in cfg['initial_normal']),
            'common initial state must be a small three-state vector')
    require([x['name'] for x in cfg['cases']]==['minimum','nonminimum','saturated','tracking','singular_initial'],
            'use the five explicitly plotted comparison cases')
    expected_cases=[(-1,'ideal','zero'),(1,'ideal','zero'),(1,'saturated','zero'),
                    (-1,'ideal','sine'),(-1,'ideal','zero')]
    require([(case['sigma'],case['mode'],case['reference']) for case in cfg['cases']]==expected_cases,
            'case names must keep their stated sigma/mode/reference meaning')
    rows,events,errors,saved,summary=[],[],[],{},{}
    for case in cfg['cases']:
        require(case['sigma'] in (-1,1) and case['mode'] in ('ideal','saturated') and
                case['reference'] in ('zero','sine'),'invalid declared case')
        if 'initial_normal' in case:
            require(case['name']=='singular_initial' and len(case['initial_normal'])==3 and
                    all(math.isfinite(x) and abs(x)<=1 for x in case['initial_normal']),
                    'only the initial-domain failure case may override the common state')
        bound=safe_bound(cfg,case)
        if case['name'] in ('minimum','tracking'):
            require(bound['protected_minimum_case'],'protected minimum-phase amplitude certificate fails')
        routes=[integrate(cfg,case,n) for n in (1,2,4,8)]
        original=integrate(cfg,case,4,original=True)
        require(time.monotonic()-start<60,'finite CPU pre-run budget exhausted')
        finest={round(t,12):z for t,z in routes[3][0]}
        diffs=[]
        for sub,(route,status) in zip((1,2,4),routes[:3]):
            matching=[math.dist(z,finest[round(t,12)]) for t,z in route if round(t,12) in finest]
            err=max(matching,default=0.0);diffs.append(err)
            errors.append([case['name'],dt/sub,dt/8,err,len(matching),status,route[-1][0],
                           abs(route[-1][0]-routes[3][0][-1][0])])
        data,status=routes[2];original_map={round(t,12):z for t,z in original[0]}
        coord_error=max((math.dist(z,original_map[round(t,12)]) for t,z in data if round(t,12) in original_map),default=0.0)
        exact_error=0.0;identity_error=0.0;case_rows=[];first_bad=None
        for t,z in data:
            y,s,eta=z;x=to_original(z);r,dr,ddr=reference(t,cfg,case)
            if status.startswith('initial_'):
                raw=applied=nu=None;beta=1-y*y;accel=None;feasible=None
            else:
                raw,applied,nu,beta=command(t,z,cfg,case)
                accel=eta+beta*applied;feasible=abs(raw)<=cfg['actuator_limit']+1e-12
                # J_T f_original equals f_normal at the same state and applied input.
                f1,f2,f3=rhs_original(t,x,cfg,case)
                pulled=(f1,f2+eta*f1+y*f3,f3)
                identity_error=max(identity_error,math.dist(pulled,rhs_normal(t,z,cfg,case)))
                if case['mode']=='ideal':exact_error=max(exact_error,math.dist(z,analytic(t,cfg,case)))
                if not feasible and first_bad is None:first_bad=t
            record=[case['name'],case['mode'],case['sigma'],t,t*cfg['time_scale_s'],
                    y,s,eta,*x,r,y-r,beta,raw,applied,nu,accel,feasible,status]
            rows.append(record);case_rows.append(record)
        if first_bad is not None:events.append([case['name'],'first_export_request_over_limit',first_bad,first_bad*cfg['time_scale_s'],
                                               '', 'grid observation, not an exact actuator event'])
        if status!='completed':events.append([case['name'],status,data[-1][0],data[-1][0]*cfg['time_scale_s'],data[-1][1][0],
                                            'no records or model continuation after this stop'])
        require(identity_error<1e-9 and coord_error<1e-5,'coordinate/plant finite consistency check failed')
        if case['mode']=='ideal' and status=='completed':
            require(exact_error<1e-7 and diffs[2]<=diffs[1]+1e-12 and diffs[1]<=diffs[0]+1e-12,
                    'smooth analytic/refinement check failed')
        if status=='guard_event_stop':
            require(abs(abs(data[-1][1][0])-guard)<1e-10,'event endpoint misses guard')
        summary[case['name']]={'status':status,'rows':len(case_rows),'final_tau':data[-1][0],
            'final_normal':list(data[-1][1]),'analytic_max_difference':exact_error if case['mode']=='ideal' and status=='completed' else None,
            'coordinate_route_max_difference':coord_error,'plant_identity_max_error':identity_error,
            'step_differences':diffs,'final_tau_reference_differences':[abs(route[0][-1][0]-routes[3][0][-1][0]) for route in routes[:3]],
            'coordinate_route_final_tau_difference':abs(data[-1][0]-original[0][-1][0]),'first_export_request_over_limit_tau':first_bad,'amplitude_bound':bound}
        saved[case['name']]=case_rows
    # This is an instantaneous authority scan at eta=.02 and desired acceleration nu=0.
    authority=[]
    for j in range(199):
        y=-.99+j*.01;beta=1-y*y;u=-.02/beta
        authority.append([y,beta,.02,0.0,u,abs(u)<=cfg['actuator_limit']])
    authority.append([1.0,0.0,.02,0.0,'','undefined'])
    args.output_dir.mkdir(parents=True)
    for name,header,records in [
        ('trajectories.csv',['case','mode','sigma','tau','t_s','y_scaled','s_scaled','eta_scaled','x1_scaled','x2_scaled','x3_scaled',
                             'reference_scaled','tracking_error_scaled','decoupling_gain','request_scaled','applied_scaled','nu_scaled',
                             'y_second_derivative_scaled','actuator_feasible','case_status'],rows),
        ('events.csv',['case','event','tau','t_s','y_scaled','interpretation'],events),
        ('step-errors.csv',['case','step_tau','reference_step_tau','max_normal_state_difference','common_grid_points','status','final_tau','final_tau_difference_from_reference'],errors),
        ('authority.csv',['y_scaled','decoupling_gain','eta_scaled','desired_acceleration_scaled','request_scaled','feasible'],authority)]:
        with (args.output_dir/name).open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(header);writer.writerows(records)
    def series(name,col):return [(z[4],z[col]) for z in saved[name]]
    xmax=end*cfg['time_scale_s']
    eta_log=[(z[4],math.log10(max(abs(z[7]),1e-12))) for z in saved['minimum']]
    eta_log_bad=[(z[4],math.log10(max(abs(z[7]),1e-12))) for z in saved['nonminimum']]
    ly=min(y for _,y in eta_log+eta_log_bad)-.1;hy=max(y for _,y in eta_log+eta_log_bad)+.1
    panel_svg(args.output_dir/'output-hidden.svg','The same output can hide opposite internal dynamics',
      'Ideal feedback; sigma changes sign; states/input normalized; log eta display floor=1e-12.',
      [('Output curves overlap: both have poles -1 and -2','time t (s)','normalized output y',0,xmax,min(0,min(z[5] for z in saved['minimum'])*1.1),max(.055,max(z[5] for z in saved['minimum'])*1.1),
        [('sigma=-1',series('minimum',5),''),('sigma=+1',series('nonminimum',5),'7 3')],[]),
       ('Internal coordinate eta diverges in the nonminimum-phase case','time t (s)','log10 |eta| (normalized)',0,xmax,ly,hy,
        [('sigma=-1',eta_log,''),('sigma=+1',eta_log_bad,'7 3')],[])])
    saturated=saved['saturated'];end_sat=saturated[-1][4]
    lo_u=min(-cfg['actuator_limit'],min(z[14] for z in saturated))-.1
    hi_u=max(cfg['actuator_limit'],max(z[14] for z in saturated))+.1
    sat_y=[z[5] for z in saturated]+[z[5] for z in saved['nonminimum']]
    guard_sign=1 if saturated[-1][5]>=0 else -1
    sat_ymin=min(0,min(sat_y),guard_sign*guard);sat_ymax=max(0,max(sat_y),guard_sign*guard)
    sat_ypad=.08*(sat_ymax-sat_ymin)
    panel_svg(args.output_dir/'saturation.svg','The finite actuator exposes hidden instability',
      f'Saturated plant stops at |y|={guard:g}; ideal curve is a separate unbounded-command model.',
      [('No future saturated samples after the guard event','time t (s)','normalized output y',0,xmax,sat_ymin-sat_ypad,sat_ymax+sat_ypad,
        [('ideal nonminimum',series('nonminimum',5),''),('saturated until stop',series('saturated',5),'7 3')],[(guard_sign*guard,'stop guard')]),
       ('Request versus applied input, only until the stop','time t (s)','normalized input',0,end_sat,lo_u,hi_u,
        [('request',series('saturated',14),''),('applied',series('saturated',15),'7 3')],[(-cfg['actuator_limit'],'negative limit'),(cfg['actuator_limit'],'positive limit')])])
    tr=saved['tracking'];yr=[z[5] for z in tr]+[z[11] for z in tr]+[z[7] for z in tr]
    panel_svg(args.output_dir/'tracking.svg','Smooth output tracking includes reference derivatives',
      f'Minimum-phase example; reference amplitude={cfg["tracking"]["amplitude"]:g}, omega={cfg["tracking"]["omega_per_tau"]:g}/tau.',
      [('The output follows the reference while internal eta remains bounded','time t (s)','normalized states',0,xmax,min(0,min(yr)-.01),max(yr+[z[7] for z in tr])+.01,
        [('output y',series('tracking',5),''),('reference',series('tracking',11),'7 3'),('internal eta',series('tracking',7),'2 3')],[]),
       ('Tracking error has an analytic decaying response','time t (s)','normalized tracking error',0,xmax,
        min(0,min(z[12] for z in tr)),max(.001,max(z[12] for z in tr)*1.1),
        [('error',series('tracking',12),'')],[])])
    vals=[z[4] for z in authority[:-1]];limit=cfg['actuator_limit']
    panel_svg(args.output_dir/'authority.svg','A nonzero denominator can still demand too much input',
      'Instantaneous scan: eta=0.02, desired y second derivative=0; this is not a trajectory.',
      [('Input gain beta=1-y^2 decreases towards the singular boundary','normalized output coordinate y','normalized request',-.99,.99,min(min(vals)*1.1,-limit*1.05),.05,
        [('request -0.02/(1-y^2)',[(z[0],z[4]) for z in authority[:-1]],'')],[(-limit,'negative limit')])])
    final={'cases':summary,'trajectory_rows':len(rows),'event_rows':len(events),'authority_rows':len(authority),
           'scope':'finite model checks; general definitions and counterexample proof live in lesson 16'}
    (args.output_dir/'summary.json').write_text(json.dumps(final,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'status':'PASS','python':platform.python_version(),'platform':platform.platform(),
        'elapsed_s':time.monotonic()-start,'observed_peak_rss_bytes':rss if platform.system()=='Darwin' else rss*1024,
        **final},indent=2,allow_nan=False))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as exc:
        raise SystemExit('Input/output/domain check failed: '+str(exc))
```
