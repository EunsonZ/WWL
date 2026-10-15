"""Generate an editable, narrow-screen SVG of finite STFT denominators."""
import argparse
from pathlib import Path


def svg_text():
    rows = [("完整帧：起点 0、2、4", [0, .25, 1, .5, 1, .5, 1, .25],
             "可恢复：1–7；第 0 点未知", "#b45309"),
            ("补边界帧：−2、0、2、4、6", [1, .5, 1, .5, 1, .5, 1, .5],
             "零延拓后：原始 0–7 点均可恢复", "#0f766e")]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" viewBox="0 0 480 480">',
             '<title>有限 STFT 的实际窗平方覆盖分母</title>',
             '<desc>窗 [0, 0.5, 1, 0.5]、hop 2、记录索引 0 至 7。完整帧起点 0、2、4 留下首点未覆盖；显式补边界帧起点负 2、0、2、4、6 后，八个原始样本均可恢复。</desc>',
             '<rect width="480" height="480" fill="#f8fafc"/>',
             '<g font-family="PingFang SC, sans-serif" fill="#0f172a">',
             '<text x="20" y="32" font-size="26" font-weight="600">有限 STFT：逐点覆盖</text>',
             '<text x="20" y="61" font-size="23">D[n] = Σ w[n−s]²</text>']
    for row, (title, values, note, color) in enumerate(rows):
        top = 96 + row*178
        base = top + 85
        parts.append(f'<text x="20" y="{top}" font-size="23" font-weight="600">{title}</text>')
        parts.append(f'<path d="M 20 {base} H 460" stroke="#475569" fill="none"/>')
        for i, value in enumerate(values):
            x = 30+i*55
            height = value*57
            parts.append(f'<rect x="{x}" y="{base-height}" width="35" height="{height}" fill="{color}"/>')
            if value == 0:
                parts.append(f'<circle cx="{x+17.5}" cy="{base}" r="5" fill="#dc2626"/>')
            parts.append(f'<text x="{x+17.5}" y="{base-height-7}" text-anchor="middle" font-size="23">{value:g}</text>')
            parts.append(f'<text x="{x+17.5}" y="{base+25}" text-anchor="middle" font-size="20">{i}</text>')
        parts.append(f'<text x="20" y="{base+54}" font-size="23" fill="{color}" font-weight="600">{note}</text>')
    parts += ['<text x="20" y="438" font-size="20">横轴：原始索引 n；柱上数字：D[n]</text>',
              '<text x="20" y="465" font-size="20">窗 [0, ½, 1, ½]，hop = 2</text>', '</g>', '</svg>']
    return '\n'.join(parts)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='explicit SVG destination; choose a path outside the vault for experiments')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg_text(), encoding='utf-8')


if __name__ == '__main__':
    main()
