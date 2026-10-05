"""Deterministic teaching models, SI units; no SPICE or physical validation.
Run: python3 -B device_examples.py. Plots require existing matplotlib/numpy.
All public inputs are finite scalar reals; bool and nonfinite values rejected.
"""
import math
import json
from pathlib import Path


def scalar(x, positive=False, nonnegative=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError('finite real scalar required')
    if positive and x <= 0 or nonnegative and x < 0:
        raise ValueError('input outside domain')
    return float(x)


def diode_current(v, isat=1e-12, vt=.026, ideality=1.):
    v, isat, vt, ideality = scalar(v), scalar(isat, positive=True), scalar(vt, positive=True), scalar(ideality, positive=True)
    try:
        return isat * math.expm1(v/(ideality*vt))
    except OverflowError as exc:
        raise ValueError('exponential outside numerical range') from exc


def diode_bias(vs, resistance, isat=1e-12, vt=.026, ideality=1.):
    vs, resistance = scalar(vs, nonnegative=True), scalar(resistance, positive=True)
    scalar(isat, positive=True); scalar(vt, positive=True); scalar(ideality, positive=True)
    # Solve in current, avoiding exp(vs/vt) overflow for high supply voltages.
    lo, hi = 0., vs/resistance
    for _ in range(100):
        current = (lo+hi)/2
        voltage = ideality*vt*math.log1p(current/isat)
        residual = resistance*current + voltage - vs
        if residual > 0: hi = current
        else: lo = current
    current = (lo+hi)/2
    voltage = ideality*vt*math.log1p(current/isat)
    return {'voltage': voltage, 'current': current,
            'rd': ideality*vt/(current+isat),
            'kcl_A': (vs-voltage)/resistance-current}


def mos_current(vov, vds, k=.002, lam=.02):
    """Piecewise long-channel model. Negative VDS is unsupported.
    Both regions use the teaching factor (1+lam*vds), continuous at boundary.
    Boundary is assigned to saturation; do not finite-difference across it.
    """
    vov, vds, k, lam = scalar(vov), scalar(vds, nonnegative=True), scalar(k, positive=True), scalar(lam, nonnegative=True)
    if vov <= 0: return 0.
    if vds < vov: return k*(vov*vds-vds*vds/2)*(1+lam*vds)
    return k*vov*vov/2*(1+lam*vds)


def mos_small(vov, vds, k=.002, lam=.02):
    mos_current(vov, vds, k, lam)  # domain validation
    if vov <= 0: return 0., 0.
    if vds < vov: return k*vds*(1+lam*vds), k*(vov-vds)*(1+lam*vds)+k*(vov*vds-vds*vds/2)*lam
    return k*vov*(1+lam*vds), k*vov*vov*lam/2


def mos_bias(vs, rd, vov, k=.002, lam=.02):
    vs, rd, vov, k, lam = scalar(vs, positive=True), scalar(rd, positive=True), scalar(vov, positive=True), scalar(k, positive=True), scalar(lam, nonnegative=True)
    i0 = k*vov*vov/2
    iq = i0*(1+lam*vs)/(1+i0*lam*rd)
    vd = vs-iq*rd
    if vd < vov: raise ValueError('saturation candidate outside region; solve triode separately')
    gm, go = mos_small(vov, vd, k, lam)
    return {'current': iq, 'vd': vd, 'gm': gm, 'ro': math.inf if go == 0 else 1/go,
            'kcl_A': (vs-vd)/rd-mos_current(vov, vd, k, lam)}


def bjt_small(ic, beta, vt, va, vce):
    ic, beta, vt, va, vce = scalar(ic, positive=True), scalar(beta, positive=True), scalar(vt, positive=True), scalar(va, positive=True), scalar(vce, nonnegative=True)
    # Caller must establish forward-active junction bias; VCE alone is insufficient.
    gm = ic/vt
    return gm, beta/gm, (va+vce)/ic


def opamp(a0, gbw, noise_gain, frequency, output_peak, slew):
    a0, gbw, noise_gain = scalar(a0, positive=True), scalar(gbw, positive=True), scalar(noise_gain, positive=True)
    if noise_gain < 1: raise ValueError('noninverting resistive noise gain must be >=1')
    frequency, output_peak, slew = scalar(frequency, nonnegative=True), scalar(output_peak, nonnegative=True), scalar(slew, positive=True)
    dc = a0/(1+a0/noise_gain)
    fc = gbw/a0*(1+a0/noise_gain)
    return {'dc_gain': dc, 'dc_relative_error': 1/(1+a0/noise_gain),
            'fc': fc, 'normalized_magnitude': 1/math.hypot(1, frequency/fc),
            'sr_required': 2*math.pi*frequency*output_peak,
            'sr_ok': 2*math.pi*frequency*output_peak <= slew}


def mos_periodic_candidate(amplitude, phase, vs=5., rd=2000., rl=10000.,
                           u0=1., k=.002, coupling_x=None):
    """Formal full-saturation CLM=0 periodic candidate, SI units.
    coupling_x = omega*C*(RD+RL); None is its infinite-frequency limit.
    Mean capacitor charge is constrained by periodicity, not old no-signal Q.
    Caller must verify saturation for the ENTIRE cycle; invalid candidates are
    evidence for rejection, never accepted as the physical waveform.
    """
    amplitude, phase = scalar(amplitude, nonnegative=True), scalar(phase)
    vs, rd, rl, u0, k = (scalar(v, positive=True) for v in (vs, rd, rl, u0, k))
    if coupling_x is not None: coupling_x = scalar(coupling_x, positive=True)
    c = k/2
    u = u0+amplitude*math.sin(phase)
    mean_i = c*(u0*u0+amplitude*amplitude/2)
    mean_v = vs-rd*mean_i
    vc = mean_v
    if coupling_x is not None:
        x = coupling_x
        vc += -2*rd*c*u0*amplitude*(math.sin(phase)-x*math.cos(phase))/(1+x*x)
        vc += rd*c*amplitude*amplitude/2*(math.cos(2*phase)+2*x*math.sin(2*phase))/(1+4*x*x)
    current = c*u*u  # formal algebra; u<=0 is explicitly rejected below
    resistance = 1/(1/rd+1/rl)
    vd = resistance*(vs/rd+vc/rl-current)
    load_i = (vd-vc)/rl
    return {'mean_current':mean_i, 'mean_vd':mean_v, 'vc':vc, 'vd':vd,
            'current':current, 'load_current':load_i, 'vov':u,
            'saturation_margin':vd-u,
            'instantaneous_saturation_ok':u>0 and vd>=u,
            'kcl_A':(vs-vd)/rd-current-load_i}


def mos_periodic_boundary(vs=5., rd=2000., rl=10000., u0=1., k=.002):
    """First positive-input saturation boundary in ideal-coupling periodic limit.
    Requires no-signal saturated bias. If cutoff happens first, reject this
    boundary formula rather than extrapolate the full-saturation derivation.
    """
    vs, rd, rl, u0, k = (scalar(v, positive=True) for v in (vs, rd, rl, u0, k))
    c = k/2; resistance=1/(1/rd+1/rl)
    constant=vs-rd*c*u0*u0-u0
    if constant <= 0: raise ValueError('no-signal point lacks saturation margin')
    quadratic=c*(rd+resistance)/2
    linear=2*resistance*c*u0+1
    amplitude=2*constant/(linear+math.sqrt(linear*linear+4*quadratic*constant))
    if amplitude >= u0: raise ValueError('cutoff occurs before this boundary')
    return amplitude


def plots(destination, only=None):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    destination.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none'})
    def save(fig, name):
        if only is not None and name not in only:
            plt.close(fig)
            return
        if name == 'mos-region-gain':
            # Fixed full canvas retains 3D labels; PNG is rendered FROM the SVG.
            fig.savefig(destination/(name+'.svg'))
            import cairosvg
            cairosvg.svg2png(url=str(destination/(name+'.svg')),
                            write_to=str(destination/(name+'-425.png')), output_width=425)
            plt.close(fig)
            return
        fig.savefig(destination/(name+'.svg'), bbox_inches='tight')
        # Exact 425 px width, fixed figure geometry and no tight cropping for PNG.
        fig.savefig(destination/(name+'-425.png'), dpi=425/fig.get_figwidth())
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(6,4), layout='constrained')
    v=np.linspace(0,.58,250); ids=np.array([diode_current(float(x)) for x in v]); q=diode_bias(5,4700)
    ax.plot(v,ids*1e3,label='Diode model',color='black'); ax.plot(v,(5-v)/4700*1e3,'--',label='5 V / 4.7 kohm load',color='tab:blue'); ax.plot(q['voltage'],q['current']*1e3,'o',color='black',label='Q')
    ax.set(xlabel='Diode voltage (V)',ylabel='Current (mA)',ylim=(0,2.3),title='One point satisfies both constraints'); ax.legend(fontsize=9); ax.grid(); save(fig,'diode-load')
    u=np.linspace(.2,1.6,18); d=np.linspace(.15,4.,23); U,D=np.meshgrid(u,d); Z=np.empty_like(U)
    records=[]
    for index in np.ndindex(U.shape):
        gm,go=mos_small(float(U[index]),float(D[index])); Z[index]=gm/(1/2000+1/10000+go)
        records.append([float(U[index]),float(D[index]),float(Z[index]),'triode' if D[index]<U[index] else 'saturation'])
    fig=plt.figure(figsize=(7,5),layout='constrained'); ax=fig.add_subplot(projection='3d'); ax.plot_surface(U,D,Z,cmap='Greys',alpha=.75,edgecolor='gray',linewidth=.2)
    zz=[mos_small(float(x),float(x))[0]/(1/2000+1/10000+mos_small(float(x),float(x))[1]) for x in u]
    ax.plot(u,u,zz,'--',color='black',linewidth=2,label='VDS = VOV boundary')
    ax.set(xlabel='VOV (V)',ylabel='VDS (V)',zlabel='Local |Av| (V/V)',title='Independent gate and drain bias'); ax.legend(fontsize=9); ax.view_init(25,-55); save(fig,'mos-region-gain')
    import csv
    if only is None:
        with (destination/'mos-region-gain.csv').open('w',newline='') as f:
            writer=csv.writer(f); writer.writerow(['vov_V','vds_V','gain_V_per_V','region']); writer.writerows(records)
    fig,ax=plt.subplots(figsize=(7,3),layout='constrained'); ax.set(xlim=(0,10),ylim=(0,3)); ax.axis('off')
    for x,text in [(0.3,'Source\nvs, Rs'),(3.3,'Device\ngm vg'),(6.5,'Output\nRD || RL || ro')]:
        ax.add_patch(Rectangle((x,.9),2.5,1.2,fill=False)); ax.text(x+1.25,1.5,text,ha='center',va='center')
    ax.annotate('',(3.3,1.5),(2.8,1.5),arrowprops={'arrowstyle':'->'}); ax.annotate('',(6.5,1.5),(5.8,1.5),arrowprops={'arrowstyle':'->'}); ax.text(5,2.6,'DC bias sets gm; AC load converts current to voltage',ha='center'); ax.text(5,.25,'BJT input: rpi + bias network; MOS input: gate capacitance',ha='center'); save(fig,'small-signal')
    f=np.geomspace(100,1e6,300); amplitude=np.minimum(2,.5e6/(2*np.pi*f)); f1=.1424922826*100010
    fig,ax=plt.subplots(figsize=(6,4),layout='constrained'); ax.loglog(f,amplitude,'--',color='black',label='SR + swing envelope'); ax.axvline(f1,color='black',label='1% single-pole amplitude limit'); ax.axhline(2,color='tab:blue',linestyle=':',label='2 V peak swing'); ax.fill_between(f,.005,amplitude,where=f<=f1,color='lightgray'); ax.set(xlabel='Frequency (Hz)',ylabel='Output peak (V)',ylim=(.005,4),title='Necessary conditions, not a stability proof'); ax.legend(fontsize=8); ax.grid(); save(fig,'opamp-limits')


if __name__ == '__main__':
    out=Path(__file__).parent/'assets'
    plots(out)
    result={'diode':diode_bias(5,4700), 'diode_transfer':diode_bias(3,2200),
            'mos':mos_bias(5,2000,1),
            'opamp_transfer':opamp(20000,2e6,20,20000,2,1e6),
            'linearization':{
                'diode_5mV_exact_delta_A':diode_current(diode_bias(5,4700)['voltage']+.005)-diode_bias(5,4700)['current'],
                'diode_5mV_linear_delta_A':.005/diode_bias(5,4700)['rd'],
                'mos_5mV_exact_delta_A':mos_current(1.005,3,lam=0)-mos_current(1,3,lam=0),
                'mos_5mV_linear_delta_A':.002*.005},
            'periodic_a035':mos_periodic_candidate(.35,math.pi/2),
            'periodic_boundary':mos_periodic_boundary(),
            'periodic_transfer_boundary':mos_periodic_boundary(rd=3000,rl=6000)}
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))
