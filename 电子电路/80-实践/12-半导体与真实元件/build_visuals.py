"""Original editable SVG mechanism drawings. No import-time writes or global MPL config."""
from pathlib import Path
import argparse,math,json
import semiconductor_lab as s

def wrap(body,h=650):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{h}" viewBox="0 0 480 {h}"><rect width="480" height="{h}" fill="#ffffff"/><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#304967"/></marker></defs><style>text{{font-family:Arial,sans-serif;font-size:17px;fill:#182f48}}.small{{font-size:14px}}.title{{font-size:21px;font-weight:bold}}.line{{fill:none;stroke:#304967;stroke-width:2}}.curve{{fill:none;stroke:#006a91;stroke-width:3}}.dash{{stroke:#8799aa;stroke-dasharray:4 4;stroke-width:1}}.box{{fill:#f0f6fa;stroke:#304967;stroke-width:1.5}}</style>{body}</svg>'''
def txt(x,y,t,cls=''):
 import html
 return f'<text x="{x}" y="{y}" class="{cls}">{html.escape(t)}</text>'
def line(x,y,a,b,cls='line',arrow=False):return f'<line x1="{x}" y1="{y}" x2="{a}" y2="{b}" class="{cls}"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>'
def poly(points):return '<polyline class="curve" points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+'"/>'
def bands():
 b=txt(20,32,'Bands and occupancy','title')+txt(20,60,'Schematic energy relations; not to scale','small')
 for x,name in [(95,'intrinsic'),(250,'n type'),(390,'p type')]:
  b+=txt(x-40,110,name)+line(x-45,190,x+45,190)+line(x-45,420,x+45,420)
  b+=txt(x-30,183,'Ec')+txt(x-30,444,'Ev')
  if name=='n type':b+=line(x-40,230,x+40,230,'dash')+txt(x-36,260,'donor')+txt(x-36,157,'electrons')
  elif name=='p type':b+=line(x-40,380,x+40,380,'dash')+txt(x-40,367,'acceptor')+txt(x-32,473,'holes')
  else:b+=line(x-40,305,x+40,305,'dash')+txt(x-36,331,'EF')
 b+=line(35,460,35,140,arrow=True)+txt(15,500,'Electron energy E (J) increases upward')
 b+=txt(20,550,'Gap Eg = Ec - Ev; hole carries +q')+txt(20,580,'n type: mobile electrons + fixed positive donors')
 return wrap(b,620)
def pn():
 na,nd,ni=1e22,2e22,1e16;d=s.pn_dimensions(na,nd,ni,300);a=-d['xp']*1.5;b=d['xn']*1.7
 xs=[a+(b-a)*i/300 for i in range(301)];records=[s.pn_space(x,na,nd,ni,300) for x in xs]
 X=lambda x:100+340*(x-a)/(b-a)
 body=txt(20,30,'PN: one x axis, seven aligned panels','title')+txt(20,55,'300 K; NA=1e22, ND=2e22, ni=1e16 m^-3','small')
 body+=txt(20,79,'Depletion rho; Boltzmann n,p are approximate','small')
 panels=[('Net dopant (10^22 m^-3)',[-1 if x<0 else 2 for x in xs],-1.3,2.3),('n (log10 m^-3)',[math.log10(r['n']) for r in records],10,22.5),('p (log10 m^-3)',[math.log10(r['p']) for r in records],9,22.5),('rho (10^3 C/m^3)',[r['rho']/1e3 for r in records],-2,4),('E (10^6 V/m)',[r['e']/1e6 for r in records],-4.3,.3),('phi (V)',[r['phi'] for r in records],-.05,.8),('Ec offset (eV)',[-r['phi'] for r in records],-.8,.05)]
 for j,(label,vals,lo,hi) in enumerate(panels):
  y=110+j*145;Y=lambda v:y+115-100*(v-lo)/(hi-lo)
  body+=txt(20,y+5,label,'small')+line(100,y+120,440,y+120)+line(100,y+25,100,y+120)
  for z in [-d['xp'],0,d['xn']]:body+=line(X(z),y+23,X(z),y+120,'dash')
  body+=txt(52,y+38,f'{hi:g}','small')+txt(52,y+117,f'{lo:g}','small')+poly([(X(x),Y(v)) for x,v in zip(xs,vals)])
 body+=txt(X(-d['xp'])-10,1150,'-xp','small')+txt(X(0)-4,1150,'0','small')+txt(X(d['xn'])-8,1150,'xn','small')+txt(425,1150,'x (m)','small')+txt(20,1185,'E = -dphi/dx; bands = const - q phi','small')
 return wrap(body,1210)
