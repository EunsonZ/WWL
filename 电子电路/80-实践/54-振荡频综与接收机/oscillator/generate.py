from pathlib import Path
import json,math
r=Path(__file__).resolve().parent
card={'VDD_V':1.8,'L_each_H':100e-9,'R_series_each_ohm':10.,'C_each_F':25e-12,'tail_A':.002,'seed_diff_V':.001,'KP_A_V2':.002,'W_m':10e-6,'L_m':1e-6,'VTO_V':.5,'LAMBDA_V_inv':.02,'TOX_m':20e-9,'TEMP_C':27,'stop_s':2e-6,'maxstep_s':10e-12,'method':'Gear2','cases':{'nominal':{},'zero_seed':{'seed_diff_V':0.},'low_tail':{'tail_A':1e-6},'cap30p':{'C_each_F':30e-12},'nominal_5ps':{'maxstep_s':5e-12}}}
card=json.loads((r/'fixed-inputs.json').read_text()) # packaged card is the reproduction input
for name,delta in card['cases'].items():
 c={**card,**delta};d=r/name;d.mkdir(exist_ok=True);vd=c['VDD_V']-c['tail_A']/2*c['R_series_each_ohm'];lo=0.;hi=vd-c['VTO_V'];beta=c['KP_A_V2']*c['W_m']/c['L_m']
 for _ in range(100):
  vs=(lo+hi)/2;id=.5*beta*(vd-vs-c['VTO_V'])**2*(1+c['LAMBDA_V_inv']*(vd-vs))
  if id>c['tail_A']/2:lo=vs
  else:hi=vs
 vs=(lo+hi)/2;c['analytic_DC']={'drain_V':vd,'source_V':vs};(d/'configuration.json').write_text(json.dumps(c,indent=2))
 text=f'''Cross coupled NMOS LC oscillator {name}; educational LEVEL1 not PDK
.temp {c['TEMP_C']}
.options reltol=1e-6 abstol=1e-13 vntol=1e-9 method=gear maxord=2
VDD vdd 0 {c['VDD_V']}
RLP vdd lp {c['R_series_each_ohm']}
RLN vdd ln {c['R_series_each_ohm']}
LP lp p {c['L_each_H']:.17g} IC={c['tail_A']/2:.17g}
LN ln n {c['L_each_H']:.17g} IC={c['tail_A']/2:.17g}
CP p 0 {c['C_each_F']:.17g}
CN n 0 {c['C_each_F']:.17g}
M1 p n s 0 NN W={c['W_m']:.17g} L={c['L_m']:.17g}
M2 n p s 0 NN W={c['W_m']:.17g} L={c['L_m']:.17g}
IT s 0 DC {c['tail_A']}
.model NN NMOS LEVEL=1 KP={c['KP_A_V2']} VTO={c['VTO_V']} LAMBDA={c['LAMBDA_V_inv']} GAMMA=0 TOX={c['TOX_m']} TNOM={c['TEMP_C']}
.ic v(p)={vd+c['seed_diff_V']/2:.17g} v(n)={vd-c['seed_diff_V']/2:.17g} v(s)={vs:.17g}
.control
set noaskquit
set numdgt=15
op
print v(p) v(n) v(s) @m1[id] @m1[gm] @m1[gds] @m1[cgs] @m1[cgd] @m1[cgb]
save all @m1[id] @m2[id]
tran {c['maxstep_s']:.17g} {c['stop_s']:.17g} 0 {c['maxstep_s']:.17g} uic
set wr_vecnames
set wr_singlescale
wrdata waveform.txt v(p) v(n) v(s) i(vdd) @m1[id] @m2[id]
quit
.endc
.end
''';(d/'osc.cir').write_text(text)
