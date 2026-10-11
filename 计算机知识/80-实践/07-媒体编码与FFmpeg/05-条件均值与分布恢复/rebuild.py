#!/usr/bin/env python3
"""Enumerate a two-pixel posterior; build metrics and SVG from one input table."""
import argparse
import csv
from fractions import Fraction as F
from html import escape
import json
from math import log10
from pathlib import Path
import tempfile


def load(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'states'}:
        raise ValueError('input must contain only states')
    rows = data['states']
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError('exactly two states are required')
    states = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'pixels', 'probability'}:
            raise ValueError('each state needs pixels and probability')
        pixels = row['pixels']
        if (not isinstance(pixels, list) or len(pixels) != 2 or
                any(type(v) is not int or v not in (0, 1) for v in pixels)):
            raise ValueError('pixels must be two integer values in {0,1}')
        if not isinstance(row['probability'], str) or len(row['probability']) > 40:
            raise ValueError('probability must be a short fraction string')
        probability = F(row['probability'])
        if probability <= 0:
            raise ValueError('probabilities must be positive')
        states.append((tuple(F(v) for v in pixels), probability))
    if set(y for y, _ in states) != {(F(0), F(1)), (F(1), F(0))}:
        raise ValueError('the support must be (0,1) and (1,0)')
    if sum(prob for _, prob in states) != 1:
        raise ValueError('probabilities must sum to one')
    return states


def mse(y, z):
    return sum((a-b)**2 for a, b in zip(y, z)) / 2


def psnr(error):
    # MAX=1. A string preserves infinity without emitting invalid JSON.
    return '+infinity' if error == 0 else 10*log10(1/float(error))


def vector(y):
    return '(' + ','.join(str(v) for v in y) + ')'


def enumerate_case(states, observe):
    groups = {}
    for y, p in states:
        x = sum(y)/2 if observe == 'average' else y[0]
        groups.setdefault(x, []).append((y, p))
    joint, means = [], []
    mean_risk, sample_risk, match = F(0), F(0), F(0)
    mean_inf, draw_inf = F(0), F(0)
    mean_db, draw_db = 0.0, 0.0
    output = {y: F(0) for y, _ in states}
    for x, group in sorted(groups.items()):
        mass = sum(p for _, p in group)
        posterior = [(y, p/mass) for y, p in group]
        mu = tuple(sum(y[i]*q for y, q in posterior) for i in range(2))
        means.append({'x': str(x), 'mean': [str(v) for v in mu],
                      'posterior': [{'pixels': vector(y), 'probability': str(q)}
                                    for y, q in posterior]})
        for y, p in group:
            mean_error = mse(y, mu)
            mean_risk += p*mean_error
            if mean_error == 0:
                mean_inf += p
            else:
                mean_db += float(p)*psnr(mean_error)
            for z, q in posterior:
                weight = p*q  # P(X) P(Y|X) P(draw|X), independent given X.
                error = mse(y, z)
                sample_risk += weight*error
                output[z] += weight
                match += weight*(y == z)
                if error == 0:
                    draw_inf += weight
                else:
                    draw_db += float(weight)*psnr(error)
                joint.append({'observation': observe, 'x': str(x),
                              'true': vector(y), 'draw': vector(z),
                              'joint_probability': str(weight), 'match': y == z,
                              'draw_mse': str(error), 'draw_psnr_db': psnr(error),
                              'mean': vector(mu), 'mean_mse': str(mean_error),
                              'mean_psnr_db': psnr(mean_error)})
    summary = {'observation': observe, 'max_value': 1,
               'mean_mse': str(mean_risk), 'draw_mse': str(sample_risk),
               'match_probability': str(match),
               'mean_pooled_psnr_db': psnr(mean_risk),
               'draw_pooled_psnr_db': psnr(sample_risk),
               'mean_per_image_psnr_expectation_db': '+infinity' if mean_inf else mean_db,
               'draw_per_image_psnr_expectation_db': '+infinity' if draw_inf else draw_db,
               'draw_zero_error_probability': str(draw_inf),
               'draw_output_distribution': [{'pixels': vector(y), 'probability': str(q)}
                                            for y, q in output.items()],
               'conditional_means': means}
    return summary, joint


