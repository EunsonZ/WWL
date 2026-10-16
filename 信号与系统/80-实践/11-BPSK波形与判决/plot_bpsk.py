#!/usr/bin/env python3
"""Draw a bounded SVG from the completed physical-model result; no dependencies."""
import argparse
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape


def draw(result, path):
    c = result['inputs']
    eb, n0 = c['Eb_J'], c['N0_J']
    sigma_over_a = math.sqrt(n0/(2*eb))
    gammas = [row['threshold_sqrtJ']/math.sqrt(eb) for row in result['theory']]
    extent = max(2.8, max(abs(v) for v in gammas) + .5)
    peak = 1/(math.sqrt(2*math.pi)*sigma_over_a)
    x = lambda z: 90 + (z+extent)*700/(2*extent)
    y = lambda d: 340 - 224*d/peak
    divider = 389 + 25*len(result['theory'])
    grid_top = divider+55
    height = grid_top+160
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}" role="img" aria-labelledby="title desc">',
           '<title id="title">BPSK: same conditional densities, different prior thresholds</title>',
           f'<desc id="desc">Real BPSK at Eb/N0={eb/n0:g}. Fixed conditional densities; thresholds depend on the listed priors. Grids {c["grids"]} preserve pulse energy, signal energy, and projected noise variance.</desc>',
           f'<rect width="920" height="{height}" fill="white"/>',
           '<g font-family="Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif" fill="#172333" font-size="15">',
           '<text x="35" y="30" font-size="21">同一条件密度，改变先验只移动判决边界</text>',
           f'<text x="35" y="55">实 BPSK · Eb/N0={eb/n0:g} · 横坐标 z=y/√Eb · σ/√Eb={sigma_over_a:g}</text>',
           '<path d="M90 85 V340 H790" fill="none" stroke="#35465b"/>',
           '<text x="30" y="86">密度</text>', '<text x="793" y="362">z</text>']
    for value in [-.8*extent, -.4*extent, 0, .4*extent, .8*extent]:
        svg.append(f'<path d="M{x(value):.2f} 340 v5" stroke="#35465b"/><text x="{x(value)-5:.2f}" y="363">{value:.2g}</text>')
    for density in [peak*j/4 for j in range(5)]:
        svg.append(f'<path d="M85 {y(density):.2f} H790" stroke="#e2e7ed"/><text x="48" y="{y(density)+5:.2f}">{density:.2g}</text>')
    for mean, color in [(-1, '#315fa6'), (1, '#9a3985')]:
        pts = []
        for j in range(281):
            z = -extent + j*2*extent/280
            density = math.exp(-.5*((z-mean)/sigma_over_a)**2)/(math.sqrt(2*math.pi)*sigma_over_a)
            pts.append(f'{x(z):.2f},{y(density):.2f}')
        svg.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="3"/>')
    svg += ['<text x="210" y="106" fill="#315fa6">f(z | −)</text>',
            '<text x="570" y="106" fill="#9a3985">f(z | +)</text>']
    for index, row in enumerate(result['theory']):
        gamma = row['threshold_sqrtJ']/math.sqrt(eb)
        prior = row['pi_plus']
        color = '#394a59' if prior == .5 else '#bb5f08'
        svg.append(f'<path d="M{x(gamma):.2f} 120 V340" stroke="{color}" stroke-width="2" stroke-dasharray="7 5"/>')
        yy = 391 + index*25
        svg.append(f'<text x="90" y="{yy}" fill="{color}">π+={prior:g}: γ/√Eb={gamma:.6f}; 左侧判−，右侧判+</text>')
    svg += [f'<path d="M35 {divider} H885" stroke="#d4dce5"/>',
            f'<text x="35" y="{divider+28}" font-size="20">同一矩形脉冲：样点数改变，积分对象不变</text>']
    for j, row in enumerate(result['fixed']):
        L = row['grid']
        yy = grid_top+j*61
        svg.append(f'<text x="35" y="{yy+20}">L={L}</text>')
        for k in range(L):
            svg.append(f'<rect x="{110+360*k/L:.2f}" y="{yy}" width="{360/L:.2f}" height="30" fill="#cee5dc" stroke="#27674f"/>')
        label = (f'Δt={row["dt_s"]*1000:g} ms; cell Var={row["cell_noise_variance_W"]:g} W')
        svg.append(f'<text x="490" y="{yy+20}">{escape(label)}</text>')
    svg += [f'<text x="35" y="{height-25}">两网格：∫p²dt=1; Eb={eb*1e6:g} μJ; Var〈n,p〉={n0/2*1e6:g} μJ（非瞬时白噪声采样）</text>',
            '</g></svg>']
    path.write_text('\n'.join(svg)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; choose a new path')
    result = json.loads(args.results.read_text())
    draw(result, args.output)
    print(args.output)


if __name__ == '__main__':
    main()