def resistor(x,y,label):return line(x,y,x+20,y)+f'<rect x="{x+20}" y="{y-9}" width="55" height="18" class="box"/>'+line(x+75,y,x+95,y)+txt(x+18,y-19,label,'small')
def diode(x,y,label,zener=False):
 b=line(x,y,x+18,y)+f'<path d="M{x+18},{y-12} L{x+18},{y+12} L{x+42},{y} Z" class="line"/>'+line(x+43,y-13,x+43,y+13)+line(x+43,y,x+65,y)
 if zener:b+=line(x+43,y-13,x+51,y-13)+line(x+35,y+13,x+43,y+13)
 return b+txt(x+15,y+35,'A   K','small')+txt(x+10,y-23,label,'small')
def node(x,y,label=''):
 return f'<circle cx="{x}" cy="{y}" r="3" fill="#304967"/>'+txt(x+8,y-8,label,'small')
def terminal(x,y,label):
 return f'<circle cx="{x}" cy="{y}" r="4" fill="white" stroke="#304967" stroke-width="2"/>'+txt(x-5,y-12,label,'small')
def ground(x,y):
 return line(x,y,x,y+10)+line(x-12,y+10,x+12,y+10)+line(x-8,y+16,x+8,y+16)+line(x-3,y+22,x+3,y+22)+txt(x+18,y+20,'0 V','small')
def source(x,top,bottom,label,ac=False):
 cy=(top+bottom)/2
 return line(x,top,x,cy-20)+f'<circle cx="{x}" cy="{cy}" r="20" class="line"/>'+line(x,cy+20,x,bottom)+txt(x-25,top-17,label,'small')+(txt(x-7,cy+6,'~') if ac else txt(x-6,cy-4,'+')+txt(x-5,cy+14,'-'))+node(x,top)+node(x,bottom)
def circuits():
 b=txt(20,30,'Four independent complete circuits','title')+txt(20,60,'A = anode; K = cathode; each 0 V is local','small')
 b+=txt(20,105,'1. Half-wave: vs -> D1 -> RL -> return')+source(50,155,265,'vs',True)+line(50,155,90,155)+diode(90,155,'D1')+line(155,155,240,155)+node(240,155,'vo')
 b+=line(240,155,240,190)+f'<rect x="225" y="190" width="30" height="50" class="box"/>'+txt(270,221,'RL')+line(240,240,240,265)+line(50,265,240,265)+node(240,265)+ground(180,265)
 b+=txt(20,330,'2. Upper clip: Vref absorbs ID')+source(50,390,500,'vs')+resistor(80,390,'R')+line(50,390,80,390)+line(175,390,230,390)+node(200,390,'vo')+diode(230,390,'D2')+line(295,390,380,390)+source(380,390,500,'Vref=2 V')
 b+=line(50,500,380,500)+ground(210,500)+line(315,369,355,369,arrow=True)+txt(318,351,'ID','small')+txt(20,551,'High-Z output load; reference needs sink capability','small')
 b+=txt(20,590,'3. Shunt regulator: K at vo, A at return')+source(45,630,740,'VS')+line(45,630,80,630)+resistor(80,630,'R')+line(175,630,300,630)+node(210,630,'vo')
 b+=f'<g transform="translate(210 695) rotate(-90)">'+diode(0,0,'DZ',True)+'</g>'+line(210,695,210,740)+node(210,740)
 b+=line(300,630,300,655)+f'<rect x="288" y="655" width="24" height="45" class="box"/>'+txt(330,683,'RL')+line(300,700,300,740)+line(45,740,300,740)+node(300,630)+node(300,740)+ground(150,740)
 b+=txt(20,825,'4. LED: source -> R -> LED -> return')+source(45,870,980,'5 V')+line(45,870,80,870)+resistor(80,870,'330 ohm')+line(175,870,230,870)+diode(230,870,'')+txt(303,831,'LED','small')+line(295,870,350,870)+line(350,870,350,980)+line(45,980,350,980)+node(350,870)+node(350,980)+ground(200,980)
 b+=line(256,844,272,827,arrow=True)+line(271,852,287,835,arrow=True)
 return wrap(b,1030)
