"""Deterministic SVG sources from the actual circuit and retained SPICE trajectories."""
from pathlib import Path
from html import escape
import argparse

def svg_header(width,height,title,desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><rect width="100%" height="100%" fill="#fff"/><style>text{{font-family:Arial,"Noto Sans CJK SC",sans-serif;fill:#172936}} .wire{{fill:none;stroke:#253b4a;stroke-width:2}} .gate{{fill:none;stroke:#106c9d;stroke-width:2.5}}</style>']
def figures(data,output):
    import numpy as np
    data=Path(data);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    s=svg_header(1200,680,'11管OTA与实际共模反馈','左侧M1/M2输入差分对、M3/M4 PMOS负载、M5尾源。右侧M7/M8误差对、M9尾源、M10/M11 PMOS镜。M6与50微安参考生成vb。sense由两只电阻取样，vc连接主PMOS栅。电容逐节点列于图下。')
    def line(x1,y1,x2,y2,cls='wire'):s.append(f'<path class="{cls}" d="M{x1} {y1} L{x2} {y2}"/>')
    def text(x,y,t,size=15,anchor='start'):s.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{escape(t)}</text>')
    def dot(x,y):s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#253b4a"/>')
    def mos(x,y,name,pm=False):
        line(x,y-25,x,y-14);line(x,y-14,x,y+14);line(x,y+14,x,y+25)
        line(x-12,y-14,x-12,y+14);line(x-38,y,x-12,y,'gate')
        if pm:s.append(f'<circle cx="{x-17}" cy="{y}" r="4" fill="white" stroke="#253b4a" stroke-width="1.5"/>')
        text(x+13,y+5,name)
    text(30,30,'One 11-MOS circuit: bias, sensing, actuation and hidden states',24)
    text(70,70,'Main differential OTA',19);text(740,70,'CMFB: sense up -> vc up -> main current down',18)
    line(150,105,520,105);text(155,95,'VDD = 3.3 V')
    for x,p,n in ((220,'M3','M1'),(480,'M4','M2')):
        mos(x,165,p,True);line(x,105,x,140);line(x,190,x,270);dot(x,250)
        mos(x,325,n);line(x,270,x,300);line(x,350,x,410)
    line(220,410,480,410);line(350,410,350,450);mos(350,475,'M5');line(350,500,350,540);text(350,562,'0',16,'middle')
    text(205,245,'op',16,'end');text(500,245,'om',16)
    text(158,330,'gp',15,'end');text(418,330,'gm',15,'end');text(360,405,'s')
    line(182,165,182,130,'gate');line(442,165,442,130,'gate');line(182,130,442,130,'gate');text(320,123,'vc controls both PMOS gates',14,'middle')
    text(303,480,'vb',14,'end')
    # Actual two-resistor detector, not a lossless average block.
    line(220,250,220,280);line(220,280,285,280)
    s.append('<path class="wire" d="M285 280 l5 -7 10 14 10 -14 10 14 10 -14 10 14 5 -7 L350 280"/>')
    line(350,280,355,280);dot(350,280)
    s.append('<path class="wire" d="M355 280 l5 -7 10 14 10 -14 10 14 10 -14 10 14 5 -7 L480 280"/>')
    line(480,250,480,280);text(310,265,'200 kΩ',13,'middle');text(405,265,'200 kΩ',13,'middle')
    s.append('<path class="gate" d="M350 280 L350 370 L670 370 L670 325 L762 325"/>');text(555,362,'sense',16)
    # Error pair and PMOS mirror.
    line(760,105,1060,105);text(765,95,'VDD')
    for x,p,n in ((800,'M10','M7'),(1030,'M11','M8')):
        mos(x,165,p,True);line(x,105,x,140);line(x,190,x,250);dot(x,250)
        mos(x,325,n);line(x,250,x,300);line(x,350,x,410)
    line(800,410,1030,410);line(915,410,915,450);mos(915,475,'M9');line(915,500,915,540);text(915,562,'0',16,'middle')
    line(800,250,745,250);line(745,250,745,165,'gate');line(745,165,762,165,'gate');line(745,130,992,130,'gate');line(745,130,745,165,'gate');line(992,130,992,165,'gate')
    text(812,245,'vm',16);text(1045,245,'vc',16)
    line(992,325,960,325,'gate');text(957,350,'ref = 1.65 V',14,'end');text(867,480,'vb',14,'end');text(930,405,'sc')
    s.append('<path class="gate" d="M1030 250 L1110 250 L1110 48 L182 48 L182 130"/>')
    text(690,43,'CMFB wire: vc -> M3/M4 gates',14,'middle')
    # Diode reference inset.
    text(35,435,'Bias',17);line(100,450,100,468);s.append('<circle cx="100" cy="488" r="19" fill="none" stroke="#253b4a" stroke-width="2"/>');text(100,493,'↓',19,'middle');text(130,492,'50 µA')
    line(100,507,100,545);dot(100,530);mos(100,570,'M6');line(100,530,52,530,'gate');line(52,530,52,570,'gate');line(52,570,62,570,'gate');line(100,595,100,620);text(100,640,'0',16,'middle');text(110,535,'vb')
    text(100,444,'VDD',14,'middle')
    text(320,600,'Bodies: NMOS -> 0; PMOS -> VDD. Teaching GAMMA = 0.',15)
    text(320,625,'C to 0: op/om 20 pF; s/vb/sense/sc/vm 5 pF; vc 10 nF.',15)
    text(320,650,'Ideal sources: supply, 50 uA, ref and external DM sum. Dots = junctions.',14)
    s.append('</svg>');(output/'ota-cmfb.svg').write_text(''.join(s))
    normal=np.loadtxt(data/'spice/nominal-tran/transient.txt',skiprows=1);bad=np.loadtxt(data/'spice/smallcap-tran/transient.txt',skiprows=1)
    s=svg_header(960,610,'同一差模衰减，隐藏共模却失稳','保留SPICE原始有限扰动轨迹，横轴0至100微秒。上图输出平均值，下图输出差值。实线vc对地10nF，虚线20pF。两者工作点相同，20pF共同状态进入大幅运动。')
    def txt(x,y,t,size=15):s.append(f'<text x="{x}" y="{y}" font-size="{size}">{escape(t)}</text>')
    txt(70,30,'Only Cvc changes: a DM probe misses the growing common mode',23)
    def panel(y0,low,high,label,fn):
        x0=85;y1=y0+185
        for k in range(6):
            xx=x0+k*150;s.append(f'<path d="M{xx} {y0} V{y1}" stroke="#e5e9ed"/>');txt(xx-8,y1+23,str(k*20),13)
        for k in range(4):
            yy=y1-k*185/3;s.append(f'<path d="M{x0} {yy} H835" stroke="#e5e9ed"/>');txt(12,yy+5,f'{low+(high-low)*k/3:.3g}',13)
        txt(85,y0-13,label,16)
        for arr,color,dash in ((normal,'#006e87',''),(bad,'#be5031','stroke-dasharray="6 4"')):
            rows=arr[arr[:,0]<=.0001];stride=max(1,len(rows)//1500);rows=rows[::stride]
            values=fn(rows);points=' '.join(f'{x0+t/.0001*750:.3f},{y1-(v-low)/(high-low)*185:.3f}' for t,v in zip(rows[:,0],values))
            s.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" {dash}/>')
    panel(90,0,3.3,'Output mean voc, V',lambda a:(a[:,1]+a[:,2])/2)
    panel(345,-.2,1.1,'Output difference vod, mV (initial 1 mV)',lambda a:(a[:,1]-a[:,2])*1000)
    txt(715,580,'Time, us',15);txt(110,575,'Solid 10 nF: stable full state',15);txt(380,575,'Dashed 20 pF: unstable CM',15)
    s.append('</svg>');(output/'hidden-common-mode.svg').write_text(''.join(s))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();figures(a.data,a.output)
