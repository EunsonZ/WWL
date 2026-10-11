#!/usr/bin/env python3
"""Two addressable spin-1/2 systems; stdlib only, fixed row-major basis.
Matrices use units S/hbar, J/hbar, K=(S_A dot S_B)/hbar**2.
Results and SVGs always live beside this source, independent of cwd.
"""
import cmath
import csv
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def eye(n):
    return [[complex(i == j) for j in range(n)] for i in range(n)]


def add(*matrices):
    return [[sum(m[i][j] for m in matrices) for j in range(len(matrices[0][0]))]
            for i in range(len(matrices[0]))]


def scale(a, m):
    return [[a * x for x in row] for row in m]


def dagger(m):
    return [[m[j][i].conjugate() for j in range(len(m))] for i in range(len(m[0]))]


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def mv(m, v):
    return [sum(a * b for a, b in zip(row, v)) for row in m]


def dot(v, w):
    return sum(a.conjugate() * b for a, b in zip(v, w))


def outer(v):
    return [[a * b.conjugate() for b in v] for a in v]


def kron(a, b):
    return [[a[i // len(b)][j // len(b[0])] * b[i % len(b)][j % len(b[0])]
             for j in range(len(a[0]) * len(b[0]))] for i in range(len(a) * len(b))]


def trace(m):
    return sum(m[i][i] for i in range(len(m)))


def error(a, b):
    if isinstance(a[0], list):
        return max(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))
    return max(abs(x - y) for x, y in zip(a, b))


def comm(a, b):
    return add(mm(a, b), scale(-1, mm(b, a)))


def partial_a(rho):
    return [[sum(rho[2 * i + j][2 * k + j] for j in range(2))
             for k in range(2)] for i in range(2)]


def exp_taylor(a):
    # Scaling and squaring, then <=80 Taylor terms at ||a_scaled||inf <= 1.
    norm = max(sum(abs(x) for x in row) for row in a)
    squarings = max(0, math.ceil(math.log2(norm))) if norm > 0 else 0
    b = scale(2.0 ** (-squarings), a)
    total = eye(len(a))
    term = eye(len(a))
    for n in range(1, 81):
        term = scale(1 / n, mm(term, b))
        total = add(total, term)
        if max(abs(x) for row in term for x in row) < 1e-17:
            break
    else:
        raise ArithmeticError('Taylor series did not converge')
    for _ in range(squarings):
        total = mm(total, total)
    return total


