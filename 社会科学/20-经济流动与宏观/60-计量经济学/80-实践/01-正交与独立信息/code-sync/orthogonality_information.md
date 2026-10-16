---
type: code
stage: 0
aliases: []
sources: []
prerequisites: []
---
# 正交与独立信息复算源码

源码为真源；返回 [[社会科学/20-经济流动与宏观/60-计量经济学/80-实践/01-正交与独立信息/README|实践说明]]。

<!-- code-sync: 社会科学/20-经济流动与宏观/60-计量经济学/80-实践/01-正交与独立信息/orthogonality_information.py -->

```python
#!/usr/bin/env python3
"""Exact finite teaching models. No regression package, random simulation or policy data."""
import argparse
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path


def mean(values):
    return sum(values, F(0)) / len(values)


def variance(values):
    center = mean(values)
    return mean([(v - center) ** 2 for v in values])


def line_fit(ds, ys):
    """Equal-weight intercept and slope; also works for an equally weighted finite population."""
    md, my = mean(ds), mean(ys)
    vd = variance(ds)
    if not vd:
        raise ValueError("intercept+slope design is not full rank")
    slope = mean([(d - md) * (y - my) for d, y in zip(ds, ys)]) / vd
    intercept = my - slope * md
    residual = [y - intercept - slope * d for d, y in zip(ds, ys)]
    assert sum(residual) == 0
    assert sum(d * e for d, e in zip(ds, residual)) == 0
    return intercept, slope, residual


def exchangeable_mean_variance(groups, copies, sigma2, rho):
    if type(groups) is not int or type(copies) is not int or groups < 1 or copies < 1:
        raise ValueError("groups/copies must be positive integers")
    if sigma2 <= 0:
        raise ValueError("positive marginal variance required")
    if copies > 1 and not -F(1, copies - 1) <= rho <= 1:
        raise ValueError("equal-correlation covariance is not positive semidefinite")
    return sigma2 * (1 + (copies - 1) * rho) / (groups * copies)


def calculate(inp):
    # This artifact is a finite oracle for the declared two-point distributions, not an input simulator.
    if inp['u_support'] != ['0', '1'] or inp['v_support'] != ['-1', '1']:
        raise ValueError("this model requires equal-probability U=0,1 and V=-1,1")
    if inp['cluster_shocks'] != ['-1', '1']:
        raise ValueError("two independent equal-probability +/-1 cluster shocks required")
    thetas = [F(t) for t in inp['thetas']]
    if not thetas or any(t < 0 or t > 1 for t in thetas):
        raise ValueError("theta must lie in the declared mechanism family [0,1]")
    worlds = []
    common_observed = None
    for theta in thetas:
        rows = []
        for u, v in product([F(0), F(1)], [F(-1), F(1)]):
            d = u
            y = theta * d + (1 - theta) * u + v
            y0 = (1 - theta) * u + v
            y1 = theta + (1 - theta) * u + v
            structural_error = (1 - theta) * (u - F(1, 2)) + v
            rows.append(dict(u=u, v=v, d=d, y=y, y0=y0, y1=y1,
                             structural_error=structural_error, probability=F(1, 4)))
        ds, ys = [r['d'] for r in rows], [r['y'] for r in rows]
        a, b, residual = line_fit(ds, ys)
        observed = list(zip(ds, ys))
        if common_observed is None:
            common_observed = observed
        assert observed == common_observed
        assert (a, b) == (0, 1)
        ate = mean([r['y1'] - r['y0'] for r in rows])
        assert ate == theta
        structural_cov = mean([(r['d'] - F(1, 2)) * r['structural_error'] for r in rows])
        assert structural_cov == (1 - theta) / 4
        worlds.append(dict(theta=theta, rows=rows, intercept=a, slope=b, residual=residual,
                           ate=ate, cov_d_structural_error=structural_cov,
                           sample_sum_e=sum(residual),
                           sample_sum_de=sum(d * e for d, e in zip(ds, residual))))
    randomized = []
    theta = F(1, 2)
    for u, v, d in product([F(0), F(1)], [F(-1), F(1)], [F(0), F(1)]):
        randomized.append((d, theta * d + (1 - theta) * u + v))
    a, b, _ = line_fit([r[0] for r in randomized], [r[1] for r in randomized])
    assert (a, b) == (F(1, 4), F(1, 2))
    clusters = []
    if not inp['copies_per_cluster']:
        raise ValueError('at least one copy count required')
    for m in inp['copies_per_cluster']:
        if type(m) is not int or m < 1:
            raise ValueError("positive integer copies required")
        n = 2 * m
        states = []
        for w1, w2 in product([F(-1), F(1)], repeat=2):
            # mu=0 without loss for centered variance; the intercept design is fixed.
            ys = [w1] * m + [w2] * m
            estimate = mean(ys)
            residual = [y - estimate for y in ys]
            hc0 = sum(e * e for e in residual) / (n * n)
            hc1 = F(n, n - 1) * hc0
            cr0 = (sum(residual[:m]) ** 2 + sum(residual[m:]) ** 2) / (n * n)
            cr1 = 2 * cr0  # G/(G-1)*(n-1)/(n-k), G=2,k=1.
            assert hc1 == (F(1, 2 * m - 1) if w1 != w2 else 0)
            assert cr1 == (1 if w1 != w2 else 0)
            states.append(dict(w1=w1, w2=w2, probability=F(1, 4), estimate_error=estimate,
                               hc0=hc0, hc1=hc1, cr0=cr0, cr1=cr1))
        true_var = variance([s['estimate_error'] for s in states])
        # Matrix/covariance expansion is independent of residual-based estimated variances.
        diagonal_terms = 2 * m
        off_diagonal_terms = 2 * m * (m - 1)
        covariance_sum_var = F(diagonal_terms + off_diagonal_terms, n * n)
        wrong_independent_var = F(diagonal_terms, n * n)
        assert true_var == covariance_sum_var == F(1, 2)
        assert mean([s['hc1'] for s in states]) == F(1, 2 * (2 * m - 1))
        assert mean([s['cr1'] for s in states]) == F(1, 2)
        probability_large_error = sum(s['probability'] for s in states if abs(s['estimate_error']) > F(1, 2))
        assert probability_large_error == F(1, 2)
        clusters.append(dict(m=m, n=n, true_variance=true_var,
                             covariance_sum_variance=covariance_sum_var,
                             wrong_independent_variance=wrong_independent_var,
                             mean_hc1=mean([s['hc1'] for s in states]),
                             mean_cr1=mean([s['cr1'] for s in states]),
                             probability_error_gt_half=probability_large_error, states=states))
    mig = inp['migration']
    migration_var = exchangeable_mean_variance(mig['groups'], mig['copies'], F(mig['variance']), F(mig['rho']))
    # Finite nonlinear orthogonality example; conditional mean is not zero.
    nonlinear = [F(d * d) - F(2, 3) for d in [-1, 0, 1]]
    assert mean(nonlinear) == sum(F(d) * r for d, r in zip([-1, 0, 1], nonlinear)) == 0
    return dict(identity=inp['identity'], worlds=worlds, clusters=clusters,
                randomized_theta_half=dict(intercept=a, slope=b, ate=theta),
                migration_variance=migration_var,
                migration_wrong_independent_variance=F(mig['variance']) / (mig['groups'] * mig['copies']),
                nonlinear_projection_residual=nonlinear)


def svg(result):
    # Plot coordinates alone use float; all substantive results above use exact rational arithmetic.
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="690" viewBox="0 0 960 690">',
             '<title>Same observations do not identify the effect; copying two shocks does not reduce variance</title>',
             '<desc>Top: four synthetic observations and the line y=d, identical for theta=0, one half, one. Bottom: two independent clusters, m copies per cluster; true mean variance one half is flat, while an incorrect independence calculation one over two m declines.</desc>',
             '<rect width="960" height="690" fill="white"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#18212c;font-size:16px}.small{font-size:14px}.heading{font-size:20px;font-weight:bold}.axis{stroke:#263238;stroke-width:1.5}.grid{stroke:#dfe4e9;stroke-width:1}</style>',
             '<text x="40" y="32" class="heading">A. Same observed distribution; different intervention effects</text>']
    x0, y0, sx, sy = 90, 222, 300, 52
    px = lambda d: x0 + float(d) * sx
    py = lambda y: y0 - float(y) * sy
    parts += [f'<line x1="{x0}" y1="{py(-1.5)}" x2="{x0}" y2="{py(2.5)}" class="axis"/>',
              f'<line x1="65" y1="{y0}" x2="460" y2="{y0}" class="axis"/>']
    for d in [0, 1]:
        parts.append(f'<text x="{px(d)-4}" y="315">{d}</text>')
    for y in [-1, 0, 1, 2]:
        parts.append(f'<text x="45" y="{py(y)+5}">{y}</text>')
    parts += ['<text x="445" y="248">D</text>', '<text x="55" y="85">Y</text>',
              f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(1)}" y2="{py(1)}" stroke="#2563a6" stroke-width="3"/>']
    for row in result['worlds'][0]['rows']:
        d, y = row['d'], row['y']
        parts.append(f'<circle cx="{px(d)}" cy="{py(y)}" r="6" fill="#2563a6" stroke="white" stroke-width="1.5"/>')
    for j, label in enumerate(['Each point has probability 1/4.', 'Prediction line: E[Y|D] = D', 'theta = 0, 1/2, 1: same four points', 'Replacing D=U by D=d gives ATE=theta.', 'The line cannot choose the mechanism.']):
        parts.append(f'<text x="505" y="{105+j*35}" class="small">{label}</text>')
    parts.append('<text x="40" y="364" class="heading">B. Two independent shocks; m exact copies of each</text>')
    left, right, top, bottom = 90, 680, 395, 610
    ms = sorted(set(row['m'] for row in result['clusters']))
    mmin, mmax = min(ms), max(ms)
    xx = lambda m: left + (m - mmin) / max(1, mmax - mmin) * (right - left)
    yy = lambda v: bottom - float(v) / .55 * (bottom - top)
    for v in [F(0),F(1,4),F(1,2)]:
        parts += [f'<line x1="{left}" y1="{yy(v):.2f}" x2="{right}" y2="{yy(v):.2f}" class="grid"/>',
                  f'<text x="40" y="{yy(v)+5:.2f}">{float(v):g}</text>']
    parts += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
              f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>',
              '<text x="40" y="389" class="small">Variance</text>']
    parts.append(f'<line x1="{left}" y1="{yy(F(1,2)):.2f}" x2="{right}" y2="{yy(F(1,2)):.2f}" stroke="#2563a6" stroke-width="3"/>')
    curve = ' '.join(f"{xx(row['m']):.2f},{yy(row['wrong_independent_variance']):.2f}" for row in sorted(result['clusters'], key=lambda r: r['m']))
    parts.append(f'<polyline points="{curve}" fill="none" stroke="#b34438" stroke-width="3" stroke-dasharray="7 4"/>')
    for m in ms:
        parts += [f'<text x="{xx(m)-5:.2f}" y="632">{m}</text>',
                  f'<circle cx="{xx(m):.2f}" cy="{yy(F(1,2*m)):.2f}" r="4" fill="#b34438"/>']
    parts += ['<text x="285" y="661">m: records per cluster (G=2 fixed)</text>',
              '<text x="708" y="425" class="small">Solid: true Var = 1/2</text>',
              '<text x="708" y="462" class="small">Dashed: wrong 1/(2m)</text>',
              '<text x="708" y="514" class="small">Variance, not standard error.</text>',
              '<text x="708" y="544" class="small">Known model; no CI claimed.</text>',
              '</svg>']
    return '\n'.join(parts) + '\n'


def encode(value):
    if isinstance(value, F):
        return str(value)
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).with_name('results'))
    args = parser.parse_args()
    result = calculate(json.loads(args.input.read_text(encoding='utf-8')))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'exact-results.json').write_text(json.dumps(result, default=encode, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output_dir / 'independent-units.svg').write_text(svg(result), encoding='utf-8')
    print('PASS: exact observed worlds, intervention contrasts, residual moments, cluster states and migration moments')


if __name__ == '__main__':
    main()
```
