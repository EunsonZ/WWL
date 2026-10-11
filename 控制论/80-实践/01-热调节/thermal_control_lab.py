"""Deterministic scalar thermal-control lab; standard library only.

x and reference are temperature deviations in K, u and disturbance in W,
time in s. Fixed pedagogical model; no hardware or measured identification.
"""
from __future__ import annotations

import argparse
import cmath
import csv
import json
import math
from pathlib import Path
import platform

C = 10.0  # J/K
H = 1.0  # W/K
KP = 3.0  # W/K
KI = 0.4  # W/(K s)
R = 2.0  # K


def zoh(dt):
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive, in s")
    a = math.exp(-H * dt / C)
    b = -math.expm1(-H * dt / C) / H
    return a, b


def poles2(trace, determinant):
    root = cmath.sqrt(trace * trace - 4 * determinant)
    return [(trace + root) / 2, (trace - root) / 2]


def rk4_hold(x, u, disturbance, dt, n):
    """Independent ODE integration of a held plant input."""
    h = dt / n
    def f(v):
        return (-H * v + u + disturbance) / C
    for _ in range(n):
        k1 = f(x)
        k2 = f(x + h * k1 / 2)
        k3 = f(x + h * k2 / 2)
        k4 = f(x + h * k3)
        x += h * (k1 + 2*k2 + 2*k3 + k4) / 6
    return x


def trajectory(dt, count, *, integral=False, disturbance=0.0,
               bias=0.0, limit=False, reference=R):
    a, b = zoh(dt)
    x, z = 0.0, 0.0
    rows = []
    for k in range(count + 1):
        y = x + bias
        error = reference - y
        command = H * reference + KP * error + (KI*z if integral else 0)
        u = max(-10.0, min(10.0, command)) if limit else command
        rows.append(dict(t_s=k*dt, x_K=x, y_K=y, u_W=u, command_W=command,
                         z_Ks=z, disturbance_W=disturbance))
        # Every right-hand side reads the old sampled state.
        x_next = a*x + b*(u + disturbance)
        z_next = z + dt*error if integral else z
        x, z = x_next, z_next
    return rows


