"""Planar holonomic acceleration robot. No hardware or external I/O.
State = [px, py, vx, vy], metres and seconds; held acceleration per sample.
Run: python -B robotics_lab.py [--figures]
"""
from pathlib import Path
import argparse
import json
import numpy as np

DT = 0.05
KP, KD, KI, LIMIT = 2.0, 2.0, 0.3, 1.5
SIGMA_A, SIGMA_Z = 0.2, 0.08
THETA = np.pi / 2
WAYPOINTS = np.array([[0., 0.], [0., 1.5], [4., 1.5], [4., 0.]])
DURATIONS = np.array([4., 8., 4.])
OBSTACLE = np.array([2., 0.])
OBSTACLE_RADIUS, ROBOT_RADIUS = 0.4, 0.2


def finite(value, shape, name):
    a = np.asarray(value, dtype=float)
    if a.shape != shape or not np.all(np.isfinite(a)):
        raise ValueError(f'{name}: expected finite shape {shape}')
    return a


def positive(value, name, allow_zero=False):
    v = float(value)
    if not np.isfinite(v) or v < 0 or (not allow_zero and v == 0):
        raise ValueError(f'{name}: expected finite positive value')
    return v


def covariance(value, n, name, strict=False):
    a = finite(value, (n, n), name)
    if not np.allclose(a, a.T, atol=1e-12, rtol=1e-12):
        raise ValueError(f'{name}: not symmetric')
    eigen = np.linalg.eigvalsh(a)
    if eigen.min() < -1e-12 or (strict and eigen.min() <= 0):
        raise ValueError(f'{name}: invalid covariance')
    return (a + a.T) / 2


def rotation(theta):
    theta = float(theta)
    if not np.isfinite(theta):
        raise ValueError('theta must be finite radians')
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def se2(p, theta):
    T = np.eye(3)
    T[:2, :2] = rotation(theta)
    T[:2, 2] = finite(p, (2,), 'p')
    return T


def model(dt=DT):
    dt = positive(dt, 'dt')
    if dt > np.sqrt(np.finfo(float).max) or dt*dt == 0:
        raise ValueError('dt squared is not representable in float64')
    A = np.eye(4)
    A[:2, 2:] = dt * np.eye(2)
    B = np.vstack([0.5 * dt**2 * np.eye(2), dt * np.eye(2)])
    return A, B


def predict(mean, P, u, Q, dt=DT):
    mean = finite(mean, (4,), 'mean')
    P, Q = covariance(P, 4, 'P'), covariance(Q, 4, 'Q')
    u = finite(u, (2,), 'u_world')
    A, B = model(dt)
    return A @ mean + B @ u, A @ P @ A.T + Q


def update(mean, P, z, H, R):
    mean = finite(mean, (4,), 'mean')
    P = covariance(P, 4, 'P')
    H = np.asarray(H, dtype=float)
    if H.ndim != 2 or H.shape[1] != 4 or H.shape[0] == 0:
        raise ValueError('H must have shape (m,4), m>0')
    H = finite(H, H.shape, 'H')
    m = H.shape[0]
    z, R = finite(z, (m,), 'z'), covariance(R, m, 'R', strict=True)
    innovation = z - H @ mean
    S = H @ P @ H.T + R
    # Solve S K.T = H P; never explicitly invert innovation covariance.
    K = np.linalg.solve(S, H @ P).T
    J = np.eye(4) - K @ H
    post = J @ P @ J.T + K @ R @ K.T  # Joseph covariance
    return mean + K @ innovation, (post + post.T) / 2, innovation, S


def discrete_bayes(prior, transition, likelihood):
    p = np.asarray(prior, dtype=float)
    if p.ndim != 1 or len(p) == 0:
        raise ValueError('prior must be nonempty vector')
    n = len(p)
    p = finite(p, (n,), 'prior')
    T = finite(transition, (n, n), 'transition')
    L = finite(likelihood, (n,), 'likelihood')
    if np.any(p < 0) or np.any(T < 0) or np.any(L < 0):
        raise ValueError('negative probability or likelihood')
    if not np.isclose(p.sum(), 1) or not np.allclose(T.sum(axis=0), 1):
        raise ValueError('prior / transition not normalized (columns are previous state)')
    predicted = T @ p
    # Scaling likelihood avoids overflow; evidence remains in original scale.
    scale = L.max()
    if scale == 0:
        raise ValueError('zero evidence')
    weights = predicted * (L / scale)
    mass = weights.sum()
    if mass <= 0:
        raise ValueError('zero evidence')
    return predicted, weights / mass, float(mass * scale)


def observability_rank(H, dt=DT):
    H = np.asarray(H, dtype=float)
    if H.ndim != 2 or H.shape[1] != 4 or H.shape[0] == 0:
        raise ValueError('H shape')
    H = finite(H, H.shape, 'H')
    A, _ = model(dt)
    return int(np.linalg.matrix_rank(np.vstack([H @ np.linalg.matrix_power(A, i) for i in range(4)])))


