"""Deterministic SVGs from results.json; no manual data edits or third-party libraries."""
import html
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets'


def plot(filename,title,xlabel,ylabel,xrange,yrange,curves,footer):
    left,right,top,bottom=115,855,75,420
    def px(x):return left+(x-xrange[0])/(xrange[1]-xrange[0])*(right-left)
    def py(y):return bottom-(y-yrange[0])/(yrange[1]-yrange[0])*(bottom-top)
    esc=html.escape
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="575" viewBox="0 0 920 575">',
         '<rect width="920" height="575" fill="white"/>',
         f'<defs><clipPath id="frame"><rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}"/></clipPath></defs>',
         '<g font-family="sans-serif" fill="#17202a" font-size="16">',
         f'<text x="460" y="30" font-size="20" text-anchor="middle">{esc(title)}</text>']
    for i in range(6):
        x=xrange[0]+i*(xrange[1]-xrange[0])/5
        y=yrange[0]+i*(yrange[1]-yrange[0])/5
        out.append(f'<path d="M {px(x):.2f} {top} V {bottom} M {left} {py(y):.2f} H {right}" stroke="#e5e8ec" fill="none"/>')
        out.append(f'<text x="{px(x):.2f}" y="445" text-anchor="middle">{x:.4g}</text>')
        out.append(f'<text x="100" y="{py(y)+5:.2f}" text-anchor="end">{y:.3g}</text>')
    out.append(f'<path d="M {left} {top} V {bottom} H {right}" stroke="#17202a" fill="none"/>')
    for i,(label,color,points,dashed) in enumerate(curves):
        xy=' '.join(f'{px(x):.3f},{py(y):.3f}' for x,y in points)
        dash=' stroke-dasharray="7 4"' if dashed else ''
        out.append(f'<polyline points="{xy}" stroke="{color}" stroke-width="2.5" fill="none" clip-path="url(#frame)"{dash}/>')
        out.append(f'<text x="{left+i*230}" y="505" fill="{color}">{esc(label)}</text>')
    out.extend([f'<text x="475" y="480" text-anchor="middle">{esc(xlabel)}</text>',
                f'<text transform="translate(32 250) rotate(-90)" text-anchor="middle">{esc(ylabel)}</text>',
                f'<text x="460" y="548" text-anchor="middle" font-size="14">{esc(footer)}</text>',
                '</g></svg>'])
    (ASSETS/filename).write_text('\n'.join(out)+'\n')


def hall_axes(pairs):
    # x right, y up, z out of page. Electron accumulation at -y yields Ey<0.
    p1,p2=pairs
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="560" viewBox="0 0 920 560">',
         '<rect width="920" height="560" fill="white"/>',
         '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>',
         '<g font-family="sans-serif" font-size="18" fill="#17202a">',
         '<text x="460" y="35" text-anchor="middle" font-size="22">Hall axes and sign: Jx &gt; 0, Bz &gt; 0, Jy = 0</text>',
         '<rect x="180" y="140" width="550" height="175" fill="#f1f7fc" stroke="#17202a"/>',
         '<text x="455" y="170" text-anchor="middle" fill="#b03a2e">+ + + : electron deficit at +y</text>',
         '<text x="455" y="302" text-anchor="middle" fill="#1565c0">- - - : electron excess at -y</text>',
         '<path d="M 300 215 H 610" stroke="#17202a" stroke-width="3" marker-end="url(#arrow)"/>',
         '<text x="455" y="205" text-anchor="middle">Jx and conventional current: +x</text>',
         '<path d="M 610 260 H 300" stroke="#1565c0" stroke-width="3" marker-end="url(#arrow)"/>',
         '<text x="455" y="285" text-anchor="middle" fill="#1565c0">electron vx &lt; 0</text>',
         '<path d="M 765 180 V 275" stroke="#b03a2e" stroke-width="3" marker-end="url(#arrow)"/>',
         '<text x="785" y="230" fill="#b03a2e">Ey &lt; 0</text>',
         '<path d="M 75 350 H 150 M 75 350 V 275" stroke="#17202a" stroke-width="2" marker-end="url(#arrow)"/>',
         '<text x="155" y="355">+x</text><text x="65" y="264">+y</text>',
         '<circle cx="90" cy="195" r="15" fill="none" stroke="#17202a"/><circle cx="90" cy="195" r="4" fill="#17202a"/>',
         '<text x="36" y="225">+z: out</text>',
         '<text x="460" y="360" text-anchor="middle">Ey = vx Bz; RH = Ey / (Jx Bz) = -1/(q n)</text>',
         '<text x="460" y="402" text-anchor="middle">Same L=1 um, A=1 um^2, same G=21.6293846 uS</text>']
    for i,p in enumerate((p1,p2)):
        y=443+42*i
        out.append(f'<text x="460" y="{y}" text-anchor="middle">n={p["n_m3"]:.3g} m^-3, mu={p["mu_m2_Vs"]:.4g} m^2/(V s): RH={p["RH_m3_C"]:.7g} m^3/C</text>')
    out.extend(['<text x="460" y="532" text-anchor="middle" font-size="15">Single isotropic electron band, constant momentum relaxation time, Hall factor 1, weak B</text>',
                '</g></svg>'])
    (ASSETS/'hall-axes.svg').write_text('\n'.join(out)+'\n')


def main():
    data=json.loads((ASSETS/'results.json').read_text())
    rows=data['sweep']
    plot('temperature-carriers.svg','Joint neutrality + FD + impurity ionization (fixed band model)',
         'temperature T [K]','log10(density / 1 m^-3) [1]',(40,1200),(10,24),[
         ('electrons n','#1565c0',[(r['T_K'],math.log10(r['n_m3'])) for r in rows],False),
         ('holes p','#b03a2e',[(r['T_K'],math.log10(r['p_m3'])) for r in rows],False),
         ('ND+ - NA-','#117864',[(r['T_K'],math.log10(r['NDplus_m3']-r['NAminus_m3'])) for r in rows],True)],
         'ND=1e22, NA=2e21 m^-3; Ec=0, Ev=-1.12 eV; p below 1e10 m^-3 is outside the plotted range')
    plot('temperature-conductivity.svg','Conductivity needs both populations and a mobility model',
         'temperature T [K]','log10(sigma / 1 S m^-1) [1]',(40,1200),(-3,4),[
         ('joint n,p + assumed mu(T)','#1565c0',[(r['T_K'],math.log10(r['sigma_S_m'])) for r in rows],False),
         ('n=ND-NA shortcut','#b03a2e',[(r['T_K'],math.log10(1.602176634e-19*8e21*r['mu_n_m2_Vs'])) for r in rows],True)],
         'Assumed mu_n=0.135(300/T)^1.5, mu_p=0.045(300/T)^1.5 m^2/(V s); illustrative, not material prediction')
    hall_axes(data['same_G_Hall_pairs'])


if __name__=='__main__':main()
