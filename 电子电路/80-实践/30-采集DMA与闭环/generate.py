"""Explicit generation only; importing this module creates no files and loads no plotting code."""
from pathlib import Path
import argparse
import csv
import json
import os
import tempfile
import math
import html


def _vault_root():
    """Locate the actual relocated vault from this truth source, not the cwd spelling."""
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / 'AGENTS.md').is_file() and (ancestor / 'scripts/check_vault.py').is_file():
            return ancestor
    raise ValueError('cannot locate vault root: AGENTS.md and scripts/check_vault.py required')


def _destination(output):
    out=Path(output).expanduser().resolve()
    vault=_vault_root()
    if out==vault or vault in out.parents:
        raise ValueError('output must be outside the main vault')
    return out


def native(title, body, height=350):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="425" height="'+str(height)+
            '" viewBox="0 0 425 '+str(height)+'"><rect width="425" height="'+str(height)+
            '" fill="white"/><style>text{font-family:DejaVu Sans,sans-serif;font-size:12px;fill:#111} .w{stroke:#111;stroke-width:1.8;fill:none} .p{fill:white;stroke:#111;stroke-width:1.8}</style>'+
            '<text x="15" y="22" style="font-size:15px;font-weight:bold">'+html.escape(title)+'</text>'+body+'</svg>')


def text(x,y,s): return '<text x="%s" y="%s">%s</text>'%(x,y,html.escape(s))
def line(x,y,xx,yy): return '<path class="w" d="M%s %s L%s %s"/>'%(x,y,xx,yy)
def node(x,y): return '<circle cx="%s" cy="%s" r="3" fill="#111"/>'%(x,y)
def box(x,y,w,h,s): return '<rect class="p" x="%s" y="%s" width="%s" height="%s"/>'%(x,y,w,h)+text(x+7,y+h/2+4,s)
def ground(x,y):
    return line(x,y,x,y+8)+line(x-9,y+8,x+9,y+8)+line(x-6,y+12,x+6,y+12)+line(x-3,y+16,x+3,y+16)
def resistor(x,y,w=45):
    return line(x,y,x+8,y)+'<path class="w" d="M%s %s l5 -5 l6 10 l6 -10 l6 10 l6 -10 l5 5"/>'%(x+8,y)+line(x+42,y,x+w,y)


