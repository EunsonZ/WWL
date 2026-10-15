"""U5 SVG sources and 425px raster checks. Explicit destination; cairosvg required."""
from pathlib import Path
import argparse
from xml.sax.saxutils import escape
import cairosvg


def svg(height, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#222"/></marker></defs>
<rect width="425" height="{height}" fill="white"/>
<style>text{{font-family:Arial,sans-serif;font-size:14px;fill:#171717}} .title{{font-size:18px;font-weight:bold}} .small{{font-size:12px}} .box{{fill:#eef3f7;stroke:#222;stroke-width:1.5}} .path{{fill:none;stroke:#222;stroke-width:1.5;marker-end:url(#arrow)}}</style>
{body}</svg>'''


def text(x,y,s,cls='',anchor='start'):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(s)}</text>'


def build(output):
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    b=text(20,28,'One-place control FSM','title')
    b+='<circle cx="98" cy="165" r="52" class="box"/><circle cx="326" cy="165" r="52" class="box"/>'
    for x,name,q in [(98,'EMPTY','q=0'),(326,'FULL','q=1')]:
        b+=text(x,161,name,anchor='middle')+text(x,182,q,anchor='middle')
    b+='<path d="M137 130 Q212 70 287 130" class="path"/>'+text(212,87,'p=1 / LOAD',anchor='middle')
    b+='<path d="M287 201 Q212 255 137 201" class="path"/>'+text(212,248,'c=1, p=0 / EMPTY',anchor='middle')
    b+='<path d="M291 125 C250 32 402 32 361 125" class="path"/>'+text(326,78,'REPLACE','small','middle')+text(326,98,'p=c=1','small','middle')
    b+='<path d="M360 204 C402 295 250 295 292 204" class="path"/>'+text(326,296,'p=c=0: HOLD',anchor='middle')
    b+='<path d="M55 136 C-8 85 -8 245 55 194" class="path"/>'+text(8,265,'p=0', 'small')
    b+=text(20,323,'p=push: accept input; c=pop: emit old data')
    b+=text(20,347,'rst_n=0: any state -> EMPTY; no transfers')
    b+=text(20,371,'HOLD forbids write; REPLACE writes new data')
    b+=text(20,395,'Control q is one bit; payload d is W bits')
    figures={'fsm':svg(415,b)}
    b=text(14,28,'Edges: observe old, then update','title')
    headers=['k','sv/in','mr','r/v','POP','after']
    xs=[22,87,148,205,273,361]
    for x,h in zip(xs,headers): b+=text(x,61,h,anchor='middle')
    rows=[('0','reset','-','0/0','-','EMPTY'),('1','1/A1','1','1/0','-','A1'),('2','1/B2','0','0/1','-','A1'),('3','1/B2','0','0/1','-','A1'),('4','1/B2','1','1/1','A1','B2'),('5','0/.','1','1/1','B2','EMPTY'),('6','0/.','1','1/0','-','EMPTY')]
    for j,row in enumerate(rows):
        y=88+j*39
        b+=f'<rect x="8" y="{y-20}" width="409" height="35" fill="{ "#eef3f7" if j%2 else "#fff"}" stroke="#bbb"/>'
        for x,h in zip(xs,row): b+=text(x,y,h,anchor='middle')
    b+=text(14,379,'PUSH at 1: A1; at 4: B2')+text(14,402,'STALL at 2,3: pending B2 is NOT accepted')
    b+=text(14,425,'POP at 4 uses old A1; after holds new B2')
    b+=text(14,448,'First PUSH at 1 -> earliest POP at 2')
    b+=text(14,471,'No fall-through; . means invalid payload')
    figures['cycles']=svg(490,b)
    b=text(16,28,'RTL-to-signoff evidence','title')
    b+=text(111,59,'Logic / sampled state',anchor='middle')+text(317,59,'Physical / integration',anchor='middle')
    left=[('Contract + induction','all lengths, given assumptions'),('Python queue tests','finite traces: executed'),('RTL + testbench + SVA','compile/run: NOT executed'),('Synthesis + formal','netlist/properties: NOT run')]
    right=[('Clock / IO constraints','board budgets: NOT measured'),('CDC / RDC review','structure + reset assumptions'),('Place/route + STA','setup/hold, recovery/removal'),('FPGA / device tests','actual clocks, resets, corners')]
    for side,items in [(14,left),(225,right)]:
        for j,(a,c) in enumerate(items):
            y=78+j*98
            b+=f'<rect x="{side}" y="{y}" width="186" height="75" class="box"/>'
            b+=text(side+93,y+26,a,anchor='middle')+text(side+93,y+50,c,'small','middle')
            if j<3:b+=f'<path d="M{side+93} {y+75} L{side+93} {y+98}" class="path"/>'
    b+='<path d="M202 215 L223 215" class="path"/>'
    b+='<rect x="7" y="266" width="411" height="219" fill="none" stroke="#222" stroke-dasharray="5 4"/>'
    b+=text(16,510,'Dashed region: EDA/device evidence absent')+text(16,535,'No implication from Python PASS to timing PASS')
    b+=text(16,560,'CDC/RDC also reviewed before/after synthesis')
    figures['signoff']=svg(580,b)
    for name,data in figures.items():
        (out/(name+'.svg')).write_text(data,encoding='utf-8')
        cairosvg.svg2png(bytestring=data.encode(),write_to=str(out/(name+'-425.png')),output_width=425)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    build(parser.parse_args().output)