def dynamics():
 b=txt(20,32,'Charge slope and stored-charge removal','title')+txt(20,61,'Teaching parameters; no measured device curve','small')
 v=[i*4/200 for i in range(201)];q=[s.nonlinear_charge(x)*1e6 for x in v]
 b+=txt(20,110,'Q (microC); Cdiff is tangent slope')+line(80,355,435,355)+line(80,355,80,140)
 b+=poly([(80+85*x,350-8*y) for x,y in zip(v,q)])
 b+=line(80,350,250,224,'dash')+txt(275,233,'Q/V = 7.854 uF','small')
 b+=line(165,264,335,184)+txt(270,180,'dQ/dV = 5 uF','small')+txt(218,384,'V (V)')+txt(55,360,'0','small')+txt(408,375,'4','small')
 b+=txt(20,436,'Storage: IF = IR = 1 mA; tau = 100 ns')
 t=[i*100e-9/200 for i in range(201)];val=[max(0,(2e-10*math.exp(-x/1e-7)-1e-10)*1e12) for x in t]
 b+=line(80,685,435,685)+line(80,685,80,470)+poly([(80+x/1e-7*340,680-y*1.8) for x,y in zip(t,val)])
 ts=s.storage_time(.001,.001,1e-7);xx=80+340*ts/1e-7
 b+=line(xx,475,xx,685,'dash')+txt(170,493,'Q stored (pC)')+txt(35,510,'100','small')+txt(50,688,'0','small')+txt(405,710,'100','small')+txt(280,710,'t (ns)','small')+txt(130,724,'ts = 69.31 ns; switch model at Q=0')
 return wrap(b,750)
def rcl():
 b=txt(20,32,'Real passive components: minimal models','title')+txt(20,62,'Topology and parameters must be specified','small')
 b+=txt(20,110,'C: ESR + ESL + (C || Rleak)')+resistor(25,160,'ESR')+txt(150,143,'ESL')
 b+=line(120,160,145,160)+f'<path d="M145,160 q7,-18 14,0 q7,-18 14,0 q7,-18 14,0" class="line"/>'+line(187,160,275,160)
 b+=line(275,160,275,230)+line(410,160,410,230)
 b+=line(275,195,319,195)+line(319,179,319,211)+line(329,179,329,211)+line(329,195,410,195)+txt(345,191,'C','small')
 b+=resistor(275,230,'')+txt(295,265,'Rleak','small')+line(370,230,410,230)+line(410,160,455,160)
 b+=txt(20,295,'L: (Rw + L) || Cp')+resistor(25,350,'Rw')+line(120,350,160,350)
 b+=f'<path d="M160,350 q8,-20 16,0 q8,-20 16,0 q8,-20 16,0" class="line"/>'+txt(178,324,'L')+line(208,350,430,350)
 b+=line(25,350,25,425)+line(430,350,430,425)+line(25,425,210,425)+line(210,410,210,440)+line(220,410,220,440)+line(220,425,430,425)+txt(230,414,'Cp')
 b+=txt(20,490,'R: (R + Ls) || Cp')+resistor(25,540,'R')+line(120,540,160,540)+f'<path d="M160,540 q8,-20 16,0 q8,-20 16,0 q8,-20 16,0" class="line"/>'+txt(178,513,'Ls','small')+line(208,540,430,540)+line(25,540,25,610)+line(430,540,430,610)+line(25,610,210,610)+line(210,595,210,625)+line(220,595,220,625)+line(220,610,430,610)+txt(235,600,'Cp','small')+txt(20,655,'R(T), power and voltage ratings are separate','small')
 b+=txt(20,700,'Capacitor example: 100 nF, 1 nH, ESR .05 ohm','small')+txt(20,730,'SRF 15.915 MHz: below capacitive, above inductive','small')
 for yy in [160,350,540]:
  b+=line(8,yy,25,yy)+terminal(8,yy,'a')
  if yy==160:b+=terminal(455,yy,'b')+node(275,195)+node(410,195)+node(275,230)+node(410,230)
  else:b+=line(430,yy,455,yy)+terminal(455,yy,'b')+node(25,yy)+node(430,yy)
 b+=txt(20,90,'Z = (Va - Vb) / Ia; Ia enters terminal a','small')
 return wrap(b,770)
def card():
 b=txt(20,30,'A value is a condition-bound statement','title')
 rows=[('1  Identity','Manufacturer, full part, revision, package'),('2  Stress boundary','Absolute: damage limit; not normal bias'),('3  Operating region','Recommended table, or explicitly absent'),('4  Characteristic','min / typ / max / nominal; blank is unknown'),('5  Test conditions','Bias, T, pulse, f, circuit, endpoint'),('6  Model and checks','Assumptions, range, source; test extrapolation')]
 for j,(head,sub) in enumerate(rows):
  y=65+j*92;b+=f'<rect x="20" y="{y}" width="440" height="72" rx="8" class="box"/>'+txt(35,y+27,head)+txt(35,y+53,sub,'small')
  if j<5:b+=line(240,y+73,240,y+88,arrow=True)
 b+=txt(20,640,'A test point cannot identify every model parameter','small')
 return wrap(b,665)
