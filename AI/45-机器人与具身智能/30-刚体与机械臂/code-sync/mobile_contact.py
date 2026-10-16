"""Finite differential-drive and single-point contact examples; not a simulator platform.
Reuse published rigid_dynamics -> arm_kinematics -> robotics_lab (SE2/reference/units).
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import numpy as np

_RD = None
_RD_PATH = None


def set_sources(rigid_source=None):
    global _RD, _RD_PATH
    path = Path(rigid_source) if rigid_source else Path(__file__).with_name('rigid_dynamics.py')
    spec = importlib.util.spec_from_file_location('wwl_rigid_published', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.set_sources()
    _RD, _RD_PATH = module, path.resolve()


def rigid():
    if _RD is None:
        set_sources()
    return _RD


def base():
    return rigid().arm().base()


def wheels(v, omega, radius, track):
    radius,track = base().positive(radius,'wheel radius m'),base().positive(track,'track m')
    values = base().finite([v,omega],(2,),'v m/s, yaw rad/s')
    return np.array([(values[0]-.5*track*values[1])/radius,
                     (values[0]+.5*track*values[1])/radius])  # left, right


def body_control(wheel_rates, radius, track):
    left,right = base().finite(wheel_rates,(2,),'left/right rad/s')
    radius,track = base().positive(radius,'wheel radius m'),base().positive(track,'track m')
    return np.array([.5*radius*(left+right),radius*(right-left)/track])


def exact_mobile_step(q, v, omega, dt):
    q = base().finite(q,(3,),'x m, y m, heading rad')
    dt = base().positive(dt,'dt s')
    v,omega = base().finite([v,omega],(2,),'body speed/yaw')
    angle = omega*dt
    local = v*dt*np.array([np.sinc(angle/np.pi),.5*angle*np.sinc(angle/(2*np.pi))**2])
    transform = base().se2(q[:2],q[2])@base().se2(local,angle)
    return np.r_[transform[:2,2],q[2]+angle]


def primitive(t, durations):
    total = 0.
    for index,(kind,amount,duration) in enumerate(zip(['turn','straight','turn'],[np.pi/2,1.,-np.pi/2],durations)):
        if t < total+duration:
            _,rate,_ = rigid().reference(t-total,[0.,0.],[amount,0.],duration)
            return np.array([rate[0],0.]) if kind=='straight' else np.array([0.,rate[0]]),index
        total += duration
    return np.zeros(2),3


def simulate_mobile(config, scenario, max_steps=None):
    p = config['mobile'];dt = base().positive(p['dt_s'],'mobile dt s');duration = sum(scenario['durations_s'])
    n = round(duration/dt)
    if not np.isclose(n*dt,duration,atol=1e-12,rtol=0):
        raise ValueError('phase horizon must align with sample grid')
    if max_steps is not None:n=min(n,max_steps)
    q = np.zeros(3);rows=[]
    for k in range(n+1):
        t=k*dt
        command,phase = primitive(t,scenario['durations_s'])
        requested = wheels(*command,p['wheel_radius_m'],p['track_m'])
        applied = np.clip(requested,-p['wheel_limit_rad_s'],p['wheel_limit_rad_s']) if scenario['clip_wheels'] else requested.copy()
        v,omega = body_control(applied,p['wheel_radius_m'],p['track_m'])
        world_velocity = v*np.array([np.cos(q[2]),np.sin(q[2])])
        normal = np.array([-np.sin(q[2]),np.cos(q[2])])
        clearance = np.linalg.norm(q[:2]-p['obstacle_center_W_m'])-p['obstacle_radius_m']-p['body_radius_m']
        rows.append({'case':scenario['id'],'k':k,'t_s':t,'q_x_y_heading':q.tolist(),'phase':phase,
                     'requested_body_v_omega':command.tolist() if k<n else None,
                     'requested_wheel_rad_s':requested.tolist() if k<n else None,
                     'applied_wheel_rad_s':applied.tolist() if k<n else None,
                     'applied_body_v_omega':[float(v),float(omega)] if k<n else None,
                     'world_velocity_m_s':world_velocity.tolist() if k<n else None,
                     'no_slip_residual_m_s':float(normal@world_velocity) if k<n else None,
                     'sampled_clearance_m':float(clearance)})
        if k<n:q=exact_mobile_step(q,v,omega,dt)
    controls=rows[:-1]
    # These three-phase experiments use only pure turns or straight translations.
    if any(abs(x['applied_body_v_omega'][0]*x['applied_body_v_omega'][1])>1e-12 for x in controls):
        raise ValueError('continuous segment-clearance audit requires pure turn/straight primitives')
    continuous_clearance=min(base().segment_clearance(a['q_x_y_heading'][:2],b['q_x_y_heading'][:2],
                            p['obstacle_center_W_m'],p['obstacle_radius_m']+p['body_radius_m'])
                            for a,b in zip(rows[:-1],rows[1:]))
    return rows,{'case':scenario['id'],'states':len(rows),'intervals':n,
                 'position_error_m':float(np.linalg.norm(q[:2]-[0.,1.])), 'heading_error_rad':float(abs(q[2])),
                 'peak_requested_wheel_rad_s':float(np.max(np.abs([r['requested_wheel_rad_s'] for r in controls]))),
                 'peak_applied_wheel_rad_s':float(np.max(np.abs([r['applied_wheel_rad_s'] for r in controls]))),
                 'clipped_intervals':sum(bool(np.max(np.abs(np.array(r['requested_wheel_rad_s'])-r['applied_wheel_rad_s']))>1e-12) for r in controls),
                 'max_abs_no_slip_residual_m_s':max(abs(r['no_slip_residual_m_s']) for r in controls),
                 'min_sampled_clearance_m':min(r['sampled_clearance_m'] for r in rows),
                 'continuous_primitive_clearance_m':continuous_clearance}


def impact(velocity, mass, restitution, friction):
    velocity=base().finite(velocity,(2,),'preimpact vx/vy m/s')
    mass=base().positive(mass,'mass kg')
    e=base().positive(restitution,'restitution',allow_zero=True)
    mu=base().positive(friction,'friction',allow_zero=True)
    if e>1 or velocity[1]>=0:
        raise ValueError('impact needs 0<=e<=1 and approaching normal velocity')
    normal_impulse=-(1+e)*mass*velocity[1]
    tangent_impulse=float(np.clip(-mass*velocity[0],-mu*normal_impulse,mu*normal_impulse))
    after=np.array([velocity[0]+tangent_impulse/mass,-e*velocity[1]])
    normal_loss=.5*mass*(velocity[1]**2-after[1]**2)
    tangent_loss=.5*mass*(velocity[0]**2-after[0]**2)
    work=float(np.array([tangent_impulse,normal_impulse])@(.5*(velocity+after)))
    return after,{'normal_impulse_N_s':float(normal_impulse),'tangent_impulse_N_s':tangent_impulse,
                  'normal_loss_J':float(normal_loss),'tangent_loss_J':float(tangent_loss),
                  'impulse_work_J':work}


def floor_slide(x, vx, duration, mass, gravity, friction):
    # No horizontal actuation in the formal trajectories: slide to zero, then stick.
    if vx==0.:
        return float(x),0.,0.,0.,0.
    decel=friction*gravity
    stop=abs(vx)/decel if decel>0 else np.inf
    moving=min(duration,stop)
    sign=np.sign(vx)
    nextx=x+vx*moving-.5*sign*decel*moving*moving
    nextv=sign*max(0.,abs(vx)-decel*duration)
    loss=.5*mass*(vx*vx-nextv*nextv)
    return float(nextx),float(nextv),float(loss),float(moving),float(stop)


def time_to_floor(y, vy, gravity):
    root=np.sqrt(vy*vy+2*gravity*y)
    return 2*y/(root-vy) if vy<0 and y>0 else (vy+root)/gravity


def advance_contact(state, duration, mass, gravity, e, mu, start_time):
    state=np.array(state,float).copy()
    if state.shape!=(4,) or not np.isfinite(state).all() or state[1]<0:
        raise ValueError('expected x,y,vx,vy with y>=0')
    remaining=duration;elapsed=0.;loss=np.zeros(3);events=[];segments=[];count=0
    while remaining>0:
        count+=1
        if count>64:
            raise ValueError('unresolved repeated impacts / possible Zeno; no automatic rest projection')
        if state[1]==0 and state[3]==0:
            before=state.copy();x,vx,dl,moving,stop=floor_slide(state[0],state[2],remaining,mass,gravity,mu)
            state[0],state[2]=x,vx;loss[2]+=dl
            segments.append({'mode':'support','start_s':start_time+elapsed,'duration_s':remaining,
                             'normal_force_N':mass*gravity,'sliding_duration_s':moving,
                             'friction_force_while_sliding_N':float(-mu*mass*gravity*np.sign(before[2])) if moving>0 else 0.,
                             'friction_impulse_N_s':float(mass*(vx-before[2])),'slide_loss_J':dl,
                             'state_before':before.tolist(),'state_after':state.tolist()})
            if before[2]!=0 and stop<=remaining:
                events.append({'kind':'tangent_stop','t_s':start_time+elapsed+stop,'x_m':x,
                               'state_at_stop':[x,0.,0.,0.]})
            remaining=0.
            continue
        hit=time_to_floor(state[1],state[3],gravity)
        travel=min(hit,remaining)
        before=state.copy()
        state[0]+=state[2]*travel
        state[1]+=state[3]*travel-.5*gravity*travel*travel
        state[3]-=gravity*travel
        segments.append({'mode':'flight','start_s':start_time+elapsed,'duration_s':travel,
                         'state_before':before.tolist(),'state_after':state.tolist()})
        elapsed+=travel;remaining-=travel
        if hit<=travel:
            # Set the known event surface, only after solving its exact ballistic root.
            state[1]=0.
            before=state.copy();after,ledger=impact(state[2:4],mass,e,mu)
            state[2:4]=after
            events.append({'kind':'impact','t_s':start_time+elapsed,'state_before':before.tolist(),
                           'state_after':state.tolist(),**ledger})
            loss[:2]+=np.array([ledger['normal_loss_J'],ledger['tangent_loss_J']])
    return state,loss,events,segments


def mechanical_energy(state,mass,gravity):
    state=np.array(state,float)
    return float(.5*mass*(state[2]**2+state[3]**2)+mass*gravity*state[1])


def simulate_contact(config,scenario,max_steps=None):
    p=config['contact'];m=base().positive(p['mass_kg'],'mass');g=base().positive(p['gravity_m_s2'],'gravity')
    dt=base().positive(p['dt_s'],'dt');e,mu=scenario['restitution'],scenario['friction']
    if not (0<=e<=1 and mu>=0):raise ValueError('unsupported restitution or friction')
    n=round(scenario['horizon_s']/dt)
    if not np.isclose(n*dt,scenario['horizon_s'],atol=1e-12,rtol=0):raise ValueError('contact horizon alignment')
    if max_steps is not None:n=min(n,max_steps)
    state=np.array(p['initial_x_y_vx_vy'],float);e0=mechanical_energy(state,m,g)
    losses=np.zeros(3);rows=[];events=[];segments=[]
    for k in range(n+1):
        energy=mechanical_energy(state,m,g)
        on_floor=state[1]==0 and state[3]==0
        rows.append({'case':scenario['id'],'k':k,'t_s':k*dt,'state_x_y_vx_vy':state.tolist(),
                     'mechanical_energy_J':energy,'impact_normal_loss_J':float(losses[0]),
                     'impact_tangent_loss_J':float(losses[1]),'slide_loss_J':float(losses[2]),
                     'energy_residual_J':float(energy-e0+losses.sum()),
                     'normal_force_N':m*g if on_floor else 0.,
                     'tangent_force_N':float(-mu*m*g*np.sign(state[2])) if on_floor else 0.})
        if k<n:
            state,dl,de,ds=advance_contact(state,dt,m,g,e,mu,k*dt)
            losses+=dl
            events.extend({'case':scenario['id'],**x} for x in de)
            segments.extend({'case':scenario['id'],**x} for x in ds)
    impacts=[x for x in events if x['kind']=='impact']
    return rows,events,segments,{'case':scenario['id'],'states':len(rows),'impacts':len(impacts),
                               'first_impact_s':impacts[0]['t_s'] if impacts else None,
                               'final_state_x_y_vx_vy':state.tolist(),'final_energy_J':rows[-1]['mechanical_energy_J'],
                               'normal_loss_J':float(losses[0]),'tangent_impact_loss_J':float(losses[1]),
                               'slide_loss_J':float(losses[2]),
                               'max_abs_energy_residual_J':max(abs(x['energy_residual_J']) for x in rows)}


def static_point_contact(mass,gravity,mu,force_x,force_y):
    required=mass*gravity-force_y
    if required<0:
        return {'mode':'lift','normal_force_N':0.,'tangent_force_N':0.,'acceleration_m_s2':[force_x/mass,force_y/mass-gravity]}
    tangent=float(np.clip(-force_x,-mu*required,mu*required))
    return {'mode':'stick' if abs(force_x)<=mu*required else 'slip','normal_force_N':required,
            'tangent_force_N':tangent,'acceleration_m_s2':[(force_x+tangent)/mass,0.]}


def examples(config):
    p=config['mobile'];eps=.1;a=.1
    q=np.zeros(3)
    for v,w,dt in [(0.,eps,1.),(a,0.,1.),(0.,-eps,1.),(-a,0.,1.)]:
        q=exact_mobile_step(q,v,w,dt)
    impossible=[]
    n=round(9./p['dt_s'])
    for k in range(n+1):
        t=k*p['dt_s'];position,velocity,_=rigid().reference(t,[0.,0.],[1.,0.],9.)
        impossible.append({'t_s':t,'q_x_y_heading':[0.,float(position[0]),0.],
                           'qdot_x_y_heading':[0.,float(velocity[0]),0.],
                           'no_slip_residual_m_s':float(velocity[0])})
    nominal=json.loads((_RD_PATH.parents[1]/'dynamics-inputs.json').read_text())['nominal']
    plant=rigid().parameters(nominal)
    arm_q=np.array([np.pi/6,-np.pi/3]);j=rigid().arm().jacobian(arm_q,plant['lengths_m'])
    _,_,gravity=rigid().mechanics(arm_q,[0.,0.],plant)
    pressures=[]
    for normal in [5.,20.]:
        torque=gravity-j.T@np.array([0.,normal])
        pressures.append({'normal_force_N':normal,'pure_tangent_force_N':0.,'motor_torque_N_m':torque.tolist(),
                          'within_20_8_N_m':bool(np.all(np.abs(torque)<=np.array([20.,8.])))})
    # Coarse position projection of an elastic drop is deliberately NOT the contact solver.
    state=np.array([0.,1.,0.,0.]);duration=.5;m=1.;g=9.81
    exact,_,events,_=advance_contact(state,duration,m,g,1.,0.,0.)
    ballistic=np.array([0.,1.-.5*g*duration**2,0.,-g*duration])
    keep=ballistic.copy();keep[1]=max(0.,keep[1]);zero=keep.copy();zero[3]=0.
    return {'commutator':{'epsilon_rad':eps,'a_m':a,'terminal_q':q.tolist(),
                          'analytic_terminal_q':[a*(np.cos(eps)-1),a*np.sin(eps),0.]},
            'illegal_configuration_interpolation':impossible,
            'independent_box_counterexample':{'v_m_s':.4,'omega_rad_s':1.6,'wheel_rad_s':wheels(.4,1.6,p['wheel_radius_m'],p['track_m']).tolist()},
            'mobile_local_linearization':{'A':np.zeros((3,3)).tolist(),'B_at_heading_0':[[1.,0.],[0.,0.],[0.,1.]],'rank':2},
            'continuous_mobile_peaks':[{'case':s['id'],'phase_wheel_peaks_rad_s':[1.875*(np.pi/2)*p['track_m']/(2*p['wheel_radius_m']*s['durations_s'][0]),1.875/(p['wheel_radius_m']*s['durations_s'][1]),1.875*(np.pi/2)*p['track_m']/(2*p['wheel_radius_m']*s['durations_s'][2])]} for s in p['scenarios']],
            'static_point_modes':[{'force_x_N':fx,'force_y_N':fy,**static_point_contact(1.,9.81,.2,fx,fy)}
                                  for fx,fy in [(.8,4.81),(1.2,4.81),(0.,10.81)]],
            'arm_contact':{'q_rad':arm_q.tolist(),'J_position_m_rad':j.tolist(),'gravity_N_m':gravity.tolist(),
                           'pure_normal_feasible_interval_N':[0.,plant['gravity_m_s2']/2+16/np.sqrt(3)],'pressures':pressures},
            'projection_counterexample':{'initial_energy_J':9.81,'duration_s':duration,
                                         'exact_state':exact.tolist(),'exact_energy_J':mechanical_energy(exact,m,g),
                                         'clamp_y_only_state':keep.tolist(),'clamp_y_only_energy_J':mechanical_energy(keep,m,g),
                                         'clamp_y_vy_state':zero.tolist(),'clamp_y_vy_energy_J':mechanical_energy(zero,m,g),
                                         'exact_impacts':events}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rigid',type=Path)
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parents[1]/'mobile-contact-inputs.json')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--max-steps',type=int)
    args=parser.parse_args();set_sources(args.rigid);config=json.loads(args.input.read_text())
    if args.max_steps is not None and args.max_steps<1:raise ValueError('pre-run step count')
    args.output.mkdir(parents=True,exist_ok=True)
    mobile=[];contact=[]
    with (args.output/'mobile.jsonl').open('w') as stream:
        for scenario in config['mobile']['scenarios']:
            rows,summary=simulate_mobile(config,scenario,args.max_steps);mobile.append(summary)
            for row in rows:stream.write(json.dumps(row,allow_nan=False)+'\n')
    with (args.output/'contact.jsonl').open('w') as states,(args.output/'events.jsonl').open('w') as events,(args.output/'segments.jsonl').open('w') as segments:
        for scenario in config['contact']['scenarios']:
            rr,ee,ss,summary=simulate_contact(config,scenario,args.max_steps);contact.append(summary)
            for target,rows in [(states,rr),(events,ee),(segments,ss)]:
                for row in rows:target.write(json.dumps(row,allow_nan=False)+'\n')
    result={'examples':examples(config),'mobile_summaries':mobile,'contact_summaries':contact,'pre_run_max_steps':args.max_steps,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
            'rigid_source_sha256':hashlib.sha256(_RD_PATH.read_bytes()).hexdigest(),
            'kinematics_sha256':hashlib.sha256(rigid()._ARM_PATH.read_bytes()).hexdigest(),
            'base_sha256':hashlib.sha256(rigid().arm()._BASE_PATH.read_bytes()).hexdigest(),
            'thread_limit_environment':{x:os.environ.get(x) for x in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']}}
    (args.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'mobile':mobile,'contact':contact},ensure_ascii=False))


if __name__=='__main__':main()
