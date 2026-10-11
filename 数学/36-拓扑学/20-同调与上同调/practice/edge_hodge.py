#!/usr/bin/env python3
"""Finite real Hodge teaching example; exact arithmetic, explicit output paths.

Coordinates represent dimensionless real data. Fraction is used to make this
rational input exactly reproducible; this is not an integer-homology algorithm.
No input probabilities, circuit observations or noise calibration are inferred.
"""
import argparse
from fractions import Fraction as F
from html import escape
import json
from pathlib import Path


def transpose(a):
    return [list(row) for row in zip(*a)]


def mv(a, x):
    return [sum((v * w for v, w in zip(row, x)), F(0)) for row in a]


def mm(a, b):
    return [[sum((v * w for v, w in zip(row, col)), F(0))
             for col in transpose(b)] for row in a]


def dot(x, y):
    return sum((v * w for v, w in zip(x, y)), F(0))


def sub(x, y):
    return [v - w for v, w in zip(x, y)]


def solve(a, b):
    """Gauss-Jordan over rational entries; require a nonsingular square system."""
    n = len(a)
    if len(b) != n or any(len(row) != n for row in a):
        raise ValueError('square solve shape mismatch')
    aug = [list(row) + [value] for row, value in zip(a, b)]
    for j in range(n):
        pivot = next((i for i in range(j, n) if aug[i][j]), None)
        if pivot is None:
            raise ValueError('singular system: one reference does not fix this model')
        aug[j], aug[pivot] = aug[pivot], aug[j]
        p = aug[j][j]
        aug[j] = [v / p for v in aug[j]]
        for i in range(n):
            if i != j:
                c = aug[i][j]
                aug[i] = [v - c * w for v, w in zip(aug[i], aug[j])]
    return [row[-1] for row in aug]


def project(b1, y, weights):
    # Fix phi_0=0. D maps remaining vertex potentials to oriented edge readings.
    d = [row[1:] for row in transpose(b1)]
    wd = [[w * v for v in row] for w, row in zip(weights, d)]
    wy = [w * v for w, v in zip(weights, y)]
    normal = mm(transpose(d), wd)
    rhs = mv(transpose(d), wy)
    psi = solve(normal, rhs)
    g = mv(d, psi)
    r = sub(y, g)
    return {'D': d, 'normal': normal, 'rhs': rhs, 'phi': [F(0)] + psi,
            'gradient': g, 'residual': r,
            'normal_residual': mv(b1, [w * v for w, v in zip(weights, r)]),
            'gradient_residual_inner_product': dot(g, [w * v for w, v in zip(weights, r)]),
            'residual_square': dot(r, [w * v for w, v in zip(weights, r)])}


def finite_hodge(b1, face, y):
    result = project(b1, y, [F(1)] * len(y))
    r = result['residual']
    q = [F(0)] * len(y)
    a = F(0)
    if face is not None:
        if any(mv(b1, face)):
            raise ValueError('B1 B2 != 0')
        norm = dot(face, face)
        if not norm:
            raise ValueError('face column is zero')
        a = dot(face, r) / norm
        q = [a * v for v in face]
    h = sub(r, q)
    l1 = mm(transpose(b1), b1)
    if face is not None:
        l1 = [[v + face[i] * face[j] for j, v in enumerate(row)]
              for i, row in enumerate(l1)]
    result.update({'face_coefficient': a, 'face_part': q, 'harmonic': h,
                   'L1': l1, 'L1_harmonic': mv(l1, h),
                   'B1_harmonic': mv(b1, h),
                   'B2T_harmonic': [] if face is None else [dot(face, h)]})
    return result


def exact_json(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(v) for v in value]
    return value


