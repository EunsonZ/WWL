"""SO(3)/SE(3) conventions and a vertical-plane 2R Lagrange model.
Angular-first twist/wrench, RH column vectors. Reuses published arm_kinematics.
No contact, estimator, actuator hardware or 3D renderer.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import numpy as np

_ARM = None
_ARM_PATH = None


def set_sources(kinematics=None, base_source=None):
    global _ARM, _ARM_PATH
    path = Path(kinematics) if kinematics else Path(__file__).with_name('arm_kinematics.py')
    spec = importlib.util.spec_from_file_location('wwl_2r_published', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.set_base(base_source)
    _ARM, _ARM_PATH = module, path.resolve()


def arm():
    if _ARM is None:
        set_sources()
    return _ARM


def finite(x, shape, name):
    return arm().base().finite(x, shape, name)


def hat(w):
    x, y, z = finite(w, (3,), '3-vector')
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def rotation_vector(vector):
    w = finite(vector, (3,), 'rotation vector radians')
    angle = np.linalg.norm(w)
    if not np.isfinite(angle):
        raise ValueError('rotation angle norm is not representable')
    k = hat(w)
    return np.eye(3) + np.sinc(angle/np.pi)*k + .5*np.sinc(angle/(2*np.pi))**2*(k@k)


def transform(rotation, translation):
    r = finite(rotation, (3,3), 'rotation')
    if not np.allclose(r.T@r, np.eye(3), atol=1e-10, rtol=0) or not np.isclose(np.linalg.det(r), 1., atol=1e-10, rtol=0):
        raise ValueError('rotation must belong to SO(3), not a reflection or affine scaling')
    t = np.eye(4)
    t[:3,:3], t[:3,3] = r, finite(translation, (3,), 'translation metres')
    return t


def checked_transform(t):
    t = finite(t, (4,4), 'SE(3)')
    if not np.array_equal(t[3], [0.,0.,0.,1.]):
        raise ValueError('expected affine homogeneous bottom row')
    transform(t[:3,:3], t[:3,3])
    return t


def inverse_transform(t):
    t = checked_transform(t)
    r, p = t[:3,:3], t[:3,3]
    return transform(r.T, -r.T@p)


def adjoint(t):
    t = checked_transform(t)
    r, p = t[:3,:3], t[:3,3]
    return np.block([[r, np.zeros((3,3))], [hat(p)@r, r]])


def twist_matrix(v):
    v = finite(v, (6,), 'angular-first twist')
    result = np.zeros((4,4))
    result[:3,:3], result[:3,3] = hat(v[:3]), v[3:]
    return result


def body_to_space(t, body_twist, body_wrench):
    t = checked_transform(t)
    vb = finite(body_twist, (6,), 'body twist')
    fb = finite(body_wrench, (6,), 'body wrench: moment then force')
    ad = adjoint(t)
    vs, fs = ad@vb, np.linalg.solve(ad.T, fb)
    pdot = vs[3:] + np.cross(vs[:3], t[:3,3])
    return vs, fs, pdot


def parameters(raw):
    result = {}
    for key in ['lengths_m','masses_kg','com_m','inertia_kg_m2','damping_N_m_s']:
        result[key] = finite(raw[key], (2,), key)
    if any(np.any(result[k] <= 0) for k in ['lengths_m','masses_kg','com_m','inertia_kg_m2']):
        raise ValueError('length, mass, COM distance, inertia must be positive')
    if np.any(result['com_m'] > result['lengths_m']) or np.any(result['damping_N_m_s'] < 0):
        raise ValueError('COM must lie on its link; damping must be nonnegative')
    result['gravity_m_s2'] = arm().base().positive(raw['gravity_m_s2'], 'gravity', allow_zero=True)
    return result


def mechanics(q, qdot, p):
    q = finite(q, (2,), 'joint radians')
    u, v = finite(qdot, (2,), 'joint rad/s')
    l1, _ = p['lengths_m']; m1, m2 = p['masses_kg']
    r1, r2 = p['com_m']; i1, i2 = p['inertia_kg_m2']
    a = i1+i2+m1*r1*r1+m2*(l1*l1+r2*r2)
    b, d = m2*l1*r2, i2+m2*r2*r2
    c2, s2 = np.cos(q[1]), np.sin(q[1])
    matrix = np.array([[a+2*b*c2,d+b*c2], [d+b*c2,d]])
    velocity = np.array([-b*s2*(2*u*v+v*v), b*s2*u*u])
    g = p['gravity_m_s2']
    gravity = g*np.array([(m1*r1+m2*l1)*np.cos(q[0])+m2*r2*np.cos(q.sum()),
                          m2*r2*np.cos(q.sum())])
    return matrix, velocity, gravity


def energy(q, qdot, p):
    q, qdot = finite(q, (2,), 'joint radians'), finite(qdot, (2,), 'joint rad/s')
    m, _, _ = mechanics(q, qdot, p)
    l1 = p['lengths_m'][0]; m1,m2 = p['masses_kg']; r1,r2 = p['com_m']
    potential = p['gravity_m_s2']*((m1*r1+m2*l1)*np.sin(q[0])+m2*r2*np.sin(q.sum()))
    return float(.5*qdot@m@qdot), float(potential)


def acceleration(q, qdot, torque, p, force_world=(0.,0.)):
    m,c,g = mechanics(q, qdot, p)
    torque, force = finite(torque, (2,), 'motor N m'), finite(force_world, (2,), 'external N')
    external = arm().jacobian(q, p['lengths_m']).T@force
    return np.linalg.solve(m, torque+external-c-g-p['damping_N_m_s']*qdot)


def reference(t, start, goal, duration):
    start, goal = finite(start, (2,), 'start rad'), finite(goal, (2,), 'goal rad')
    duration = arm().base().positive(duration, 'duration seconds')
    s = float(np.clip(t/duration, 0.,1.))
    step = 10*s**3-15*s**4+6*s**5
    speed = (30*s*s-60*s**3+30*s**4)/duration
    accel = (60*s-180*s*s+120*s**3)/(duration*duration)
    delta = goal-start
    return start+step*delta, speed*delta, accel*delta


def command(q, qdot, ref, nominal, mode, kp, kd):
    qr, vr, ar = ref
    if mode == 'feedforward':
        m,c,g = mechanics(qr, vr, nominal)
        return m@ar+c+g+nominal['damping_N_m_s']*vr
    if mode != 'computed_torque':
        raise ValueError('unknown controller')
    m,c,g = mechanics(q, qdot, nominal)
    target = ar + kd*(vr-qdot)+kp*(qr-q)
    return m@target+c+g+nominal['damping_N_m_s']*qdot


def rhs(state, torque, plant, force_world):
    q, v = state[:2], state[2:4]
    acc = acceleration(q, v, torque, plant, force_world)
    endpoint_velocity = arm().jacobian(q, plant['lengths_m'])@v
    return np.r_[v, acc, torque@v, np.asarray(force_world)@endpoint_velocity,
                 v@(plant['damping_N_m_s']*v)]


def step_rk4(state, torque, plant, dt, force_world=(0.,0.)):
    k1 = rhs(state, torque, plant, force_world)
    k2 = rhs(state+.5*dt*k1, torque, plant, force_world)
    k3 = rhs(state+.5*dt*k2, torque, plant, force_world)
    k4 = rhs(state+dt*k3, torque, plant, force_world)
    return state+dt*(k1+2*k2+2*k3+k4)/6


def simulate(config, scenario, max_steps=None):
    nominal_raw = config['nominal']
    plant_raw = {**nominal_raw, 'masses_kg': (np.array(nominal_raw['masses_kg'])*scenario['mass_factor']).tolist(),
                 'inertia_kg_m2': (np.array(nominal_raw['inertia_kg_m2'])*scenario['mass_factor']).tolist()}
    nominal, plant = parameters(nominal_raw), parameters(plant_raw)
    dt, horizon = config['dt_s'], config['horizon_s']
    dt = arm().base().positive(dt, 'sample period seconds')
    horizon = arm().base().positive(horizon, 'horizon seconds')
    steps = round(horizon/dt)
    if not np.isclose(steps*dt,horizon,atol=1e-12,rtol=0):
        raise ValueError('horizon must be an integer number of samples')
    if max_steps is not None:
        if max_steps < 1:
            raise ValueError('pre-run steps must be positive')
        steps = min(steps,max_steps)
    state = np.r_[config['start_q_rad'], config['start_qdot_rad_s'], [0.,0.,0.]]
    e0 = sum(energy(state[:2],state[2:4],plant))
    rows = []
    count_limited = 0
    for k in range(steps+1):
        t = k*dt
        q, v = state[:2], state[2:4]
        ref = reference(t,config['start_q_rad'],config['goal_q_rad'],scenario['reference_duration_s'])
        requested = command(q,v,ref,nominal,scenario['controller'],config['kp_s_2'],config['kd_s_1'])
        limit = scenario['torque_limit_N_m']
        actual = requested.copy() if limit is None else np.clip(requested,-np.array(limit),np.array(limit))
        limited = bool(np.any(np.abs(actual-requested)>1e-12))
        if k < steps:
            count_limited += int(limited)
        kinetic,potential = energy(q,v,plant)
        _, _, endpoint = arm().forward(q,plant['lengths_m'])
        _, _, desired_endpoint = arm().forward(ref[0],plant['lengths_m'])
        row = {'case':scenario['id'],'k':k,'t_s':t,'q_rad':q.tolist(),'qdot_rad_s':v.tolist(),
               'q_ref_rad':ref[0].tolist(),'qdot_ref_rad_s':ref[1].tolist(),'qddot_ref_rad_s2':ref[2].tolist(),
               'requested_N_m': requested.tolist() if k < steps else None,
               'applied_N_m': actual.tolist() if k < steps else None,
               'limited': limited if k < steps else None,
               'endpoint_W_m':endpoint.tolist(),'endpoint_ref_W_m':desired_endpoint.tolist(),
               'kinetic_J':kinetic,'potential_J':potential,'motor_work_J':float(state[4]),
               'external_work_J':float(state[5]),'dissipated_J':float(state[6]),
               'energy_residual_J':float(kinetic+potential-e0-state[4]-state[5]+state[6])}
        rows.append(row)
        if k < steps:
            state = step_rk4(state,actual,plant,dt,config['external_force_W_N'])
            if not np.isfinite(state).all():
                raise ValueError('nonfinite simulated state; preserve as failed run')
    error = np.array([np.array(x['q_rad'])-x['q_ref_rad'] for x in rows])
    tip_error = np.array([np.array(x['endpoint_W_m'])-x['endpoint_ref_W_m'] for x in rows])
    torque_rows = rows[:-1]
    summary = {'case':scenario['id'],'samples':len(rows),'intervals':steps,
               'rms_joint_error_rad':float(np.sqrt(np.mean(np.sum(error*error,axis=1)))),
               'rms_endpoint_error_m':float(np.sqrt(np.mean(np.sum(tip_error*tip_error,axis=1)))),
               'final_joint_error_rad':float(np.linalg.norm(error[-1])),
               'peak_requested_N_m':np.max(np.abs([x['requested_N_m'] for x in torque_rows]),axis=0).tolist(),
               'peak_applied_N_m':np.max(np.abs([x['applied_N_m'] for x in torque_rows]),axis=0).tolist(),
               'limited_intervals':count_limited,
               'max_abs_energy_residual_J':max(abs(x['energy_residual_J']) for x in rows),
               'plant':plant_raw}
    return rows,summary


def reference_path_audit(config):
    p = parameters(config['nominal'])
    obstacle = config['reference_obstacle']
    rows = []
    for duration in sorted({x['reference_duration_s'] for x in config['scenarios']}):
        intervals = round(duration/config['dt_s'])
        for k in range(intervals+1):
            t = k*duration/intervals
            q,v,a = reference(t,config['start_q_rad'],config['goal_q_rad'],duration)
            m,c,g = mechanics(q,v,p)
            torque = m@a+c+g+p['damping_N_m_s']*v
            _,elbow,tip = arm().forward(q,p['lengths_m'])
            radius = obstacle['radius_m']+obstacle['rod_radius_m']
            clear = min(arm().base().segment_clearance([0.,0.],elbow,obstacle['center_W_m'],radius),
                        arm().base().segment_clearance(elbow,tip,obstacle['center_W_m'],radius))
            rows.append({'duration_s':duration,'t_s':t,'q_rad':q.tolist(),'qdot_rad_s':v.tolist(),
                         'qddot_rad_s2':a.tolist(),'inverse_dynamics_N_m':torque.tolist(),
                         'elbow_W_m':elbow.tolist(),'endpoint_W_m':tip.tolist(),'sampled_clearance_m':clear})
    return rows


def examples(config):
    r = rotation_vector(config['rigid']['rotation_vector_rad'])
    t = transform(r, config['rigid']['translation_m'])
    vb,fb = config['rigid']['body_twist'],config['rigid']['body_wrench']
    vs,fs,pdot = body_to_space(t,vb,fb)
    dot_t = t@twist_matrix(vb)
    x = rotation_vector([np.pi/2,0.,0.]); z = rotation_vector([0.,0.,np.pi/2])
    ry = rotation_vector([0.,np.pi/2,0.])
    chart = np.column_stack([ry@np.array([1.,0.,0.]),[0.,1.,0.],[0.,0.,1.]])
    chart_same = rotation_vector([0.,0.,.4])@ry@rotation_vector([.4,0.,0.])
    p = parameters(config['nominal'])
    m,c,g = mechanics([0.,0.],[0.,0.],p)
    static_external = np.array([0.,-2.])
    static_torque = g-arm().jacobian([0.,0.],p['lengths_m']).T@static_external
    # Local linearization at zero speed and the chosen equilibrium, both motors active.
    qstar = np.array(config['goal_q_rad'])
    mstar,_,_ = mechanics(qstar,[0.,0.],p)
    l1 = p['lengths_m'][0]; m1,m2 = p['masses_kg']; r1,r2 = p['com_m']; grav = p['gravity_m_s2']
    h = -grav*np.array([[(m1*r1+m2*l1)*np.sin(qstar[0])+m2*r2*np.sin(qstar.sum()),m2*r2*np.sin(qstar.sum())],
                       [m2*r2*np.sin(qstar.sum()),m2*r2*np.sin(qstar.sum())]])
    inv_m = np.linalg.solve(mstar,np.eye(2))
    a = np.block([[np.zeros((2,2)),np.eye(2)],[-inv_m@h,-inv_m@np.diag(p['damping_N_m_s'])]])
    b = np.vstack([np.zeros((2,2)),inv_m]); obs = np.hstack([np.eye(2),np.zeros((2,2))])
    return {'rigid':{'T_WB':t.tolist(),'inverse_T':inverse_transform(t).tolist(),'adjoint':adjoint(t).tolist(),
                     'V_body':vb,'F_body':fb,'V_space':vs.tolist(),'F_space':fs.tolist(),
                     'body_origin_velocity_W_m_s':pdot.tolist(),'T_dot':dot_t.tolist(),
                     'body_power_W':float(np.array(vb)@fb),'space_power_W':float(vs@fs),
                     'wrong_tip_velocity_power_W':float(np.r_[vs[:3],pdot]@fs),
                     'Rz_Rx_on_y':(z@x@np.array([0.,1.,0.])).tolist(),
                     'Rx_Rz_on_y':(x@z@np.array([0.,1.,0.])).tolist(),
                     'ZYX_space_angle_rate_at_pitch_pi_2':chart.tolist(),
                     'ZYX_rate_rank':int(np.linalg.matrix_rank(chart,tol=1e-12)),
                     'ZYX_equal_roll_yaw_rotation_difference':float(np.linalg.norm(chart_same-ry))},
            'straight_dynamics':{'M_kg_m2':m.tolist(),'c_N_m':c.tolist(),'G_N_m':g.tolist(),
                                  'det_M':float(np.linalg.det(m)),'external_force_W_N':static_external.tolist(),
                                  'static_motor_N_m':static_torque.tolist()},
            'local_linearization':{'qstar_rad':qstar.tolist(),'A':a.tolist(),'B':b.tolist(),'H':obs.tolist(),
                                   'controllability_B_AB_rank':int(np.linalg.matrix_rank(np.hstack([b,a@b]))),
                                   'observability_H_HA_rank':int(np.linalg.matrix_rank(np.vstack([obs,obs@a])))}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kinematics', type=Path)
    parser.add_argument('--base', type=Path)
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[1]/'dynamics-inputs.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-steps', type=int, help='short pre-run truncation only, not a different protocol')
    args = parser.parse_args()
    set_sources(args.kinematics,args.base)
    config = json.loads(args.input.read_text())
    args.output.mkdir(parents=True,exist_ok=True)
    summaries = []
    (args.output/'reference-path.json').write_text(json.dumps(reference_path_audit(config),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with (args.output/'trajectories.jsonl').open('w') as stream:
        for scenario in config['scenarios']:
            rows,summary = simulate(config,scenario,args.max_steps)
            for row in rows:
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
            summaries.append(summary)
    result = {'examples':examples(config),'summaries':summaries,
              'pre_run_max_steps':args.max_steps,
              'thread_limit_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']},
              'inputs_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'kinematics_sha256':hashlib.sha256(_ARM_PATH.read_bytes()).hexdigest(),
              'se2_base_sha256':hashlib.sha256(arm()._BASE_PATH.read_bytes()).hexdigest()}
    (args.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summaries,ensure_ascii=False))


if __name__ == '__main__':
    main()
