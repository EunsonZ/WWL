"""Editable deterministic SVG and explicitly labelled CPU predictions. No fake VCD."""
from pathlib import Path
import argparse
import csv
import html
import json
from hdl_model import directed,enumerate_transitions,random_check

def _vault_root():
    """Locate the actual relocated vault from this truth source, not the cwd spelling."""
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / 'AGENTS.md').is_file() and (ancestor / 'scripts/check_vault.py').is_file():
            return ancestor
    raise ValueError('cannot locate vault root: AGENTS.md and scripts/check_vault.py required')


def _destination(output):
    out=Path(output).expanduser().resolve(); vault=_vault_root()
    if out==vault or vault in out.parents:
        raise ValueError('output must be outside the main vault')
    return out


class Drawing:
 def __init__(self,title,height):
  self.height=height;self.items=[]
  self.text(18,28,title,16);self.text(18,49,'Concept / CPU prediction — not a tool waveform',12)
 def text(self,x,y,s,size=14):self.items.append(f'<text x="{x}" y="{y}" font-size="{size}">{html.escape(s)}</text>')
 def line(self,x,y,u,v):self.items.append(f'<path d="M{x} {y} L{u} {v}"/>')
 def wire(self,*points):self.items.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+'"/>')
 def box(self,x,y,w,h,label):
  self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>');self.text(x+8,y+23,label)
 def dot(self,x,y):self.items.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#15263a"/>')
 def ff(self,x,y,label):
  self.box(x,y,110,76,label);self.text(x+5,y+46,'D');self.text(x+85,y+46,'Q')
  self.wire((x+28,y+76),(x+28,y+66),(x+35,y+71),(x+28,y+76));self.text(x+52,y+70,'/RST',12)
 def svg(self):return f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{self.height}" viewBox="0 0 420 {self.height}"><rect width="420" height="{self.height}" fill="white"/><g font-family="Arial, sans-serif" fill="#15263a" stroke="none">'+''.join(x for x in self.items if x.startswith('<text'))+'</g><g fill="none" stroke="#15263a" stroke-width="1.8">'+''.join(x for x in self.items if not x.startswith('<text'))+'</g></svg>'

