#!/usr/bin/env python3
"""Small standard-library computations for lessons 06/07; no hardware data."""
import cmath
import json
import math
from pathlib import Path

H = 6.62607015e-34
HBAR = H / (2 * math.pi)
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SAMPLES = 400
SUBSTEPS = (50, 100, 200)


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def mv(a, v):
    return [sum(x * y for x, y in zip(row, v)) for row in a]


def dagger(a):
    return [[a[j][i].conjugate() for j in range(len(a))]
            for i in range(len(a[0]))]


def identity(n):
    return [[complex(i == j) for j in range(n)] for i in range(n)]


def difference(a, b):
    return [[x - y for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def scale(c, a):
    return [[c * x for x in row] for row in a]


def maxabs(a):
    return max(abs(x) for row in a for x in row)


def norm(v):
    return sum(abs(x) ** 2 for x in v)


def require(name, value, limit):
    if not value <= limit:
        raise AssertionError(f"{name}: {value} > {limit}")


def spin_one():
    q = 1 / math.sqrt(2)
    jx = [[0j, q, 0j], [q, 0j, q], [0j, q, 0j]]
    jy = [[0j, -1j*q, 0j], [1j*q, 0j, -1j*q], [0j, 1j*q, 0j]]
    jz = [[1+0j, 0j, 0j], [0j, 0j, 0j], [0j, 0j, -1+0j]]
    js = (jx, jy, jz)
    comm_error = max(maxabs(difference(difference(mm(a, b), mm(b, a)), scale(1j, c)))
                     for a, b, c in ((jx,jy,jz), (jy,jz,jx), (jz,jx,jy)))
    casimir = [[sum(mm(j, j)[i][k] for j in js) for k in range(3)] for i in range(3)]
    casimir_error = maxabs(difference(casimir, scale(2, identity(3))))
    beta = math.pi / 3
    jy2 = mm(jy, jy)
    u = [[complex(i == k) - 1j*math.sin(beta)*jy[i][k]
          + (math.cos(beta)-1)*jy2[i][k] for k in range(3)] for i in range(3)]
    rotated = mv(u, [0j, 1+0j, 0j])
    hand = [-math.sin(beta)/math.sqrt(2), math.cos(beta), math.sin(beta)/math.sqrt(2)]
    vector_error = max(abs(x-y) for x,y in zip(rotated, hand))
    unitarity_error = maxabs(difference(mm(dagger(u), u), identity(3)))
    for name, err in (("spin commutator",comm_error),("spin casimir",casimir_error),
                      ("rotation vector",vector_error),("unitarity",unitarity_error)):
        require(name, err, 1e-12)
    # Actual matrix products check that a field tilted toward x breaks Jz conservation.
    perturb_comm = difference(mm(jx,jz), mm(jz,jx))
    broken_error = maxabs(difference(perturb_comm, scale(-1j,jy)))
    require("broken symmetry sign", broken_error, 1e-12)
    return {"basis_m": [1,0,-1], "beta_rad": beta,
            "probabilities": [abs(x)**2 for x in rotated],
            "Jz_mean_over_hbar": abs(rotated[0])**2-abs(rotated[2])**2,
            "Jz_variance_over_hbar2": abs(rotated[0])**2+abs(rotated[2])**2,
            "commutator_error": comm_error, "casimir_error": casimir_error,
            "unitarity_error": unitarity_error, "vector_error": vector_error,
            "broken_symmetry_commutator_error": broken_error}


def rotor():
    # Integrate exponentials directly on a periodic 1024-point grid, modes -2..2.
    points = 1024
    dphi = 2*math.pi/points
    modes = range(-2,3)
    errors = []
    norm_sum = 0.0
    for i in range(points):
        phi = i*dphi
        chi = (cmath.exp(1j*phi)+cmath.exp(-1j*phi))/math.sqrt(4*math.pi)
        norm_sum += abs(chi)**2*dphi
    for n in modes:
        for np in modes:
            integral = sum(cmath.exp(1j*(n-np)*i*dphi)*math.cos(i*dphi)
                           for i in range(points))/points
            expected = .5 if abs(n-np) == 1 else 0.0
            errors.append(abs(integral-expected))
    require("rotor norm", abs(norm_sum-1), 1e-12)
    require("rotor cos selection", max(errors), 1e-12)
    return {"I_kg_m2": 1e-46, "E1_J": HBAR**2/(2e-46),
            "mode_window_for_matrix_elements": [-2,2], "quadrature_points": points,
            "norm_error": abs(norm_sum-1), "cos_matrix_element_error": max(errors),
            "scope": "selected matrix elements, not a full rotor spectrum solver"}


def pauli_action(v, bx, by, bz):
    a,b = v
    return [bz*a+(bx-1j*by)*b, (bx+1j*by)*a-bz*b]


def evolve_constant(v, bx, by, bz, dt):
    """Exact exp[-i dt (b dot sigma)/2] on a two-entry complex vector."""
    size = math.sqrt(bx*bx+by*by+bz*bz)
    if size == 0:
        return list(v)
    c = math.cos(size*dt/2)
    s = -1j*math.sin(size*dt/2)/size
    bv = pauli_action(v,bx,by,bz)
    return [c*x+s*y for x,y in zip(v,bv)]


def drive_trajectory(epsilon, kind, substeps, drive_ratio=1.0):
    # tau=omega0*t, omega0 scaled to 1; real units restored in the report.
    # Fixed Hamiltonian at each time midpoint; no renormalization is performed.
    total_tau = 2*math.pi/epsilon
    dt = total_tau/(SAMPLES*substeps)
    state = [0j,1+0j]
    probs = [0.0]
    states = [list(state)]
    largest_norm_error = 0.0
    for sample in range(SAMPLES):
        for j in range(substeps):
            tau = (sample*substeps+j+.5)*dt
            angle = drive_ratio*tau
            if kind == "linear":
                bx,by = 2*epsilon*math.cos(angle),0.0
            else:
                bx,by = epsilon*math.cos(angle),epsilon*math.sin(angle)
            state = evolve_constant(state,bx,by,1.0,dt)
        probs.append(abs(state[0])**2)
        states.append(list(state))
        largest_norm_error = max(largest_norm_error,abs(norm(state)-1))
    require("drive norm", largest_norm_error, 1e-10)
    require("drive probability interval", max(max(probs)-1,-min(probs),0), 1e-10)
    return probs,largest_norm_error,states


def compare_drive(epsilon, kind="linear", drive_ratio=1.0):
    trajectories = [drive_trajectory(epsilon,kind,s,drive_ratio) for s in SUBSTEPS]
    coarse,medium,fine = [t[0] for t in trajectories]
    d01 = max(abs(a-b) for a,b in zip(coarse,medium))
    d12 = max(abs(a-b) for a,b in zip(medium,fine))
    require("finest step comparison",d12,5e-6)
    if d12 > 1e-12:
        require("midpoint convergence ratio",d12/d01,.35)
    delta = 1-drive_ratio
    r = math.hypot(delta,epsilon)
    phases = [2*math.pi*i/SAMPLES for i in range(SAMPLES+1)]
    oracle = [epsilon**2/r**2*math.sin(r*x/(2*epsilon))**2 for x in phases]
    max_error = max(abs(a-b) for a,b in zip(fine,oracle))
    if kind == "circular":
        require("circular analytic probability",max_error,5e-6)
        vector_error = 0.0
        for phase,state in zip(phases,trajectories[-1][2]):
            tau = phase/epsilon
            chi = evolve_constant([0j,1+0j],epsilon,0,delta,tau)
            exact = [cmath.exp(-1j*drive_ratio*tau/2)*chi[0],
                     cmath.exp(1j*drive_ratio*tau/2)*chi[1]]
            vector_error = max(vector_error,max(abs(a-b) for a,b in zip(state,exact)))
        require("circular full vector including lab phase",vector_error,5e-6)
    omega0 = 2*math.pi*1e6
    result = {"kind":kind, "Omega_over_omega0":epsilon,
              "omega_over_omega0":drive_ratio, "omega0_rad_per_s":omega0,
              "Omega_rad_per_s":epsilon*omega0,
              "end_time_s":2*math.pi/(epsilon*omega0),
              "samples":SAMPLES+1,"substeps_per_sample":list(SUBSTEPS),
              "max_coarse_medium_probability_difference":d01,
              "max_medium_fine_probability_difference":d12,
              "largest_norm_error":max(t[1] for t in trajectories),
              "max_sample_probability_difference_from_formula":max_error,
              "P_plus_at_pi_over_Omega":fine[SAMPLES//2],
              "formula_P_plus_at_pi_over_Omega":oracle[SAMPLES//2]}
    if kind == "circular":
        result["max_vector_error_including_lab_phase"] = vector_error
    return result,(phases,fine,oracle)


def rotating_frame_identity():
    # Independently multiply R-dagger H R and the derivative term at five angles.
    errors = []
    epsilon,drive_ratio = .2,.9
    for tau in (0,.25,1,2,5):
        angle = drive_ratio*tau
        r = [[cmath.exp(-1j*angle/2),0j],[0j,cmath.exp(1j*angle/2)]]
        for kind in ("circular","linear"):
            if kind == "circular":
                bx,by = epsilon*math.cos(angle),epsilon*math.sin(angle)
                expected_bx,expected_by = epsilon,0
            else:
                bx,by = 2*epsilon*math.cos(angle),0
                expected_bx = epsilon*(1+math.cos(2*angle))
                expected_by = -epsilon*math.sin(2*angle)
            h = [[.5+0j,(bx-1j*by)/2],[(bx+1j*by)/2,-.5+0j]]
            hr = mm(mm(dagger(r),h),r)
            hr[0][0] -= drive_ratio/2
            hr[1][1] += drive_ratio/2
            target = [[(1-drive_ratio)/2+0j,(expected_bx-1j*expected_by)/2],
                      [(expected_bx+1j*expected_by)/2,-(1-drive_ratio)/2+0j]]
            errors.append(maxabs(difference(hr,target)))
    require("rotating frame identity",max(errors),1e-12)
    return max(errors)


def svg(comparisons):
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="640" viewBox="0 0 900 640">',
             '<title>Linear drive versus rotating wave approximation</title>',
             '<desc>Same two-level Hamiltonian, initial minus-z. Probability plotted against Omega t. Weak and strong drive are compared with a converged unitary midpoint evolution; no hardware data.</desc>',
             '<rect width="900" height="640" fill="#ffffff"/>',
             '<g font-family="sans-serif" fill="#172534" font-size="15">',
             '<text x="70" y="28" font-size="21">Linear drive: complete model and RWA</text>',
             '<text x="70" y="53">omega = omega0 = 2 pi x 1 MHz; initial |-z&gt;; closed two-level model</text>']
    left,width,height = 82,760,190
    for panel,(result,data) in enumerate(comparisons):
        phases,full,approx = data
        top = 105+panel*265
        eps = result["Omega_over_omega0"]
        end_us = result["end_time_s"]*1e6
        lines.append(f'<text x="82" y="{top-15}">Omega / omega0 = {eps:g}; time window 0 to {end_us:g} us</text>')
        for y in (0,.25,.5,.75,1):
            py = top+(1-y)*height
            lines.append(f'<line x1="{left}" y1="{py}" x2="{left+width}" y2="{py}" stroke="#d7dfe5"/>')
            lines.append(f'<text x="{left-12}" y="{py+5}" text-anchor="end">{y:g}</text>')
        lines.append(f'<text x="25" y="{top+height/2}" transform="rotate(-90 25 {top+height/2})" text-anchor="middle">P(+z), dimensionless</text>')
        for x,label in ((0,"0"),(math.pi/2,"pi/2"),(math.pi,"pi"),(3*math.pi/2,"3pi/2"),(2*math.pi,"2pi")):
            px = left+width*x/(2*math.pi)
            lines.append(f'<line x1="{px}" y1="{top}" x2="{px}" y2="{top+height}" stroke="#edf0f3"/>')
            lines.append(f'<text x="{px}" y="{top+height+21}" text-anchor="middle">{label}</text>')
        for values,color,dash in ((full,"#1968ae",""),(approx,"#c35812",' stroke-dasharray="7 5"')):
            points = ' '.join(f'{left+width*x/(2*math.pi):.3f},{top+(1-p)*height:.3f}' for x,p in zip(phases,values))
            lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.3"{dash}/>')
        lines.append(f'<text x="{left+width/2}" y="{top+height+44}" text-anchor="middle">Omega t (rad)</text>')
    lines.extend(['<line x1="100" y1="620" x2="140" y2="620" stroke="#1968ae" stroke-width="3"/>',
                  '<text x="150" y="625">complete linear-drive model (numerical)</text>',
                  '<line x1="560" y1="620" x2="600" y2="620" stroke="#c35812" stroke-width="3" stroke-dasharray="7 5"/>',
                  '<text x="610" y="625">RWA formula</text>','</g></svg>'])
    return '\n'.join(lines)


def main():
    spin = spin_one()
    circular,_ = compare_drive(.2,"circular",.9)
    results=[]
    plots=[]
    for eps in (.05,.2,.8):
        result,data = compare_drive(eps)
        results.append(result)
        if eps in (.05,.8):
            plots.append((result,data))
    # Derive the spin-half 2pi factor through the same actual propagator.
    minus_identity = evolve_constant([1+0j,0j],0,0,1,2*math.pi)
    require("spin half 2pi",max(abs(minus_identity[0]+1),abs(minus_identity[1])),1e-12)
    ASSETS.mkdir(exist_ok=True)
    report={"status":"PASS","method":"single-thread Python standard library; no renormalization",
            "spin_one":spin,"rotor":rotor(),"circular_exact_oracle":circular,
            "rotating_frame_matrix_identity_error":rotating_frame_identity(),
            "linear_drive_comparisons":results,
            "short_time_perturbation": {"P_first_order_at_pi":math.pi**2/4,"P_exact_at_pi":1.0},
            "not_verified":["hardware or measured fidelity","general Lie group integration theorem",
                            "full rotor/central-potential spectrum","uniform RWA error bound",
                            "Obsidian rendering or human mastery"]}
    (ASSETS/"checks.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ASSETS/"rwa-comparison.svg").write_text(svg(plots))
    print(json.dumps({"status":report["status"],"linear":results,
                      "circular_max_error":circular["max_sample_probability_difference_from_formula"]},indent=2))


if __name__ == "__main__":
    main()
