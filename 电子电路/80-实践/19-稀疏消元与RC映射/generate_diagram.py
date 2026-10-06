"""Generate original SVG matrix adjacency graph; standard library only."""
import argparse
from pathlib import Path


def svg():
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="420" height="610" viewBox="0 0 420 610" role="img" aria-labelledby="title desc">',
             '<title id="title">先消中心还是先消叶：哪里形成填充？</title>',
             '<desc id="desc">三幅矩阵邻接图。中心先消使三叶间形成三条虚线。叶先消只改中心对角项与右端，不产生新边。所有线只表示矩阵非零项，不是接线。</desc>',
             '<rect width="420" height="610" fill="white"/>',
             '<g font-family="Arial, sans-serif" fill="#142b3a" font-size="15">',
             '<text x="16" y="25">Center first or leaf first: fill-in?</text>',
             '<text x="16" y="47" font-size="13">Matrix adjacency; not circuit wiring</text>']
    for panel, y in enumerate((145,320,495)):
        parts.append(f'<rect x="12" y="{y-83}" width="396" height="165" rx="8" fill="#f3f6fa" stroke="#647b90"/>')
        labels = ('Y: c connects to three leaves','Eliminate c: three new fill edges','Leaf 1 first: no new edge')
        parts.append(f'<text x="25" y="{y-60}">{labels[panel]}</text>')
        pos = {0:(103,y),1:(237,y-30),2:(319,y),3:(237,y+32)}
        if panel != 1:
            for node in ((1,2,3) if panel==0 else (2,3)):
                x1,y1=pos[0];x2,y2=pos[node]
                parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#275a80" stroke-width="2"/>')
        if panel == 1:
            for i,j in ((1,2),(1,3),(2,3)):
                x1,y1=pos[i];x2,y2=pos[j]
                parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#923b26" stroke-width="2" stroke-dasharray="6 4"/>')
        for node,(x,ny) in pos.items():
            removed = (panel==1 and node==0) or (panel==2 and node==1)
            fill = '#e0e0e0' if removed else 'white'
            parts.append(f'<circle cx="{x}" cy="{ny}" r="14" fill="{fill}" stroke="#233f50" stroke-width="2"/>')
            parts.append(f'<text x="{x-4}" y="{ny+5}">{"c" if node==0 else node}</text>')
            if removed:
                parts.append(f'<path d="M{x-10},{ny-10} L{x+10},{ny+10}" stroke="#222" stroke-width="2"/>')
        foot=('Leaf diagonals include 1 S to reference','Dashed: -1/3 S; new RHS: 1/3 A each','c diagonal: 3 to 5/2 S; no fill')[panel]
        parts.append(f'<text x="25" y="{y+64}" font-size="13">{foot}</text>')
    parts.append('<text x="16" y="603" font-size="12">Ordering changes storage, not physical wires.</text></g></svg>')
    return '\n'.join(parts)+'\n'


def generate(output):
    data = svg()
    dest=Path(output)
    dest.mkdir(parents=True,exist_ok=True)
    p=dest/'sparse-fill.svg'
    p.write_text(data)
    return p


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    generate(args.output)


if __name__ == '__main__':
    main()
