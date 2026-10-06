---
type: code-mirror
domain: electronics
stage: 3
aliases: []
sources: []
prerequisites: []
---
# 组合图真源阅读副本

真源 `bridge_figures.py`，SHA256 `8e7ee144ebd426964bce0af1726919242e5e2e68cb0ad52fbbcc132d59dabc3b`；改源同步本镜像。

```python
"""Six source-bound teaching bridges. Inert import; explicit fresh external output."""
import argparse,hashlib,json,math
from pathlib import Path
from html import escape
HERE=Path(__file__).resolve().parent

def source(vault):
    registry=json.loads((HERE/'bridge-inputs.json').read_text()); data={}
    for key,item in registry.items():
        f=Path(vault)/item['path']; body=f.read_bytes()
        if hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('input drift: '+key)
        if f.suffix=='.json':data[key]=json.loads(body)
    return data,registry

def drawings(d):
    def text(x,y,s,klass=''):return f'<text x="{x}" y="{y}" class="{klass}">{escape(s)}</text>'
    def line(x,y,X,Y,arrow=False,dash=False):return f'<path class="wire" d="M{x} {y}L{X} {Y}"'+(' marker-end="url(#a)"' if arrow else '')+(' stroke-dasharray="5 4"' if dash else '')+'/>'
    def box(x,y,w,h,labels):
        return f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}"/>'+''.join(text(x+10,y+23+24*i,s) for i,s in enumerate(labels))
    def svg(title,body,height):
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}"><rect width="425" height="{height}" fill="white"/><style>text{{font:16px sans-serif;fill:#18232c}}.title{{font-weight:bold}}.small{{font-size:14px}}.wire{{stroke:#18232c;stroke-width:2;fill:none}}.box{{fill:#f2f5f7;stroke:#18232c;stroke-width:1.5}}</style><defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="#18232c"/></marker></defs>{text(16,28,title,'title')}{body}</svg>'''
    figures={}
    s=box(16,48,393,100,['Latch: transparent while EN=1','EN  ____| HIGH |____','D may propagate during HIGH','DFF: sample only near rising edge'])
    s+=box(16,170,393,76,['Source Q -> logic + wire -> capture D','Launch L0=0; capture C0=1, C1=11 ns','s = capture - launch = +1 ns'])
    s+=text(16,280,'SETUP: longest path -> NEXT capture')+line(30,315,390,315,True)
    for x,label in [(30,'0'),(235,'8'),(260,'9'),(312,'11')]:s+=line(x,308,x,322)+text(x-3,345,label)
    s+=text(16,372,'Stable at 8; deadline 9; slack +1 ns')
    s+=text(16,409,'HOLD: shortest path -> SAME capture')+line(30,444,390,444,True)
    for x,label in [(30,'0'),(56,'1'),(108,'3')]:s+=line(x,437,x,451)+text(x-3,474,label)
    s+=text(16,502,'Pollution 3; deadline 3; slack 0 ns')+text(16,528,'Teaching bounds, no STA or analog trace','small')
    figures['V32-window']=svg('V32: transparency and two timing paths',s,550)
    s=text(16,58,'CPU expected values; not HDL / VCD')
    s+=text(16,85,'drive edge observe = 20 / 25 / 26 ns')
    s+=text(16,112,'Next rows advance by 10 ns')
    labels=['edge','sv','mr','push','pop','old','new'];xs=[16,78,120,166,224,282,347]
    for x,l in zip(xs,labels):s+=text(x,153,l)
    for k,row in enumerate(d['waveform']['rows']):
        vals=[row['edge_ns'],row['sv'],row['mr'],row['push'],row['pop'],f"{row['data']:02X}" if row['valid'] else '--',f"{row['after_data']:02X}" if row['after_full'] else '--']
        for x,v in zip(xs,vals):s+=text(x,185+k*34,str(v))
        s+=line(16,194+k*34,409,194+k*34)
    s+=box(16,414,393,100,['55 ns: deliver OLD A1, accept B2','56 ns: registered head is NEW B2','35/45 ns: retain A1 under backpressure','Reset cancels queue before this table'])
    s+=text(16,545,'FIFO history: pop head, then append push')+text(16,570,'True VCD requires actual tool run: not_run')
    figures['V33-cycle']=svg('V33: old transactions / new storage',s,594)
    s=box(16,48,393,76,['Single-bit state -> FF1 -> FF2 -> logic','FF1 is not a direct functional source','Destination clock; analog risk remains'])
    s+=box(16,146,393,76,['Pulse HIGH at 1..4 ns','Destination edges 0,10,20 ns miss it','More stages do not restore lost events'])
    s+=box(16,244,393,76,['Multi-bit 01 -> 10 may appear 00 / 11','Binary 011 -> 100 changes 3 bits','Gray   010 -> 110 changes 1 bit'])
    s+=box(16,345,182,76,['wclk: binary','address + Gray','write / full'])+box(226,345,183,76,['rclk: binary','address + Gray','read / empty'])
    s+=line(198,367,226,367,True)+line(226,397,198,397,True)
    s+=text(16,446,'Pointers cross synchronizers; data uses RAM')
    s+=box(16,463,393,76,['Dual-port RAM; separate read/write timing','Gray skew, wrap bit, full/empty required','This is structure, not implemented FIFO'])
    s+=box(16,562,393,76,['Reset: asynchronous assert in each domain','Release waits for each LOCAL clock','Recovery/removal + epoch remain checks'])
    s+=text(16,665,'No simulated metastable voltages / MTBF claim','small')
    figures['V34-cdc']=svg('V34: information and physical boundaries',s,687)
    s=text(16,57,'Top view: signal above reference plane')
    s+=f'<rect class="box" x="16" y="75" width="393" height="83"/>'+line(40,101,380,101,True)+line(380,131,40,131,True)+text(45,94,'signal')+text(110,150,'distributed return, continuous plane')
    s+=f'<rect class="box" x="16" y="184" width="393" height="119"/><rect x="201" y="184" width="24" height="78" fill="white" stroke="#18232c"/>'
    s+=line(40,203,380,203,True)+f'<path class="wire" d="M380 231H255V278H171V231H40" marker-end="url(#a)"/>'+text(30,296,'Slot -> return detour; not a universal split rule')
    s+=text(16,333,'Section: isolated signal via / GND stitch')
    # Two-layer teaching section: top signal and separate GND patch; lower
    # signal island is isolated from the surrounding B.Cu GND pour.
    s+=line(25,370,280,370)+text(25,355,'F.Cu SIGNAL')
    s+=line(330,370,399,370)+text(325,355,'GND')
    s+=line(25,440,243,440)+line(279,440,399,440)
    s+=line(250,440,272,440)+line(261,370,261,440)
    s+=line(355,370,355,440)
    s+=text(25,397,'1.6 mm dielectric')+text(25,426,'B.Cu GND')
    s+=text(16,467,'Signal via -> SAME signal isolated pad')
    s+=text(16,491,'Gap at plane = antipad / copper clearance')
    s+=text(16,515,'GND stitch connects GND patch to plane')
    s+=text(16,539,'Different reference nets need another path')
    s+=box(16,560,393,54,['Local power -> LOAD -> GND -> C -> power','Fast di/dt closes locally; remote source is slower'])
    s+=text(16,640,'5 mA / 5 ns: 2 nH -> 2 mV')+text(16,667,'detour 20 nH -> 20 mV (assumed L)')
    s+=text(16,694,'100 nF + .05 ohm + 2 nH: |Z|1.242 ohm')+text(16,721,'at 100 MHz; resonance 11.254 MHz')
    s+=text(16,748,'Swap reference: analyze plane connection / C')+text(16,772,'No fill, EM extraction, board or TDR result','small')
    figures['V35-return']=svg('V35: layer, reference and local loop',s,795)
    s=box(16,48,393,100,['850 nm, launch 100 uW; 10 dB loss','Detector plane: 10 uW; eta=.7 assumed','E=hc/lambda [J]; Phi=P/E [1/s]','q*eta*Phi = 4.798999 uA'])
    s+=line(212,148,212,173,True)+box(16,180,393,76,['TIA current node + CT 10 pF','RF 100 kohm / CF 1 pF; finite A','DC output -0.479995 V incl. dark current'])
    s+=text(16,285,'Below: independent MEMS teaching object')
    s+=box(16,305,393,76,['base a [m/s2] -> relative x [m]','m*xdd+b*xd+k*x = -m*a + F','f0 1 kHz; +1 g -> x=-0.248405 um'])
    s+=line(212,381,212,408,True)+box(16,413,393,100,['Parallel plates: gap 2 um; area 4e-8 m2','C+/-=epsilon*A/(g-/+x) [F]','Delta C = -44.677765 fF at 1 g','Qp=0, high-Z: vp/Vc=x/g; no Cp'])
    s+=box(16,540,393,100,['Separate cantilever: x_tip=+1 um','L200 um, t2 um -> strain 75 ustrain','GF100 (assumed) -> delta=.0075','Vexc1 V, four-arm bridge -> 7.5 mV'])
    s+=text(16,670,'Keep units, geometry and port conditions')+text(16,695,'Source values: formal F03/F04 CPU models','small')
    figures['V42-domain']=svg('V42: photon charge and mechanical ports',s,718)
    s=box(16,48,393,100,['Synthetic source -> protection concept','AFE / bias -> ADC in local domain A','Data barrier -> HOST in domain H','Power / shield / other paths need review'])
    s+=box(16,175,393,76,['A ref <-> Cp 10 pF <-> H ref','Test source spans A/H: 1 Vrms, 100 Hz','Closed return: I=2*pi*f*C*V = 6.283 nA'])
    s+=text(16,279,'Concept only; not body wiring or safety pass')
    s+=box(16,303,393,76,['Independent 2x2 array; shared 0 V','Rows U=[.1,.2] V; G=[10,20;30,40] uS','Columns clamped to 0 V by readout'])
    s+=line(212,379,212,407,True)+box(16,413,393,76,['Iij = Gij * (Ui - Vcolumn) [A]','Ideal Vcolumn=0 -> I=[7,10] uA','Finite wire -> solve 8 node voltages'])
    s+=box(16,516,393,76,['Negative weights: G+ and G- arrays','Currents subtract; both powers add','ADC/DAC/driver rails and energy needed'])
    s+=text(16,621,'Calibration is input-dependent with line loss')+text(16,648,'No chip, body, certification or training result','small')
    figures['V43-boundary']=svg('V43: domain barrier and array conditions',s,672)
    return figures

def generate(vault,output):
    root=Path(vault).resolve();out=Path(output).resolve()
    if root==out or root in out.parents or HERE==out or HERE in out.parents:raise ValueError('external output required')
    if out.exists():raise FileExistsError('fresh output required')
    d,registry=source(root)
    # Independent SI checks on combined claims; finite author checks, not review signature.
    q=1.602176634e-19;h=6.62607015e-34;c=299792458
    I=q*.7*850e-9/(h*c)*10e-6
    assert math.isclose(I,d['photon']['optical']['photo_A'],rel_tol=1e-12)
    x=-9.80665/(2*math.pi*1000)**2
    assert math.isclose(x,d['mems']['x_1g_m'],rel_tol=1e-12)
    assert math.isclose(2*math.pi*100*10e-12,6.283185307179586e-9,rel_tol=1e-12)
    assert math.isclose(d['array']['ideal']['output_A'][0],7e-6,rel_tol=1e-12)
    assert math.isclose(d['array']['ideal']['output_A'][1],10e-6,rel_tol=1e-12)
    figures=drawings(d)
    import cairosvg
    from PIL import Image,ImageOps
    out.mkdir(parents=True)
    for name,body in figures.items():
        (out/(name+'.svg')).write_text(body+'\n')
        for w in (360,425):
            file=out/(name+f'-{w}.png');cairosvg.svg2png(bytestring=body.encode(),write_to=str(file),output_width=w)
            with Image.open(file) as image:
                rgb=image.convert('RGB');gray=ImageOps.grayscale(rgb)
                gray.save(out/(name+f'-{w}-gray.png'))
                ImageOps.invert(gray).save(out/(name+f'-{w}-dark.png'))
    rows=d['waveform']['rows']
    waves={'head':{'text':'CPU expected, not HDL VCD'},'signal':[{'name':'rst_n','wave':'1.....'},{'name':'clk','wave':'p.....'},{'name':'s_valid','wave':''.join(str(r['sv']) for r in rows)},{'name':'m_ready','wave':''.join(str(r['mr']) for r in rows)},{'name':'push','wave':''.join(str(r['push']) for r in rows)},{'name':'pop','wave':''.join(str(r['pop']) for r in rows)},{'name':'preedge output','wave':'x====x','data':['A1','A1','A1','B2']},{'name':'postedge head','wave':'====xx','data':['A1','A1','A1','B2']}], 'config':{'hscale':2}}
    (out/'V33-wavedrom.json').write_text(json.dumps(waves,indent=2)+'\n')
    timing={'head':{'text':'V32 expected timing; tick=1 ns; no STA'},'signal':[
        ['Latch / positive-edge DFF',
         {'name':'latch enable','wave':'001111000000'},
         {'name':'input D','wave':'0.1....0....'},
         {'name':'latch Q expected','wave':'0.1.........'},
         {'name':'DFF clk','wave':'0....10.....'},
         {'name':'DFF Q expected','wave':'0....1......'}],
        ['Setup / hold path windows',
         {'name':'launch clock','wave':'10..........','node':'a...........'},
         {'name':'capture clock','wave':'010........1','node':'.b.........c'},
         {'name':'max path D stable','wave':'xxxxxxxx1...','node':'........f...'},
         {'name':'setup deadline','wave':'0........10.','node':'.........d..'},
         {'name':'min path pollution','wave':'0..xxxxxxxxx','node':'...e........'}]],
        'edge':['a~>b +1 ns skew','f~>d 1 ns setup slack'],
        'foot':{'text':'setup: next capture 11 ns / deadline 9; hold: same capture 1 ns / deadline 3'},
        'config':{'hscale':2}}
    (out/'V32-wavedrom.json').write_text(json.dumps(timing,indent=2)+'\n')

    result={'checks':5,'status':'author finite source-bound checks pass','actual_HDL_VCD':'not_run','WaveDrom_renderer':'not_run','hardware':'not_run','input_sha':registry,'figures':list(figures),'photon_A':I,'MEMS_x_m':x,'barrier_A':2*math.pi*100*10e-12,'ideal_array_A':[7e-6,10e-6]}
    (out/'bridge-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--vault',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(argv);generate(a.vault,a.output)
if __name__=='__main__':main()
```
