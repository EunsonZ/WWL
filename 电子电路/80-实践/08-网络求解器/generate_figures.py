"""Deterministic original SVGs. Import has no generation side effects."""
import argparse
import html
import json
from pathlib import Path
from network_examples import results, diode_residual


def label(x,y,s,size=14,color='#17324d'):
    return f'<text xml:space="preserve" x="{x}" y="{y}" font-size="{size}" fill="{color}">{html.escape(str(s))}</text>'

def line(x1,y1,x2,y2,color='#17324d',arrow=False):
    return f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="2" fill="none"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>'

def node(x,y,num):
    return f'<circle cx="{x}" cy="{y}" r="4" fill="#17324d"/>'+label(x+7,y-7,num)

def resistor(x1,y1,x2,y2):
    if y1==y2:
        mid=(x1+x2)/2
        points=[(x1,y1),(mid-22,y1),(mid-16,y1-7),(mid-10,y1+7),(mid-4,y1-7),(mid+2,y1+7),(mid+8,y1-7),(mid+14,y1+7),(mid+20,y1),(x2,y2)]
    else:
        mid=(y1+y2)/2
        points=[(x1,y1),(x1,mid-22),(x1-7,mid-16),(x1+7,mid-10),(x1-7,mid-4),(x1+7,mid+2),(x1-7,mid+8),(x1+7,mid+14),(x1,mid+20),(x2,y2)]
    return '<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+'" stroke="#17324d" stroke-width="2" fill="none"/>'

def wrap(height,body,title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}"><title>{html.escape(title)}</title><rect width="360" height="{height}" fill="#fff"/><defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="#17324d"/></marker></defs><g font-family="Arial, sans-serif">{body}</g></svg>\n'

