"""Finite surface transport laboratory. No general scene engine, GPU or photometric calibration."""
from pathlib import Path
from functools import lru_cache
import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import numpy as np

ROOT = Path(__file__).resolve().parent
SAMPLERS = ('uniform', 'cosine', 'cap')
SCENARIOS = ('constant', 'cone', 'visibility')


def real(value, low, high):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError('expected finite non-bool real scalar')
    x = float(value)
    if not math.isfinite(x) or not low <= x <= high:
        raise ValueError('scalar outside declared finite range')
    return x


def integer(value, low, high):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or not low <= value <= high:
        raise ValueError('expected bounded non-bool integer')
    return int(value)


def finite(value, last=None):
    a = np.asarray(value)
    if a.dtype.kind not in 'iuf' or (last is not None and (a.ndim == 0 or a.shape[-1] != last)):
        raise ValueError('expected finite real array with declared last dimension')
    a = a.astype(float)
    if not np.isfinite(a).all() or np.any(np.abs(a) > 1e20):
        raise ValueError('array outside declared finite range')
    return a


def uniforms(value):
    a = finite(value, 2)
    if np.any((a <= 0) | (a > 1)):
        raise ValueError('uniform coordinates must be in (0,1]')
    return a


def random_uv(rng, shape):
    # In (0,1], so this finite implementation never divides by a sampled horizon PDF.
    return 1-rng.random((*shape, 2))


def hemisphere(uv, method):
    u = uniforms(uv)
    if method == 'uniform':
        mu = u[..., 0]
        pdf = np.full_like(mu, 1/(2*np.pi))
    elif method == 'cosine':
        mu = np.sqrt(u[..., 0])
        pdf = mu/np.pi
    elif method == 'cap':
        mu = .5+.5*u[..., 0]
        pdf = np.full_like(mu, 1/np.pi)
    else:
        raise ValueError('unknown hemisphere sampler')
    phi = 2*np.pi*u[..., 1]
    radius = np.sqrt(np.maximum(0., 1-mu*mu))
    direction = np.stack([radius*np.cos(phi), radius*np.sin(phi), mu], axis=-1)
    return direction, pdf


def aperture_visibility(direction):
    # At the benchmark point: black plane 2m above, circular opening R=2*sqrt(3)m.
    d = finite(direction, 3)
    if np.any(d[..., 2] <= 0):
        raise ValueError('aperture rays require positive local z')
    hit_xy = 2*d[..., :2]/d[..., 2, None]
    return (np.sum(hit_xy*hit_xy, axis=-1) <= 12).astype(float)


def lambert_samples(rho, li, method, scenario, uv, *, wrong_pdf=False):
    rho, li = real(rho, 0, 1), real(li, 0, 100)
    if scenario not in SCENARIOS or type(wrong_pdf) is not bool:
        raise ValueError('unknown incident/visibility contract')
    direction, pdf = hemisphere(uv, method)
    mu = direction[..., 2]
    incident = np.ones_like(mu) if scenario != 'cone' else (mu >= .5).astype(float)
    visible = np.ones_like(mu) if scenario != 'visibility' else aperture_visibility(direction)
    used_pdf = np.full_like(pdf, 1/(2*np.pi)) if wrong_pdf else pdf
    return (rho/np.pi)*li*incident*visible*mu/used_pdf


def lambert_theory(rho, li, method, scenario):
    c = real(rho, 0, 1)*real(li, 0, 100)
    if method not in SAMPLERS or scenario not in SCENARIOS:
        raise ValueError('unknown theory contract')
    target = c if scenario == 'constant' else .75*c
    if method == 'cap':
        mean, var = .75*c, c*c/48
    elif method == 'cosine':
        mean = target
        var = 0. if scenario == 'constant' else 3*c*c/16
    else:
        mean = target
        var = c*c/3 if scenario == 'constant' else 29*c*c/48
    return {'target': target, 'mean': mean, 'single_variance': var, 'bias': mean-target}


def disk_samples(rho, le, radius, distance, uv):
    c = real(rho, 0, 1)*real(le, 0, 100)
    radius, distance = real(radius, .01, 100), real(distance, .01, 100)
    u = uniforms(uv)
    radial = radius*np.sqrt(u[..., 0])
    phi = 2*np.pi*u[..., 1]
    point = np.stack([radial*np.cos(phi), radial*np.sin(phi),
                      np.full_like(radial, distance)], axis=-1)
    r2 = np.sum(point*point, axis=-1)
    mu = distance/np.sqrt(r2)
    pdf_area = 1/(np.pi*radius*radius)
    pdf_solid = pdf_area*r2/mu
    weight_area = (c/np.pi)*(mu*mu/r2)/pdf_area
    weight_solid = (c/np.pi)*mu/pdf_solid
    # Deliberate dimensionally-invalid numeric counterexample: p_A used as p_omega.
    wrong = (c/np.pi)*mu/pdf_area
    return point, weight_area, weight_solid, wrong


