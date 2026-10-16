"""Fixed-base planar 2R position kinematics; m, rad, s, N. No dynamics.
Reuse the published robotics_lab.py column-vector SE(2), never its point-mass model.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

_BASE = None
_BASE_PATH = None


def set_base(path=None):
    global _BASE, _BASE_PATH
    path = Path(path) if path is not None else Path(__file__).resolve().parents[2] / 'robotics_lab.py'
    spec = importlib.util.spec_from_file_location('wwl_planar_base', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _BASE, _BASE_PATH = module, path.resolve()


def base():
    if _BASE is None:
        set_base()
    return _BASE


def inputs(q, lengths):
    q = base().finite(q, (2,), 'q radians')
    lengths = base().finite(lengths, (2,), 'link metres')
    if np.any(lengths <= 0):
        raise ValueError('link lengths must be strictly positive')
    return q, lengths


def forward(q, lengths=(1., 1.)):
    """T_WE (3,3), elbow_W (2,), endpoint_W (2,); right factor acts first."""
    q, lengths = inputs(q, lengths)
    first = base().se2([0., 0.], q[0])
    second = base().se2([lengths[0], 0.], q[1])
    tool = base().se2([lengths[1], 0.], 0.)
    transform = first @ second @ tool
    elbow = (first @ np.array([lengths[0], 0., 1.]))[:2]
    return transform, elbow, transform[:2, 2].copy()


def jacobian(q, lengths=(1., 1.)):
    """Position derivative d(x_W,y_W)/d(q1,q2), 2x2, m/rad."""
    q, (a, b) = inputs(q, lengths)
    s1, c1 = np.sin(q[0]), np.cos(q[0])
    s12, c12 = np.sin(q.sum()), np.cos(q.sum())
    return np.array([[-a*s1-b*s12, -b*s12], [a*c1+b*c12, b*c12]])


def pose_jacobian(q, lengths=(1., 1.)):
    """Local coordinate derivative (x_W,y_W,phi)/q; not a spatial twist J."""
    return np.vstack([jacobian(q, lengths), [1., 1.]])


def inverse(target, lengths=(1., 1.), cosine_tolerance=1e-12):
    """Unconstrained position IK modulo 2pi. Exact zero/equal lengths => continuum.
    Only |c2|-1 <= tolerance is clamped; boundary answers are numerical.
    """
    _, (a, b) = inputs([0., 0.], lengths)
    target = base().finite(target, (2,), 'target metres')
    tolerance = base().positive(cosine_tolerance, 'cosine tolerance', allow_zero=True)
    if np.all(target == 0.) and a == b:
        return {'kind': 'continuum', 'branches': [], 'family': 'q1 arbitrary; q2 = pi modulo 2pi'}
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        c = float((target @ target - a*a - b*b) / (2*a*b))
    if not np.isfinite(c):
        raise ValueError('cosine not representable')
    if abs(c) > 1. + tolerance:
        return {'kind': 'unreachable', 'branches': [], 'cosine_raw': c}
    clipped = float(np.clip(c, -1., 1.))
    sine = np.sqrt(max(0., 1.-clipped*clipped))
    signs = [1.] if sine == 0. else [1., -1.]
    branches = []
    for sign in signs:
        q2 = np.arctan2(sign*sine, clipped)
        q1 = np.arctan2(target[1], target[0]) - np.arctan2(b*np.sin(q2), a+b*np.cos(q2))
        q = (np.array([q1, q2]) + np.pi) % (2*np.pi) - np.pi
        branches.append(q.tolist())
    return {'kind': 'boundary' if sine == 0. else 'two_branches', 'branches': branches,
            'cosine_raw': c, 'cosine_clamped': clipped}


def power(q, qdot, force, lengths=(1., 1.)):
    """F is desired robot-on-environment endpoint force, both F and v in W.
    tau = J.T F is its ideal port-equivalent joint torque, not inverse dynamics.
    """
    j = jacobian(q, lengths)
    qdot = base().finite(qdot, (2,), 'joint rad/s')
    force = base().finite(force, (2,), 'endpoint force N')
    velocity, torque = j @ qdot, j.T @ force
    return {'velocity_m_s': velocity.tolist(), 'torque_N_m': torque.tolist(),
            'endpoint_power_W': float(force @ velocity), 'joint_power_W': float(torque @ qdot)}


def speed_request(q, velocity, limit, lengths=(1., 1.)):
    j = jacobian(q, lengths)
    velocity = base().finite(velocity, (2,), 'velocity m/s')
    limit = base().positive(limit, 'joint speed rad/s')
    # This API reports inverse demand only at numerically nonsingular configurations.
    if np.linalg.svd(j, compute_uv=False)[-1] <= 1e-12:
        raise ValueError('position Jacobian numerically singular; no ordinary inverse')
    demand = np.linalg.solve(j, velocity)
    scale = min(1., limit / max(float(np.max(np.abs(demand))), np.finfo(float).tiny))
    scaled = scale * demand
    clipped = np.clip(demand, -limit, limit)
    return {'demand_rad_s': demand.tolist(), 'scale': scale,
            'scaled_rad_s': scaled.tolist(), 'scaled_velocity_m_s': (j @ scaled).tolist(),
            'clipped_rad_s': clipped.tolist(), 'clipped_velocity_m_s': (j @ clipped).tolist()}


def run(config):
    cases = []
    for item in config['configurations']:
        q, lengths = item['q_rad'], item['lengths_m']
        transform, elbow, endpoint = forward(q, lengths)
        j = jacobian(q, lengths)
        cases.append({**item, 'T_WE': transform.tolist(), 'elbow_W_m': elbow.tolist(),
                      'endpoint_W_m': endpoint.tolist(), 'J_position_m_rad': j.tolist(),
                      'J_pose': pose_jacobian(q, lengths).tolist(),
                      'singular_values_m_rad': np.linalg.svd(j, compute_uv=False).tolist(),
                      'position_rank_at_1e-12': int(np.linalg.matrix_rank(j, tol=1e-12)),
                      'pose_rank_at_1e-12': int(np.linalg.matrix_rank(pose_jacobian(q, lengths), tol=1e-12))})
    ik = []
    for item in config['targets']:
        answer = inverse(item['target_W_m'], item['lengths_m'])
        checked = []
        for q in answer['branches']:
            _, _, endpoint = forward(q, item['lengths_m'])
            checked.append({'q_rad': q, 'endpoint_W_m': endpoint.tolist(),
                            'residual_m': float(np.linalg.norm(endpoint - item['target_W_m']))})
        ik.append({**item, **answer, 'forward_checks': checked})
    near = []
    for epsilon in config['near_singular']['epsilon_rad']:
        q = [0., epsilon]
        near.append({'epsilon_rad': epsilon,
                     'sigma_min_m_rad': float(np.linalg.svd(jacobian(q), compute_uv=False)[-1]),
                     **speed_request(q, config['near_singular']['velocity_W_m_s'],
                                     config['near_singular']['joint_limit_rad_s'])})
    curve = []
    for epsilon in config['null_curve_epsilon_rad']:
        q = [epsilon, -2*epsilon]
        _, elbow, endpoint = forward(q)
        curve.append({'epsilon_rad': epsilon, 'q_rad': q, 'elbow_W_m': elbow.tolist(),
                      'endpoint_W_m': endpoint.tolist(), 'inward_displacement_m': float(2.-endpoint[0])})
    return {'model': config['model'], 'units': config['units'], 'configurations': cases,
            'targets': ik, 'power_cases': [{**item, **power(item['q_rad'], item['qdot_rad_s'], item['force_W_N'])}
                                         for item in config['power_cases']],
            'near_singular': near, 'null_curve': curve,
            'base_sha256': hashlib.sha256(_BASE_PATH.read_bytes()).hexdigest(),
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, help='published robotics_lab.py; needed in isolated candidate')
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[1] / 'inputs.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    set_base(args.base)
    config = json.loads(args.input.read_text())
    result = run(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'configurations': len(result['configurations']), 'targets': len(result['targets']),
                      'power_cases': len(result['power_cases']), 'near_singular': len(result['near_singular'])}))


if __name__ == '__main__':
    main()