def svg_plot(path, curves, *, ymin, ymax, duration, title):
    width, height = 760, 410
    left, top, pw, ph = 75, 95, 650, 235
    def point(t, x):
        return f"{left+pw*t/duration:.3f},{top+ph*(ymax-x)/(ymax-ymin):.3f}"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           f'<title id="title">{title}</title>',
           '<desc id="desc">Temperature deviation in K against time in s. Sampled values joined by straight lines, not continuous trajectories. C=10 J/K, H=1 W/K, kp=3 W/K; labels and dash patterns distinguish curves.</desc>',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="75" y="25" font-size="17">{title}</text>']
    for i in range(6):
        t = duration*i/5
        px = left+pw*i/5
        out.append(f'<path d="M {px} {top} v {ph}" stroke="#ddd"/>')
        out.append(f'<text x="{px}" y="350" text-anchor="middle" font-size="13">{t:g}</text>')
    for i in range(5):
        y = ymin+(ymax-ymin)*i/4
        py = top+ph*(1-i/4)
        out.append(f'<path d="M {left} {py} h {pw}" stroke="#ddd"/>')
        out.append(f'<text x="65" y="{py+4}" text-anchor="end" font-size="13">{y:g}</text>')
    out.append('<text x="390" y="390" font-size="14">time t [s]</text>')
    out.append('<text x="12" y="55" font-size="14">x [K]</text>')
    palette = [('#222', ''), ('#1366a5', '8 4'), ('#a34900', '2 3')]
    for i, (name, rows) in enumerate(curves):
        color, dash = palette[i]
        points = ' '.join(point(row['t_s'], row['x_K']) for row in rows)
        out.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
        out.append(f'<text x="{left}" y="{45+i*16}" font-size="12" fill="{color}">{name}</text>')
    out.append('</svg>')
    path.write_text('\n'.join(out)+'\n', encoding='utf-8')


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    a, b = zoh(1.0)
    f = a-b*KP
    first = b*(H*R+KP*R)
    nominal = trajectory(1, 40)
    disturbed = trajectory(1, 40, disturbance=-2)
    pi = trajectory(1, 60, integral=True, disturbance=-2)
    biased = trajectory(1, 150, integral=True, disturbance=-2, bias=.5)
    saturated = trajectory(1, 150, integral=True, reference=12, limit=True)
    unstable = trajectory(8, 8)
    # Exact scalar closed-form trajectory is separate from recurrence.
    analytical_error = max(abs(row['x_K']-R*(1-f**k)) for k,row in enumerate(nominal))
    rk_errors = []
    for n in (1,2,4,8):
        approx = rk4_hold(.7, 2.3, -.8, 1.0, n)
        rk_errors.append(abs(approx-(a*.7+b*1.5)))
    assert analytical_error < 1e-12
    assert rk_errors[-1] < 1e-10 and all(rk_errors[i+1]<rk_errors[i] for i in range(3))
    assert abs(first-0.7613006557123239) < 1e-12
    pi_det = f+b*KI
    pi_poles = poles2(f+1, pi_det)
    delay_poles = poles2(a, b*KP)
    assert all(abs(p)<1 for p in pi_poles+delay_poles)
    assert abs(zoh(8)[0]-zoh(8)[1]*KP)>1
    assert abs(biased[-1]['x_K']-1.5)<1e-8
    assert abs(saturated[-1]['x_K']-10)<1e-5
    result = {
        'environment': {'python':platform.python_version(), 'platform':platform.platform()},
        'parameters': {'C_J_per_K':C, 'H_W_per_K':H, 'kp_W_per_K':KP,
                       'ki_W_per_Ks':KI, 'reference_K':R, 'x0_K':0, 'z0_Ks':0},
        'a_Ts1':a, 'b_Ts1_K_per_W':b, 'P_pole_Ts1':f,
        'P_first_step_K':first, 'P_second_step_K':nominal[2]['x_K'],
        'continuous_P_x_at_1s_K':R*(1-math.exp(-.4)),
        'P_disturbed_steady_K':R-2/(H+KP),
        'P_pole_Ts5':zoh(5)[0]-zoh(5)[1]*KP,
        'P_pole_Ts8':zoh(8)[0]-zoh(8)[1]*KP,
        'P_Ts_upper_bound_s':C/H*math.log((KP+H)/(KP-H)),
        'PI_poles_Ts1':[{'real':p.real,'imag':p.imag,'modulus':abs(p)} for p in pi_poles],
        'delay_poles_Ts1':[{'real':p.real,'imag':p.imag,'modulus':abs(p)} for p in delay_poles],
        'delay_pole_modulus_Ts5':max(abs(p) for p in poles2(zoh(5)[0],zoh(5)[1]*KP)),
        'PI_disturbed_x_at_60s_K':pi[-1]['x_K'],
        'PI_biased_x_at_150s_K':biased[-1]['x_K'],
        'PI_saturated_x_at_150s_K':saturated[-1]['x_K'],
        'PI_saturated_z_at_150s_Ks':saturated[-1]['z_Ks'],
        'closed_form_max_error_K':analytical_error,
        'RK4_hold_errors_K_n_1_2_4_8':rk_errors,
        'finite_regulation_table':[[d-action for action in range(3)] for d in range(3)]}
    (output/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    all_curves = {'P_nominal':nominal,'P_disturbed':disturbed,'PI_disturbed':pi,
                  'PI_biased':biased,'PI_saturated':saturated,'P_Ts8_unstable':unstable}
    with (output/'trajectories.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=['case']+list(nominal[0]))
        writer.writeheader()
        for name, rows in all_curves.items():
            for row in rows:
                writer.writerow({'case':name,**row})
    svg_plot(output/'disturbance.svg', [('P nominal; Ts=1 s; d=0 W',nominal),
                                      ('P disturbed; Ts=1 s; d=-2 W',disturbed),
                                      ('PI disturbed; Ts=1 s; d=-2 W',pi[:41])],
             ymin=0,ymax=2.2,duration=40,title='Same plant: constant cooling disturbance')
    svg_plot(output/'sampling.svg', [('P stable; Ts=1 s',trajectory(1,64)),
                                    ('P unstable; Ts=8 s',unstable)],
             ymin=-8,ymax=12,duration=64,title='Same gain: changing the sample period')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args=parser.parse_args()
    run(args.output_dir)
