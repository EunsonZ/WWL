"""Explicit empty-output generator; rendering is lazy, no main-vault writes."""
import argparse
import csv
from contextlib import contextmanager
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape
import production_model as model


@contextmanager
def isolated_cache(cache):
    keys=('MPLCONFIGDIR','XDG_CACHE_HOME')
    old={k:os.environ.get(k) for k in keys}
    cache.mkdir(parents=True,exist_ok=True)
    try:
        for k in keys: os.environ[k]=str(cache)
        yield
    finally:
        for k,v in old.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v


def svg_text(x,y,lines,size=14,anchor='start'):
    return ''.join(f'<text x="{x}" y="{y+i*20}" font-family="DejaVu Sans,sans-serif" font-size="{size}" text-anchor="{anchor}" fill="#17212b">{escape(s)}</text>' for i,s in enumerate(lines))


def svg_document(height,content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#17212b"/></marker><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0 8 L8 0" stroke="#88929a" stroke-width="1"/></pattern></defs><rect width="360" height="{height}" fill="white"/>{content}</svg>'''


def arrow(x1,y1,x2,y2):
    return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#17212b" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'


def boxes(title,steps,footer,disconnected=()):
    content=svg_text(20,25,title,16)
    start=30+20*len(title)
    for i,lines in enumerate(steps):
        y=start+75*i
        content+=f'<rect x="20" y="{y}" width="320" height="55" rx="5" fill="#edf3f6" stroke="#17212b"/>'
        content+=svg_text(30,y+22,lines)
        if i<len(steps)-1 and i not in disconnected:content+=arrow(180,y+55,180,y+72)
    y=start+75*len(steps)
    content+=svg_text(20,y,footer,13)
    return svg_document(y+20*len(footer)+15,content)


def process_section():
    c=svg_text(18,25,['Original planar NMOS section','Teaching layers; not to scale'],16)
    c+='<rect x="40" y="85" width="280" height="290" fill="#f0f3f5" stroke="#17212b"/>'
    for x,y,w,h,fill in [(40,85,280,40,'#dee4ea'),(40,310,280,65,'#e7ded0'),(70,310,65,18,'#a2bacf'),(230,310,65,18,'#a2bacf'),(145,304,70,6,'#556b7a'),(150,280,60,24,'#d8c797'),(65,220,65,15,'#71899d'),(230,220,65,15,'#71899d'),(210,145,85,15,'#71899d'),(95,235,10,75,'#a7adb5'),(260,235,10,75,'#a7adb5'),(260,160,10,60,'#a7adb5')]:
        c+=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#17212b" stroke-width="1"/>'
    c+=svg_text(50,108,['Passivation'])
    c+=svg_text(48,145,['ILD'])+svg_text(217,180,['M2'])
    c+=svg_text(48,205,['M1 / source'])+svg_text(218,210,['M1'],13)
    c+=svg_text(276,195,['Via'],12)+svg_text(276,273,['Contact'],11)
    c+=svg_text(135,263,['Gate (poly)'])
    c+=svg_text(82,322,['n+ S'],12)+svg_text(246,322,['n+ D'],12)
    c+=svg_text(52,356,['p-type silicon body'])
    c+=svg_text(20,405,['Thin gate oxide at y = 304','S/D contacts reach silicon','Gate contact is out of this section','Body tap / isolation omitted', 'Package and PCB are later objects'],13)
    return svg_document(515,c)


def thermal_section():
    c=svg_text(20,25,['Thermal paths: same P = 0.2 W','3D layer sketch; not a solved field'],15)
    layers=[(230,'PCB node b','#a6b9c5'),(180,'Package path','#d6dadd'),(130,'Die: node j','#ddb195')]
    for y,label,fill in layers:
        c+=f'<polygon points="50,{y} 230,{y} 310,{y+35} 130,{y+35}" fill="{fill}" stroke="#17212b"/>'
        c+=f'<polygon points="130,{y+35} 310,{y+35} 310,{y+52} 130,{y+52}" fill="url(#hatch)" stroke="#17212b"/>'
        c+=svg_text(130,y+29,[label],13)
    c+=arrow(182,86,182,127)+svg_text(200,98,['P = 0.2 W'],13)
    c+=arrow(110,145,110,248)+svg_text(12,198,['j to b'],12)
    c+=arrow(220,286,220,324)+svg_text(25,340,['b to ambient; parallel j to ambient'],13)
    c+='<path d="M310 165 L340 165 L340 321 L250 321" stroke="#17212b" stroke-width="2" stroke-dasharray="5 4" fill="none" marker-end="url(#arrow)"/>'
    c+=svg_text(20,380,['Cj = 2 J/K; Cb = 8 J/K','Rjb = 5 K/W; Rba = 20 K/W','Rja = 100 K/W (parallel path)','Ta = 300 K; no geometry calibration'],13)
    return svg_document(465,c)


def dump_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def generate(output):
    out=Path(output).expanduser().resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('output must be absent or an empty directory')
    out.mkdir(parents=True,exist_ok=True)
    # Every side effect below is an explicit generate() call in a fresh output.
    with isolated_cache(out/'.cache'):
        import matplotlib
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        import cairosvg
        with matplotlib.rc_context({'font.family':'DejaVu Sans','font.size':12,
                                    'svg.fonttype':'none','svg.hashsalt':'production1-r1',
                                    'axes.grid':False}):
            assets=out/'assets';assets.mkdir()
            def save_native(name,svg):
                p=assets/(name+'.svg');p.write_text(svg,encoding='utf8')
                for w in (360,425):
                    cairosvg.svg2png(url=str(p),write_to=str(assets/f'{name}-{w}.png'),output_width=w)
            def save_plot(name,fig):
                FigureCanvasAgg(fig)
                p=assets/(name+'.svg')
                fig.savefig(p,metadata={'Date':None,'Creator':'production1 teaching source'})
                for w in (360,425):
                    cairosvg.svg2png(url=str(p),write_to=str(assets/f'{name}-{w}.png'),output_width=w)
            save_native('process-section',process_section())
            steps=[['Function / DFT architecture','control and observation design'],
                   ['Synthesis / DFT insertion','logic equivalence; flow-specific order'],
                   ['Constraints / pre-route STA','named modes, PVT and libraries'],
                   ['Place / clock tree / route','geometry, clock and wire budget'],
                   ['PEX: extract parasitics','process / RC corner / version'],
                   ['Post-PEX STA / power','feedback to place or route'],
                   ['LVS netlist / DRC geometry','feedback to design; different claims'],
                   ['Sign-off under specified PDK','license / rule / library version'],
                   ['Masks / wafer processing','deposit / pattern / etch / connect'],
                   ['Wafer probe / dicing','die-level screening'],
                   ['Package / final ATE','new interfaces and conditions'],
                   ['Board assembly and tests','ICT / boundary scan / function']]
            save_native('manufacturing-flow',boxes(['Design to manufactured object','Workflow is not PPA proof'],steps,
                ['STA / PEX / LVS / DRC / ATE not run','Arrows are dependencies, not tool logs']))
            save_native('test-probabilities',boxes(['Different denominators','Coverage is not a defect prior'],
                [['Fixed stuck-at universe: 12','Detected: 10; raw fraction = 10/12'],
                 ['Detectable-only universe: 10','Detected: 10; fraction = 10/10'],
                 ['Toy real-defect prior d = 0.02','s = 0.9; false reject f = 0.01'],
                 ['Bad accepted = 0.002 of input','Total accepted = 0.9722 of input'],
                 ['Bad | accepted = 0.205719%','Model coverage does not give s']],
                ['No ATE / physical screening performed'],disconnected=(0,1)))
            save_native('thermal-section-3d',thermal_section())
            save_native('lifecycle-trace',boxes(['Versioned traceability'],
                [['PCN or EOL: identified document','affected part / suffix / dates'],
                 ['Difference and affected need','function / thermal / interface / EMC'],
                 ['Approved BOM / PCB / firmware','approval is not installed history'],
                 ['Serial and original material lot','U001 -> BOM-A -> LOT-X'],
                 ['Test version and actual result','new repair state preserves old record'],
                 ['Archive and bounded decision','no vendor / price / lifecycle claim']],
                ['All identifiers here are fictional']))
            mc=model.mismatch_mc();grid=model.thermal_grid();trace=model.thermal_trace()
            fig=Figure(figsize=(3.6,5.4));ax=fig.add_axes((.25,.16,.70,.65))
            ax.scatter([p[0] for p in mc['points_first_300']], [p[1] for p in mc['points_first_300']],s=8,c='#283c51',marker='o')
            ax.set_xlabel('Relative R1 deviation');ax.set_ylabel('Relative R2 deviation',labelpad=5);ax.tick_params(labelsize=10)
            ax.set_xlim(-.11,.11);ax.set_ylim(-.11,.11);ax.set_aspect('equal')
            ax.plot([-.11,.11],[-.11,.11],color='#59636b',linestyle='--',linewidth=1)
            fig.text(.06,.95,'Same-die correlated deviations\nShared G; separate L1 and L2',fontsize=13,va='top')
            fig.text(.06,.055,'First 300 of 10,000 virtual dies\nNo wafer measurements; axes dimensionless',fontsize=10)
            save_plot('correlated-process',fig)
            fig=Figure(figsize=(3.6,5.8));ax=fig.add_axes((.19,.2,.76,.60))
            ax.plot([r[0] for r in trace],[r[1] for r in trace],color='#243c53',label='Junction j',linestyle='-')
            ax.plot([r[0] for r in trace],[r[2] for r in trace],color='#9b4a22',label='Board b',linestyle='--')
            ax.axhline(4,color='#243c53',linestyle=':',linewidth=1)
            ax.axhline(3.2,color='#9b4a22',linestyle='-.',linewidth=1)
            ax.set_xlabel('Time (s)');ax.set_ylabel('Excess temperature (K)');ax.set_xlim(0,200);ax.set_ylim(0,4.3)
            ax.legend(loc='lower right',fontsize=10)
            fig.text(.06,.95,'Two-node thermal transient\nP = 0.2 W; Ta = 300 K\nRK4; initial excess = 0 K',fontsize=13,va='top')
            fig.text(.06,.06,'Horizontal lines: analytic steady states\nTeaching values; not device thermometry',fontsize=10)
            save_plot('thermal-transient',fig)
            fig=Figure(figsize=(3.6,6.2));ax=fig.add_axes((.18,.23,.76,.56))
            t=[[300+v for v in row] for row in grid['theta_K']]
            contours=ax.contour(range(9),range(9),t,levels=[300.05,300.1,300.2,300.4,300.7],colors='#243c53',linewidths=1.2)
            ax.clabel(contours,inline=True,fontsize=9,fmt='%.2f K')
            # Heat-flow direction on this discrete solution; not calibrated vector magnitude.
            qx=[];qy=[];xs=[];ys=[]
            for y in (2,4,6):
                for x in (2,4,6):
                    vx=(t[y][x-1]-t[y][x+1])/2
                    vy=(t[y-1][x]-t[y+1][x])/2
                    norm=(vx*vx+vy*vy)**.5
                    if norm>1e-8:xs.append(x);ys.append(y);qx.append(vx/norm*.65);qy.append(vy/norm*.65)
            ax.quiver(xs,ys,qx,qy,angles='xy',scale_units='xy',scale=1,color='#a04420',width=.009)
            ax.plot(4,4,'ks',markersize=5)
            ax.set_aspect('equal');ax.set_xlabel('x grid index');ax.set_ylabel('y grid index');ax.set_xlim(0,8);ax.set_ylim(0,8)
            fig.text(.06,.95,'Discrete thermal isotherms\nP = 0.2 W at centre; Ta = 300 K\nLinks = 0.1 W/K; boundary = Ta',fontsize=12,va='top')
            fig.text(.06,.07,'Arrows: direction only, not heat magnitude\nNo metric grid spacing or FEM calibration\nSeparate model from two-node RC network',fontsize=10)
            save_plot('thermal-isotherms',fig)
            parameters={'model_status':'original_bounded_teaching_not_measured','thermal':model.THERMAL,
                        'power_W':.2,'feedback_W_per_K':0,'mc_n':10000,'mc_seed':2403,
                        'sigma_global':.03,'sigma_local':.01,'threshold':.02,
                        'grid_size':9,'grid_link_W_per_K':.1,'grid_boundary_K':300}
            dump_json(out/'parameters.json',parameters)
            serials=[{'serial':'U001','bom':'BOM-A','lot':'LOT-X'},
                     {'serial':'U002','bom':'BOM-A','lot':'LOT-Y'},
                     {'serial':'U003','bom':'BOM-B','lot':'LOT-Z'}]
            results={'status':'finite_CPU_teaching_only','poisson_yield':model.poisson_yield(1e-4,1000),
                     'accepted_bad':model.accepted_bad(.02,.9,.01),
                     'zero_failure_upper_n100':model.zero_failure_upper(100),
                     'arrhenius_300_to_350_Ea0_5':model.arrhenius_factor(.5,300,350),
                     'mc':{k:v for k,v in mc.items() if k!='points_first_300'},
                     'thermal_final':trace[-1], 'grid':{k:v for k,v in grid.items() if k!='theta_K'},
                     'trace_records':serials,'affected_LOT_X':model.affected_serials(serials,'LOT-X'),
                     'compliance_reading':{'product':'fictional board A; classification not confirmed',
                                          'supply_assumption_V':5,'regions_to_check':['EU','US'],
                                          'limits':None,'test_results':None,'status':'not_run'},
                     'not_run':['PDK','STA','PEX','LVS','DRC','ATE','SPICE','EMC','safety','hardware','human']}
            dump_json(out/'results.json',results)
            with (out/'thermal-trace.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['time_s','theta_j_K','theta_b_K']);w.writerows(trace)
            with (out/'mc-first300.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['relative_R1','relative_R2']);w.writerows(mc['points_first_300'])
            with (out/'thermal-grid.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['x_index','y_index','temperature_K'])
                w.writerows((x,y,300+grid['theta_K'][y][x]) for y in range(9) for x in range(9))
    return out


def main(argv=None):
    parser=argparse.ArgumentParser(description='Bounded manufacturing and thermal teaching assets')
    parser.add_argument('--output',required=True,help='absent or empty new directory')
    args=parser.parse_args(argv)
    generate(args.output)


if __name__=='__main__':
    main()
