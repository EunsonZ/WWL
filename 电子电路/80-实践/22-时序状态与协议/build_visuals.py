"""Deterministic editable SVG event figures; rendering dependencies load after parse."""
import argparse
import html
import json
from pathlib import Path

class SVG:
    def __init__(self,title,height=420):
        self.h=height;self.items=[f'<rect width="600" height="{height}" fill="white"/>'];self.text(300,25,title,18,'middle')
    def text(self,x,y,s,size=15,anchor='start'):
        self.items.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="black" font-family="DejaVu Sans">{html.escape(str(s))}</text>')
    def line(self,x,y,x2,y2,dash=False,width=2):
        self.items.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="black" stroke-width="{width}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')
    def rect(self,x,y,w,h,fill='#eeeeee'):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="black"/>')
    def dot(self,x,y,filled=True):
        self.items.append(f'<circle cx="{x}" cy="{y}" r="4" stroke="black" fill="'+('black' if filled else 'white')+'"/>')
    def save(self,path):
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="{self.h}" viewBox="0 0 600 {self.h}">'+''.join(self.items)+'</svg>\n')
    def wave(self,label,events,y,end,edges=()):
        self.text(8,y-8,label,15)
        def X(t):return 135+440*t/end
        def Y(v):return y-25*int(v)
        previous_t,previous_v=events[0]
        for t,v in events[1:]+[(end,events[-1][1])]:
            self.line(X(previous_t),Y(previous_v),X(t),Y(previous_v));self.line(X(t),Y(previous_v),X(t),Y(v))
            previous_t,previous_v=t,v
        for t in edges:self.line(X(t),y-38,X(t),y+5,True,1)
    def axis(self,y,end,ticks):
        self.line(135,y,575,y,False,1)
        for t in ticks:
            x=135+440*t/end;self.line(x,y-3,x,y+3,False,1);self.text(x,y+21,t,14,'middle')
        self.text(575,y+43,'time (ns)',14,'end')

def table(title,heads,rows,labels,name,out,foot='Pre = sampled before edge; post = committed after edge.'):
    fig=SVG(title,100+42*(len(rows)+1)+45);x0=130;w=440/len(heads)
    for k,h in enumerate(heads):fig.text(x0+w*(k+.5),65,h,15,'middle')
    for r,(label,row) in enumerate(zip(labels,rows)):
        y=80+r*42;fig.text(8,y+27,label,14)
        for k,v in enumerate(row):fig.rect(x0+k*w,y,w,42,'white');fig.text(x0+w*(k+.5),y+27,v,15,'middle')
    fig.text(10,fig.h-12,foot,13);fig.save(out/(name+'.svg'))