def pn_bias():
 b=txt(20,32,'PN bias: common x and field conventions','title')+txt(20,60,'Forward +0.2 V vs reverse -1 V; depletion only','small')
 na,nd,ni=1e22,2e22,1e16;eps=11.7*s.EPS0
 dims=[s.pn_dimensions(na,nd,ni,300,vd=v) for v in [.2,-1]]
 xmin=-dims[1]['xp']*1.2;xmax=dims[1]['xn']*1.2;X=lambda x:85+(x-xmin)/(xmax-xmin)*350
 for j,field in enumerate(['e','phi']):
  y=130+j*220;b+=txt(20,y-25,'E (10^6 V/m)' if field=='e' else 'phi (V)')+line(85,y+155,435,y+155)+line(85,y,85,y+155)
  for dim,color,name in zip(dims,['#00729a','#b3442f'],['+0.2 V','-1 V']):
   points=[]
   for i in range(301):
    x=xmin+(xmax-xmin)*i/300;xp,xn,B=dim['xp'],dim['xn'],dim['barrier']
    if x<=-xp:e=0;phi=0
    elif x<0:e=-s.Q_E*na*(x+xp)/eps;phi=s.Q_E*na*(x+xp)**2/(2*eps)
    elif x<xn:e=s.Q_E*nd*(x-xn)/eps;phi=B-s.Q_E*nd*(xn-x)**2/(2*eps)
    else:e=0;phi=B
    z=y+15-e/1e6*21 if field=='e' else y+155-phi*75
    points.append((X(x),z))
   b+=poly(points).replace('class="curve"',f'fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="{"none" if name=="+0.2 V" else "8 4"}"')
   lx=95 if name=='+0.2 V' else 280
   b+=f'<rect x="{lx-15}" y="{y+174}" width="10" height="10" fill="{color}"/>'+txt(lx,y+185,name,'small')
  b+=txt(45,y+(20 if field=='e' else 10),'0' if field=='e' else '2','small')+txt(30,y+160,'-6.5' if field=='e' else '0','small')+line(X(0),y,X(0),y+155,'dash')+txt(X(0)-4,y+173,'0','small')
 b+=txt(80,593,'x: -0.46 um to +0.23 um','small')+txt(20,626,'Bias fields do not imply equilibrium np=ni^2','small')
 return wrap(b,650)

def diode_plot():
 d=s.diode_load(5,1000);vq,iq=d['v'],d['i'];rd=s.thermal_voltage(300)/(iq+1e-12)
 b=txt(20,32,'Diode curve and network load line','title')+txt(20,60,'5 V, 1 kohm, Is=1 pA, eta=1, T=300 K','small')
 X=lambda v:80+350*v/.63;Y=lambda i:430-340*i/.012
 b+=line(80,430,440,430)+line(80,430,80,95)+txt(22,110,'I (mA)')+txt(335,465,'VD (V)')
 for v,label in [(0,'0'),(.3,'.3'),(.6,'.6')]:b+=txt(X(v)-6,451,label,'small')
 for i,label in [(0,'0'),(.005,'5'),(.01,'10')]:b+=txt(50,Y(i)+5,label,'small')
 vs=[.63*i/300 for i in range(301)];b+=poly([(X(v),Y(s.diode_current(v))) for v in vs if s.diode_current(v)<=.012])
 b+=line(X(0),Y(.005),X(.63),Y(.00437))+txt(175,290,'network load line','small')
 b+=line(X(vq-.02),Y(iq-.02/rd),X(vq+.02),Y(iq+.02/rd),'dash')
 b+=line(X(0),Y(0),X(vq),Y(iq),'dash')+f'<circle cx="{X(vq)}" cy="{Y(iq)}" r="5" fill="#b3442f"/>'
 b+=txt(120,505,'Q: .57419 V, 4.42581 mA')+txt(20,540,'Tangent rd=5.84 ohm; secant V/I=129.74 ohm','small')+txt(20,575,'Models are teaching parameters, not fitted 1N4148','small')
 return wrap(b,610)

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
 target=args.output.resolve();vault_root=Path(__file__).resolve().parents[3]
 if target.is_relative_to(vault_root):p.error('--output must be outside the candidate/vault root')
 args.output=target
 import cairosvg
 args.output.mkdir(parents=True,exist_ok=True)
 for name,builder in [('bands',bands),('pn-five',pn),('pn-bias',pn_bias),('diode-load',diode_plot),('circuits',circuits),('dynamics',dynamics),('real-rcl',rcl),('datasheet-card',card)]:
  svg=builder();(args.output/(name+'.svg')).write_text(svg)
  for width in [360,425]:cairosvg.svg2png(bytestring=svg.encode(),write_to=str(args.output/f'{name}-{width}.png'),output_width=width)
if __name__=='__main__':main()
