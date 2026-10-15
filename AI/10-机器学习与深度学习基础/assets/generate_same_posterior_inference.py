"""Editable same-posterior figure. Explicit output only; no import side effects."""
import argparse
import math
from pathlib import Path


def svg_text():
    # Same four-state target derived by exact elimination of A in the fixed model.
    exact = [v/1130 for v in (98, 42, 297, 693)]
    r, t = .5, .5
    for _ in range(40):
        r = 1/(1+math.exp(-((1-t)*math.log(297/98)+t*math.log(693/42))))
        t = 1/(1+math.exp(-(2*r-1)*math.log(7/3)))
    vi = [(1-r)*(1-t), (1-r)*t, r*(1-t), r*t]
    path = [1/8, 0, 3/8, 4/8]
    series = [('精确', exact, '#1d4ed8'), ('变分', vi, '#b45309'), ('八步', path, '#0f766e')]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" viewBox="0 0 480 480">',
             '<title>同一后验：精确、独立变分与固定八步轨迹</title>',
             '<desc>目标是原四变量模型观测 C 等于 1 后的 B,D 边缘。四状态顺序 00、01、10、11；精确和变分分布与八步轨迹频率逐状态比较。八步是教学轨迹，并非平稳分布。</desc>',
             '<rect width="480" height="480" fill="#f8fafc"/>',
             '<g font-family="PingFang SC, sans-serif" fill="#0f172a">',
             '<text x="20" y="31" font-size="26" font-weight="600">同一后验，三种计算</text>',
             '<text x="20" y="59" font-size="21">固定观测 C=1；先精确消去 A</text>']
    for k, (name, values, color) in enumerate(series):
        x = 20+k*145
        parts += [f'<rect x="{x}" y="77" width="18" height="18" fill="{color}"/>',
                  f'<text x="{x+25}" y="94" font-size="21">{name}</text>']
    base = 254
    for value in (0, .3, .6):
        y = base-value*210
        parts += [f'<path d="M 48 {y} H 460" stroke="#cbd5e1" fill="none"/>',
                  f'<text x="38" y="{y+5}" text-anchor="end" font-size="18">{value:g}</text>']
    for i in range(4):
        x = 70+i*103
        for k, (_, values, color) in enumerate(series):
            h = values[i]*210
            parts.append(f'<rect x="{x+k*24}" y="{base-h}" width="20" height="{h}" fill="{color}"/>')
        parts.append(f'<text x="{x+34}" y="279" text-anchor="middle" font-size="22">{i//2}{i%2}</text>')
    parts.append('<text x="20" y="280" font-size="18">BD</text>')
    for k, (name, values, color) in enumerate(series):
        y = 308+k*26
        parts.append(f'<text x="20" y="{y}" font-size="20" fill="{color}">{name}</text>')
        for i, value in enumerate(values):
            parts.append(f'<text x="{104+i*103}" y="{y}" text-anchor="middle" font-size="20">{value:.3f}</text>')
    parts += ['<text x="20" y="389" font-size="20">八步行是频率；其余两行是质量</text>',
              '<text x="20" y="422" font-size="23" font-weight="600">查询：P(D=1 | C=1)</text>',
              f'<text x="20" y="451" font-size="21">精确 {147/226:.4f}；变分 {t:.4f}；八步 0.5000</text>',
              '<text x="20" y="475" font-size="19">八步为固定示例，不能认证收敛</text>', '</g>', '</svg>']
    return '\n'.join(parts)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='explicit SVG path outside the vault for experiments')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg_text(), encoding='utf-8')


if __name__ == '__main__':
    main()