def generate(output):
    output=Path(output).resolve();main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if output.is_relative_to(main):raise ValueError('output must be outside main vault')
    import sequential as s
    import cairosvg
    from PIL import Image, ImageOps
    output.mkdir(parents=True,exist_ok=True)
    data=s.demo();handshake,captures=s.handshake_trace();data['handshake']=handshake;data['captures']=captures
    data['latch_events']=[(0,False,False),(2,False,True),(3,True,True),(5,False,True),(7,True,True),(8,True,False),(10,False,False)]
    data['counter']=[{'edge':k,'time_ns':10*k,'enable':e} for k,e in enumerate((True,False,True,True),1)]
    q=6
    for r in data['counter']:r['before']=q;q,r['carry']=s.counter(q,3,r['enable']);r['after']=q
    f=SVG('Latch transparency vs positive-edge sampling',390)
    events=data['latch_events'];f.wave('G (level)',[(t,g) for t,d,g in events],100,14)
    d=[(0,False),(3,True),(5,False),(7,True),(10,False)];f.wave('D (bit)',d,165,14,edges=(4,12))
    l=s.latch(False,events);f.wave('Latch Q',l,230,14)
    ff=[(0,False),(4,s.sample(False,d,4,.5,.5)),(12,s.sample(False,d,12,.5,.5))];f.wave('Edge Q',ff,295,14,edges=(4,12))
    for t,v in ff[1:]:f.dot(135+440*t/14,295-25*int(v))
    f.axis(325,14,(0,2,4,8,12,14));f.text(8,382,'Zero-delay binary view; real Q has tCQ bounds, not instant changes.',12);f.save(output/'latch-edge.svg')
    f=SVG('Setup uses next capture; hold uses same capture',430)
    def X(t):return 130+440*t/12
    f.text(8,60,'Max path: launch 0 -> stable 8 ns; next capture 11 ns',15)
    f.rect(X(0),90,X(8)-X(0),30);f.text(X(4),111,'not guaranteed stable',13,'middle')
    f.line(X(8),95,X(12),95);f.text(X(9.7),87,'new value valid',13,'middle')
    for t,label,y in ((0,'launch',145),(8,'latest 8',145),(9,'setup 9',185),(11,'capture 11',145)):
        f.line(X(t),75,X(t),135,True,1);f.text(X(t),y,label,13,'middle')
    f.text(8,220,'Min path: old value must last to hold deadline 3 ns',15)
    f.line(X(0),255,X(3),255);f.text(X(1.5),246,'old valid',13,'middle')
    f.rect(X(3),255,X(12)-X(3),30);f.text(X(7.5),276,'may change from 3 ns',13,'middle')
    for t,label,y in ((0,'launch 0',315),(1,'same capture 1',350),(3,'hold 3 = earliest',315)):
        f.line(X(t),240,X(t),300,True,1);f.text(X(t),y,label,13,'middle')
    f.axis(370,12,(0,3,6,9,12));f.text(8,427,'Tc=10; skew=capture-launch=+1; setup slack 1 ns, hold slack 0 ns.',12);f.save(output/'setup-hold.svg')
    c=data['counter'];table('3-bit counter: enabled update and wrap',[str(r['time_ns'])+' ns' for r in c],
        [[int(r['enable']) for r in c],[r['before'] for r in c],[format(r['after'],'03b') for r in c],[r['after'] for r in c],[int(r['carry']) for r in c]],
        ['enable pre','q pre (uint)','q post bits','q post (uint)','wrap post'],'counter',output)
    p=data['pipeline'];table('Two registers read old values at each edge',[f"edge {r['edge']}" for r in p],
        [[r['input'] for r in p],[r['before'][0] if r['before'][0] is not None else '--' for r in p],[r['before'][1] if r['before'][1] is not None else '--' for r in p],[r['after'][0] for r in p],[r['after'][1] if r['after'][1] is not None else '--' for r in p]],
        ['input pre','q1 pre','q2 pre','q1 post','q2 post'],'pipeline',output,'Input 10 commits to q1 at edge 1, to q2 at edge 2; -- means invalid.')
    fs=data['fsm10101'];mealy=0;before=[]
    for r in fs:mealy,hit,_=s.detector(mealy,bool(r['input']),False);before.append(int(hit))
    table('Overlapping 101: same event, different output time',[f"{r['edge']*10} ns" for r in fs],
        [[r['input'] for r in fs],['S'+('0','1','10','101')[r['before']] for r in fs],['S'+('0','1','10','101')[r['after']] for r in fs],before,[r['hit_after'] for r in fs]],
        ['x sampled','Moore pre','Moore post','Mealy pre y','Moore post y'],'fsm',output,'Mealy y is combinational before edge; Moore y follows state commit.')
    b=data['buffer'][:6];table('One slot: sample old head, then replace',[f"{r['time_ns']} ns" for r in b],
        [[int(r['sv']) for r in b],[f"{r['sd']:02X}" if r['sv'] else '--' for r in b],[int(r['mr']) for r in b],[int(r['full_before']) for r in b],[f"{int(r['push'])}/{int(r['pop'])}" for r in b],[f"{r['data_before']:02X}" if r['pop'] else '--' for r in b],[f"{r['data_after']:02X}" if r['full_after'] else '--' for r in b]],
        ['sv pre','data pre','ready down','full pre','push/pop','pop old word','word post'],'buffer',output,'Reset at 0 ns flushes; 40 ns pops A1, commits B2; no fall-through.')
    f=SVG('Pulse information vs two-stage binary synchronization',530)
    f.wave('short pulse',[(0,False),(1,True),(4,False)],95,30,edges=(0,10,20,30));f.wave('first Q',[(0,False)],155,30,edges=(0,10,20,30));f.wave('second Q',[(0,False)],215,30,edges=(0,10,20,30))
    f.text(140,245,'No edge observes 1; another stage cannot recover it.',13)
    f.wave('held level',[(0,False),(1,True)],310,30,edges=(0,10,20,30));f.wave('first Q',[(0,False),(10,True)],370,30);f.wave('second Q',[(0,False),(20,True)],430,30)
    f.axis(442,30,(0,10,20,30));f.text(8,520,'Ideal binary model only; these are not measured metastable voltages.',12);f.save(output/'cdc-pulse.svg')
    f=SVG('Four-phase bundled-data handshake: two clock domains',430)
    f.wave('source CLK',[(k,not bool((k//5)%2)) for k in range(0,81,5)],85,80)
    f.wave('dest edges',[(0,False)],145,80,edges=tuple(range(1,80,7)))
    for label,key,y in (('req source','req',205),('ack dest','ack',265),('data = 42','data',325)):
        if key=='data':f.line(135,y-15,575,y-15);f.text(350,y-23,'42 held; capture at 15 ns',14,'middle')
        else:
            ev=[(0,False)]+[(r['time_ns'],r[key]) for r in handshake if r['time_ns']<=80]
            f.wave(label,ev,y,80)
    f.line(135+440*15/80,55,135+440*15/80,340,True,1);f.text(135+440*15/80,358,'capture',13,'middle')
    done=next(r['time_ns'] for r in handshake if r['source_phase']=='done');f.line(135+440*done/80,55,135+440*done/80,340,True,1);f.text(135+440*done/80,358,'source done',13,'end')
    f.axis(375,80,(0,20,40,60,80));f.text(8,426,'Destination reads held word once; ACK crosses back; not analog CDC validation.',12);f.save(output/'handshake.svg')
    f=SVG('Async reset assertion; local synchronous release',390)
    f.wave('external rst_n',[(0,True),(2,False),(13,True)],105,50,edges=(10,20,30,40,50))
    f.wave('local stage1',[(0,True),(2,False),(20,True)],180,50)
    f.wave('local stage2',[(0,True),(2,False),(30,True)],255,50)
    f.dot(135+440*30/50,230);f.line(135+440*40/50,60,135+440*40/50,295,True,1)
    f.text(135+440*40/50,313,'first functional edge',13,'middle');f.axis(330,50,(0,10,20,30,40,50));f.text(8,389,'Binary reset model; real release must satisfy recovery/removal and pulse width.',12);f.save(output/'reset.svg')
    (output/'events.json').write_text(json.dumps(data,indent=2)+'\n')
    for path in sorted(output.glob('*.svg')):
        for width in (360,425):
            target=path.with_name(path.stem+f'-{width}.png');cairosvg.svg2png(url=str(path),write_to=str(target),output_width=width)
            with Image.open(target) as im:
                gray=ImageOps.grayscale(im.convert('RGB'));gray.save(target);ImageOps.invert(gray).save(path.with_name(path.stem+f'-{width}-dark.png'))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args(argv);generate(args.output)

if __name__=='__main__':main()