def reference(t):
    t = positive(t, 't', allow_zero=True)
    ends = np.cumsum(DURATIONS)
    if t >= ends[-1]:
        return WAYPOINTS[-1].copy(), np.zeros(2), np.zeros(2)
    j = int(np.searchsorted(ends, t, side='right'))
    start = 0. if j == 0 else ends[j - 1]
    tau, duration = (t - start) / DURATIONS[j], DURATIONS[j]
    s = 10*tau**3 - 15*tau**4 + 6*tau**5
    sd = (30*tau**2 - 60*tau**3 + 30*tau**4) / duration
    sdd = (60*tau - 180*tau**2 + 120*tau**3) / duration**2
    d = WAYPOINTS[j+1] - WAYPOINTS[j]
    return WAYPOINTS[j] + d*s, d*sd, d*sdd


def segment_clearance(a, b, center=OBSTACLE, radius=OBSTACLE_RADIUS+ROBOT_RADIUS):
    a, b, c = (finite(x, (2,), name) for x, name in [(a, 'a'), (b, 'b'), (center, 'center')])
    radius = positive(radius, 'radius', allow_zero=True)
    d = b - a
    tau = 0. if d @ d == 0 else np.clip((c-a) @ d / (d @ d), 0, 1)
    return float(np.linalg.norm(a + tau*d - c) - radius)


def pid(mean, integral, t, dt=DT, limit=LIMIT, gains=(KP, KD, KI)):
    mean, integral = finite(mean, (4,), 'mean'), finite(integral, (2,), 'integral')
    dt, limit = positive(dt, 'dt'), positive(limit, 'limit')
    gains = finite(gains, (3,), 'gains')
    if np.any(gains < 0):
        raise ValueError('negative gains')
    kp, kd, ki = gains
    p, v, a = reference(t)
    ep, ev = p - mean[:2], v - mean[2:]
    raw = a + kp*ep + kd*ev + ki*integral
    u = np.clip(raw, -limit, limit)  # per WORLD axis limits
    # Conditional integration: freeze only when error drives further into saturation.
    freeze = ((raw > limit) & (ki*ep > 0)) | ((raw < -limit) & (ki*ep < 0))
    next_integral = integral + dt * np.where(freeze, 0, ep)
    return u, next_integral, raw


def pid_error_matrix(dt=DT, gains=(KP, KD, KI)):
    dt = positive(dt, 'dt')
    kp, kd, ki = finite(gains, (3,), 'gains')
    A = np.array([[1., dt], [0., 1.]])
    B = np.array([[dt**2/2], [dt]])
    C = np.zeros((3, 3))
    C[:2, :2] = A - B @ np.array([[kp, kd]])
    C[:2, 2] = -B[:, 0]*ki
    C[2] = [dt, 0., 1.]
    return C


def simulate(seed=7, bias=(0., 0.), kick=True, noise=True, duration=24., dt=DT):
    duration, dt = positive(duration, 'duration'), positive(dt, 'dt')
    if duration / dt > 200000:
        raise ValueError('simulation too long')
    bias = finite(bias, (2,), 'bias')
    rng = np.random.default_rng(seed)
    A, B = model(dt)
    H, R = np.eye(4)[:2], SIGMA_Z**2*np.eye(2)
    Q = SIGMA_A**2 * B @ B.T
    true, mean, P = np.zeros(4), np.zeros(4), np.diag([.1, .1, 1., 1.])
    integral = np.zeros(2)
    rows = {key: [] for key in ['t', 'truth', 'observed', 'estimate', 'reference', 'u', 'P', 'innovation']}
    kicked = False
    for k in range(int(np.floor(duration/dt)) + 1):
        t = k*dt
        if kick and not kicked and t >= 10.:
            true[2:] += np.array([0.8, -0.5])  # velocity impulse in m/s
            kicked = True
        z = H @ true + bias + (rng.normal(0, SIGMA_Z, 2) if noise else 0)
        mean, P, innovation, _ = update(mean, P, z, H, R)
        u, integral, _ = pid(mean, integral, t, dt)
        # World command -> body actuator -> world motion, orientation known/fixed.
        body_u = rotation(THETA).T @ u
        applied_world = rotation(THETA) @ body_u
        p, v, _ = reference(t)
        for key, value in [('t', t), ('truth', true.copy()), ('observed', z), ('estimate', mean.copy()),
                           ('reference', np.r_[p, v]), ('u', u), ('P', P.copy()), ('innovation', innovation)]:
            rows[key].append(value)
        accel_noise = rng.normal(0, SIGMA_A, 2) if noise else np.zeros(2)
        true = A @ true + B @ (applied_world + accel_noise)
        mean, P = predict(mean, P, u, Q, dt)
    return {k: np.asarray(v) for k, v in rows.items()}


