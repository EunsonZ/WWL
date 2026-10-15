"""Same quadratic: exact rational GD, linear ODE and staged NumPy rounding.

No installs/network/GPU. --output is required and must be outside this source
folder. References: rational powers are exact before diagnostic float64 cast;
ODE uses host float64 exp. Norms/objectives are float64 diagnostics, not part of
low-precision updates. All quantities, including model time, are dimensionless.
"""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path
import platform
import numpy as np

INITIAL = (Fraction(2), Fraction(3, 5))
CURVATURE = (Fraction(1), Fraction(10))


def validate(h, steps, initial, curvature):
    if isinstance(steps, bool) or not isinstance(steps, (int, np.integer)) or steps < 0:
        raise ValueError('steps must be a nonnegative integer')
    h = float(h)
    initial = np.asarray(initial, dtype=np.float64)
    curvature = np.asarray(curvature, dtype=np.float64)
    if not np.isfinite(h) or h <= 0:
        raise ValueError('h must be finite and positive')
    if initial.shape != (2,) or curvature.shape != (2,):
        raise ValueError('initial and diagonal curvature must each have shape (2,)')
    if not np.all(np.isfinite(initial)) or not np.all(np.isfinite(curvature)) or np.any(curvature <= 0):
        raise ValueError('finite state and positive finite curvature required')


def real_gd(h: Fraction, steps: int, initial=INITIAL, curvature=CURVATURE):
    """Exact real/rational closed form, NOT a float64 GD recurrence."""
    if not isinstance(h, Fraction) or any(not isinstance(v, Fraction) for v in (*initial, *curvature)):
        raise TypeError('rational inputs required to avoid silently changing the model')
    validate(h, steps, initial, curvature)
    return tuple(a * (1 - h * lam) ** int(steps) for a, lam in zip(initial, curvature))


def ode(t: float, initial=INITIAL, curvature=CURVATURE):
    if not np.isfinite(t) or t < 0:
        raise ValueError('t must be finite and nonnegative')
    validate(1, 0, initial, curvature)
    return np.asarray(initial, dtype=np.float64) * np.exp(-float(t) * np.asarray(curvature, dtype=np.float64))


def rounded_gd(h: Fraction, steps: int, dtype, initial=INITIAL, curvature=CURVATURE):
    """Each multiply/subtract writes dtype. No fused multiply-add is requested.

    The stored h defines updates, while diagnostic t=k*h uses intended rational h.
    This is the observed NumPy process, not a claim about native FP16 instructions.
    """
    validate(h, steps, initial, curvature)
    dt = np.dtype(dtype)
    if dt not in (np.dtype(np.float16), np.dtype(np.float32)):
        raise ValueError('only binary16/binary32 storage are in this experiment')
    hh = np.asarray(float(h), dtype=dt)
    lam = np.asarray(curvature, dtype=dt)
    state = np.asarray(initial, dtype=dt)
    if float(hh) <= 0 or not np.isfinite(hh) or not np.all(np.isfinite(state)) or not np.all(np.isfinite(lam)):
        raise ValueError('conversion changed valid input to zero step or nonfinite values')
    path = np.empty((steps + 1, 2), dtype=dt)
    path[0] = state
    with np.errstate(over='raise', invalid='raise'):
        for k in range(steps):
            gradient = np.multiply(lam, state, dtype=dt)
            delta = np.multiply(hh, gradient, dtype=dt)
            state = np.subtract(state, delta, dtype=dt)
            path[k+1] = state
    return path