def disk_theory(rho, le, radius, distance):
    c = real(rho, 0, 1)*real(le, 0, 100)
    radius, distance = real(radius, .01, 100), real(distance, .01, 100)
    t = (radius/distance)**2
    mean = c*t/(1+t)
    variance = c*c*t**4/(3*(1+t)**3)  # algebraic form avoids tiny-t cancellation
    # Stable form of 2*C*d*(sqrt(d²+R²)-d), but not a radiance unit.
    wrong = 2*c*distance*radius*radius/(math.hypot(distance, radius)+distance)
    return {'mean': mean, 'single_variance': variance,
            'wrong_pdf_numeric_mean_not_radiance': wrong}


def path_parameters(rho_floor, rho_ceiling, le, cone, survival=.5):
    rf, rc, le = real(rho_floor, 0, .95), real(rho_ceiling, 0, .95), real(le, 0, 100)
    cone, survival = real(cone, 0, .95), real(survival, .2, .95)
    if rf*rc >= survival:
        raise ValueError('teaching RR contract requires rho_floor*rho_ceiling < survival')
    return rf, rc, le, cone, survival


def plane_step(origin, uv, floor, rho):
    if type(floor) is not bool:
        raise ValueError('floor selector must be bool')
    rho = real(rho, 0, .95)
    origin, u = finite(origin, 3), uniforms(uv)
    if origin.shape[:-1] != u.shape[:-1] or not np.all(origin[..., 2] == (-2 if floor else 2)):
        raise ValueError('origins must lie on declared current plane and match samples')
    local, pdf = hemisphere(u, 'cosine')
    direction = local.copy()
    direction[..., 2] *= 1 if floor else -1
    target_z = 2. if floor else -2.
    length = (target_z-origin[..., 2])/direction[..., 2]
    hit = origin+length[..., None]*direction
    hit[..., 2] = target_z
    if not np.isfinite(hit).all():
        raise ValueError('nonfinite ray-plane hit')
    factor = (rho/np.pi)*local[..., 2]/pdf
    return hit, local[..., 2], pdf, factor, direction, length


def fixed_paths(origins, uv, rho_floor=.6, rho_ceiling=.5, le=4., cone=.5):
    rf, rc, le, cone, _ = path_parameters(rho_floor, rho_ceiling, le, cone)
    origin, u = finite(origins, 3), uniforms(uv)
    if origin.ndim != 2 or u.ndim != 3 or u.shape != (len(origin), 5, 2):
        raise ValueError('fixed path array shapes must be (N,3) and (N,5,2)')
    if not np.all(origin[:, 2] == -2):
        raise ValueError('paths start on floor z=-2m')
    beta = np.ones(len(origin))
    total = np.zeros(len(origin))
    cumulative, log = [], []
    pdf_product = np.ones(len(origin))
    for step in range(5):
        floor = step % 2 == 0
        old = origin.copy()
        origin, mu, pdf, factor, direction, length = plane_step(origin, u[:, step], floor, rf if floor else rc)
        beta *= factor
        pdf_product *= pdf
        emitted = le*(mu >= cone) if floor else np.zeros(len(origin))
        contribution = beta*emitted
        total += contribution
        if floor:
            cumulative.append(total.copy())
        if len(origin):
            log.append({'reflection_count': step+1, 'surface': 'floor' if floor else 'ceiling',
                'origin_m': old[0].tolist(), 'direction': direction[0].tolist(),
                'distance_m': float(length[0]), 'hit_m': origin[0].tolist(), 'cos': float(mu[0]),
                'pdf_sr_inverse': float(pdf[0]), 'joint_direction_pdf': float(pdf_product[0]),
                'throughput': float(beta[0]), 'hit_emission': float(emitted[0]),
                'contribution_W_m2_sr': float(contribution[0])})
    return np.array(cumulative).T, log