def figures():
 d=Drawing('01  One slot: data register + occupancy',500)
 d.text(18,82,'W unsigned bits; local rst_n; rising clk')
 d.box(90,110,110,60,'MUX data');d.ff(245,100,'data_q [W]')
 d.wire((18,132),(90,132));d.text(18,119,'s_data')
 d.wire((200,142),(245,142));d.wire((355,142),(394,142),(394,210),(60,210),(60,155),(90,155));d.dot(375,142);d.text(260,231,'hold feedback')
 d.wire((375,142),(400,142));d.text(290,89,'m_data=data_q')
 d.text(90,252,'MUX select = push = sv & ready')
 d.box(90,275,110,60,'MUX full');d.ff(245,265,'full q [1]')
 d.wire((18,297),(90,297));d.text(18,284,'s_valid');d.wire((200,307),(245,307));d.wire((355,307),(394,307),(394,363),(60,363),(60,321),(90,321))
 d.text(90,394,'MUX select = ready = rst_n & (!q | mr)')
 d.wire((273,176),(273,181),(405,181),(405,350),(273,350),(273,341))
 d.wire((315,176),(315,192),(414,192),(414,360),(315,360),(315,341))
 d.text(325,381,'clk / rst_n',12)
 d.text(18,419,'m_valid = rst_n & q; reset both registers')
 d.text(18,443,'clk → both triangle pins; /RST → rst_n')
 d.text(18,470,'Empty data is retained but is not a transaction.')
 yield 'slot-circuit',d
 d=Drawing('02  Old RHS, NBA update, safe observations',425)
 for y,label in [(90,'10 ns falling edge: drive source / ready'),(160,'11 ns: settle + record pre-edge ports'),(230,'15 ns rising: Active evaluates old RHS'),(300,'15 ns NBA: registers receive scheduled values'),(370,'16 ns: testbench checks resulting queue')]:
  d.box(18,y-20,382,44,label);d.line(205,y+24,205,y+48)
 d.text(18,416,'Logical regions at 15 ns are not physical delay.',12)
 yield 'event-regions',d
 d=Drawing('03  Directed expected transfers, no fallthrough',680)
 for i,r in enumerate(directed()['rows']):
  y=85+90*i
  d.text(18,y,f"Edge {r['edge_ns']} ns; observe {r['observe_ns']} ns")
  d.text(18,y+20,f"sv={r['sv']} word={r['source']:02X} mr={r['mr']}  ready={r['ready']}")
  d.text(18,y+40,f"PRE valid={r['valid']} data={r['data']:02X}  PUSH={r['push']} POP={r['pop']}")
  d.line(18,y+51,400,y+51);d.text(18,y+69,f"POST full={r['after_full']} data={r['after_data']:02X}")
 d.text(18,660,'Expected CPU table; actual VCD currently not_run.')
 yield 'expected-cycles',d
 d=Drawing('04  Mutation: unaccepted B2 destroys A1',350)
 d.text(18,88,'25 ns: PUSH A1 → history queue [A1]')
 d.text(18,120,'30 ns drive: sv=1, B2, mr=0')
 d.text(18,152,'35 ns PRE: ready=0, valid=1, data=A1')
 d.text(18,184,'Correct write enable push=0 → keep A1')
 d.text(18,216,'Mutant write enable sv=1 → overwrite B2')
 d.box(18,240,382,55,'36 ns predicted failure: expected A1, got B2')
 d.text(18,325,'Prediction only; no invented simulator log / VCD.')
 yield 'expected-fault',d
 d=Drawing('05  Physical timing path: Q → logic → D',520)
 d.ff(25,95,'launch L');d.ff(270,95,'capture C');d.wire((135,137),(165,137));d.box(165,112,75,50,'logic');d.wire((240,137),(270,137))
 d.text(18,212,'MAX: tCQ=3 + tPD=5 + setup=2 = 10 ns')
 d.text(18,237,'T=10 ns; skew C−L=+1 ns; u_setup=.2')
 d.text(18,262,'Available 10+1−.2=10.8 → slack +.8 ns')
 d.text(18,304,'MIN: tCQ=1 + tCD=2 = 3 ns')
 d.text(18,329,'Hold needs 2+1+.1=3.1 → slack −.1 ns')
 d.wire((53,171),(53,190),(298,190),(298,171));d.text(18,406,'Common clock tree, different branch arrival times')
 d.text(18,435,'L clock arrival 0 ns; C arrival +1 ns')
 d.text(18,468,'Slower T helps MAX; does not repair MIN.')
 d.text(18,495,'Not STA signoff; cell/route values are hypotheses.')
 yield 'physical-path',d
 d=Drawing('06  Incomplete branch requires memory',505)
 d.text(18,85,'if(en) y=d;  no else → retain y when en=0')
 d.box(65,110,120,65,'level latch');d.wire((18,145),(65,145));d.text(18,132,'d');d.wire((185,145),(340,145));d.text(340,137,'y');d.wire((125,175),(125,205));d.text(145,201,'EN=en (level)')
 d.text(18,247,'Complete combination: y = en ? d : 0')
 d.box(150,280,100,65,'MUX');d.wire((18,300),(150,300));d.text(18,286,'d');d.wire((18,328),(150,328));d.text(18,316,"0");d.wire((250,312),(380,312));d.text(355,298,'y');d.wire((200,345),(200,368));d.text(219,369,'en')
 d.text(18,413,'Clocked if(en) q<=d retains via FF enable.')
 d.text(18,438,'Same missing else, different triggering process.')
 d.text(18,476,'Synthesis diagram here is conceptual, not netlist.')
 yield 'latch-mux',d
 d=Drawing('07  Single-bit CDC and torn two-bit bus',530)
 d.ff(80,100,'FF1');d.ff(270,100,'FF2');d.wire((18,142),(80,142));d.text(18,94,'async level');d.wire((190,142),(270,142));d.wire((380,142),(402,142));d.text(280,90,'use only Q2')
 d.wire((108,176),(108,215),(298,215),(298,176));d.wire((150,176),(150,190),(340,190),(340,176));d.wire((18,190),(150,190));d.dot(150,190);d.text(18,184,'local rst_n',12)
 d.wire((18,215),(108,215));d.dot(108,215)
 d.text(18,245,'clk_B → both triangles; no FF1 fanout')
 d.text(18,278,'FF1 may go metastable; extra settling time')
 d.text(18,301,'Probability reduced; no deterministic 2-cycle bound')
 d.text(18,342,'Two independent bit chains do not make a word.')
 d.text(18,367,'Source 01 → 10; skewed capture can be 00 / 11')
 d.text(18,405,'Atomic bus: hold data, synchronize request,')
 d.text(18,430,'capture after stability margin, return ack.')
 d.text(18,470,'Narrow pulses need toggle / handshake / FIFO.')
 d.text(18,500,'CDC hardware not delivered by this single-clock RTL.')
 yield 'cdc-single-bus',d
 d=Drawing('08  Gray FIFO structure: two clock domains',675)
 d.box(18,80,175,55,'clk_W: wbin + 1');d.box(225,80,175,55,'clk_R: rbin + 1')
 d.box(18,164,175,55,'wgray=b ^ (b>>1)');d.box(225,164,175,55,'rgray=b ^ (b>>1)');d.line(105,135,105,164);d.line(310,135,310,164)
 d.text(18,262,'clk_W / rgray sync',12);d.text(225,262,'clk_R / wgray sync',12)
 for x,label in ((18,'R1'),(118,'R2'),(225,'W1'),(325,'W2')):
  d.box(x,270,75,55,label);d.text(x+4,310,'D',12);d.text(x+60,310,'Q',12)
  d.wire((x+28,325),(x+28,316),(x+35,320),(x+28,325))
 d.wire((93,305),(118,305));d.wire((300,305),(325,305))
 d.wire((310,219),(310,240),(7,240),(7,305),(18,305));d.wire((105,219),(105,251),(215,251),(215,305),(225,305))
 d.wire((46,325),(46,338),(146,338),(146,325));d.wire((253,325),(253,338),(353,338),(353,325))
 d.wire((193,305),(205,305),(205,350),(105,350),(105,365));d.wire((400,305),(414,305),(414,350),(310,350),(310,365))
 d.box(18,365,175,55,'FULL comparator');d.box(225,365,175,55,'EMPTY comparator')
 d.wire((18,192),(12,192),(12,393),(18,393));d.wire((400,192),(408,192),(408,393),(400,393))
 d.box(18,460,382,55,'Dual-port memory: W write / R read addresses')
 d.wire((45,135),(2,135),(2,488),(18,488));d.wire((375,135),(418,135),(418,488),(400,488))
 d.text(18,552,'Depth 4: address 2 bits, pointer 3 bits')
 d.text(18,578,'FULL next: wg_next == {~rg_sync[2:1],rg_sync[0]}',12)
 d.text(18,604,'EMPTY: rg == wg_sync; local reset release in W/R')
 d.text(18,632,'Gray routing skew + dual-port timing required.',12)
 d.text(18,661,'Crossings without dots: separate nets.',12)
 yield 'gray-fifo',d
 d=Drawing('09  Async assertion, per-domain sync release',500)
 d.ff(85,110,'sync1');d.ff(270,110,'sync2');d.wire((18,152),(85,152));d.text(18,136,"1'b1");d.wire((195,152),(270,152));d.wire((380,152),(404,152));d.text(265,95,'local rst_n=Q2')
 d.wire((113,186),(113,235),(298,235),(298,186));d.text(18,259,'clk_domain → both CLK pins')
 d.wire((155,186),(155,205),(340,205),(340,186));d.wire((18,205),(155,205));d.dot(155,205);d.text(18,199,'rst_n')
 d.wire((18,235),(113,235));d.dot(113,235)
 d.text(18,321,'external rst_n → both asynchronous /RST pins')
 d.text(18,358,'Assert low: both Q immediately reset to 0.')
 d.text(18,383,'Release high: shift 1, then 1 on safe clock edges.')
 d.text(18,410,'Only Q2 resets downstream local registers.')
 d.text(18,439,'Recovery/removal, placement and MTBF still apply.')
 d.text(18,470,'Separate chain for each unrelated clock domain.')
 yield 'reset-chain',d


def generate(output):
 out=_destination(output)
 # heavy render libraries imported only after explicit output has been resolved
 import cairosvg
 from PIL import Image
 out.mkdir(parents=True,exist_ok=True)
 for name,drawing in figures():
  raw=drawing.svg().encode();(out/(name+'.svg')).write_bytes(raw)
  for width in (360,425):
   cairosvg.svg2png(bytestring=raw,write_to=str(out/f'{name}-{width}.png'),output_width=width)
 prediction=directed();(out/'expected-waveform.json').write_text(json.dumps(prediction,indent=2)+'\n')
 (out/'expected-fault.json').write_text(json.dumps(directed(True),indent=2)+'\n')
 data={'cpu_graph':enumerate_transitions(),'random':random_check(),'actual_hdl':'not_run at author freeze; see execution evidence','timing_ns':{'setup_slack':.8,'hold_slack':-.1}}
 (out/'verification-data.json').write_text(json.dumps(data,indent=2)+'\n')
 with (out/'expected-waveform.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(prediction['rows'][0]));writer.writeheader();writer.writerows(prediction['rows'])
 return data

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
 args=parser.parse_args();print(json.dumps(generate(args.output),indent=2))
if __name__=='__main__':main()
