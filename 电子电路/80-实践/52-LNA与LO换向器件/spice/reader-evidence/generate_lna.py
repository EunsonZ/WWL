from pathlib import Path
import math,json
r=Path(__file__).resolve().parent
card=json.loads((r/'fixed-inputs.json').read_text()); c=card['lna']
assert card['temperature_K']==300.15 and c['vdd_V']==1.8 and c['source_bias_V']==.1 and c['nominal_Id_A']==.001
assert c['Rs_cases_ohm']==[25,50,100] and c['Rd_ohm']==800 and c['Rl_ohm']==1000
assert c['kp_A_per_V2']==.02 and c['W_m']==10e-6 and c['L_m']==1e-6 and c['Vth_V']==.5 and c['lambda_per_V']==.02 and c['tox_m']==20e-9
assert c['Cgs_external_F']==.5e-12 and c['Cgd_external_F']==.05e-12 and c['Cds_external_F']==.1e-12 and c['Cout_F']==1e-9
assert c['frequencies_Hz']==[1000000,90000000,100000000,110000000]
for rs in [25,50,100]:
 qd=.001;vs=.1+qd*rs;vd=1.8-qd*800;vg=vs+.5+math.sqrt(2*qd/(.2*(1+.02*(vd-vs))))
 d=r/f'lna-Rs{rs}';d.mkdir(exist_ok=True)
 lines=[f'CG LNA Rs={rs} ideal LEVEL1 no PDK','.temp 27','.options reltol=1e-7 abstol=1e-14 vntol=1e-9','Vsig sig 0 DC .1 AC 1',f'RS sig s {rs}','VDD vdd 0 1.8',f'VG g 0 {vg:.17g}','RD vdd d 800','M1 d g s s NN W=10u L=1u','Cgs g s .5p','Cgd g d .05p','Cds d s .1p','Cout d out 1n','RL out 0 1k noisy=0','.model NN NMOS LEVEL=1 KP=.02 VTO=.5 LAMBDA=.02 GAMMA=0 TOX=20n TNOM=27','.control','set noaskquit','set numdgt=15','set filetype=ascii','op','print v(d) v(g) v(s) @m1[id] @m1[gm] @m1[gds] @m1[vdsat]','print @m1[cgs] @m1[cgd] @m1[cgb]','write op.raw all','set wr_vecnames','set wr_singlescale']
 for index,f in enumerate([1000000,90000000,100000000,110000000]):
  lines +=[f'ac lin 1 {f} {f}',f'wrdata ac-{f}.txt v(out) v(s) v(d)',f'noise v(out) Vsig lin 1 {f} {f} 1',f'write noise-{f}.raw all','print all']
 lines+=['quit','.endc','.end'];(d/'lna.cir').write_text('\n'.join(lines)+'\n')