def rr_paths(origins, rng, rho_floor=.6, rho_ceiling=.5, le=4., cone=.5, survival=.5):
    rf, rc, le, cone, survival = path_parameters(rho_floor, rho_ceiling, le, cone, survival)
    origin = finite(origins, 3).copy()
    if origin.ndim != 2 or not np.all(origin[:, 2] == -2):
        raise ValueError('RR paths start at floor z=-2m')
    count = len(origin)
    values, beta = np.zeros(count), np.ones(count)
    active = np.arange(count)
    cycles, segments = 0, 0
    while len(active):
        cycles += 1
        if cycles > 10000:
            raise RuntimeError('execution guard raises; never return a silently truncated RR estimate')
        hit, mu, _, factor, _, _ = plane_step(origin[active], random_uv(rng, (len(active),)), True, rf)
        origin[active] = hit
        beta[active] *= factor
        values[active] += beta[active]*le*(mu >= cone)
        segments += len(active)
        keep = rng.random(len(active)) < survival
        active = active[keep]
        beta[active] /= survival
        if len(active):
            hit, _, _, factor, _, _ = plane_step(origin[active], random_uv(rng, (len(active),)), False, rc)
            origin[active] = hit
            beta[active] *= factor
            segments += len(active)
    return values, {'paths': count, 'max_emission_visits': cycles, 'total_ray_segments': segments}


def path_theory(rho_floor=.6, rho_ceiling=.5, le=4., cone=.5, survival=.5):
    rf, rc, le, cone, survival = path_parameters(rho_floor, rho_ceiling, le, cone, survival)
    a, c, b = rf*rc, rf*le, 1-cone*cone
    mean = c*b/(1-a)
    finite_terms = []
    for m in (1, 2, 3):
        partial = c*b*(1-a**m)/(1-a)
        var = c*c*b*(1-b)*(1-a**(2*m))/(1-a*a)
        finite_terms.append({'reflections': 2*m-1, 'mean': partial, 'single_variance': var,
                             'bias_to_full': partial-mean})
    second = (c*c*b+2*c*b*a*mean)/(1-a*a/survival)
    return {'full_mean': mean, 'a': a, 'emission_probability': b, 'finite': finite_terms,
            'rr_single_variance': max(0., second-mean*mean)}


def ggx_ndf(mu, alpha):
    mu, alpha = finite(mu), real(alpha, .05, 1.)
    if np.any((mu < 0) | (mu > 1)):
        raise ValueError('GGX cosine must be in [0,1]')
    return alpha*alpha/(np.pi*(1+(alpha*alpha-1)*mu*mu)**2)


def tone_map(radiance, exposure=1., reference=1.):
    a = finite(radiance)
    exposure, reference = real(exposure, .001, 100), real(reference, .001, 100)
    if np.any(a < 0):
        raise ValueError('nonnegative band radiance required')
    x = exposure*a/reference
    return x/(1+x)