def make_svg(y, g, r, face_coefficient):
    # Same vertex/edge layout as triangle-boundary-fill.svg; arrows never flip
    # to disguise a negative reading. Bottom-right alone contains an actual face.
    panels = [('原读数 y；只有边', y, False, '闭路评价 y^T z = ' + str(dot(y, [F(1), F(1), F(-1)]))),
              ('势差 g；只有边', g, False, 'φ = (0, ' + str(g[0]) + ', ' + str(g[2]) + ')'),
              ('剩余 r；只有边', r, False, '调和 h = r；面项 q = 0'),
              ('同一 r；填一个面', r, True, '面项 q = r；h = 0；a = ' + str(face_coefficient))]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 740" role="img" aria-labelledby="title desc">',
             '<title id="title">同一三角形读数的势差与残差：填面改变残差身份</title>',
             '<desc id="desc">边01从0到1，12从1到2，02从0到2，所有箭头固定。左上原读数，右上欧氏势差，左下没有面时的调和残差，右下新增面后的面边界。负读数按固定箭头显示。</desc>',
             '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#203950"/></marker></defs>',
             '<rect width="980" height="740" fill="#fff"/>',
             '<g font-family="Arial Unicode MS, sans-serif" font-size="20" fill="#172e40">']
    for k, (title, values, filled, footer) in enumerate(panels):
        dx, dy = (k % 2) * 490, (k // 2) * 350
        parts.append(f'<g transform="translate({dx},{dy})">')
        parts.append(f'<text x="42" y="34" font-weight="bold">{escape(title)}</text>')
        if filled:
            parts.append('<path d="M100 250L380 250L240 83Z" fill="#dfedf9"/>')
            parts.append('<text x="231" y="205">t</text>')
        parts.append('<g stroke="#203950" stroke-width="3" fill="none" marker-end="url(#arrow)"><path d="M100 250H380"/><path d="M380 250L240 83"/><path d="M100 250L240 83"/></g>')
        parts.append('<g fill="#203950"><circle cx="100" cy="250" r="5"/><circle cx="380" cy="250" r="5"/><circle cx="240" cy="83" r="5"/></g>')
        parts.append('<text x="70" y="273">v₀</text><text x="378" y="273">v₁</text><text x="230" y="72">v₂</text>')
        for x, yy, label, val in [(197, 275, '01', values[0]), (327, 165, '12', values[1]), (42, 165, '02', values[2])]:
            parts.append(f'<text x="{x}" y="{yy}" font-size="18">{label}: {escape(str(val))}</text>')
        parts.append(f'<text x="42" y="317" font-size="18">{escape(footer)}</text></g>')
    parts.append('<text x="42" y="726" font-size="18">边序 01、12、02；全部无量纲。箭头是参考方向；负值不改变边方向。浅色只表示右下面 t。</text></g></svg>')
    return '\n'.join(parts) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--svg', required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.input.resolve() or args.svg.resolve() in (args.input.resolve(), args.output.resolve()):
        raise ValueError('input and outputs must be different files')
    raw = json.loads(args.input.read_text())
    b1 = [[F(v) for v in row] for row in raw['B1']]
    y, face, w = ([F(v) for v in raw[key]] for key in ('y', 'face', 'weights'))
    if len(b1) != 3 or any(len(row) != 3 for row in b1) or len(y) != 3 or len(face) != 3 or len(w) != 3:
        raise ValueError('this diagram/model requires three vertices and three edges')
    if any(v <= 0 for v in w):
        raise ValueError('weights must be positive')
    # SVG labels have the specified triangle topology; reject another B1 rather
    # than drawing a misleading diagram for it. y/weights/increment may change.
    if b1 != [[F(-1), F(0), F(-1)], [F(1), F(-1), F(0)], [F(0), F(1), F(1)]]:
        raise ValueError('SVG requires fixed edge order 01,12,02')
    base = finite_hodge(b1, None, y)
    filled = finite_hodge(b1, face, y)
    flip = raw['flip_edge']
    if type(flip) is not int or flip not in range(3):
        raise ValueError('flip_edge must be 0,1,2')
    signs = [F(-1) if j == flip else F(1) for j in range(3)]
    b1_flip = [[v * s for v, s in zip(row, signs)] for row in b1]
    y_flip, face_flip = ([v * s for v, s in zip(vec, signs)] for vec in (y, face))
    increment = F(raw['cycle_increment'])
    shifted = [v + increment * c for v, c in zip(y, face)]
    d = base['D']
    precision = [[v + (i == j) for j, v in enumerate(row)] for i, row in enumerate(base['normal'])]
    mean = solve(precision, base['rhs'])
    covariance = transpose([solve(precision, [F(i == j) for i in range(2)]) for j in range(2)])
    prediction = mv(d, mean)
    posterior_residual = sub(y, prediction)
    output = {'input': raw, 'empty_face': base, 'filled_face': filled,
              'new_reference_node_2': sub(base['phi'], [base['phi'][2]] * 3),
              'zero_mean_reference': sub(base['phi'], [sum(base['phi']) / 3] * 3),
              'flipped': {'B1': b1_flip, 'y': y_flip, 'B2': face_flip,
                          'empty_face': finite_hodge(b1_flip, None, y_flip),
                          'filled_face': finite_hodge(b1_flip, face_flip, y_flip)},
              'cycle_shifted': {'y': shifted, 'empty_face': finite_hodge(b1, None, shifted),
                               'filled_face': finite_hodge(b1, face, shifted)},
              'weighted': project(b1, y, w),
              'posterior': {'precision': precision, 'mean': mean, 'covariance': covariance,
                            'prediction': prediction, 'residual': posterior_residual,
                            'DT_residual': mv(transpose(d), posterior_residual)}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(exact_json(output), ensure_ascii=False, indent=2) + '\n')
    args.svg.write_text(make_svg(y, base['gradient'], base['residual'], filled['face_coefficient']))
    print('Exact output:', args.output)
    print('Same-data SVG:', args.svg)


if __name__ == '__main__':
    main()
