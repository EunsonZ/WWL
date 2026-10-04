"""Regenerate U1 editable SVG, 425px PNG and SI-unit CSV/JSON data.

Run with external MPLCONFIGDIR and Python -B. Figures use bundled DejaVu
Latin labels; Chinese captions in the lesson explain each label.
"""
from pathlib import Path
import argparse
import csv
import json
import math
import platform
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rc_lab import RC, QFormat

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True, help="generated assets directory")
OUT = parser.parse_args().output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                     "svg.fonttype":"none", "svg.hashsalt":"WWL-U1-RC-20261004", "axes.grid":True,
                     "grid.alpha":.25, "lines.linewidth":1.8})


def save(fig, stem):
    fig.savefig(OUT / (stem + ".svg"), metadata={"Date":None})
    fig.savefig(OUT / (stem + "-425.png"), dpi=100)
    plt.close(fig)


def csvwrite(stem, header, rows):
    with (OUT / (stem + ".csv")).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# Hand-coded geometry is an editable, generated circuit source, not a screenshot.
circuit = '''<svg xmlns="http://www.w3.org/2000/svg" width="425" height="280" viewBox="0 0 425 280">
<rect width="425" height="280" fill="white"/>
<g fill="none" stroke="#222" stroke-width="2.5">
<path d="M55 75H110M170 75H230M290 75H345V105M345 140V205H55V140M55 105V75"/>
<circle cx="55" cy="122" r="18"/>
<rect x="110" y="65" width="60" height="20"/><rect x="230" y="65" width="60" height="20"/>
<path d="M324 105H366M324 140H366M345 205V223M328 223H362M333 230H357M339 237H351"/>
<path d="M345 75H398V104M398 158V205H345"/><rect x="389" y="104" width="18" height="54"/>
<path d="M182 48H217M217 48L209 44M217 48L209 52"/>
</g><g font-family="DejaVu Sans,sans-serif" font-size="15" fill="#222">
<text x="26" y="164">u(t)</text><text x="45" y="126">+</text>
<text x="122" y="57">Rs</text><text x="246" y="57">R</text><text x="179" y="34">i</text>
<text x="290" y="131">C</text><text x="373" y="98">RL</text>
<text x="319" y="61">v(t)</text><text x="312" y="101">+</text>
<text x="313" y="129">v</text><text x="312" y="155">−</text>
<text x="20" y="268">Rt = R + Rs; RL parallel with C</text>
</g><circle cx="345" cy="75" r="4" fill="#222"/>
</svg>'''
(OUT/"rc-circuit.svg").write_text(circuit, encoding="utf-8")
rc = RC()
t = np.linspace(0,.01,1001)
fig, axes = plt.subplots(2,1,figsize=(4.25,5.8),layout="constrained")
rows=[]
for ax,h,n in zip(axes,[.00025,.0025],[40,4]):
    tk = np.arange(n+1)*h
    ve = rc.simulate(np.ones(n),h)
    vu = rc.simulate(np.ones(n),h,method="euler")
    ax.plot(t*1e3,rc.step(t),"k-",label="continuous")
    ax.plot(tk*1e3,ve,"o",ms=4,label="exact ZOH")
    ax.plot(tk*1e3,vu,"s--",ms=4,label="Euler")
    ax.set(title=f"Ts = {h*1e3:g} ms",xlabel="time (ms)",ylabel="v (V)")
    ax.legend(fontsize=9,loc="best")
    rows.extend(zip(np.full(n+1,h),tk,ve,vu))
save(fig,"rc-response")
csvwrite("rc-discrete",["Ts_s","time_s","exact_V","euler_V"],rows)