def figures(data):
    b=label(14,24,'M07-01  graph → incidence → KCL',16)
    b+=resistor(75,85,275,85)+resistor(75,85,75,210)+resistor(275,85,275,210)
    b+=line(75,210,275,210)+node(75,85,'1')+node(275,85,'2')+node(175,210,'0 = reference')
    b+=label(135,60,'e3: 3 mS')+label(12,145,'e1')+label(10,168,'1 mS')+label(307,145,'e2')+label(302,168,'2 mS')
    b+=line(132,105,214,105,arrow=True)+label(157,125,'i3')
    b+=line(55,110,55,179,arrow=True)+label(21,192,'i1')
    b+=line(295,110,295,179,arrow=True)+label(300,192,'i2')
    b+=line(75,40,75,76,arrow=True)+label(14,40,'b1 = 1 mA')
    b+=label(20,260,'columns:   e1        e2        e3',16)
    b+=label(20,288,'row 1:      +1          0          +1',16)
    b+=label(20,316,'row 2:        0        +1          −1',16)
    b+=label(20,350,'u = Aᵀv [V]   →   i = Gu [A]',16)
    b+=label(20,382,'Ai = b [A]   →   Y = AGAᵀ [S]',16)
    b+=label(20,414,'v = (5/11, 3/11) V',16)
    b+=label(20,442,'i = (5/11, 6/11, 6/11) mA',15)
    incidence=wrap(466,b,'Three resistor branches and signed incidence columns')

    b=label(14,26,'M07-02/03  source constraint',16)
    b+=line(95,80,265,80)+line(95,80,95,120)+line(95,160,95,205)+line(95,205,265,205)
    b+=line(70,120,120,120)+line(70,135,120,135)+line(95,135,95,160)
    b+=line(265,80,265,114)+line(265,164,265,205)
    b+='<circle cx="265" cy="139" r="25" fill="none" stroke="#17324d" stroke-width="2"/>'
    b+=label(258,132,'+')+label(258,155,'−')+node(175,80,'v')+node(175,205,'0')
    b+=label(20,150,'C')+label(298,144,'Vs')+line(285,85,285,109,arrow=True)+label(300,103,'j')
    b+=label(20,245,'C dv/dt + j = 0  [A]',16)+label(20,276,'v − Vs = 0  [V]',16)
    b+=label(20,320,'Vs = 1 + 1000t V;  C = 1 µF',15)
    b+=label(20,353,'consistent: v0 = 1 V',16)+label(20,385,'then j = −1 mA',16)
    b+=label(20,427,'v0 = 0 + finite current:',16,color='#b13b36')+label(20,452,'incompatible with source constraint',14,color='#b13b36')
    constraints=wrap(478,b,'Capacitor in parallel with voltage source and consistency condition')

    b=label(14,25,'M07-04  tangent + damping',16)
    x0,x1,y0,y1=45,325,60,240
    xv=lambda v:x0+(v-.48)/(.13)*(x1-x0)
    yv=lambda f:y1-(f+.006)/(.046)*(y1-y0)
    b+=line(x0,y1,x1,y1,arrow=True)+line(x0,y1,x0,y0,arrow=True)
    pts=[(xv(.48+k*.13/100),yv(diode_residual(.48+k*.13/100)[0])) for k in range(101)]
    b+='<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+'" fill="none" stroke="#007f86" stroke-width="2"/>'
    f,j=diode_residual(.5)
    b+=line(xv(.48),yv(f+j*(.48-.5)),xv(.61),yv(f+j*(.61-.5)),'#b13b36')
    b+=line(x0,yv(0),x1,yv(0),'#999')+label(8,54,'F [A]')+label(269,260,'v [V]')+label(4,yv(0)+4,'0',12)+label(2,yv(.04)+4,'.04',12)
    b+=label(41,278,'0.48')+label(276,278,'0.61')
    b+=node(xv(.5),yv(f),'v0')+node(xv(.549185475),yv(diode_residual(.549185475)[0]),'λ=1/4')
    b+=label(18,310,'Full tangent root: 0.696742 V',15)+label(18,340,'outside plot; residual grows',15,color='#b13b36')
    b+=label(18,378,'k',16)+label(55,378,'v [V]',16)+label(182,378,'|F| [mA]',16)
    for row_idx,row in enumerate(data['diode_trace'][:5]):
        b+=label(18,410+row_idx*27,row['k'],15)+label(55,410+row_idx*27,f"{row['v_V']:.6f}",15)+label(182,410+row_idx*27,f"{abs(row['residual_A'])*1000:.6g}",15)
    b+=label(18,565,'stop: residual + voltage-error bound',14)
    newton=wrap(590,b,'Diode original residual, local tangent and damped Newton iterates')

    b=label(14,25,'M07-05  two different questions',16)
    for y,text in [(70,'AC: DC bias / operating point'),(130,'device Jacobian at bias'),(190,'complex solve at each f [Hz]'),(250,'small-signal gain / phase'),(350,'TRAN: source(t) + consistent x0'),(410,'implicit time step + nonlinear solve'),(470,'check time error by reducing h'),(530,'v(t), i(t), energy / recovery')]:
        b+=f'<rect x="12" y="{y-24}" width="336" height="38" rx="5" fill="#eef5fb" stroke="#adc4d8"/>'+label(20,y,text,14)
    for y in [87,147,207,367,427,487]:b+=line(180,y,180,y+15,arrow=True)
    b+=label(14,295,'AC amplitude is a perturbation scale.',14)
    b+=label(14,568,'Output grid ≠ fixed internal time step.',14)
    flow=wrap(590,b,'AC linearizes at bias while transient advances consistent states')
    return {'incidence.svg':incidence,'constraints.svg':constraints,'newton.svg':newton,'analysis-flow.svg':flow}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--raster',action='store_true',help='requires already-installed CairoSVG')
    args=parser.parse_args();out=args.output.resolve()
    vault=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if out==vault or vault in out.parents:parser.error('output must remain outside main vault')
    data=results();svgs=figures(data)
    renderer=None
    if args.raster:
        import cairosvg
        renderer=cairosvg.svg2png
    out.mkdir(parents=True,exist_ok=True)
    for name,svg in svgs.items():
        (out/name).write_text(svg)
        if renderer:
            for width in (360,425):
                renderer(bytestring=svg.encode(),write_to=str(out/(name[:-4]+f'-{width}.png')),output_width=width)
    (out/'figure-data.json').write_text(json.dumps({'graph_edges':[[1,0],[2,0],[1,2]],'conductance_S':[.001,.002,.003],'incidence':data['incidence'],'node_V':data['node_V'],'branch_A':data['branch_A'],'cv_source':{'C_F':1e-6,'Vs0_V':1,'slope_V_per_s':1000,'j_A':-.001},'newton_trace':data['diode_trace'],'plot_voltage_range_V':[.48,.61],'plot_residual_range_A':[-.006,.04]},ensure_ascii=False,indent=2)+'\n')
    print('generated',len(svgs),'SVGs',out)

if __name__=='__main__':main()
