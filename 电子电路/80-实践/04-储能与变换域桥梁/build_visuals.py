"""Original SVG teaching diagrams; generate(output), explicit --output only.

All curves are simplified analytic CPU models, never measured data. No figure
library or raster dependency is loaded on import. CairoSVG is already required
only when the explicit generator is called; no automatic installation.
"""
import argparse
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape
from transform_lab import rc_state, rl_state, modal


def text(x, y, value, size=15, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{escape(str(value))}</text>'


def line(x1,y1,x2,y2,dash=False,color="#222"):
    style=' stroke-dasharray="5 4"' if dash else ''
    return f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}"{style}/>'


def arrow(x1,y1,x2,y2):
    return f'<path d="M{x1} {y1}L{x2} {y2}" marker-end="url(#arrow)"/>'


def svg(height, title, description, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#222"/></marker></defs>
<rect width="425" height="{height}" style="fill:white;stroke:none"/>
<style>text{{font-family:DejaVu Sans,sans-serif;fill:#151515;stroke:none}} path,rect,circle{{stroke:#222;stroke-width:1.7;fill:none}} .point{{fill:#222}}</style>
{body}</svg>'''


def ground(x,y):
    return line(x,y,x,y+8)+line(x-12,y+8,x+12,y+8)+line(x-8,y+14,x+8,y+14)+line(x-4,y+20,x+4,y+20)


def loop(y, label, source, kind, initial):
    # Physical time-domain source -> switch -> R -> C/L -> return.
    b=text(18,y+20,label,17)
    b+=line(70,y+72,112,y+72)+line(130,y+72,170,y+72)
    b+='<circle cx="112" cy="'+str(y+72)+'" r="3"/><circle cx="130" cy="'+str(y+72)+'" r="3"/>'
    b+=line(112,y+72,130,y+72)+text(107,y+55,'S',13)
    b+=f'<rect x="170" y="{y+62}" width="55" height="20"/>'
    b+=text(195,y+52,'R',15,'middle')+line(225,y+72,335,y+72)
    b+=line(335,y+72,335,y+108)+line(335,y+156,335,y+192)
    if kind=='C':
        b+=line(315,y+108,355,y+108)+line(315,y+128,355,y+128)+line(335,y+128,335,y+156)
    else:
        b+=f'<path d="M335 {y+108}c-17 0 -17 12 0 12 c-17 0 -17 12 0 12 c-17 0 -17 12 0 12 c-17 0 -17 12 0 12"/>'
    b+=text(365,y+130,kind)+text(300,y+100,'+',16)+text(300,y+157,'-',16)
    b+=text(365,y+157,'v',14)+arrow(263,y+52,300,y+52)+text(276,y+41,'i',14)
    b+=line(335,y+192,70,y+192)+ground(335,y+192)
    b+=line(70,y+72,70,y+110)+line(70,y+150,70,y+192)
    b+=f'<circle cx="70" cy="{y+130}" r="20"/>'+text(70,y+124,'+',15,'middle')+text(70,y+141,'-',15,'middle')
    b+=text(18,y+176,source,13)+text(345,y+69,'a',14)+text(343,y+190,'0',14)
    b+=text(125,y+226,initial,14)
    return b


def graph(y, title, xvalues, yvalues, ymax, ylabel, color="#222", dashed=False, shade_until=None):
    left,right,top,bottom=66,397,y+40,y+170
    b=text(18,y+20,title,16)+line(left,top,left,bottom)+line(left,bottom,right,bottom)
    ymin=min(0.,min(yvalues));ymax=max(ymax, max(yvalues))
    points=[]
    for x,v in zip(xvalues,yvalues):
        px=left+(right-left)*x/max(xvalues)
        py=bottom-(bottom-top)*(v-ymin)/(ymax-ymin)
        points.append(f'{px:.3f},{py:.3f}')
    if shade_until is not None:
        selected=[point for x,point in zip(xvalues,points) if x<=shade_until]
        if selected:
            end_x=selected[-1].split(',')[0]
            polygon=f'{left},{bottom} '+ ' '.join(selected)+f' {end_x},{bottom}'
            b+=f'<polygon points="{polygon}" style="fill:#e4edf3;stroke:none"/>'
            b+=text(170,top+60,'Shaded to 1 ms:',13)+text(170,top+80,'delta q = 0.379272 uC',13)
    dash=' stroke-dasharray="6 4"' if dashed else '' 
    b+=f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"{dash}/>'
    b+=text(left,top-8,ylabel,12)+text(left-8,bottom+5,round(ymin,2),12,'end')+text(left-8,top+5,round(ymax,2),12,'end')
    b+=text(left,bottom+19,'0',12)+text(right,bottom+19,f'{max(xvalues):g}',12,'end')+text(240,bottom+35,'time (ms)',13,'middle')
    return b


def region(y,title,side):
    b=text(18,y+20,title,16)
    left,right,top,bottom=58,395,y+45,y+185
    pole=171
    if side=='right': lo,hi=pole,right
    elif side=='left': lo,hi=left,pole
    else: lo,hi=pole,283
    b+=f'<rect x="{lo}" y="{top}" width="{hi-lo}" height="{bottom-top}" style="fill:#e4edf3;stroke:none"/>'
    b+=arrow(left,y+115,right,y+115)+arrow(227,bottom,227,top)
    b+=line(pole,top,pole,bottom,True)+text(pole,y+140,'-1',13,'middle')
    if side=='strip':b+=line(283,top,283,bottom,True)+text(283,y+140,'+1',13,'middle')
    b+=text(400,y+109,'sigma/a',12,'end')+text(234,top+8,'omega/a',12)+text(230,y+140,'0',12)
    b+=line(pole-4,y+111,pole+4,y+119)+line(pole-4,y+119,pole+4,y+111)
    if side=='strip':b+=line(279,y+111,287,y+119)+line(279,y+119,287,y+111)
    b+=text(25,y+211, {'right':'Re(s) > -a; boundary excluded','left':'Re(s) < -a; boundary excluded','strip':'-a < Re(s) < a; both tails converge'}[side],14)
    return b


def source_panel(y,title,kind,series):
    b=text(18,y+20,title,16)
    top,bottom=y+55,y+185
    b+=line(83,top,160,top)+arrow(83,top,130,top)+text(100,top-10,'I',14)
    b+=text(152,top-9,'a',14)+text(152,bottom+20,'b',14)+text(40,top+15,'+',15)+text(40,bottom,'-',15)+text(25,y+130,'V',15)
    if series:
        b+=line(160,top,160,y+75)+f'<rect x="146" y="{y+75}" width="28" height="35"/>'
        b+=text(194,y+99,'1/(sC)' if kind=='C' else 'sL',15)
        b+=line(160,y+110,160,y+135)+text(146,y+127,'m',13)
        b+=f'<circle cx="160" cy="{y+155}" r="20"/>'+line(160,y+175,160,bottom)
        b+=text(160,y+148,'+' if kind=='C' else '-',15,'middle')+text(160,y+165,'-' if kind=='C' else '+',15,'middle')
        b+=text(194,y+159,'v0/s' if kind=='C' else 'L i0',15)
    else:
        b+=line(160,top,310,top)+line(160,bottom,310,bottom)
        b+=line(160,top,160,y+90)+f'<rect x="144" y="{y+90}" width="32" height="50"/>'+line(160,y+140,160,bottom)
        b+=text(91,y+121,'1/(sC)' if kind=='C' else 'sL',13,'middle')
        b+=line(310,top,310,y+100)+f'<circle cx="310" cy="{y+120}" r="20"/>'+line(310,y+140,310,bottom)
        b+=arrow(310,y+132 if kind=='C' else y+108,310,y+108 if kind=='C' else y+132)
        b+=text(347,y+123,'C v0' if kind=='C' else 'i0/s',14)
    b+=text(25,y+214, ('I = sC V - C v0' if kind=='C' else 'V = sL I - L i0'),15)
    return b


def generate(output):
    import cairosvg
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    figures={}
    figures['switch-state']=svg(775,'开关前后参考方向与储能状态','三幅完整回路：0.4V预充RC、改选1V后的RC、独立RL；节点a与参考点0、电流被动方向明示。',loop(0,'Before: t < 0; settled','0.4 V','C','R = 1 kohm; C = 1 uF; v0 = 0.4 V')+loop(255,'After: t > 0; finite R','1 V','C','v(0+) = 0.4 V; i(0+) = 0.6 mA')+loop(510,'Separate RL after switching','1 V','L','R = 100 ohm; L = 10 mH; i0 = 20 mA'))
    times=[k*1e-5 for k in range(501)]
    records=[(t,rc_state(t),rl_state(t)) for t in times]
    figures['charge-energy']=svg(675,'同一RC的电压电流与储能','R1千欧C1微法，1V输入0.4V初值；三条曲线分别为电压、电流和储能，横轴毫秒；解析CPU数据。',graph(0,'Voltage accumulates charge',[t*1000 for t in times],[z['v_V'] for _,z,_ in records],1.,'v (V)')+graph(225,'Current falls as resistor drop falls',[t*1000 for t in times],[z['i_A']*1000 for _,z,_ in records],.6,'i (mA)',shade_until=1.)+graph(450,'Energy depends on voltage squared',[t*1000 for t in times],[z['energy_J']*1e6 for _,z,_ in records],.5,'E (uJ)'))
    b=text(18,25,'s = sigma + j omega',18)+arrow(40,155,398,155)+arrow(222,198,222,48)
    b+=text(399,178,'sigma (1000 /s)',13,'end')+text(230,53,'omega (1000 rad/s)',13)
    for x,label in [(100,'-1'),(222,'0'),(344,'+1')]:
        b+=line(x,155,x,95,True)+f'<circle cx="{x}" cy="95" r="4" class="point"/>'+text(x,146,label,13,'middle')
    b+=text(236,95,'1',12)+text(30,211,'Points: sigma=-1000, 0, +1000; omega=1000',13)
    mt=[k*.00002 for k in range(301)]
    for offset,sigma,label in [(225,-1000,'Decaying'),(450,0,'Constant envelope'),(675,1000,'Growing')]:
        vals=[modal(t,sigma,1000) for t in mt]
        b+=graph(offset,label,[t*1000 for t in mt],vals,max(1.,max(vals)),'v (V)',dashed=sigma==0)
    figures['s-modal']=svg(900,'s平面点与实部波形','同一角频率1000rad/s，三个实部控制不同包络；各小图电压轴尺度分别标出，不能用图上高度比较原点不同数值。',b)
    figures['roc-regions']=svg(715,'左右侧与双侧信号的ROC','横轴sigma/a纵轴omega/a；右侧和左侧同一极点-1的不同开半平面，双侧两个极点之间的开条带，虚线排除边界。',region(0,'Right-sided: exp(-a t) theta(t)','right')+region(240,'Left-sided: -exp(-a t) theta(-t)','left')+region(480,'Two-sided: exp(-a |t|)','strip'))
    b=text(18,26,'Origin protocol: x- = 0.4 V; x+ = 1 V',16)+arrow(54,184,398,184)+arrow(212,203,212,55)
    b+=line(54,139,212,139)+line(212,139,212,75,True)+line(212,75,395,75)+text(61,131,'0.4 V',15)+text(329,64,'1 V',15)+text(215,221,'0',14)+text(393,203,'time',13)
    b+=text(18,263,'Right-side ordinary derivative = 0',15)+text(18,292,'Generalized derivative adds 0.6 V * delta(t)',14)
    b+=arrow(212,410,212,332)+line(70,410,396,410)+text(226,365,'area = 0.6 V',15)+text(24,448,'Arrow denotes area, not a finite pulse height.',14)
    b+=text(24,480,'L- derivative: s X - x- = 0.6 V',16)+text(24,512,'L+ ordinary derivative: s X - x+ = 0',16)
    figures['origin-jump']=svg(540,'原点跳变及其广义导数面积','协议演示x由0.4V跳到1V，普通右导数为0，原点导数冲激面积0.6V；箭头不表示实际有限高度冲激。',b)
    b=source_panel(0,'C parallel: source from b to a','C',False)+source_panel(230,'C series: source + at m, - at b','C',True)+source_panel(460,'L series: source - at m, + at b','L',True)+source_panel(690,'L parallel: source from a to b','L',False)
    figures['initial-sources']=svg(930,'电容电感的初始储能等效源','四幅s域端口图，a对b为正电压，I进入a；电容并联源向上、串联正端m；电感串联正端b、并联源向下。',b)
    for name,value in figures.items():
        path=out/(name+'.svg');path.write_text(value,encoding='utf-8')
        for width in (360,425):
            cairosvg.svg2png(url=str(path),write_to=str(out/(name+f'-{width}.png')),output_width=width)
    with (out/'state-data.csv').open('w',encoding='utf-8',newline='') as stream:
        w=csv.writer(stream);w.writerow(['time_s','rc_voltage_V','rc_current_A','rc_charge_C','rc_energy_J','rl_current_A','rl_voltage_V','rl_energy_J'])
        w.writerows([t,z['v_V'],z['i_A'],z['q_C'],z['energy_J'],l['i_A'],l['vL_V'],l['energy_J']] for t,z,l in records)
    with (out/'modal-data.csv').open('w',encoding='utf-8',newline='') as stream:
        w=csv.writer(stream);w.writerow(['time_s','sigma_per_s','omega_rad_per_s','real_voltage_V'])
        w.writerows((t,sigma,1000,modal(t,sigma,1000)) for sigma in (-1000,0,1000) for t in mt)
    metadata={'scope':'Analytic CPU teaching diagrams; no measurement/SPICE/client/human evidence','rc':{'R_ohm':1000,'C_F':1e-6,'source_V':1,'initial_V':.4},'rl':{'R_ohm':100,'L_H':.01,'source_V':1,'initial_A':.02},'figure_widths_px':[360,425],'figures':list(figures)}
    (out/'parameters.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
    return metadata


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(generate(parser.parse_args(argv).output),indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