def jacobi_eigenvalues(m):
    # A separate real symmetric diagonalizer; no coupled vectors supplied.
    a = [[x.real for x in row] for row in m]
    if max(abs(x.imag) for row in m for x in row) > 1e-15:
        raise ValueError('Jacobi routine requires a real matrix')
    for _ in range(100):
        p, q = max(((i, j) for i in range(len(a)) for j in range(i + 1, len(a))),
                   key=lambda ij: abs(a[ij[0]][ij[1]]))
        if abs(a[p][q]) < 1e-15:
            return sorted(a[i][i] for i in range(len(a)))
        phi = 0.5 * math.atan2(2 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(phi), math.sin(phi)
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        for k in range(len(a)):
            if k not in (p, q):
                akp, akq = a[k][p], a[k][q]
                a[k][p] = a[p][k] = c * akp - s * akq
                a[k][q] = a[q][k] = s * akp + c * akq
        a[p][p] = c * c * app - 2 * c * s * apq + s * s * aqq
        a[q][q] = s * s * app + 2 * c * s * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
    raise ArithmeticError('Jacobi iteration did not converge')


def pack(value):
    if isinstance(value, complex):
        return [value.real, value.imag]
    if isinstance(value, list):
        return [pack(v) for v in value]
    if isinstance(value, dict):
        return {k: pack(v) for k, v in value.items()}
    return value


def svg_start(width, height, title, desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc>',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            '<g font-family="sans-serif" fill="#172b4d" font-size="15">']


def text_svg(parts, x, y, value, size=15, anchor='start'):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{html.escape(value)}</text>')


def plot_svg(path, rows, frequency_hz):
    parts = svg_start(900, 860, 'Exchange changes local predictions while total spin probabilities stay fixed',
                      'Three panels from the same Born and partial trace matrix calculation. Horizontal variable theta=Jc t/hbar, radians. Vertical axes dimensionless. Fixed initial states |01> and |+x,0>.')
    text_svg(parts, 45, 32, 'Two spin-1/2 systems: isotropic exchange, no external field', 21)
    frequency_mhz = frequency_hz / 1e6
    swap_time_microseconds = 1e6 / (2 * frequency_hz)
    text_svg(parts, 45, 58, f'theta = Jc t / hbar; Jc / h = {frequency_mhz:g} MHz; theta = pi at t = {swap_time_microseconds:g} microsecond', 15)
    panels = [
        ('Initial |01>: z,z probabilities and A purity', [('p01', '#1261a0', ''), ('p10', '#b14413', '7 4'), ('purity_01', '#58459c', '2 4')]),
        ('Initial |+x,0>: A local Born probabilities', [('p_x_plus_changed', '#1261a0', ''), ('p_z_plus_changed', '#b14413', '7 4'), ('p_y_plus_changed', '#58459c', '2 4')]),
        ('Initial |+x,0>: total spin probabilities and A purity', [('p_triplet_changed', '#1261a0', ''), ('p_singlet_changed', '#b14413', '7 4'), ('purity_changed', '#58459c', '2 4')])
    ]
    for index, (title, curves) in enumerate(panels):
        top, left, width, height = 105 + 246 * index, 95, 730, 164
        text_svg(parts, 45, top - 17, title, 18)
        for v in [0, 0.25, 0.5, 0.75, 1]:
            y = top + height * (1 - v)
            parts.append(f'<line x1="{left}" y1="{y}" x2="{left+width}" y2="{y}" stroke="#dce2e9"/>')
            text_svg(parts, left - 12, y + 5, f'{v:g}', 13, 'end')
        for k in range(5):
            x = left + width * k / 4
            parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top+height}" stroke="#e6eaf0"/>')
            text_svg(parts, x, top + height + 21, ['0', 'pi/2', 'pi', '3pi/2', '2pi'][k], 13, 'middle')
        for n, (key, color, dash) in enumerate(curves):
            points = ' '.join(f'{left+width*r["theta_rad"]/(2*math.pi):.3f},{top+height*(1-r[key]):.3f}' for r in rows)
            parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.8" stroke-dasharray="{dash}"/>')
            lx = left + n * 245
            parts.append(f'<line x1="{lx}" y1="{top+height+43}" x2="{lx+32}" y2="{top+height+43}" stroke="{color}" stroke-width="3" stroke-dasharray="{dash}"/>')
            text_svg(parts, lx+40, top+height+48, key.replace('_changed','').replace('_01',''), 13)
    text_svg(parts, 450, 849, 'theta (rad) | mathematical prediction, no hardware measurements', 14, 'middle')
    parts.append('</g></svg>')
    path.write_text('\n'.join(parts) + '\n')


def spectrum_svg(path, states, energy_ratios):
    parts = svg_start(860, 400, 'Coupled basis, total spin and exchange energy',
                      'Four coupled states form one j=1 triplet and one j=0 singlet. Energy divided by Jc is one quarter or minus three quarters. Assumes Jc positive; no position space model.')
    text_svg(parts, 35, 34, 'Coupled states and energy: Jc > 0', 21)
    for i, (name, j, m, exchange) in enumerate(states):
        x, y = 80 + i * 195, 105 if j else 250
        parts.append(f'<line x1="{x}" y1="{y}" x2="{x+135}" y2="{y}" stroke="#1261a0" stroke-width="4"/>')
        text_svg(parts, x, y - 15, name, 17)
        text_svg(parts, x, y + 28, f'j={j}, m={m}', 15)
        text_svg(parts, x, y + 53, f'P={exchange:+d}', 15)
        text_svg(parts, x, y + 78, f'E/Jc={energy_ratios[i]:g}', 15)
    text_svg(parts, 35, 385, 'The repeated triplet energy is degeneracy, not three copies of the same state.', 15)
    parts.append('</g></svg>')
    path.write_text('\n'.join(parts) + '\n')


def main():
    inp = json.loads((ROOT / 'inputs.json').read_text())
    if inp['basis'] != ['00', '01', '10', '11']:
        raise ValueError('basis must remain 00,01,10,11')
    if not (math.isfinite(inp['exchange_frequency_Hz']) and inp['exchange_frequency_Hz'] > 0):
        raise ValueError('default time-axis frequency must be positive and finite; sign reversal is reported separately')
    tol = inp['tolerance_dimensionless']
    i2, i4 = eye(2), eye(4)
    pauli = [[[0j, 1+0j], [1+0j, 0j]], [[0j, -1j], [1j, 0j]], [[1+0j, 0j], [0j, -1+0j]]]
    a = [scale(0.5, kron(s, i2)) for s in pauli]
    b = [scale(0.5, kron(i2, s)) for s in pauli]
    j = [add(x, y) for x, y in zip(a, b)]
    j2 = add(*(mm(x, x) for x in j))
    jp, jm = add(j[0], scale(1j, j[1])), add(j[0], scale(-1j, j[1]))
    k = add(*(mm(x, y) for x, y in zip(a, b)))
    swap = [[1+0j,0j,0j,0j], [0j,0j,1+0j,0j], [0j,1+0j,0j,0j], [0j,0j,0j,1+0j]]
    # Construct the triplet by lowering; construct singlet by orthogonality in M=0.
    tplus = [1+0j, 0j, 0j, 0j]
    tzero = [x / math.sqrt(2) for x in mv(jm, tplus)]
    tminus = [x / math.sqrt(2) for x in mv(jm, tzero)]
    singlet = [0j, 1/math.sqrt(2)+0j, -1/math.sqrt(2)+0j, 0j]
    vectors = [tplus, tzero, tminus, singlet]
    labels = [('t+',1,1,1), ('t0',1,0,1), ('t-',1,-1,1), ('s',0,0,-1)]
    q = [[v[row] for v in vectors] for row in range(4)]
    pt = add(*(outer(v) for v in vectors[:3]))
    ps = outer(singlet)
    residuals = {}
    check_count = 0
    def check(name, residual):
        nonlocal check_count
        check_count += 1
        group = re.sub(r'_[-0-9.]+$', '', name)
        residuals[group] = max(residuals.get(group, 0), float(residual))
        if residual > tol:
            raise AssertionError(f'{name}: {residual} exceeds {tol}')
    check('unitary_coupled_basis', error(mm(dagger(q),q),i4))
    check('projector_completeness',error(add(pt,ps),i4))
    check('K_direct_matrix', error(k, scale(0.25, [[1+0j,0j,0j,0j],[0j,-1+0j,2+0j,0j],[0j,2+0j,-1+0j,0j],[0j,0j,0j,1+0j]])))
    check('K_from_J_squared',error(k,scale(0.5,add(j2,scale(-1.5,i4)))))
    check('swap_from_K',error(swap,add(scale(2,k),scale(0.5,i4))))
    check('Hermitian_H_ratio',error(k,dagger(k)))
    check('total_algebra',max(error(comm(j[x],j[y]),scale(1j,j[z])) for x,y,z in ((0,1,2),(1,2,0),(2,0,1))))
    check('isotropic_total_conservation',max(error(comm(k,x),scale(0,i4)) for x in j))
    check('local_Casimir',max(error(add(*(mm(x,x) for x in v)),scale(0.75,i4)) for v in (a,b)))
    for idx, ((name,jj,m,parity),v) in enumerate(zip(labels,vectors)):
        check(f'{name}_J2',error(mv(j2,v),[jj*(jj+1)*x for x in v]))
        check(f'{name}_Jz',error(mv(j[2],v),[m*x for x in v]))
        check(f'{name}_swap',error(mv(swap,v),[parity*x for x in v]))
        check(f'{name}_K',error(mv(k,v),[(0.25 if jj else -0.75)*x for x in v]))
    check('singlet_ladders',max(max(abs(x) for x in mv(op,singlet)) for op in (jp,jm)))
    eigenvalues = jacobi_eigenvalues(k)
    check('Jacobi_spectrum',error(eigenvalues,[-0.75,0.25,0.25,0.25]))
    psi01 = [0j,1+0j,0j,0j]
    changed = [1/math.sqrt(2)+0j,0j,1/math.sqrt(2)+0j,0j]
    mix = scale(0.5,add(outer(psi01),outer([0j,0j,1+0j,0j])))
    checkpoints, rows = [], []
    def sample(theta, detailed=False):
        u = add(scale(cmath.exp(-1j*theta/4),pt),scale(cmath.exp(3j*theta/4),ps))
        check(f'U_unitarity_{theta:.9g}',error(mm(dagger(u),u),i4))
        row = {'theta_rad':theta, 'time_s':theta/(2*math.pi*inp['exchange_frequency_Hz'])}
        details = {'theta_rad':theta,'time_s':row['time_s']}
        for name, initial in [('01',psi01),('changed',changed)]:
            psi = mv(u,initial)
            rho = outer(psi)
            ra = partial_a(rho)
            check(f'{name}_norm_{theta:.9g}',abs(dot(psi,psi)-1))
            check(f'{name}_partial_trace_{theta:.9g}',abs(trace(ra)-1))
            purity = trace(mm(ra,ra)).real
            c,s = math.cos(theta/2),math.sin(theta/2)
            analytic_ra = [[c*c+0j,0j],[0j,s*s+0j]] if name=='01' else scale(0.5,[[1+s*s+0j,c*cmath.exp(-1j*theta/2)],[c*cmath.exp(1j*theta/2),c*c+0j]])
            check(f'{name}_analytic_rho_A_{theta:.9g}',error(ra,analytic_ra))
            if name=='01':
                row.update(p01=abs(psi[1])**2,p10=abs(psi[2])**2,purity_01=purity,XY_01=dot(psi,mv(kron(pauli[0],pauli[1]),psi)).real)
                check(f'01_XY_{theta:.9g}',abs(row['XY_01']-math.sin(theta)))
                check(f'01_Born_{theta:.9g}',max(abs(row['p01']-c*c),abs(row['p10']-s*s)))
            else:
                row['purity_changed'] = purity
                row['p_triplet_changed'] = dot(psi,mv(pt,psi)).real
                row['p_singlet_changed'] = dot(psi,mv(ps,psi)).real
                for axis,sigma in zip('xyz',pauli):
                    prob = trace(mm(ra,scale(0.5,add(i2,sigma)))).real
                    row[f'p_{axis}_plus_changed'] = prob
                check(f'changed_Born_xyz_{theta:.9g}',max(abs(row['p_x_plus_changed']-(3+math.cos(theta))/4),abs(row['p_z_plus_changed']-(3-math.cos(theta))/4),abs(row['p_y_plus_changed']-(0.5+math.sin(theta)/4))))
                check(f'changed_purity_{theta:.9g}',abs(purity-(1-math.sin(theta)**2/8)))
                check(f'changed_total_spin_{theta:.9g}',max(abs(row['p_triplet_changed']-0.75),abs(row['p_singlet_changed']-0.25)))
            if detailed:
                details[name] = {'psi':psi,'rho_A':ra,'purity_A':purity,'p_triplet':dot(psi,mv(pt,psi)).real,'p_singlet':dot(psi,mv(ps,psi)).real}
            phase = cmath.exp(1j*inp['global_phase_rad'])
            check(f'{name}_global_phase_{theta:.9g}',error(outer([phase*x for x in psi]),rho))
        if detailed:
            check(f'exponential_direct_{theta:.9g}',error(exp_taylor(scale(-1j*theta,k)),u))
            evolved_mix = mm(mm(u,mix),dagger(u))
            check(f'mixed_stationary_{theta:.9g}',error(evolved_mix,mix))
            details['mixed_rho_A'] = partial_a(evolved_mix)
            details['mixed_XY'] = trace(mm(evolved_mix,kron(pauli[0],pauli[1]))).real
            check(f'mixed_XY_zero_{theta:.9g}',abs(details['mixed_XY']))
        return row,details
    for f in inp['checkpoint_theta_over_pi']:
        _,details = sample(f*math.pi,True)
        checkpoints.append(details)
    for n in range(inp['plot_intervals']+1):
        row,_ = sample(2*math.pi*n/inp['plot_intervals'])
        rows.append(row)
    _,negative_theta = sample(-math.pi/2, True)
    h=inp['h_J_s']; hbar=h/(2*math.pi); jc=h*inp['exchange_frequency_Hz']
    output=ROOT/'assets'; output.mkdir(exist_ok=True)
    energy_ratios = [dot(v,mv(k,v)).real for v in vectors]
    report = {'model':'two addressable spin-1/2 systems, isotropic exchange', 'basis':inp['basis'],
              'units':{'J_and_S':'hbar','K':'dimensionless','theta':'rad','time':'s','energies':'J','complex_encoding':'[real,imag]'},
              'constants':{'h_J_s':h,'hbar_J_s':hbar,'Jc_J':jc,'Jc_over_h_Hz':inp['exchange_frequency_Hz'],'swap_time_s':1/(2*inp['exchange_frequency_Hz'])},
              'matrices':{'Jz_over_hbar':j[2],'Jplus_over_hbar':jp,'Jminus_over_hbar':jm,'J2_over_hbar2':j2,'K':k,'P':swap,'Q_columns_coupled_basis':q},
              'spectrum':{'K_Jacobi_eigenvalues':eigenvalues,'coupled_order_E_over_Jc':energy_ratios,'coupled_order_E_J':[jc*x for x in energy_ratios]},
              'sign_reversal_at_positive_time':{'time_s':1/(4*inp['exchange_frequency_Hz']), 'Jc_over_h_Hz':-inp['exchange_frequency_Hz'], 'theta_rad':-math.pi/2, 'rho_A_01':negative_theta['01']['rho_A'], 'rho_A_changed':negative_theta['changed']['rho_A']},
              'checkpoints':checkpoints,'tolerance_dimensionless':tol,'max_residual':max(residuals.values()),'residuals':residuals,
              'boundary':'author calculation; independent review, Obsidian display, hardware and learner evidence separate'}
    (output/'checks.json').write_text(json.dumps(pack(report),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with (output/'exchange.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    plot_svg(output/'exchange.svg',rows,inp['exchange_frequency_Hz'])
    spectrum_svg(output/'coupled-spectrum.svg',labels,energy_ratios)
    print(json.dumps({'max_residual':report['max_residual'],'evaluations':check_count, 'residual_groups':len(residuals),'samples':len(rows),'swap_time_s':report['constants']['swap_time_s']},indent=2))


if __name__ == '__main__':
    main()