f=np.logspace(0,4,400)
fig,axes=plt.subplots(2,1,figsize=(4.25,5.3),layout="constrained")
H=rc.frequency(f)
axes[0].semilogx(f,20*np.log10(abs(H)),"k-")
axes[0].axvline(1/(2*np.pi*rc.tau),color=".4",ls=":")
axes[0].set(xlabel="frequency (Hz)",ylabel="gain (dB)",title="RC: fc = 159.15 Hz")
axes[1].semilogx(f,np.angle(H)*180/np.pi,"k-")
axes[1].set(xlabel="frequency (Hz)",ylabel="phase (degrees)")
save(fig,"rc-frequency")
csvwrite("rc-frequency",["frequency_Hz","gain_dimensionless","phase_rad"],zip(f,abs(H),np.angle(H)))

fig,ax=plt.subplots(figsize=(4.25,3.5),layout="constrained")
configs=[(RC(),0.,"ideal; v0=0","-"),(RC(),.4,"ideal; v0=0.4","--"),
         (RC(rs=200,rl=10000),0.,"Rs=200; RL=10k",":"),
         (RC(r=1050,c=1.2e-6),0.,"R +5%; C +20%","-.")]
for model,v0,label,style in configs:
    ax.plot(t*1e3,model.step(t,v0=v0),style,label=label)
ax.set(xlabel="time (ms)",ylabel="v (V)",title="Initial state and physical model")
ax.legend(fontsize=8.5)
save(fig,"rc-models")
csvwrite("rc-models",["time_s"]+[x[2] for x in configs],zip(t,*[x[0].step(t,v0=x[1]) for x in configs]))

rgrid=np.linspace(950,1050,31)
cgrid=np.linspace(.8e-6,1.2e-6,31)
rg,cg=np.meshgrid(rgrid,cgrid)
v=-np.expm1(-.001/(rg*cg))
fig=plt.figure(figsize=(4.25,4.3),layout="constrained")
ax=fig.add_subplot(111,projection="3d")
ax.plot_surface(rg,cg*1e6,v,cmap="viridis",alpha=.95,edgecolor="none")
ax.set(xlabel="R (ohm)",ylabel="C (uF)",zlabel="v at 1 ms (V)",title="1 V step; ideal unloaded RC")
ax.view_init(elev=27,azim=-50)
ax.tick_params(labelsize=8)
ax.set_box_aspect((1,1,.8), zoom=.83)
save(fig,"rc-tolerance-surface")
csvwrite("rc-tolerance-surface",["R_ohm","C_F","v_at_1ms_V"],zip(rg.ravel(),cg.ravel(),v.ravel()))
fig,ax=plt.subplots(figsize=(4.25,3.5),layout="constrained")
for cap,style in zip([.8e-6,1e-6,1.2e-6],["-","--",":"]):
    ax.plot(rgrid,-np.expm1(-.001/(rgrid*cap)),style,label=f"C={cap*1e6:g} uF")
ax.set(xlabel="R (ohm)",ylabel="v at 1 ms (V)",title="Slices of the tolerance surface")
ax.legend(fontsize=9)
save(fig,"rc-tolerance-slices")

h=.00025;n=80;q=QFormat();exact=rc.simulate(np.ones(n),h)
quant=rc.simulate(np.ones(n),h,quantizer=q)
fig,axes=plt.subplots(2,1,figsize=(4.25,5.1),layout="constrained")
axes[0].plot(np.arange(n+1)*h*1e3,quant,"k-",label="Q16.14 state")
axes[0].set(xlabel="time (ms)",ylabel="v (V)",title="Coefficient/state rounding; no clipping")
axes[1].plot(np.arange(n+1)*h*1e3,(quant-exact)*1e6,"k-")
axes[1].set(xlabel="time (ms)",ylabel="Q minus float64 (uV)")
save(fig,"rc-rounding")
csvwrite("rc-rounding",["time_s","float64_V","Q16_14_V","difference_V"],zip(np.arange(n+1)*h,exact,quant,quant-exact))

