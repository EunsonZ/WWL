from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent;cardpath=r/'fixed-inputs.json';card=json.loads(cardpath.read_text());c=card['mixer'];T=card['temperature_K']-273.15
assert c['LO_low_V']==0, 'fixed SPICE generator requires LO_low_V=0'
A=c['small_signal_peak_V'];B=c['blocker_peak_V'];lo=c['LO_high_V'];fl=c['LO_Hz'];fi=c['IF_Hz']
cases={'baseline':(fl+fi,0.,0.,lo),'wanted':(fl+fi,A,0.,lo),'image':(fl-fi,A,0.,lo),'weak_LO':(fl+fi,A,0.,c['weak_LO_high_V']),'large_signal_0p1':(fl+fi,c['blocker_peak_cases_V'][0],0.,lo),'large_signal_0p4':(fl+fi,c['blocker_peak_cases_V'][1],0.,lo),'wanted_with_blocker':(fl+fi,A,B,lo),'blocker_only':(fl+fi,0.,B,lo)}
for name,(freq,amp,blocker,high) in cases.items():
 d=r/('mixer-'+name);d.mkdir(exist_ok=True);period=1/fl;edge=c['LO_edge_s'];td=period/4-edge/2;pw=period/2-edge;rb=c['output_bias_each_ohm'];cm=c['common_mode_V'];halfRs=c['source_diff_ohm']/2
 expr=f'{amp/2:.17g}*cos(2*pi*{freq:.17g}*time)+{blocker/2:.17g}*cos(2*pi*{c["blocker_Hz"]:.17g}*time)'
 deck=f'''Four NMOS commutating bridge {name}; ideal LEVEL1 not PDK
.temp {T:.14g}
.options reltol=1e-6 abstol=1e-13 vntol=1e-9 method=gear maxord=2
BRFP sigp 0 V={{{cm}+({expr})}}
BRFN sign 0 V={{{cm}-({expr})}}
RSP sigp p {halfRs}
RSN sign n {halfRs}
VLO lop 0 PULSE({high} {c['LO_low_V']} {td:.17g} {edge:.17g} {edge:.17g} {pw:.17g} {period:.17g})
BLON lon 0 V={{{high}-v(lop)}}
VCM cm 0 {cm}
RBOP op cm {rb}
RBON on cm {rb}
M1 op lop p 0 NN W={c['W_m']:.17g} L={c['L_m']:.17g}
M2 on lop n 0 NN W={c['W_m']:.17g} L={c['L_m']:.17g}
M3 op lon n 0 NN W={c['W_m']:.17g} L={c['L_m']:.17g}
M4 on lon p 0 NN W={c['W_m']:.17g} L={c['L_m']:.17g}
RL op on {c['load_diff_ohm']}
.model NN NMOS LEVEL=1 KP={c['kp_A_per_V2']:.17g} VTO={c['Vth_V']:.17g} LAMBDA=0 GAMMA=0 TOX={c['tox_m']:.17g} CGSO=0 CGDO=0 TNOM={T:.14g}
.control
set noaskquit
set numdgt=15
set filetype=binary
op
print v(p) v(n) v(op) v(on) @m1[id] @m1[gm] @m1[gds] @m3[id] @m3[gm] @m3[gds]
tran 10p 1u 0 10p
write full.raw all
set wr_vecnames
set wr_singlescale
wrdata waveform.txt v(p) v(n) v(op) v(on) v(lop) v(lon)
quit
.endc
.end
'''
 (d/'mixer.cir').write_text(deck);(d/'configuration.json').write_text(json.dumps({'canonical_sha256':hashlib.sha256(cardpath.read_bytes()).hexdigest(),'RF_Hz':freq,'A_V_peak_differential':amp,'blocker_Hz':c['blocker_Hz'],'blocker_V_peak_differential':blocker,'LO_high_V':high,'LO_Hz':fl,'LO_fall_midpoint_s':period/4,'LO_rise_midpoint_s':3*period/4,'edges_s':edge,'output_bias_each_ohm':rb,'effective_differential_Rload_ohm':1/(1/c['load_diff_ohm']+1/(2*rb)),'node_order':['p','n','op','on','lop','lon']},indent=2))