def _native_figures():
    b=text(15,49,'Physical input: v relative to AGND')
    b+='<circle class="p" cx="35" cy="99" r="16"/>'+text(30,103,'v')+line(35,83,35,72)+line(35,72,80,72)+resistor(80,72)+line(125,72,166,72)+node(156,72)+text(80,62,'Rsource')
    b+=line(156,72,156,109)+line(145,109,167,109)+line(145,115,167,115)+ground(156,115)+text(171,113,'Csample')+line(35,115,35,134)+ground(35,134)
    b+=box(220,53,90,50,'12-bit ADC')+line(166,72,220,72)+line(265,53,265,36)+text(290,41,'Vref=3.3 V')+ground(265,103)+text(213,143,'AGND; capture t[n]')
    b+=line(310,78,397,78)+text(317,65,'code c')+line(397,78,397,180)+box(240,164,160,32,'epoch / n / status')+line(240,180,205,180)+box(20,164,185,32,'calibrate: b+a*c [V]')+node(220,180)+line(220,180,220,220)+line(220,220,110,220)+line(110,220,110,230)+text(80,214,'raw c [count]')+box(20,230,185,32,'q=c-2048 [count]; filter')+line(205,246,235,246)+box(235,230,165,32,'a*filtered q [V]')+text(20,297,'Reference, units and time travel with data.')
    yield '01-chain',native('One voltage-to-program contract',b,320)
    b=text(20,48,'3.3 V supply; common GND')+line(75,64,350,64)+text(83,74,'VDD')
    for x,label in [(110,'SDA'),(290,'SCL')]:
        b+=line(x,64,x,78)+'<rect class="p" x="%s" y="78" width="12" height="40"/>'%(x-6)+line(x,118,x,155)+node(x,155)+text(x+12,101,'Rp 2.2k')+text(x+12,141,label)
        b+=line(x,155,x,190)+line(x-7,190,x+7,190)+line(x-7,194,x+7,194)+ground(x,194)+text(x+13,191,'100pF')
        # two open-drain switch branches: stable gate-controlled paths, actual bus-to-ground ports
        for dx,yy in [(-55,242),(45,277)]:
            xx=x+dx
            b+=line(x,155,xx,155)+line(xx,155,xx,yy-26)+node(xx,yy-26)+line(xx,yy-26,xx+8,yy-9)+node(xx,yy-4)+ground(xx,yy-4)+text(xx-28,yy+31,'OD switch')
    b+=text(15,342,'Only pull-down paths. Release charges Cbus.')
    yield '02-i2c',native('I2C electrical RC boundary',b,360)
    b=text(15,49,'Classic CAN: controller + transceiver')
    for x in [25,252]:
        b+=box(x,76,145,60,'CAN transceiver')+line(x+72,76,x+72,59)+text(x+80,66,'3.3V')+ground(x+72,136)
        b+=line(x+20,136,x+20,199)+line(x+115,136,x+115,242)+text(x+24,192,'H')+text(x+119,234,'L')
        b+=text(x,168,'TX / RX logic side')
    b+=line(20,199,404,199)+line(20,242,404,242)+node(45,199)+node(277,199)+node(140,242)+node(367,242)
    for x in [20,404]:
        b+=line(x,199,x,207)+'<rect class="p" x="%s" y="207" width="10" height="27"/>'%(x-5)+line(x,234,x,242)
    b+=text(33,222,'120 ohm')+text(301,222,'120 ohm')+text(15,295,'Termination links CANH to CANL at both ends.')+text(15,320,'Ground/reference path is separate from bus pair.')
    yield '03-can',native('Physical bus is not the controller',b,350)
    b=text(15,48,'B=4, Ts=1ms, IRQ J=0.3ms, CPU C=2ms')
    sx=lambda t:55+t*40
    for y,label in [(88,'sample'),(143,'DMA'),(204,'CPU')]:
        b+=text(8,y-13,label)+line(55,y,395,y)
    for t in range(9):
        b+=line(sx(t),84,sx(t),92)+text(sx(t)-4,109,str(t))
    b+=text(361,127,'ms')
    b+=box(sx(0),143,160,27,'slot0: indices 0..3')+box(sx(4),143,160,27,'slot1: 4..7')
    b+=box(sx(4.3),204,80,27,'process0')
    for t,s in [(4,'ready'),(4.3,'IRQ'),(6.3,'finish'),(8,'reuse')]:
        yy={'ready':264,'IRQ':285,'finish':306,'reuse':327}[s]
        b+=line(sx(t),180,sx(t),yy-10)+text(sx(t)-25,yy,s+' '+str(t))
    b+=text(15,350,'Finish 6.3ms; slack 1.7ms; first age 6.3ms.')
    yield '04-timeline',native('Distinct capture and service times',b,370)
    b=box(20,70,105,42,'FREE')+box(270,70,125,42,'DMA writes')+box(270,220,125,42,'READY')+box(20,220,105,42,'CPU owns')
    b+=line(125,91,270,91)+text(147,77,'arm exclusive')+line(332,112,332,220)+text(205,159,'completion')+text(190,181,'visibility / publish')+line(270,241,125,241)+text(143,230,'acquire / take')+line(72,220,72,112)+text(9,169,'release')
    b+=text(15,301,'token=(epoch, generation, slot)')+text(15,328,'Busy reuse: discard + stop/resync, not overwrite.')
    yield '05-ownership',native('Ownership and generation',b,350)
    b=box(20,74,140,43,'held command d[k]')+box(230,74,165,43,'actuator a: tau=5ms')+line(160,95,230,95)
    b+=line(315,117,205,117)+line(205,117,205,163)+line(205,163,250,163)+resistor(250,163)+line(295,163,315,163)+node(315,163)+text(233,154,'R=20k')
    b+=line(315,163,315,195)+line(304,195,326,195)+line(304,201,326,201)+ground(315,201)+text(331,198,'C=1uF')+text(331,166,'x [V]')
    b+=line(315,163,390,163)+line(390,163,390,259)+box(230,240,165,38,'sample: x[k]')+line(230,259,185,259)+box(20,240,165,38,'u[k]=-K*x[k]')+line(92,240,92,185)+box(20,144,140,41,'one tick delay')+line(92,144,92,117)+text(17,320,'x_dot=(a-x)/taup; a_dot=(d-a)/taua')+text(17,340,'All states are deviations about 1.65 V.')
    yield '07-control',native('ODE, hold and one-sample delay',b,360)