# Series RLC, capacitor output: analytic zero-state 1 V step.
L=.01;C=1e-6;w0=1/math.sqrt(L*C);tt=np.linspace(0,.003,1201)
fig,axes=plt.subplots(2,1,figsize=(4.25,5.6),layout="constrained")
rlcrows=[];energy_residual=[]
for resistance,style in zip([50.,200.,400.],["-","--",":"]):
    alpha=resistance/(2*L)
    if alpha<w0:
        wd=math.sqrt(w0*w0-alpha*alpha)
        vv=1-np.exp(-alpha*tt)*(np.cos(wd*tt)+alpha/wd*np.sin(wd*tt))
        dv=np.exp(-alpha*tt)*w0*w0/wd*np.sin(wd*tt)
        ddv=np.exp(-alpha*tt)*w0*w0*(np.cos(wd*tt)-alpha/wd*np.sin(wd*tt))
    elif alpha==w0:
        vv=1-(1+w0*tt)*np.exp(-w0*tt)
        dv=w0*w0*tt*np.exp(-w0*tt)
        ddv=w0*w0*(1-w0*tt)*np.exp(-w0*tt)
    else:
        d=math.sqrt(alpha*alpha-w0*w0);s1=-alpha+d;s2=-alpha-d
        A=s2/(s1-s2);B=-s1/(s1-s2)
        vv=1+A*np.exp(s1*tt)+B*np.exp(s2*tt)
        dv=A*s1*np.exp(s1*tt)+B*s2*np.exp(s2*tt)
        ddv=A*s1*s1*np.exp(s1*tt)+B*s2*s2*np.exp(s2*tt)
    ii=C*dv
    # Independent KVL and energy balance residual, evaluated on closed form.
    residual=L*C*ddv+resistance*C*dv+vv-1
    assert np.max(abs(residual))<2e-15
    assert abs(vv[0])<2e-15 and abs(ii[0])<2e-15
    energy=.5*C*vv*vv+.5*L*ii*ii
    dedt=C*vv*dv+L*ii*C*ddv
    defect=dedt-(ii-resistance*ii*ii)
    assert np.max(abs(defect))<2e-17
    energy_residual.append(float(np.max(abs(defect))))
    axes[0].plot(tt*1e3,vv,style,label=f"R={resistance:g} ohm")
    axes[1].plot(tt*1e3,energy*1e6,style,label=f"R={resistance:g} ohm")
    rlcrows.extend(zip(np.full(tt.size,resistance),tt,vv,ii,energy))
axes[0].set(xlabel="time (ms)",ylabel="capacitor v (V)",title="Series RLC: L=10 mH; C=1 uF")
axes[0].legend(fontsize=9)
axes[1].set(xlabel="time (ms)",ylabel="stored energy (uJ)")
save(fig,"rlc-response-energy")
csvwrite("rlc-response-energy",["R_ohm","time_s","v_V","i_A","stored_J"],rlcrows)

results={"environment":{"python":platform.python_version(),"numpy":np.__version__,"matplotlib":matplotlib.__version__},
         "nominal":{"tau_s":rc.tau,"v_at_tau_V":float(rc.step([rc.tau])[0]),"fc_Hz":1/(2*np.pi*rc.tau)},
         "coefficients":{str(x):{m:list(rc.coefficients(x,m)) for m in ["exact","euler"]} for x in [.00025,.0025]},
         "loaded":{"gain":RC(rs=200,rl=10000).gain,"tau_s":RC(rs=200,rl=10000).tau},
         "tolerance_at_1ms_V":{"min":float(v.min()),"max":float(v.max())},
         "fixed_point":{"quantum_V":q.quantum,"max_difference_V":float(max(abs(quant-exact))),"last_state_V":float(quant[-1])},
         "rlc_energy_balance_max_defect_W":energy_residual,
         "verified":"CPU analytic reference only; no SPICE/device/client/human evidence"}
(OUT/"results.json").write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(results,indent=2,ensure_ascii=False))
