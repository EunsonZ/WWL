"""Lazy renderer; --output required, absent/nonempty path rejected. No import writes."""
import argparse
import csv
import json
import os
from pathlib import Path
import tempfile
import array_model as model

G=[[10e-6,20e-6],[30e-6,40e-6]]
V=[.1,.2]

def svg(title,body,height=650):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}"><rect width="360" height="{height}" fill="white"/><style>text{{font:14px sans-serif;fill:#18232c}}.wire{{fill:none;stroke:#18232c;stroke-width:2}}.box{{fill:#eef4f8;stroke:#18232c;stroke-width:1.5}}.node{{fill:#18232c}}</style><defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#18232c"/></marker></defs><text x="16" y="26">{title}</text>{body}</svg>'''

def text(x,y,s):return f'<text x="{x}" y="{y}">{s}</text>'
def line(x1,y1,x2,y2,arrow=False):return f'<path class="wire" d="M{x1} {y1}L{x2} {y2}"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>'
def box(x,y,w,h,s):return f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}"/>'+text(x+5,y+h/2+5,s)
def ground(x,y):return line(x,y,x,y+8)+line(x-9,y+8,x+9,y+8)+line(x-6,y+12,x+6,y+12)+text(x+12,y+12,'0 V')

def circuit():
    s=text(16,49,'2x2 resistors; fixed linear DC model')+text(16,72,'Crossings without dots are NOT junctions')
    for i,y in enumerate([160,360]):
        s+=f'<circle class="wire" cx="30" cy="{y}" r="12"/>'+text(26,y+4,'+')+ground(30,y+12)+text(40,y-37,f'U{i+1}={V[i]} V')
        s+=line(42,y,55,y)+box(55,y-7,20,14,'')+line(75,y,90,y)+text(45,y-15,'1k')
        s+=line(90,y,145,y)+box(145,y-7,35,14,'')+line(180,y,245,y)+text(147,y-15,'1k')
        for j,x in enumerate([90,245]):
            cy=y+85
            s+=line(x,y,x,y+30)+box(x-9,y+30,18,25,'')+line(x,y+55,x,cy)
            s+=text(x+14,y+45,f'{G[i][j]*1e6:.0f} uS')
            for yy,label in [(y,f'r{i+1}{j+1}'),(cy,f'c{i+1}{j+1}')]:
                s+=f'<circle class="node" cx="{x}" cy="{yy}" r="3"/>'+text(x+6,yy-8,label)
    # c11 to c21 route is left of both source symbols, with no wire crossing.
    s+=line(90,245,15,245)+line(15,245,15,285)+box(8,285,14,25,'')+text(25,303,'1k')
    s+='<path class="wire" d="M15 310L15 445L90 445"/>'
    s+=line(245,245,320,245)+line(320,245,320,285)+box(313,285,14,25,'')+text(290,303,'1k')+line(320,310,320,445)+line(320,445,245,445)
    for j,x in enumerate([90,245]):
        s+=line(x,445,x,480)+box(x-7,480,14,25,'')+text(x+15,497,'1k')+line(x,505,x,540,True)+ground(x,540)+text(x-30,588,f'I{j+1} -> clamp')
    s+=text(16,617,'0-V clamps ideal; readout rail energy omitted')
    return svg('Finite-wire array: 8 unknown node voltages',s)

def ideal_ports():
    s=text(16,53,'All voltages relative to shared return 0 V')
    s+=box(25,90,310,55,'DAC row drivers: U1=.1 V, U2=.2 V')
    s+=line(100,145,100,178,True)+line(250,145,250,178,True)
    s+=box(25,180,310,90,'G [uS] = [10 20; 30 40]')+text(40,248,'Rows input; columns output; no negative G')
    s+=line(100,270,100,310,True)+line(250,270,250,310,True)
    s+=box(25,315,310,60,'I1=7 uA; I2=10 uA into 0-V clamps')
    s+=ground(100,375)+ground(250,375)
    s+=text(16,432,'Ideal rows constant; columns clamped at 0 V')+text(16,457,'Cell: Iij=Gij Ui. Column KCL: Ij=sum_i Iij')
    s+=text(16,491,'Drivers and real readout need supply rails')+text(16,516,'VDD/VSS energy is outside this resistor model')
    return svg('Ideal MVM: voltage -> conductance -> current',s,550)

def diff_ports():
    s=text(16,54,'Two passive arrays; same referenced inputs')
    s+=box(25,85,310,55,'DAC inputs .1x [V]; return 0 V')+line(100,140,100,177,True)+line(250,140,250,177,True)
    s+=box(15,180,150,95,'')+box(195,180,150,95,'')+text(25,211,'G+ >= 0 [S]')+text(205,211,'G- >= 0 [S]')
    s+=text(25,239,'base + s max(w,0)')+text(203,239,'base + s max(-w,0)')
    s+=line(90,275,90,320,True)+line(270,275,270,320,True)
    s+=box(15,325,150,55,'0-V clamp / ADC+')+box(195,325,150,55,'0-V clamp / ADC-')
    s+=ground(90,380)+ground(270,380)+line(90,415,90,460)+line(270,415,270,460)
    s+=line(90,460,150,460,True)+line(270,460,210,460,True)+box(150,438,60,45,'+ / -')
    s+=text(16,514,'Signed result = I+ - I-; both banks draw power')+text(16,543,'Bipolar input driver or signed phase protocol')+text(16,572,'No negative resistor. ADC range specified apart')
    return svg('Differential weights and physical return paths',s,600)

def lif_circuit():
    s=text(16,53,'Synthetic electrical analogy, NOT a cell device')
    s+=line(55,120,285,120)+line(55,120,55,190)+f'<circle class="wire" cx="55" cy="210" r="20"/>'+line(55,226,55,196,True)+line(55,230,55,325)+ground(55,325)
    s+=text(16,78,'I [A] flows into v')+line(165,120,165,180)+box(158,180,14,55,'')+line(165,235,165,325)+ground(165,325)+text(185,210,'R=10 Mohm')
    s+=line(285,120,285,195)+line(267,195,303,195)+line(267,207,303,207)+line(285,207,285,325)+ground(285,325)+text(223,256,'C=1 nF')
    s+=f'<circle class="node" cx="285" cy="120" r="3"/>'+text(180,104,'v [V]; rest=0 V')
    s+=line(285,120,335,120)+line(335,120,335,395,True)+box(20,395,315,80,'')+text(30,423,'Threshold .01 V -> event -> reset 0 V')
    s+=text(34,450,'Then ideal hold for 1 ms (own extension)')+text(16,515,'C dv/dt = I - v/R; tau=RC=.01 s')+text(16,542,'Reset control/supply energy not predicted')
    return svg('LIF subthreshold node and ideal reset rule',s,565)


def generate(output):
    output=Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('output must be absent or empty directory')
    output.mkdir(parents=True,exist_ok=True)
    old_env=dict(os.environ)
    try:
        with tempfile.TemporaryDirectory(prefix='.f06-mpl-',dir=output) as cache:
            os.environ['MPLCONFIGDIR']=cache
            os.environ['XDG_CACHE_HOME']=cache
            import matplotlib
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            import cairosvg
            with matplotlib.rc_context({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'frontier06-r1','axes.spines.top':False,'axes.spines.right':False}):
                for name,data in [('ideal-ports',ideal_ports()),('array-nodes',circuit()),('differential-ports',diff_ports()),('lif-node',lif_circuit())]:
                    (output/(name+'.svg')).write_text(data,encoding='utf-8')
                def plot(name,title,ylabel,curves,xlabel='Input basis vector',ylim=None):
                    f=Figure(figsize=(3.6,4.8),layout='constrained');FigureCanvasAgg(f);a=f.add_subplot()
                    for xx,yy,label,style,marker in curves:a.plot(xx,yy,style,marker=marker,label=label)
                    a.set_title(title,fontsize=12);a.set_xlabel(xlabel);a.set_ylabel(ylabel)
                    a.grid(True,alpha=.3);a.legend(fontsize=10)
                    if ylim:a.set_ylim(*ylim)
                    f.savefig(output/(name+'.svg'),metadata={'Date':None})
                ideal=[model.array(G,v)['output_A'][0]*1e6 for v in [[.1,0],[0,.1]]]
                wire=[model.array(G,v,1000)['output_A'][0]*1e6 for v in [[.1,0],[0,.1]]]
                gain=ideal[0]/wire[0]
                plot('calibration','Column 1: one-gain calibration\nFixed linear network, 1 kohm wires','Output current [uA]',[([1,2],ideal,'Ideal','k-','o'),([1,2],wire,'Wire','k--','s'),([1,2],[gain*t for t in wire],'Calibrated on basis 1','k:','^')])
                event=model.lif(.03,2e-9)
                xx=[];yy=[]
                for start,stop,v0,v1,kind in event['segments']:
                    for k in range(31):
                        t=start+(stop-start)*k/30
                        val=0 if kind=='hold' else v0+(event['steady_V']-v0)*(-__import__('math').expm1(-(t-start)/.01))
                        xx.append(t*1e3);yy.append(val*1e3)
                plot('lif-events','Single LIF: constant input 2 nA\nInstant reset; hold 1 ms','Node voltage [mV]',[(xx,yy,'v(t)','k-',None),([0,30],[10,10],'Threshold','k--',None)],xlabel='Time [ms]',ylim=(0,11))
                e=model.energy(model.differential([[1,-2],[-3,4]],[1,2])['core_W'])
                f=Figure(figsize=(3.6,4.8),layout='constrained');FigureCanvasAgg(f);a=f.add_subplot()
                names=['Array','ADC x4','DAC x2','Digital','Calib /1000']
                vals=[e['components'][key]*1e12 for key in ['array_J','ADC_J','DAC_J','digital_J','calibration_J']]
                a.barh(names,vals,color='white',edgecolor='black',hatch='///');a.set_xlabel('Energy per MVM [pJ]');a.set_title('Synthetic costs, not device data\nComm/idle assumed zero here',fontsize=12);a.invert_yaxis()
                for i,val in enumerate(vals):a.text(val+2,i,f'{val:g}',va='center',fontsize=11)
                a.set_xlim(0,250);f.savefig(output/'energy-ledger.svg',metadata={'Date':None})
                for path in sorted(output.glob('*.svg')):
                    for width in [360,425]:cairosvg.svg2png(url=str(path),write_to=str(output/f'{path.stem}-{width}.png'),output_width=width)
    finally:
        os.environ.clear();os.environ.update(old_env)
    results={'synthetic':True,'ideal':model.array(G,V),'wire_1000ohm':model.array(G,V,1000),'differential':model.differential([[1,-2],[-3,4]],[1,2]),'energy':model.energy(3.3e-6),'lif':model.lif(.03,2e-9)}
    parameters={'units':'SI','G_S':G,'input_V':V,'wire_ohm':1000,'weights':[[1,-2],[-3,4]],'weight_scale_S':1e-5,'baseline_S':1e-6,'input_scale_V':.1,'ADC_bits':4,'ADC_fullscale_A':20e-6,'dwell_s':1e-6,'ADC_each_J':50e-12,'DAC_each_J':5e-12,'digital_J':5e-12,'calibration_J':100e-9,'amortized_uses':1000,'communication_J':0,'idle_J':0,'lif_R_ohm':1e7,'lif_C_F':1e-9,'lif_threshold_V':.01,'lif_rest_reset_V':0,'lif_current_A':2e-9,'lif_duration_s':.03,'lif_hold_s':.001}
    (output/'parameters.json').write_text(json.dumps(parameters,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    with (output/'wire-sweep.csv').open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(['wire_ohm','I1_A','I2_A','cell_W','wire_W','supplied_W'])
        for r in [0,1,10,100,1000,10000]:
            q=model.array(G,V,r);writer.writerow([r,*q['output_A'],q['cell_W'],q['wire_W'],q['supplied_W']])
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();generate(args.output)

if __name__=='__main__':main()
