---
type: code
stage: 0
aliases: []
sources: []
prerequisites: []
---

# optimal_tube_lab.py 源码镜像

真源：[optimal_tube_lab.py](../optimal_tube_lab.py)。此页仅同步源码；实验对象、命令、结果与边界见 [[控制论/80-实践/03-最优与约束热调节/README|实践03]]。

<!-- code-sync: ../optimal_tube_lab.py -->
```python
#!/usr/bin/env python3
"""Serial, standard-library reproduction of the scalar thermal optimal/tube course.
Continuous time is normalized by 10 s; QP/tube arithmetic is exact Fraction.
This is a two-variable teaching solver, not a real-time/hardware controller.
"""
from fractions import Fraction as F
from itertools import combinations, product
from pathlib import Path
import csv
import html
import json
import math
import resource
import sys

A, B, K, Q, R = F(9, 10), F(1, 10), F(2), F(1), F(1, 100)
CL = A - B * K
P = (Q + R * K * K) / (1 - CL * CL)
EPS, ZMAX, VMAX = F(1, 3), F(2, 3), F(4, 3)


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def linear_solve(matrix, rhs):
    """Exact Gauss-Jordan with pivoting; None means dependent active rows."""
    n = len(rhs)
    aug = [list(row) + [v] for row, v in zip(matrix, rhs)]
    for col in range(n):
        pivot = next((i for i in range(col, n) if aug[i][col]), None)
        if pivot is None:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for i in range(n):
            if i != col:
                scale = aug[i][col]
                aug[i] = [v - scale * w for v, w in zip(aug[i], aug[col])]
    return [row[-1] for row in aug]


def qp_data(z):
    s1, s2 = (B, F(0)), (A * B, B)
    h = [[2 * (R * (i == j) + s1[i] * s1[j] + P * s2[i] * s2[j])
          for j in range(2)] for i in range(2)]
    g = [2 * (A * z * s1[i] + P * A * A * z * s2[i]) for i in range(2)]
    rows = [(F(1), F(0)), (F(-1), F(0)), (F(0), F(1)), (F(0), F(-1)),
            s1, tuple(-v for v in s1), s2, tuple(-v for v in s2)]
    bounds = [VMAX, VMAX, VMAX, VMAX, ZMAX - A*z, ZMAX + A*z,
              ZMAX - A*A*z, ZMAX + A*A*z]
    return h, g, rows, bounds


def cost(z, v):
    z1 = A*z + B*v[0]
    z2 = A*z1 + B*v[1]
    return z*z + R*v[0]*v[0] + z1*z1 + R*v[1]*v[1] + P*z2*z2


def solve_qp(z):
    """Enumerate 0, 1, or 2 independent active rows of the 8-row 2D QP.
    Every returned candidate is independently checked for primal/dual feasibility
    and stationarity. Strict PD H makes any such certificate the unique optimum.
    """
    assert abs(z) <= ZMAX
    h, g, rows, bounds = qp_data(z)
    assert h[0][0] > 0 and h[0][0]*h[1][1] - h[0][1]**2 > 0
    candidates = []
    for count in range(3):
        for active in combinations(range(8), count):
            mat = [h[i] + [rows[j][i] for j in active] for i in range(2)]
            mat += [list(rows[j]) + [F(0)]*count for j in active]
            rhs = [-v for v in g] + [bounds[j] for j in active]
            answer = linear_solve(mat, rhs)
            if answer is None:
                continue
            v, dual = answer[:2], answer[2:]
            if any(dot(row, v) > bound for row, bound in zip(rows, bounds)):
                continue
            if any(value < 0 for value in dual):
                continue
            stationarity = [dot(h[i], v) + g[i] +
                            sum((rows[j][i]*lam for j, lam in zip(active, dual)), F(0))
                            for i in range(2)]
            assert stationarity == [0, 0]
            assert all(dot(rows[j], v) == bounds[j] for j in active)
            candidates.append((cost(z, v), v, active, dual))
    assert candidates, 'No KKT certificate: teaching solver failed'
    value, v, active, dual = min(candidates, key=lambda item: item[0])
    return v, value, active, dual


def continuous_state(t, eta, cap=math.inf):
    """Exact convolution for x'= -x+min(cap,eta*exp(t-1)), x(0)=0."""
    switch = max(0.0, min(1.0, 1.0 + math.log(cap/eta))) if math.isfinite(cap) else 1.0
    if t <= switch:
        return eta * math.exp(-1.0) * math.sinh(t)
    at_switch = eta * math.exp(-1.0) * math.sinh(switch)
    return math.exp(-(t-switch))*at_switch + cap*(1-math.exp(-(t-switch)))


def continuous_cost(eta, cap=math.inf):
    switch = max(0.0, min(1.0, 1.0 + math.log(cap/eta))) if math.isfinite(cap) else 1.0
    first = eta*eta/2*(math.exp(2*(switch-1))-math.exp(-2))
    rest = 0.0 if switch == 1.0 else cap*cap*(1-switch)
    return (first+rest)/2


def rk4_endpoint(eta, cap, steps):
    # Split at the switch: the capped input derivative has a kink there.
    switch = max(0.0, min(1.0, 1.0+math.log(cap/eta))) if math.isfinite(cap) else 1.0
    x = 0.0
    for lo, hi in ((0.0, switch), (switch, 1.0)):
        if hi == lo:
            continue
        count = max(1, math.ceil((hi-lo)*steps))
        h = (hi-lo)/count
        def rhs(t, value):
            return -value + min(cap, eta*math.exp(t-1))
        for i in range(count):
            t = lo+i*h
            k1 = rhs(t, x)
            k2 = rhs(t+h/2, x+h*k1/2)
            k3 = rhs(t+h/2, x+h*k2/2)
            k4 = rhs(t+h, x+h*k3)
            x += h*(k1+2*k2+2*k3+k4)/6
    return x


def simulate(disturbances, z=F(3,5), e=F(1,3)):
    records = []
    for index, w in enumerate(disturbances):
        v, value, _, _ = solve_qp(z)
        u, x = v[0]-K*e, z+e
        assert abs(x) <= 1 and abs(u) <= 2 and abs(e) <= EPS
        z1 = A*z+B*v[0]
        shift = [v[1], -K*(A*z1+B*v[1])]
        shifted_value = cost(z1, shift)
        assert shifted_value == value - (z*z+R*v[0]*v[0])
        assert all(abs(control) <= VMAX for control in shift)
        _, next_value, _, _ = solve_qp(z1)
        assert next_value <= shifted_value
        next_e = CL*e+w
        next_x = A*x+B*u+w
        assert next_x == z1+next_e
        records.append([index, z, e, x, v[0], u, w, value])
        z, e = z1, next_e
    records.append([len(disturbances), z, e, z+e, F(0), F(0), F(0), solve_qp(z)[1]])
    assert abs(e) <= EPS and abs(z+e) <= 1
    return records


def svg_plot(path, title, panels):
    width, height = 920, 90+260*len(panels)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#fafafa"/>',
           f'<text x="60" y="30" font-family="sans-serif" font-size="19">{html.escape(title)}</text>']
    for index, (label, bounds, curves, lines) in enumerate(panels):
        ytop, h = 68+260*index, 170
        xmin, xmax, ymin, ymax = bounds
        def coords(x, y):
            return 70+790*(x-xmin)/(xmax-xmin), ytop+h-h*(y-ymin)/(ymax-ymin)
        out += [f'<text x="70" y="{ytop-12}" font-family="sans-serif" font-size="14">{html.escape(label)}</text>',
                f'<rect x="70" y="{ytop}" width="790" height="{h}" fill="white" stroke="#b6b6b6"/>']
        for value in (ymin, 0, ymax):
            xp, yp = coords(xmin, value)
            if ymin <= value <= ymax:
                out += [f'<line x1="70" x2="860" y1="{yp:.3f}" y2="{yp:.3f}" stroke="#e0e0e0"/>',
                        f'<text x="22" y="{yp+5:.3f}" font-family="sans-serif" font-size="12">{value:.2g}</text>']
        for value, color in lines:
            _, yp = coords(xmin,value)
            out += [f'<line x1="70" x2="860" y1="{yp:.3f}" y2="{yp:.3f}" stroke="{color}" stroke-dasharray="5 4"/>']
        for j, (name, color, points) in enumerate(curves):
            dash = ('', '7 5', '2 4')[j % 3]
            points_text = ' '.join(f'{px:.3f},{py:.3f}' for px,py in (coords(x,y) for x,y in points))
            out += [f'<polyline points="{points_text}" fill="none" stroke="{color}" stroke-width="2"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>']
        for j, (name, color, _) in enumerate(curves):
            dash = ('', '7 5', '2 4')[j % 3]
            out += [f'<line x1="{70+260*j}" x2="{95+260*j}" y1="{ytop+h+21}" y2="{ytop+h+21}" stroke="{color}" stroke-width="2"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>',
                    f'<text x="{100+260*j}" y="{ytop+h+25}" font-family="sans-serif" font-size="12" fill="{color}">{html.escape(name)}</text>']
        out += [f'<text x="70" y="{ytop+h+47}" font-family="sans-serif" font-size="12">{xmin:g}</text>',
                f'<text x="830" y="{ytop+h+47}" font-family="sans-serif" font-size="12">{xmax:g}</text>']
    out.append('</svg>')
    path.write_text('\n'.join(out)+'\n', encoding='utf-8')


def as_fraction(value):
    return str(value)


def main():
    assets = Path(__file__).resolve().parent/'assets'
    assets.mkdir(exist_ok=True)
    gramian = (1-math.exp(-2))/2
    eta = 1/gramian
    lo, hi = 2.0, 2*math.e
    for _ in range(80):
        middle = (lo+hi)/2
        if continuous_state(1, middle, 2) < 1:
            lo = middle
        else:
            hi = middle
    capped_eta = (lo+hi)/2
    switch = 1+math.log(2/capped_eta)
    errors = [{'steps_per_unit': steps,
               'uncapped_error': abs(rk4_endpoint(eta, math.inf, steps)-1),
               'capped_error': abs(rk4_endpoint(capped_eta, 2, steps)-1)}
              for steps in (20,40,80)]
    assert errors[-1]['uncapped_error'] < 1e-9 and errors[-1]['capped_error'] < 1e-9
    qp, value, active, dual = solve_qp(F(3,5))
    assert qp == [F(-4,3), F(-4,3)]
    h,g,rows,bounds = qp_data(F(3,5))
    unconstrained = linear_solve(h, [-v for v in g])
    constant = simulate([B]*24)
    alternating = simulate([B if index%2==0 else -B for index in range(24)])
    corner_nodes = 0
    # Finite 6-step extreme sequences; interval algebra, not this tree, proves all-time invariance.
    for sequence in product((-B,B), repeat=6):
        simulate(sequence)
        corner_nodes += len(sequence)
    assert CL*EPS+B == EPS
    assert P*(CL*CL-1) == -(Q+R*K*K)
    total_bound = F(1,50)*1+F(1,100)*2+(B+F(1,100))*1
    widened_eps = total_bound/(1-abs(CL))
    widened_z, widened_v = 1-widened_eps, 2-K*widened_eps
    assert (total_bound,widened_eps,widened_z,widened_v) == (F(3,20),F(1,2),F(1,2),F(1))
    # Exhaust boundary conditions for uncertain a,b,d on the widened tube with terminal law.
    uncertain_corners = 0
    for z,e,da,db,d in product((-widened_z,widened_z),(-widened_eps,widened_eps),
                               (-F(1,50),F(1,50)),(-F(1,100),F(1,100)),(-F(1),F(1))):
        v, x = -K*z, z+e
        u = v-K*e
        x1 = (A+da)*x+(B+db)*(u+d)
        z1 = CL*z
        assert abs(x)<=1 and abs(u)<=2 and abs(x1-z1)<=widened_eps and abs(x1)<=1
        uncertain_corners += 1
    failure_x = A*1+B*(-2)+F(1,2)
    assert failure_x == F(6,5)
    summary = {'continuous': {'normalized_horizon':1, 'physical_horizon_s':10,
                             'gramian':gramian, 'eta_unbounded':eta,
                             'v_initial_W':eta/math.e, 'v_final_W':eta,
                             'cost_unbounded':continuous_cost(eta),
                             'U_1_5_reachable_max_K':1.5*(1-math.exp(-1)),
                             'naive_clip_terminal_K':continuous_state(1,eta,2),
                             'eta_capped':capped_eta, 'switch_s':10*switch,
                             'capped_terminal_K':continuous_state(1,capped_eta,2),
                             'cost_capped':continuous_cost(capped_eta,2), 'rk4_errors':errors},
               'discrete':{'sample_period_s':10*math.log(10/9),'a':str(A),'b_K_per_W':str(B),
                           'f':str(CL),'epsilon_K':str(EPS),'Zmax_K':str(ZMAX),
                           'Vmax_W':str(VMAX),'terminal_P':str(P),
                           'z0':str(F(3,5)), 'v_optimal':[str(v) for v in qp],
                           'z1':str(A*F(3,5)+B*qp[0]),
                           'z2':str(A*(A*F(3,5)+B*qp[0])+B*qp[1]),
                           'cost_optimal':str(value),'cost_float':float(value),
                           'active_rows_zero_based':list(active),'dual':[str(v) for v in dual],
                           'unconstrained_v':[str(v) for v in unconstrained],
                           'H':[[str(v) for v in row] for row in h],'g':[str(v) for v in g],
                           'KKT_stationarity_exact':True,'terminal_identity_exact':True,
                           'finite_corner_sequences':64,'finite_corner_steps':corner_nodes,
                           'constant_final_x_K':float(constant[-1][3]),
                           'constant_final_z_K':float(constant[-1][1]),
                           'bound_break_one_step_x_K':str(failure_x)},
               'model_error':{'effective_wmax_K':str(total_bound),'epsilon_K':str(widened_eps),
                              'Zmax_K':str(widened_z),'Vmax_W':str(widened_v),
                              'finite_boundary_cases':uncertain_corners}}
    (assets/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (assets/'tube.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle)
        writer.writerow(['scenario','k','nominal_z_K','error_e_K','actual_x_K','nominal_v_W','actual_u_W','w_K','nominal_cost'])
        for name,records in [('constant',constant),('alternating',alternating)]:
            writer.writerows([name]+[str(row[0])]+[f'{float(v):.12g}' for v in row[1:]] for row in records)
    continuous_rows=[]
    for i in range(201):
        tau=i/200
        continuous_rows.append([10*tau, eta*math.exp(tau-1), min(2,eta*math.exp(tau-1)),
                                min(2,capped_eta*math.exp(tau-1)), continuous_state(tau,eta),
                                continuous_state(tau,eta,2),continuous_state(tau,capped_eta,2)])
    with (assets/'continuous.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle)
        writer.writerow(['time_s','unbounded_u_W','naive_clipped_u_W','optimal_capped_u_W','unbounded_x_K','naive_clipped_x_K','optimal_capped_x_K'])
        writer.writerows([[f'{v:.12g}' for v in row] for row in continuous_rows])
    colors=['#146c94','#a64623','#2a7d45']
    names=['Unbounded optimum','Clip old optimum','Reoptimized cap U=2 W']
    svg_plot(assets/'terminal-control.svg','Fixed terminal x(10 s)=1 K: clipping changes feasibility',[
        ('u [W], continuous input; physical time [s]',(0,10,0,2.6),
         [(name,color,[(r[0],r[j+1]) for r in continuous_rows]) for j,(name,color) in enumerate(zip(names,colors))],[(2,'#555555')]),
        ('x [K]; at 10 s: clipped=0.978818 K, reoptimized=1 K; physical time [s]',(0,10,0,1.1),
         [(name,color,[(r[0],r[j+4]) for r in continuous_rows]) for j,(name,color) in enumerate(zip(names,colors))],[(1,'#555555')])])
    svg_plot(assets/'tube.svg','Bounded w=+0.1 K each sample; e(0)=1/3 K',[
        ('Temperature deviation [K]; sample k (Ts=1.053605 s)',(0,24,-1.1,1.1),
         [('Nominal z','#146c94',[(r[0],float(r[1])) for r in constant]),
          ('Actual x','#2a7d45',[(r[0],float(r[3])) for r in constant]),
          ('Upper tube z+1/3','#a64623',[(r[0],float(r[1]+EPS)) for r in constant])],[(1,'#555555'),(-1,'#555555')]),
        ('Actual input u [W]; sample k (last state has no action)',(0,23,-2.2,2.2),
         [('Constant disturbance','#146c94',[(r[0],float(r[5])) for r in constant[:-1]]),
          ('Alternating disturbance','#a64623',[(r[0],float(r[5])) for r in alternating[:-1]])],[(2,'#555555'),(-2,'#555555')])])
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(f'PASS: continuous RK4, exact QP KKT, terminal shift, tube/model-error checks; serial Python {sys.version.split()[0]}')
    print(f'RU_MAXRSS_BYTES={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}')


if __name__ == '__main__':
    main()
```