def diagnostic(state, reference, exact_ode, curvature=CURVATURE):
    state = np.asarray(state, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    exact_ode = np.asarray(exact_ode, dtype=np.float64)
    return {'x': float(state[0]), 'y': float(state[1]),
            'objective': float(.5 * np.sum(np.asarray(curvature, dtype=np.float64)*state**2)),
            'distance_to_minimum_2': float(np.linalg.norm(state)),
            'rounding_error_2': float(np.linalg.norm(state-reference)),
            'ode_error_2': float(np.linalg.norm(state-exact_ode)),
            'decision_x_le_0_72': bool(state[0] <= .72),
            'decision_norm_le_1e_8': bool(np.linalg.norm(state) <= 1e-8)}


def case(name, h, steps, rows):
    t = float(h * steps)
    ref = real_gd(h, steps)
    truth = ode(t)
    result = {'name': name, 'h_rational': str(h), 'steps': steps, 'T': t,
              'real_gd': diagnostic(ref, ref, truth), 'ode': diagnostic(truth, ref, truth),
              'discretization_error_2': float(np.linalg.norm(np.asarray(ref,dtype=float)-truth))}
    result['ode']['rounding_error_2'] = None  # not an implementation of GD
    result['ode']['y_reference_rounded_to_zero'] = bool(truth[1] == 0)
    sampled = list(range(steps+1)) if steps <= 400 else sorted({0,1,2,10,100,400,1000,steps})
    for dtype in (np.float16, np.float32):
        label = np.dtype(dtype).name
        path = rounded_gd(h, steps, dtype)
        changes = np.any(path[1:] != path[:-1], axis=1)
        fixed = np.flatnonzero(~changes)
        final = path[-1]
        gradient = np.multiply(np.asarray(CURVATURE,dtype=dtype), final, dtype=dtype)
        delta = np.multiply(np.asarray(float(h),dtype=dtype),gradient,dtype=dtype)
        stored_ref = real_gd(Fraction.from_float(float(dtype(float(h)))), steps,
                             tuple(Fraction.from_float(float(dtype(float(v)))) for v in INITIAL),
                             tuple(Fraction.from_float(float(dtype(float(v)))) for v in CURVATURE))
        data = diagnostic(final, ref, truth)
        data.update({'input_representation_error_2': float(np.linalg.norm(np.asarray(stored_ref,dtype=float)-np.asarray(ref,dtype=float))),
                     'operation_error_2': float(np.linalg.norm(final.astype(float)-np.asarray(stored_ref,dtype=float)))})
        data.update({'stored_h': float(dtype(float(h))), 'first_whole_state_fixed_step': int(fixed[0]+1) if len(fixed) else None,
                     'first_x_unchanged_step': next((k+1 for k in range(steps) if path[k+1,0]==path[k,0]),None),
                     'final_gradient': [float(v) for v in gradient], 'final_delta': [float(v) for v in delta],
                     'all_finite': bool(np.all(np.isfinite(path)))})
        result[label] = data
        for k in sampled:
            if k > steps: continue
            real = real_gd(h,k)
            truth_k = ode(float(k*h))
            stats = diagnostic(path[k], real, truth_k)
            rows.append({'case': name,'format':label,'h_rational':str(h),'k':k,'t':float(k*h), **stats})
    for k in sampled:
        if k > steps: continue
        real = real_gd(h,k)
        rows.append({'case':name,'format':'real_gd','h_rational':str(h),'k':k,'t':float(k*h),**diagnostic(real,real,ode(float(k*h)))})
    return result


def render(output, cases, refinement):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    from PIL import Image
    # Fail explicitly rather than silently replacing Chinese labels with tofu.
    font_manager.findfont('Arial Unicode MS', fallback_to_default=False)
    plt.rcParams.update({'font.family':'Arial Unicode MS','font.size':12,
                         'svg.fonttype':'none','svg.hashsalt':'wwl-gradient-flow-v1','figure.facecolor':'#fbfcfe',
                         'axes.facecolor':'#fbfcfe','axes.unicode_minus':False})
    # Two full-width stacked panels retain readable text when rendered at 425px.
    fig, axes = plt.subplots(2,1,figsize=(5.1,7.2),layout='constrained')
    ax = axes[0]
    ts=np.linspace(0,1,201)
    ax.plot(ts,2*np.exp(-ts),color='#6b7280',label='连续真解 x(t)')
    h=Fraction(1,10); ks=np.arange(11)
    xs=[float(real_gd(h,int(k))[0]) for k in ks]
    ax.plot(ks/10,xs,'o-',color='#1765ac',label='实数 Euler：h=0.1',markersize=4)
    ax.axhline(.72,color='#a44c13',linestyle=':',label='判定阈值 x=0.72')
    ax.set(title='稳定仍有偏差：同一终点 T=1',xlabel='模型时间 t（无量纲）',ylabel='第一分量 x（无量纲）')
    ax.legend(fontsize=11); ax.grid(alpha=.18)
    ax=axes[1]
    hs=[r['h'] for r in refinement]
    ax.loglog(hs,[r['discretization_error_2'] for r in refinement],'o-',color='#1765ac',label='离散误差：实数 GD − ODE')
    ax.loglog(hs,[r['float16_total_error_2'] for r in refinement],'s--',color='#a44c13',label='总误差：binary16 − ODE')
    ax.loglog(hs,[r['float32_total_error_2'] for r in refinement],'^:',color='#15765d',label='总误差：binary32 − ODE')
    ax.set(title='减小步长：固定 T=1，增加步数',xlabel='步长 h（无量纲，对数）',ylabel='末端欧氏误差（对数）')
    ax.legend(fontsize=10); ax.grid(alpha=.18)
    fig.savefig(output/'flow-error.svg',metadata={'Date':None})
    fig.savefig(output/'flow-error.png',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(5.1,7.0),layout='constrained')
    ax=axes[0]
    h=Fraction(1,10); path=rounded_gd(h,400,np.float16)
    ks=np.arange(401)
    ax.semilogy(ks,[float(real_gd(h,int(k))[0]) for k in ks],color='#1765ac',label='实数 GD 的 x')
    ax.semilogy(ks,path[:,0].astype(float),'--',color='#a44c13',label='binary16 的 x')
    ax.axhline(1e-8,color='#15765d',linestyle=':',label='任务容差 10⁻⁸')
    ax.set(title='长期停滞：h=0.1，T=40',xlabel='更新次数 k（整数）',ylabel='第一分量 x（对数）')
    ax.legend(fontsize=11); ax.grid(alpha=.18)
    ax=axes[1]
    h=Fraction(1,10000); path=rounded_gd(h,10000,np.float16)
    ks=np.arange(0,10001,100)
    ax.plot(ks/10000,[float(real_gd(h,int(k))[0]) for k in ks],color='#1765ac',label='实数 GD 的 x')
    ax.plot(ks/10000,path[ks,0].astype(float),'--',color='#a44c13',label='binary16 的 x')
    ax.set(title='小步也会不动：h=0.0001，T=1',xlabel='模型时间 t（无量纲）',ylabel='第一分量 x（无量纲）')
    ax.legend(fontsize=11); ax.grid(alpha=.18)
    fig.savefig(output/'flow-stagnation.svg',metadata={'Date':None})
    fig.savefig(output/'flow-stagnation.png',dpi=180)
    plt.close(fig)
    for stem in ['flow-error','flow-stagnation']:
        with Image.open(output/f'{stem}.png') as im:
            target=(425,round(im.height*425/im.width))
            im.resize(target,Image.Resampling.LANCZOS).save(output/f'{stem}-425.png')


def generate(output):
    output=Path(output).resolve()
    source=Path(__file__).resolve().parent
    if output == source or source in output.parents:
        raise ValueError('use a separate output directory')
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    cases=[case('stable',Fraction(1,10),10,rows),
           case('small_step',Fraction(1,10000),10000,rows),
           case('long_binary16',Fraction(1,10),400,rows),
           case('long_binary32',Fraction(1,10),1600,rows)]
    refinement=[]
    for n in (10,20,40,80,160,1000,10000):
        h=Fraction(1,n); ref=real_gd(h,n); truth=ode(1)
        a=rounded_gd(h,n,np.float16)[-1]; b=rounded_gd(h,n,np.float32)[-1]
        refinement.append({'steps':n,'h':float(h),'T':1,
                           'discretization_error_2':float(np.linalg.norm(np.asarray(ref,dtype=float)-truth)),
                           'float16_total_error_2':float(np.linalg.norm(a.astype(float)-truth)),
                           'float32_total_error_2':float(np.linalg.norm(b.astype(float)-truth))})
    initial_errors={dt.__name__:[str(Fraction.from_float(float(dt(float(v))))-v) for v in INITIAL] for dt in [np.float16,np.float32]}
    hidden=[float(v) for v in real_gd(Fraction(1,4),12,(Fraction(2),Fraction(0)))]
    excited=[float(v) for v in real_gd(Fraction(1,4),12,(Fraction(2),Fraction(1,10**6)))]
    migration=[]
    c=(Fraction(1),Fraction(100))
    for h,n in [(Fraction(1,100),100),(Fraction(1,4000),4000),(Fraction(1,100),4000)]:
        real=real_gd(h,n,curvature=c); truth=ode(float(h*n),curvature=c)
        for dtype in [np.float16,np.float32]:
            state=rounded_gd(h,n,dtype,curvature=c)[-1]
            migration.append({'c':100,'format':np.dtype(dtype).name,'h_rational':str(h),'steps':n,'T':float(h*n),
                              **diagnostic(state,real,truth,curvature=c)})
    summary={'model':'f=.5*(x*x+10*y*y), theta0=(2,3/5)',
             'units':'all dimensionless; t=k*h is intended rational model time',
             'runtime':{'python':platform.python_version(),'numpy':np.__version__,'machine':platform.machine()},
             'reference':'rational real GD evaluated exactly then cast to float64 for diagnostics; ODE float64 exp',
             'rounded_process':'dtype H*theta -> dtype h*g -> dtype theta-delta; no FMA request',
             'initial_representation_error':initial_errors,'migration_c100':migration,'cases':cases,'fixed_T_refinement':refinement,
             'hidden_unstable_mode':{'h':.25,'steps':12,'zero_y_initial':[2,0],'zero_y_final':hidden,
                                     'perturbed_y_initial':[2,1e-6],'perturbed_y_final':excited,'y_amplification':(-1.5)**12},
             'scope':'host NumPy CPU process; no GPU, FTZ mode, mixed precision, Adam, SGD noise or control-system validation'}
    assert cases[0]['discretization_error_2'] > .03
    assert cases[0]['real_gd']['decision_x_le_0_72'] and not cases[0]['ode']['decision_x_le_0_72']
    assert cases[1]['float16']['x'] == 2
    assert cases[2]['float16']['first_whole_state_fixed_step'] is not None
    assert cases[2]['float16']['distance_to_minimum_2'] > 1e-8
    assert cases[2]['real_gd']['distance_to_minimum_2'] < 1e-8
    assert all(c[dt]['all_finite'] for c in cases for dt in ['float16','float32'])
    (output/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with (output/'trajectories.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    render(output,cases,refinement)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); result=generate(a.output)
    print(json.dumps({'output':str(a.output),'cases':[{'name':c['name'],'discretization_error_2':c['discretization_error_2'],
                      'fp16_x':c['float16']['x'],'fp16_fixed_step':c['float16']['first_whole_state_fixed_step']} for c in result['cases']]},ensure_ascii=False))


if __name__=='__main__':
    main()