@lru_cache(maxsize=1)
def renderer():
    path = Path(os.environ.get('WWL_RENDERER_SOURCE', ROOT.parents[1]/'62-图形学'/'renderer.py')).resolve()
    spec = importlib.util.spec_from_file_location('wwl_readonly_renderer_transport', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def scene():
    s = json.loads((ROOT/'scene.json').read_text())
    if (s['contract'] != 'single-band-parallel-planes-v1' or s['floor_z_m'] != -2
            or s['ceiling_z_m'] != 2 or s['viewport'] != [64, 64]):
        raise ValueError('fixed plane geometry and viewport contract')
    return s


def observation():
    s = scene()
    pos = finite(s['observation_positions'], 3)
    if pos.shape != (3, 3) or s['observation_triangles'] != [[0, 1, 2]]:
        raise ValueError('fixed observation triangle contract')
    r, _ = renderer()
    clip = (r.perspective() @ np.column_stack([pos, np.ones(3)]).T).T
    if not np.all(clip[:, 3] == 2):
        raise ValueError('observation plane must remain z=-2')
    ndc = clip[:, :3]/clip[:, 3, None]
    screen = np.column_stack([(ndc[:, 0]+1)*32, (1-ndc[:, 1])*32])
    if r.edge(*screen) < 0:
        screen, pos, clip = screen[[0, 2, 1]], pos[[0, 2, 1]], clip[[0, 2, 1]]
    coords, points = [], []
    for x, y, lam in r.samples(screen, 64, 64):
        coords.append([x, y])
        points.append(r.interpolate(lam, clip[:, 3], pos))
    return np.array(coords), np.array(points), screen


def generate(output):
    s = scene()
    rho, li = s['benchmark_rho'], s['benchmark_Li_W_m2_sr']
    rep, ns = s['benchmark_replicates'], s['benchmark_n']
    rng = np.random.Generator(np.random.PCG64(s['benchmark_seed']))
    estimates = np.zeros((3, 3, len(ns), rep))
    benchmark = []
    for si, scenario in enumerate(SCENARIOS):
        for mi, method in enumerate(SAMPLERS):
            values = lambert_samples(rho, li, method, scenario, random_uv(rng, (rep, max(ns))))
            cumulative = np.cumsum(values, axis=1)
            theory = lambert_theory(rho, li, method, scenario)
            for ni, n in enumerate(ns):
                est = cumulative[:, n-1]/n
                estimates[si, mi, ni] = est
                benchmark.append({'scenario': scenario, 'method': method, 'n': n, **theory,
                    'expected_mse': theory['single_variance']/n+theory['bias']**2,
                    'observed_mean': float(np.mean(est)),
                    'observed_variance': float(np.var(est, ddof=1)),
                    'observed_mse': float(np.mean((est-theory['target'])**2))})
    fixed_uv = np.column_stack([np.array([1, 3, 5, 7])/8]*2)
    fixed = {m: {'uv': fixed_uv.tolist(), 'direction': hemisphere(fixed_uv, m)[0].tolist(),
        'pdf': hemisphere(fixed_uv, m)[1].tolist(),
        'constant_contribution': lambert_samples(rho, li, m, 'constant', fixed_uv).tolist()}
        for m in SAMPLERS}
    wrong = lambert_samples(rho, li, 'cosine', 'constant', random_uv(rng, (65536,)), wrong_pdf=True)
    disk_uv = random_uv(rng, (65536,))
    disk_le = s['disk_emission_W_m2_sr']
    _, wa, wo, wrong_area = disk_samples(rho, disk_le, s['disk_radius_m'], s['disk_distance_m'], disk_uv)
    _, scaled, _, scaled_wrong = disk_samples(rho, disk_le, 2*s['disk_radius_m'], 2*s['disk_distance_m'], disk_uv)
    disk = {'theory': disk_theory(rho, disk_le, s['disk_radius_m'], s['disk_distance_m']), 'observed_mean': float(np.mean(wa)),
        'area_vs_solid_max_abs': float(np.max(np.abs(wa-wo))),
        'rescaled_correct_max_abs': float(np.max(np.abs(wa-scaled))),
        'wrong_numeric_mean': float(np.mean(wrong_area)),
        'rescaled_wrong_ratio': float(np.mean(scaled_wrong)/np.mean(wrong_area)),
        'wrong_units': 'not radiance; p_A incorrectly treated as p_omega'}
    coords, points, screen = observation()
    spp = s['image_spp']
    irng = np.random.Generator(np.random.PCG64(s['image_seed']))
    origins = np.repeat(points, max(spp), axis=0)
    uv = random_uv(irng, (len(origins), 5))
    fixed_values, path_log = fixed_paths(origins, uv, s['rho_floor'], s['rho_ceiling'],
                                        s['ceiling_emission_W_m2_sr'], s['emission_cos_min'])
    rr_values, rr_record = rr_paths(origins, irng, s['rho_floor'], s['rho_ceiling'],
        s['ceiling_emission_W_m2_sr'], s['emission_cos_min'], s['rr_survival'])
    values = np.column_stack([fixed_values, rr_values]).reshape(len(points), max(spp), 4)
    images = np.zeros((4, len(spp), 64, 64))
    mask = np.zeros((64, 64), dtype=bool)
    path_stats = []
    theory = path_theory(s['rho_floor'], s['rho_ceiling'], s['ceiling_emission_W_m2_sr'],
                         s['emission_cos_min'], s['rr_survival'])
    for mi in range(4):
        for ni, n in enumerate(spp):
            means = np.mean(values[:, :n, mi], axis=1)
            images[mi, ni, coords[:, 1], coords[:, 0]] = means
            target = theory['full_mean'] if mi == 3 else theory['finite'][mi]['mean']
            path_stats.append({'mode': ('direct_1', 'through_3', 'through_5', 'rr_full')[mi],
                'spp': n, 'pixel_mean': float(np.mean(means)), 'expected_mean': target,
                'mse_to_own_target': float(np.mean((means-target)**2)),
                'mse_to_full': float(np.mean((means-theory['full_mean'])**2))})
    mask[coords[:, 1], coords[:, 0]] = True
    gx, gw = np.polynomial.legendre.leggauss(256)
    gm, gw = (gx+1)/2, gw/2
    ggx = [{'alpha': a, 'normalization': float(np.sum(gw*2*np.pi*gm*ggx_ndf(gm, a))),
            'peak_sr_inverse': float(ggx_ndf(1, a))} for a in s['ggx_alpha']]
    _, renderer_sha = renderer()
    result = {'contract': s['contract'], 'scene_sha256': hashlib.sha256((ROOT/'scene.json').read_bytes()).hexdigest(),
        'renderer_sha256': renderer_sha, 'radiance_unit': 'W m^-2 sr^-1, one fixed spectral band',
        'benchmark': benchmark, 'fixed_four_samples': fixed,
        'wrong_pdf': {'sampled': 'cosine', 'divided_by': 'uniform', 'target': rho*li,
                      'expected_mean': 4*rho*li/3, 'observed_mean': float(np.mean(wrong))},
        'disk': disk, 'paths': {'theory': theory, 'screen': screen.tolist(),
            'observed_pixels': len(points), 'modes': ['direct_1', 'through_3', 'through_5', 'rr_full'],
            'spp': spp, 'statistics': path_stats, 'rr_execution': rr_record,
            'fixed_first_path': path_log}, 'ggx': ggx,
        'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'platform': platform.platform()}}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    np.save(output/'benchmark-estimates.npy', estimates)
    np.save(output/'radiance-images.npy', images)
    np.save(output/'observation-mask.npy', mask)
    np.save(output/'disk-samples.npy', np.column_stack([disk_uv, wa, wo, wrong_area]))
    plot(output)
    return result


def plot(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output = Path(output)
    result = json.loads((output/'results.json').read_text())
    r, _ = renderer()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    for ax, scenario in zip(axes, SCENARIOS):
        for method in SAMPLERS:
            rows = [row for row in result['benchmark'] if row['scenario'] == scenario and row['method'] == method]
            ax.loglog([v['n'] for v in rows], [max(1e-16, v['observed_mse']) for v in rows], 'o-', label=method)
            ax.loglog([v['n'] for v in rows], [max(1e-16, v['expected_mse']) for v in rows], '--', color=ax.lines[-1].get_color())
        ax.set(xlabel='samples n / estimate', ylabel='MSE to full-domain target', title=scenario)
        ax.grid(alpha=.2); ax.legend()
    fig.suptitle('2048 independent replicates; solid observed, dashed Var/n + bias^2\n'
                 '1e-16 plot floor only; constant-cosine analytic variance is zero')
    fig.savefig(output/'sampling-mse.png', dpi=130); plt.close(fig)
    images = np.load(output/'radiance-images.npy', allow_pickle=False)
    s = scene()
    fig, axes = plt.subplots(2, 4, figsize=(12, 6), layout='constrained')
    for mi, mode in enumerate(result['paths']['modes']):
        for ni, n in enumerate(result['paths']['spp']):
            display = r.srgb(tone_map(images[mi, ni], s['display_exposure'], s['display_reference_W_m2_sr']))
            axes[ni, mi].imshow(display[23:57, 7:41], cmap='gray', vmin=0, vmax=1, interpolation='nearest')
            axes[ni, mi].set_title(f'{mode}, {n} spp')
            axes[ni, mi].set_xticks([]); axes[ni, mi].set_yticks([])
    fig.suptitle('Same floor observation window, common camera/geometry, crop x[7,41), y[23,57)\n'
                 'One-band radiance -> exposure 1 -> x/(1+x) -> sRGB; center coverage only')
    fig.savefig(output/'direct-indirect.png', dpi=130); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    phi = np.linspace(0, np.pi/2, 240)
    for a in s['ggx_alpha']:
        axes[0].semilogy(phi*180/np.pi, ggx_ndf(np.cos(phi), a), label=f'alpha={a}')
    axes[0].set(xlabel='micro-normal polar angle / degree', ylabel='D, sr^-1', title='GGX NDF, not a complete BRDF')
    axes[0].legend()
    for method in SAMPLERS:
        direction = np.array(result['fixed_four_samples'][method]['direction'])
        axes[1].scatter(direction[:, 0], direction[:, 2], label=method)
    axes[1].axhspan(0, .5, color='tab:red', alpha=.12, label='cap omits this band')
    axes[1].set(xlabel='direction x', ylabel='mu = cos(theta)', ylim=(0, 1.05), title='Four fixed directions, x-z projection')
    axes[1].legend(fontsize=7)
    L = np.linspace(0, 8, 300)
    for exp in (.25, 1, 4):
        axes[2].plot(L, r.srgb(tone_map(L, exp)), label=f'exposure={exp}')
    axes[2].plot(L, r.srgb(np.minimum(L, 1)), '--', label='clip at reference')
    axes[2].set(xlabel='band radiance / reference radiance', ylabel='sRGB display code', title='Display choices do not change transport')
    axes[2].legend(fontsize=8)
    fig.savefig(output/'directions-roughness-display.png', dpi=130); plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps({'full_radiance': result['paths']['theory']['full_mean'],
                      'path_statistics': result['paths']['statistics'], 'disk': result['disk']}, indent=2))
