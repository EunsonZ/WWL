"""Generate editable SVG and 360/425 previews into a new directory only."""
import argparse
import json
import math
import html
import re
from pathlib import Path

def generate(output):
    output = Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('output must be absent or an empty directory')
    # Heavy dependencies are deliberately after output checks; import is inert.
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib import rc_context
    import models as m
    output.mkdir(parents=True, exist_ok=True)
    generated=[]
    def figure(rows, title):
        f=Figure(figsize=(4.25, rows*1.9+.5),layout='constrained')
        FigureCanvasAgg(f)
        f.suptitle(title,fontsize=11)
        axes=f.subplots(rows,1,squeeze=False)[:,0]
        for a in axes:
            a.tick_params(labelsize=9);a.grid(True,alpha=.28)
        return f,axes
    def save(f,name):
        f.savefig(output/(name+'.svg'),metadata={'Date':None,'Creator':'WWL original declared-model plot'})
        svg=output/(name+'.svg')
        desc=('Same x and row scales for doping, SCR approximate n/p, depletion rho, '
              'negative electric field and potential. Boundary approximation is not full transport.'
              if name.startswith('pn-') else {
              'diode-load-tangent':'Diode ID versus VD: declared exponential model, load Q, local dI/dV tangent and IQ/VQ secant. Not measured data.',
              'bjt-load-tangent':'Static Ebers-Moll: output IC versus VCE at fixed VBE and input IC versus VBE at fixed VCE. Same Q, gm and go are separate. No Early effect.',
              'mos-load-tangent':'Declared long-channel teaching MOS: output and input slices at same Q, gm and gds separately fixed ports, load line and DC secants. Not a process model.'}[name])
        text=svg.read_text()
        text=re.sub(r'(<svg\b[^>]*>)',lambda z:z.group(1)+'\n<title>'+html.escape(f._suptitle.get_text())+'</title>\n<desc>'+html.escape(desc)+'</desc>',text,count=1)
        svg.write_text(text)
        for width in (360,425):
            f.savefig(output/f'{name}-{width}.png',dpi=width/4.25)
        generated.append(name)
    with rc_context({'svg.hashsalt':'wwl-devicefig1','svg.fonttype':'none','font.family':'DejaVu Sans'}):
        xs=[(-.65+i/600)*1e-6 for i in range(601)]
        xm=[x*1e6 for x in xs]
        for vd,name in [(0.,'pn-equilibrium'),(.2,'pn-forward'),(-1.,'pn-reverse')]:
            data=[m.pn(vd,x) for x in xs]
            f,aa=figure(5,f'PN: Vp-Vn={vd:+.1f} V\nCommon x / row scales\nApproximate SCR n,p; depletion rho')
            aa[0].plot(xm,[d['NA'] for d in data],label='NA',color='black')
            aa[0].plot(xm,[d['ND'] for d in data],label='ND',linestyle='--',color='tab:blue')
            aa[0].set_ylabel('Doping / m^-3',fontsize=10);aa[0].legend(fontsize=9)
            for key,style in [('n','-'),('p','--')]:
                aa[1].semilogy(xm,[d[key] if d[key] is not None else float('nan') for d in data],style,label=key)
            aa[1].set_ylabel('n,p / m^-3\nSCR only',fontsize=10);aa[1].set_ylim(1e-9,1e23);aa[1].legend(fontsize=9)
            for a,key,label,scale in [(aa[2],'rho','rho / C m^-3',1),(aa[3],'E','E / MV m^-1',1e-6),(aa[4],'phi','phi / V',1)]:
                a.plot(xm,[d[key]*scale for d in data],color='black');a.set_ylabel(label,fontsize=10)
            aa[3].set_ylim(-6.5,.25);aa[4].set_ylim(-.05,1.8)
            z=m.pn(vd,0.)
            for a in aa:
                a.set_xlim(-.65,.35)
                for v in [-z['xp']*1e6,0.,z['xn']*1e6]:a.axvline(v,color='gray',linestyle=':',linewidth=.8)
            aa[-1].set_xlabel('x / micrometre; p left, n right',fontsize=10)
            save(f,name)
        # Single-port diode: tangent and origin-to-Q secant in the same axes.
        f,aa=figure(1,'Diode: load intersection\nTangent and secant answer different questions')
        a=aa[0];vv=[i*.65/500 for i in range(501)];qv,qi=m.intersection(lambda v:m.diode(v)[0],.65,1000.);gd=m.diode(qv)[1]
        a.plot(vv,[m.diode(v)[0]*1e3 for v in vv],label='ID(V)',color='black')
        a.plot(vv,[(.65-v)*1e3/1000 for v in vv],'--',label='0.65 V / 1 kohm')
        local=[qv-.025,qv+.01];a.plot(local,[(qi+gd*(v-qv))*1e3 for v in local],label='dI/dV at Q')
        a.plot([0,qv],[0,qi*1e3],':',label='IQ/VQ secant');a.plot([qv],[qi*1e3],'o',color='black');a.annotate('Q',(qv,qi*1e3),xytext=(-18,8),textcoords='offset points')
        a.set_ylim(-.04,.7);a.set_xlabel('VD / V');a.set_ylabel('ID / mA');a.legend(fontsize=8);save(f,'diode-load-tangent')
        # BJT output family uses the full declared static Ebers-Moll model.
        vbeq=.026*math.log(1e12);qv,qi=m.intersection(lambda v:m.bjt(vbeq,v)[0])
        f,aa=figure(2,'BJT: output load and input tangent\nDifferent derivatives, same Q')
        vv=[i/100 for i in range(501)]
        for vbe,style in zip([.66,.7,vbeq],['-',':','-.']):aa[0].plot(vv,[m.bjt(vbe,v)[0]*1e3 for v in vv],linestyle=style,label=f'VBE={vbe:.3f} V')
        aa[0].plot(vv,[(5-v)*.5 for v in vv],'--',color='black',label='5 V / 2 kohm load')
        go=m.bjt(vbeq,qv)[2]
        aa[0].plot(vv,[(qi+go*(v-qv))*1e3 for v in vv],':',color='black',label='go output tangent')
        aa[0].plot([qv],[qi*1e3],'ko');aa[0].annotate('Q',(qv,qi*1e3),xytext=(-10,-18),textcoords='offset points');aa[0].set_xlabel('VCE / V');aa[0].set_ylabel('IC / mA');aa[0].legend(fontsize=8,loc='upper left')
        vv=[.5+i*.25/500 for i in range(501)];gm=m.bjt(vbeq,qv)[1]
        aa[1].plot(vv,[m.bjt(v,qv)[0]*1e3 for v in vv],label='fixed VCE=Q output')
        loc=[vbeq-.02,vbeq+.02];aa[1].plot(loc,[(qi+gm*(v-vbeq))*1e3 for v in loc],label='gm=dIC/dVBE')
        aa[1].plot([0,vbeq],[0,qi*1e3],':',label='ICQ/VBEQ');aa[1].plot([vbeq],[qi*1e3],'ko');aa[1].set_xlim(.5,.75);aa[1].set_ylim(-.1,3.5);aa[1].set_xlabel('VBE / V; fixed VCE');aa[1].set_ylabel('IC / mA');aa[1].legend(fontsize=8);save(f,'bjt-load-tangent')
        # MOS output tangent is gds; input tangent is gm, both at the same Q.
        qv,qi=m.intersection(lambda v:m.mos(1.5,v)[0]);_,gm,go=m.mos(1.5,qv)
        f,aa=figure(2,'MOS: same Q\ngm and gds are separate partial derivatives')
        vv=[i/100 for i in range(501)]
        for vg,style in zip([1.,1.5,2.],['-',':','-.']):aa[0].plot(vv,[m.mos(vg,v)[0]*1e3 for v in vv],linestyle=style,label=f'VGS={vg:.1f} V')
        aa[0].plot(vv,[(5-v)*.5 for v in vv],'--',color='black',label='5 V / 2 kohm load')
        aa[0].plot(vv,[(qi+go*(v-qv))*1e3 for v in vv],':',label='gds tangent');aa[0].plot([0,qv],[0,qi*1e3],'-.',label='IDQ/VDSQ secant');aa[0].plot([qv],[qi*1e3],'ko');aa[0].annotate('Q',(qv,qi*1e3),xytext=(-13,-18),textcoords='offset points');aa[0].set_xlabel('VDS / V');aa[0].set_ylabel('ID / mA');aa[0].legend(fontsize=8)
        vv=[.5+i*1.5/500 for i in range(501)];aa[1].plot(vv,[m.mos(v,qv)[0]*1e3 for v in vv],color='black',label='fixed VDS=Q output')
        loc=[1.3,1.7];aa[1].plot(loc,[(qi+gm*(v-1.5))*1e3 for v in loc],label='gm=dID/dVGS');aa[1].plot([0,1.5],[0,qi*1e3],':',label='IQ/VGSQ');aa[1].plot([1.5],[qi*1e3],'ko');aa[1].set_xlim(.5,2.);aa[1].set_xlabel('VGS / V; fixed VDS');aa[1].set_ylabel('ID / mA');aa[1].legend(fontsize=8);save(f,'mos-load-tangent')
    (output/'results.json').write_text(json.dumps(m.results(),indent=2)+'\n')
    return generated

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    generate(args.output)

if __name__=='__main__':main()