def generate(output):
    out=_destination(output)
    out.mkdir(parents=True,exist_ok=True)
    old={k:os.environ.get(k) for k in ('MPLCONFIGDIR','XDG_CACHE_HOME')}
    try:
        with tempfile.TemporaryDirectory(prefix='embedded-plot-',dir=out) as cache:
            os.environ['MPLCONFIGDIR']=cache
            os.environ['XDG_CACHE_HOME']=cache
            import matplotlib
            with matplotlib.rc_context({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'embedded-v1'}):
                from matplotlib.figure import Figure
                import numpy as np
                import cairosvg
                import models
                assets=out/'assets'; assets.mkdir(exist_ok=True)
                for stem,svg in _native_figures():
                    (assets/(stem+'.svg')).write_text(svg,encoding='utf-8')
                def plot(stem,title,drawer,height=3.5):
                    fig=Figure(figsize=(4.25,height),layout='constrained')
                    ax=fig.subplots(); drawer(ax); ax.set_title(title,fontsize=11)
                    ax.tick_params(labelsize=9); ax.grid(True,alpha=.3)
                    fig.savefig(assets/(stem+'.svg'),metadata={'Date':None})
                fit=models.fit_calibration([0,1000,2000,3000],[.010,.811,1.612,2.409])
                def cal(ax):
                    c=np.array([0,1000,2000,3000]); a,b=fit['coefficients'][1],fit['coefficients'][0]
                    ax.plot(c,[.010,.811,1.612,2.409],'o',label='references')
                    ax.plot(c,b+a*c,'--',label='b+a*code')
                    ax.set_xlabel('code [count]'); ax.set_ylabel('voltage [V]'); ax.legend(fontsize=9)
                plot('06-calibration','Four-point OLS; model, not measurement',cal)
                def response(ax):
                    for t,n in [(.001,200),(.01,100)]:
                        z=np.array(models.control_trace(n,period=t,gain=3))
                        ax.plot(np.arange(n+1)*t,z[:,0],label='Ts='+str(t*1000)+' ms')
                    ax.set_xlabel('time [s]'); ax.set_ylabel('x / x[0]'); ax.legend(fontsize=9)
                plot('08-response','K=3; linear model, no saturation',response)
                def jitter(ax):
                    phase=np.linspace(0,2*math.pi,200)
                    eps=1e-6; f=100
                    exact=np.sin(phase+2*math.pi*f*eps)-np.sin(phase)
                    linear=2*math.pi*f*eps*np.cos(phase)
                    ax.plot(phase,exact*1000,label='exact 1 us shift')
                    ax.plot(phase,linear*1000,'--',label='derivative estimate')
                    ax.set_xlabel('phase [rad]'); ax.set_ylabel('voltage error [mV]'); ax.legend(fontsize=9)
                plot('09-jitter','1 V peak, 100 Hz: sample-time error',jitter)
                for svg in sorted(assets.glob('*.svg')):
                    for w in (360,425):
                        cairosvg.svg2png(bytestring=svg.read_bytes(),write_to=str(assets/(svg.stem+'-'+str(w)+'.png')),output_width=w)
                params={'version':'embedded-v1','ADC_bits':12,'Vref_V':3.3,'period_ns':1000000,
                        'block_samples':4,'IRQ_delay_ns':300000,'CPU_WCET_ns':2000000,
                        'plant_tau_s':.02,'actuator_tau_s':.005,'gain_V_per_V':3,
                        'calibration_codes':[0,1000,2000,3000],'calibration_V':[.010,.811,1.612,2.409]}
                (out/'parameters.json').write_text(json.dumps(params,indent=2)+'\n')
                results={'calibration':fit,'I2C_rise_ns':models.pullup()*1e9,
                         'spectral_radius':{str(t):float(max(abs(np.linalg.eigvals(models.held_matrix(period=t,gain=3))))) for t in [.001,.01,.02]},
                         'integer_example':models.CountFilter().process([2048,2052,2056,2060],0,0)}
                (out/'results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
                for name,cpu in [('events-valid',2000000),('events-overrun',5000000)]:
                    rows=models.schedule(cpu_ns=cpu)
                    with (out/(name+'.csv')).open('w',newline='') as f:
                        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
                # Same ideal ADC -> ownership -> integer state -> calibrated output chain.
                voltages=[1.65+i*(3.3/4096)*4 for i in range(32)]
                codes=[models.adc(v)['code'] for v in voltages]
                filt=models.CountFilter(); ring=models.OwnedRing(); pipeline=[]
                gain=fit['coefficients'][1]; offset=fit['coefficients'][0]
                for row in models.schedule():
                    begin=row['start_index']; token=ring.publish(row['slot'],codes[begin:begin+4])
                    payload=ring.take(token); filtered=filt.process(payload,begin,0)
                    for j,(code,(fir,iir,valid)) in enumerate(zip(payload,filtered)):
                        idx=begin+j
                        pipeline.append(dict(epoch=0,index=idx,capture_ns=idx*1000000,
                          processing_finish_ns=row['cpu_finish_ns'],ideal_input_V=voltages[idx],
                          code=code,calibration_id='four-point-v1',calibrated_V=offset+gain*code,
                          FIR_count=fir,IIR_count=iir,FIR_valid=valid,
                          output_deviation_V=gain*iir,output_reference_V=offset+gain*2048,
                          status='CPU_result_only'))
                    ring.release(token)
                with (out/'pipeline.csv').open('w',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=list(pipeline[0]));writer.writeheader();writer.writerows(pipeline)
    finally:
        for key,val in old.items():
            if val is None: os.environ.pop(key,None)
            else: os.environ[key]=val
    return out


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    try: generate(args.output)
    except ValueError as exc: parser.error(str(exc))
    return 0

if __name__=='__main__': raise SystemExit(main())