def svg(states, average):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="800" viewBox="0 0 1160 800">',
             '<title>Two pixels: lost order, posterior mean and independent posterior pairs</title>',
             '<desc>Black=0, white=1, grey=one half, values in [0,1]. Each image has two pixels. '
             'The mean sensor reading is scalar, not a reference image. Four independent pairs '
             'are enumerated from the same input table. This is a mathematical diagram, no preference test.</desc>',
             '<rect width="1160" height="800" fill="#f4f6f8"/>',
             '<g font-family="sans-serif" fill="#182738">']
    def text(x, y, value, size=19):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}">{escape(value)}</text>')
    def image(x, y, vals, cell=64):
        for i, value in enumerate(vals):
            intensity = round(float(value)*255)
            parts.append(f'<rect x="{x+i*cell}" y="{y}" width="{cell}" height="{cell}" '
                         f'fill="rgb({intensity},{intensity},{intensity})" stroke="#607080" stroke-width="2"/>')
            text(x+i*cell+cell/2-10, y+cell+26, str(value), 18)
    text(30, 38, 'One table, two objectives: squared reference error and output distribution', 25)
    text(30, 72, 'Pixel order: LEFT then RIGHT. Values in [0,1]. Black=0, white=1, grey=1/2.', 18)
    for i, (y, probability) in enumerate(states):
        x = 45+i*220
        text(x, 126, f'True Y: p={probability}', 20)
        image(x, 148, y)
    text(485, 126, 'Observed X = mean(Y)', 20)
    image(548, 148, [F(1, 2)])
    text(492, 267, 'One SCALAR reading', 18)
    mu = tuple(F(v) for v in average['conditional_means'][0]['mean'])
    text(795, 126, 'Conditional mean m(X)', 20)
    image(830, 148, mu)
    text(795, 267, f"Expected MSE={average['mean_mse']}", 18)
    text(30, 325, 'Independent posterior draw: compare each candidate with its actual reference', 22)
    for k, (y, py) in enumerate(states):
        for j, (z, pz) in enumerate(states):
            index = 2*k+j; x = 40+(index%2)*570; top=355+(index//2)*190
            parts.append(f'<rect x="{x-12}" y="{top-10}" width="540" height="177" rx="10" fill="#fff" stroke="#bac5ce"/>')
            text(x, top+17, f'Pair p={py*pz}: ' + ('MATCH' if y==z else 'MISMATCH'), 20)
            text(x, top+46, 'True reference', 17); text(x+206, top+46, 'Independent draw', 17)
            image(x, top+58, y, 48); image(x+206, top+58, z, 48)
            text(x+357, top+85, f'MSE={mse(y,z)}', 20)
    text(30, 768, 'Enlarged cells show values, not calibrated display luminance. No human preference was measured.', 18)
    parts.append('</g></svg>')
    return '\n'.join(parts)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('input.json'))
    parser.add_argument('--out', type=Path, help='a new directory whose parent already exists')
    args = parser.parse_args()
    try:
        states = load(args.input)
        summaries, pairs = [], []
        for observation in ['average', 'first_pixel']:
            summary, rows = enumerate_case(states, observation)
            summaries.append(summary); pairs.extend(rows)
        chart = svg(states, summaries[0])
        out = args.out
        if out is None:
            out = Path(tempfile.mkdtemp(prefix='wwl-two-pixels-'))
        else:
            out.mkdir()  # Refuse existing output. A trusted parent is required.
        with (out/'pairs.csv').open('x', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(pairs[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(pairs)
        result = {'pixel_count': 2, 'zero_error_policy': '+infinity as a string',
                  'pairing': 'true Y and draw are independent conditional on observed X',
                  'cases': summaries}
        (out/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        (out/'two-pixels.svg').write_text(chart, encoding='utf-8')
    except (ValueError, OSError, ZeroDivisionError) as error:
        parser.exit(2, f'{error}\n')
    print(out.resolve())


if __name__ == '__main__':
    main()