def metrics(data):
    error = np.linalg.norm(data['truth'][:, :2] - data['reference'][:, :2], axis=1)
    est = np.linalg.norm(data['estimate'][:, :2] - data['truth'][:, :2], axis=1)
    tail = data['t'] >= data['t'][-1] - 3.
    after = (data['t'] >= 10.) & (data['t'] <= 12.)
    return {'tracking_rmse_m': float(np.sqrt(np.mean(error**2))),
            'estimate_rmse_m': float(np.sqrt(np.mean(est**2))),
            'post_kick_peak_m': float(error[after].max()) if np.any(after) else None,
            'last_3s_tracking_rmse_m': float(np.sqrt(np.mean(error[tail]**2))),
            'last_3s_estimated_error_rmse_m': float(np.sqrt(np.mean(np.sum(
                (data['estimate'][tail, :2]-data['reference'][tail, :2])**2, axis=1)))),
            'sampled_clearance_m': float((np.linalg.norm(data['truth'][:, :2]-OBSTACLE, axis=1)
                                            - OBSTACLE_RADIUS-ROBOT_RADIUS).min())}


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    plt.rcParams['svg.hashsalt'] = 'wwl-robotics-fixed-v1'
    out = Path(__file__).parent / 'assets'
    out.mkdir(exist_ok=True)
    nominal, biased = simulate(), simulate(bias=(.6, 0.))
    def save(fig, name):
        target = out / name
        fig.savefig(target, format='svg', metadata={'Date': None})
        target.write_text('\n'.join(line.rstrip() for line in target.read_text(encoding='utf-8').splitlines()).rstrip('\n') + '\n', encoding='utf-8')
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 4), layout='constrained')
    p, R = np.array([1., 2.]), rotation(THETA)
    ax.scatter(*p, label='body origin (1,2) m')
    for i, c in enumerate(['tab:red', 'tab:green']):
        ax.arrow(*p, *(R[:, i]*.7), color=c, head_width=.08, length_includes_head=True)
        ax.text(*(p+R[:, i]*.9), ['body x', 'body y'][i])
    sensor = p + R @ np.array([.2, 0.])
    ax.scatter(*sensor, marker='x', label='sensor body (.2,0) -> world (1,2.2)')
    ax.set(xlim=(-.3, 2), ylim=(-.2, 3), xlabel='world x (m)', ylabel='world y (m)',
           title='Known orientation pi/2 rad; points translate, vectors do not')
    ax.set_aspect('equal'); ax.grid(); ax.legend(fontsize=8)
    save(fig, 'robotics-frames.svg')
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), layout='constrained')
    ax = axes[0, 0]
    ax.plot(*nominal['reference'][:, :2].T, '--', label='reference')
    ax.plot(*nominal['truth'][:, :2].T, label='truth')
    ax.plot(*nominal['estimate'][:, :2].T, label='estimate', alpha=.7)
    ax.scatter(*nominal['observed'][::10].T, s=7, alpha=.4, label='position observed')
    ax.add_patch(Circle(OBSTACLE, .4, color='gray', alpha=.5))
    ax.add_patch(Circle(OBSTACLE, .6, fill=False, linestyle=':', label='inflated obstacle'))
    ax.set(xlabel='world x (m)', ylabel='world y (m)', title='Nominal closed loop; seed 7')
    ax.set_aspect('equal'); ax.legend(fontsize=7, loc='upper center', bbox_to_anchor=(.5, -.23), ncol=3)
    ax = axes[0, 1]
    for key, label in [('truth','truth vx'), ('estimate','estimated vx'), ('reference','reference vx')]:
        ax.plot(nominal['t'], nominal[key][:, 2], label=label)
    ax.axvline(10, color='gray', linestyle=':'); ax.set(xlabel='time (s)', ylabel='velocity (m/s)', title='Impulse at 10 s'); ax.legend(fontsize=7)
    ax = axes[1, 0]
    for data, label in [(nominal, 'unbiased'), (biased, 'sensor bias +0.6 m x')]:
        ax.plot(data['t'], np.linalg.norm(data['truth'][:, :2]-data['reference'][:, :2], axis=1), label=label)
    ax.plot(biased['t'], np.linalg.norm(biased['estimate'][:, :2]-biased['reference'][:, :2], axis=1), '--', label='biased estimated error')
    ax.set(xlabel='time (s)', ylabel='position tracking error (m)', title='Small estimated error can hide real offset'); ax.legend(fontsize=7)
    ax = axes[1, 1]
    sigma = np.sqrt(nominal['P'][:, 0, 0])
    ax.plot(nominal['t'], nominal['estimate'][:, 0]-nominal['truth'][:, 0], label='estimated x - true x')
    ax.fill_between(nominal['t'], -2*sigma, 2*sigma, alpha=.3, label='model +/-2 sigma x')
    ax.set(xlabel='time (s)', ylabel='estimation error (m)', title='Model interval; no calibrated coverage claim'); ax.legend(fontsize=7)
    for ax in axes.flat: ax.grid(alpha=.3)
    save(fig, 'robotics-closed-loop.svg')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true')
    args = parser.parse_args()
    result = {'nominal': metrics(simulate()), 'sensor_bias': metrics(simulate(bias=(.6, 0.))),
              'pid_poles': [str(x) for x in np.linalg.eigvals(pid_error_matrix())],
              'route_clearances_m': [segment_clearance(a,b) for a,b in zip(WAYPOINTS[:-1],WAYPOINTS[1:])]}
    print(json.dumps(result, indent=2))
    if args.figures: figures()
