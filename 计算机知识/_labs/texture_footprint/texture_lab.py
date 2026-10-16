"""Bounded affine texture consumer of the existing WWL renderer, not a renderer replacement."""
from pathlib import Path
from functools import lru_cache
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import numpy as np

ROOT = Path(__file__).resolve().parent
METHODS = ('nearest', 'bilinear', 'box', 'mip')


def array(value, shape=None):
    raw = np.asarray(value)
    if raw.dtype.kind not in 'iuf' or (shape is not None and raw.shape != shape):
        raise ValueError('expected real array with declared shape; bool is not a number')
    a = raw.astype(float)
    if not np.isfinite(a).all() or np.any(np.abs(a) > 1e6):
        raise ValueError('expected finite bounded real array')
    return a


def scalar(value, low, high):
    a = array(value, ())
    x = float(a)
    if not low <= x <= high:
        raise ValueError('scalar outside declared range')
    return x


@lru_cache(maxsize=1)
def renderer():
    path = Path(os.environ.get('WWL_RENDERER_SOURCE',
        ROOT.parents[1] / '62-图形学' / 'renderer.py')).resolve()
    spec = importlib.util.spec_from_file_location('wwl_readonly_renderer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def texture(value):
    t = array(value)
    if t.ndim != 2 or min(t.shape) < 1 or max(t.shape) > 64 or np.any((t < 0) | (t > 1)):
        raise ValueError('linear-gray texture must be HxW, 1..64 and in [0,1]')
    return t


def uv_value(value):
    return array(value, (2,))


def nearest(tex, uv):
    t, q = texture(tex), uv_value(uv) % 1.0
    h, w = t.shape
    # Cell [i,i+1) owns texel i; tie rule is explicit, not API conformance.
    return float(t[int(math.floor(q[1]*h)) % h, int(math.floor(q[0]*w)) % w])


def bilinear(tex, uv):
    t, q = texture(tex), uv_value(uv) % 1.0
    h, w = t.shape
    x, y = q * [w, h] - .5
    ix, iy = math.floor(x), math.floor(y)
    ax, ay = x-ix, y-iy
    return float(sum(t[(iy+dy) % h, (ix+dx) % w] * wx * wy
                     for dx, wx in ((0, 1-ax), (1, ax))
                     for dy, wy in ((0, 1-ay), (1, ay))))


def overlap_weights(center, width, size):
    # Integrate the periodic piecewise-constant texel cells, not the tent interpolant.
    lo, hi = center-width/2, center+width/2
    weights = np.zeros(size)
    for i in range(math.floor(lo), math.ceil(hi)):
        weights[i % size] += max(0., min(hi, i+1)-max(lo, i)) / width
    return weights


def box_average(tex, uv, width_texels):
    t, q, width = texture(tex), uv_value(uv) % 1.0, array(width_texels, (2,))
    if np.any((width < 1/64) | (width > 64)):
        raise ValueError('box widths must be 1/64..64 texels per axis')
    h, w = t.shape
    wx = overlap_weights(q[0]*w, width[0], w)
    wy = overlap_weights(q[1]*h, width[1], h)
    return float(wy @ t @ wx)


def mip_chain(tex):
    t = texture(tex)
    h, w = t.shape
    if h != w or h & (h-1):
        raise ValueError('mip input must be square power of two')
    levels = [t.copy()]
    while h > 1:
        t = t.reshape(h//2, 2, h//2, 2).mean(axis=(1, 3))
        levels.append(t)
        h //= 2
    return levels


def mip_sample(tex, uv, width_texels):
    # Teaching LOD convention. It is not pbrt's exact width heuristic or a GPU spec.
    width = array(width_texels, (2,))
    if np.any((width < 1/64) | (width > 64)):
        raise ValueError('mip widths must be 1/64..64 texels per axis')
    levels = mip_chain(tex)
    level = min(len(levels)-1, max(0., math.log2(float(max(width)))))
    lo = math.floor(level)
    hi = min(lo+1, len(levels)-1)
    alpha = level-lo
    return ((1-alpha)*bilinear(levels[lo], uv) + alpha*bilinear(levels[hi], uv), level)


def load_scene(path=ROOT / 'scene.json'):
    s = json.loads(Path(path).read_text())
    if s != json.loads((ROOT / 'scene.json').read_text()):
        raise ValueError('CLI accepts this fixed scene contract only')
    return s


def projected(scale):
    scale = scalar(scale, .25, 1.)
    s = load_scene()
    pos = array(s['positions'], (3, 3)).copy()
    pivot = array(s['pivot_xy'], (2,))
    pos[:, :2] = pivot + scale*(pos[:, :2]-pivot)
    r, _ = renderer()
    clip = (r.perspective() @ np.column_stack([pos, np.ones(3)]).T).T
    if not np.all(clip[:, 3] == 2) or np.any(np.abs(clip[:, :3]) > clip[:, 3, None]):
        raise ValueError('this experiment requires equal-w, fully unclipped triangle')
    ndc = clip[:, :3] / clip[:, 3, None]
    screen = np.column_stack([(ndc[:, 0]+1)*32, (1-ndc[:, 1])*32])
    uv = array(s['uv'], (3, 2))
    if r.edge(screen[0], screen[1], screen[2]) < 0:
        screen, uv, clip = screen[[0, 2, 1]], uv[[0, 2, 1]], clip[[0, 2, 1]]
    # uv(x,y) = [x,y,1] @ coefficients; exact because all w are equal.
    coefficients = np.linalg.solve(np.column_stack([screen, np.ones(3)]), uv)
    jacobian = 32*coefficients[:2].T  # rows texture axes; columns screen axes
    if not np.allclose(jacobian, np.diag(np.diag(jacobian)), atol=1e-12):
        raise ValueError('axis-aligned footprint required for exact rectangle reference')
    return screen, uv, clip[:, 3], coefficients, jacobian


def sample_value(tex, uv, width, method):
    if method == 'nearest':
        return nearest(tex, uv)
    if method == 'bilinear':
        return bilinear(tex, uv)
    if method == 'box':
        return box_average(tex, uv, width)
    if method == 'mip':
        return mip_sample(tex, uv, width)[0]
    raise ValueError('unknown sampling method')


def render_texture(scale, phase, method):
    """One fixed unlit triangle; existing renderer supplies projection/coverage/UV interpolation."""
    phase = scalar(phase, -1., 1.)
    if method not in METHODS:
        raise ValueError('unknown sampling method')
    screen, uv, w, coefficients, jacobian = projected(scale)
    width = np.abs(np.diag(jacobian))
    checker = (np.indices((32, 32)).sum(axis=0) % 2).astype(float)
    image = np.zeros((64, 64))
    mask = np.zeros((64, 64), dtype=bool)
    r, _ = renderer()
    for x, y, lam in r.samples(screen, 64, 64):
        q = r.interpolate(lam, w, uv) + phase/32
        image[y, x] = sample_value(checker, q, width, method)
        mask[y, x] = True
    return image, mask


def edge_probe():
    r, _ = renderer()
    screen = projected(1)[0] + [0., load_scene()['edge_shift_y_pixels']]
    pixel = np.array([24, 40])
    coverages = {}
    for n in (1, 4, 8, 32):
        local = (screen-pixel)*n
        coverages[str(n)] = sum(1 for _ in r.samples(local, n, n)) / n**2
    delta = load_scene()['edge_shift_y_pixels']
    return {'pixel_xy': pixel.tolist(), 'shift_y': delta,
            'exact_white_on_black_area': (1-delta)**2/2,
            'regular_n_by_n_coverage': coverages,
            'shader': 'constant white; texture filtering cannot change coverage'}


def generate(output):
    # Calculate first; output directory must be new, so retained evidence cannot be overwritten.
    s = load_scene()
    rows, images, masks = [], [], []
    for phase in s['phase_texels']:
        phase_images, phase_masks = [], []
        for scale in s['scales']:
            screen, uv, w, coefficients, jacobian = projected(scale)
            width = np.abs(np.diag(jacobian))
            # Bottom-left interior pixel: its entire unit square is away from triangle edges.
            x, y = int(round(screen[:, 0].min()))+1, int(round(screen[:, 1].max()))-2
            q = np.array([x+.5, y+.5, 1.]) @ coefficients + phase/32
            result = {'scale': scale, 'phase_texels_xy': [phase, phase],
                'screen_vertices': screen.tolist(), 'jacobian_texels_per_pixel': jacobian.tolist(),
                'width_texels': width.tolist(), 'area_texels2': float(np.prod(width)),
                'probe_pixel_xy': [x, y], 'probe_texel_xy': (32*q).tolist(),
                'checker_fundamental_cycles_per_texel_axis': .5,
                'projected_fundamental_cycles_per_pixel_axis': (.5*width).tolist(),
                'mip_lod': math.log2(float(max(width))), 'values': {}}
            method_images = []
            for method in METHODS:
                image, mask = render_texture(scale, phase, method)
                method_images.append(image)
                result['values'][method] = float(image[y, x])
            rows.append(result)
            phase_images.append(method_images)
            phase_masks.append(mask)
        images.append(phase_images)
        masks.append(phase_masks)
    stripe = np.tile(np.arange(32) % 2, (32, 1)).astype(float)
    anisotropic = {'uv': [.5/32, .5/32], 'width_texels': [1, 8],
        'box': box_average(stripe, [.5/32, .5/32], [1, 8]),
        'isotropic_mip': mip_sample(stripe, [.5/32, .5/32], [1, 8])[0]}
    r, digest = renderer()
    encoded = float(r.srgb(.5))
    decoded = ((.5+.055)/1.055)**2.4
    result = {'contract': s['contract'], 'renderer_sha256': digest,
        'scene_sha256': hashlib.sha256((ROOT/'scene.json').read_bytes()).hexdigest(),
        'image_array_order': ['phase', 'scale', 'method', 'y', 'x'],
        'phases': s['phase_texels'], 'scales': s['scales'], 'methods': METHODS,
        'rows': rows, 'edge': edge_probe(), 'anisotropic_counterexample': anisotropic,
        'linear_srgb': {'linear_mean': .5, 'encoded_linear_mean': encoded,
                        'decoded_encoded_mean': decoded},
        'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                        'platform': platform.platform()}}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    np.save(output/'linear-images.npy', np.array(images))
    np.save(output/'coverage-masks.npy', np.array(masks))
    with (output/'probes.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['scale', 'phase_texels', 'axis_width', 'area_texels2', *METHODS])
        for row in rows:
            writer.writerow([row['scale'], row['phase_texels_xy'][0], row['width_texels'][0],
                             row['area_texels2'], *row['values'].values()])
    plot(output)
    return result


def plot(output):
    # Plot only retained arrays; these are the same numbers used for probes and references.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output = Path(output)
    data = np.load(output/'linear-images.npy', allow_pickle=False)
    result = json.loads((output/'results.json').read_text())
    r, _ = renderer()
    fig, axes = plt.subplots(3, 4, figsize=(12, 8), layout='constrained')
    for i, scale in enumerate(result['scales']):
        screen = projected(scale)[0]
        left, right = int(round(screen[:, 0].min()))-1, int(round(screen[:, 0].max()))+1
        top, bottom = int(round(screen[:, 1].min()))-1, int(round(screen[:, 1].max()))+1
        for j, method in enumerate(METHODS):
            axes[i, j].imshow(r.srgb(data[1, i, j, top:bottom, left:right]),
                              cmap='gray', vmin=0, vmax=1, interpolation='nearest')
            axes[i, j].set_title(f'{method}: {1/scale:g} texels/axis/pixel')
            axes[i, j].set_xticks([]); axes[i, j].set_yticks([])
            axes[i, j].set_xlabel(f'crop x[{left},{right}), y[{top},{bottom}); sRGB')
    fig.suptitle('Same 32x32 checker / triangle / UV; phase +0.25 texel in both axes\n'
                 'Each crop enlarged independently; center-only geometric coverage in every column')
    fig.savefig(output/'texture-comparison.png', dpi=130)
    plt.close(fig)
    edge = result['edge']
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
    for offset, color in ((0., '0.6'), (.2, 'tab:blue')):
        axes[0].plot([0, 1-offset], [offset, 1], color=color, label=f'y=x+{offset}')
    axes[0].fill([0, 0, .8], [.2, 1, 1], alpha=.25, color='tab:blue')
    axes[0].set(xlim=(0, 1), ylim=(0, 1), aspect='equal', xlabel='local pixel x',
                ylabel='local pixel y (screen down)', title='White region: y >= x + 0.2')
    axes[0].invert_yaxis()
    axes[0].scatter([.5], [.5], color='red', label='center: outside')
    axes[0].legend(fontsize=8)
    values = list(edge['regular_n_by_n_coverage'].values())
    axes[1].bar(['1x1', '4x4', '8x8', '32x32'], values)
    axes[1].axhline(edge['exact_white_on_black_area'], color='tab:red', label='exact area 0.32')
    axes[1].set(ylim=(0, .45), ylabel='linear white-on-black average',
                title='Finite coverage samples; not an MSAA implementation')
    axes[1].legend()
    fig.savefig(output/'edge-coverage.png', dpi=130)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps({'rows': len(result['rows']), 'edge': result['edge'],
                      'linear_srgb': result['linear_srgb']}, indent=2))
