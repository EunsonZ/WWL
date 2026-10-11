#!/usr/bin/env python3
"""Bounded, single-thread standard-library checks of the stated teaching models."""
import cmath
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'assets'
H = 6.62607015e-34
HBAR = H / (2*math.pi)
KB = 1.380649e-23
F = 6e9
OMEGA = 2*math.pi*F
N_CUT = 64


def close(a, b, tol=1e-12):
    assert abs(a-b) <= tol, (a, b, tol)


def trap(fn, a, b, n=4000):
    dx = (b-a)/n
    return dx*(0.5*(fn(a)+fn(b))+sum(fn(a+i*dx) for i in range(1,n)))


def coherent(alpha):
    c = [complex(math.exp(-abs(alpha)**2/2))]
    for n in range(1, N_CUT):
        c.append(c[-1]*alpha/math.sqrt(n))
    return c


def moments(c):
    weights = [abs(z)**2 for z in c]
    norm = sum(weights)
    mean_n = sum(n*w for n,w in enumerate(weights))
    mean_n2 = sum(n*n*w for n,w in enumerate(weights))
    mean_a = sum(c[n-1].conjugate()*math.sqrt(n)*c[n] for n in range(1,len(c)))
    return norm, mean_a, mean_n, mean_n2-mean_n**2


def hermite_state(n, xi):
    if n == 0:
        hn = 1
    elif n == 1:
        hn = 2*xi
    else:
        hprev, hn = 1, 2*xi
        for k in range(1,n):
            hprev, hn = hn, 2*xi*hn-2*k*hprev
    return hn*math.exp(-xi*xi/2)/(math.pi**0.25*math.sqrt(2**n*math.factorial(n)))


def draw_occupations(distributions):
    width, height = 850, 450
    left, top, pw, ph = 75, 85, 715, 265
    colors = ['#1756a9','#ab4700','#24723a']
    labels = ['Fock |1>', 'coherent alpha=1', 'thermal q=1/2']
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
             '<title>Same mean occupation, different distributions</title>',
             '<desc>Ideal single harmonic mode. All three states have mean n=1 and total mean energy 1.5 h f, but different occupation variance and mean amplitude. Probabilities n=0 to 12; omitted tails are stated.</desc>',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="Arial, sans-serif" font-size="14" fill="#17212b">',
             '<text x="30" y="28" font-size="19">Same mean occupation, different distributions</text>',
             '<text x="75" y="65">P(n), dimensionless</text>',
             f'<path d="M{left},{top} V{top+ph} H{left+pw}" fill="none" stroke="#17212b"/>']
    for y in [0,0.25,0.5,0.75,1]:
        yy=top+ph*(1-y)
        parts.append(f'<text x="65" y="{yy+4}" text-anchor="end">{y:g}</text>')
    slot=pw/13
    for n in range(13):
        center=left+(n+0.5)*slot
        parts.append(f'<text x="{center:.2f}" y="{top+ph+20}" text-anchor="middle">{n}</text>')
        for j,probabilities in enumerate(distributions):
            p=probabilities[n]
            x=center+(j-1)*12-5
            y=top+ph*(1-p)
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="10" height="{ph*p:.4f}" fill="{colors[j]}"/>')
    for j,label in enumerate(labels):
        x=300+165*j
        parts.append(f'<rect x="{x}" y="44" width="10" height="10" fill="{colors[j]}"/><text x="{x+15}" y="54">{label}</text>')
    parts += [f'<text x="{left+pw}" y="390" text-anchor="end">occupation outcome n (dimensionless)</text>',
              '<text x="75" y="419">Displayed n=0..12; thermal tail = 2^-13 = 0.0001220703125.</text>',
              '<text x="75" y="440">Coherent omitted tail &lt; 6.4e-11; exact analytic distributions, no measured counts.</text>',
              '</g></svg>']
    (OUT/'occupation.svg').write_text('\n'.join(parts)+'\n')


def main():
    OUT.mkdir(exist_ok=True)
    # Dimensionless Gaussian Fourier density: kappa=k*s, mean=1, sd=1/2.
    density=lambda kap: math.sqrt(2/math.pi)*math.exp(-2*(kap-1)**2)
    close(trap(density,-5,7),1,1e-11)
    pneg=0.5*math.erfc(math.sqrt(2))
    pwindow=0.5*math.erf(2*math.sqrt(2))
    close(trap(density,-5,0,n=8000),pneg,5e-8)
    close(trap(density,-1,1,n=8000),pwindow,5e-8)
    # Hermite normalization and first four exact energy equations in xi=x/ell.
    orthogonality=[]
    for n in range(4):
        for m in range(4):
            v=trap(lambda xi:hermite_state(n,xi)*hermite_state(m,xi),-10,10)
            close(v,int(n==m),1e-11)
            orthogonality.append(abs(v-int(n==m)))
    delta=1e-4
    energy_residual=[]
    ladder_residual=[]
    for n in range(4):
        for xi in [-2,-0.5,0,1,2.5]:
            fn=lambda x:hermite_state(n,x)
            d1=(fn(xi+delta)-fn(xi-delta))/(2*delta)
            d2=(fn(xi+delta)-2*fn(xi)+fn(xi-delta))/(delta**2)
            energy_residual.append(abs(0.5*(-d2+xi*xi*fn(xi))-(n+0.5)*fn(xi)))
            target=0 if n==0 else math.sqrt(n)*hermite_state(n-1,xi)
            ladder_residual.append(abs((xi*fn(xi)+d1)/math.sqrt(2)-target))
    assert max(energy_residual)<1e-7 and max(ladder_residual)<1e-7
    fock=[0j]*N_CUT
    fock[1]=1
    coh=coherent(1)
    pthermal=[0.5**(n+1) for n in range(N_CUT)]
    pn_coh=[abs(c)**2 for c in coh]
    stats=[]
    for name,c,expected_a,expected_var in [('Fock',fock,0,0),('coherent',coh,1,1)]:
        norm,a,n,var=moments(c)
        close(norm,1);close(a,expected_a);close(n,1);close(var,expected_var)
        stats.append({'state':name,'norm':norm,'mean_a_real':a.real,'mean_a_imag':a.imag,
                      'mean_n':n,'variance_n':var,'mean_energy_J':H*F*(n+0.5)})
    nt=sum(n*p for n,p in enumerate(pthermal))
    vt=sum(n*n*p for n,p in enumerate(pthermal))-nt*nt
    close(sum(pthermal),1);close(nt,1);close(vt,2)
    stats.append({'state':'thermal q=1/2','norm':sum(pthermal),'mean_a_real':0,'mean_a_imag':0,
                  'mean_n':nt,'variance_n':vt,'mean_energy_J':H*F*(nt+0.5)})
    # Coherent and two-level oscillator superposition: exact phases for each n.
    for phase in [0,math.pi/2,math.pi,3*math.pi/2]:
        for alpha in [1,1j]:
            evolved=[c*cmath.exp(-1j*(n+0.5)*phase) for n,c in enumerate(coherent(alpha))]
            _,a,n,_=moments(evolved)
            close(a,alpha*cmath.exp(-1j*phase));close(n,abs(alpha)**2)
        superposition=[0j]*N_CUT
        superposition[0]=cmath.exp(-0.5j*phase)/math.sqrt(2)
        superposition[1]=cmath.exp(-1.5j*phase)/math.sqrt(2)
        _,a,n,_=moments(superposition)
        close(a,0.5*cmath.exp(-1j*phase));close(n,0.5)
    # Finite a_N commutator diagonal: 1 except top value 1-N, trace exactly 0.
    matrix_cut=6
    a_matrix=[[math.sqrt(j) if j==i+1 else 0 for j in range(matrix_cut)] for i in range(matrix_cut)]
    commutator=[[sum(a_matrix[i][k]*a_matrix[j][k]-a_matrix[k][i]*a_matrix[k][j]
                     for k in range(matrix_cut)) for j in range(matrix_cut)] for i in range(matrix_cut)]
    truncated_diagonal=[commutator[i][i] for i in range(matrix_cut)]
    for i in range(matrix_cut):
        for j in range(matrix_cut):
            close(commutator[i][j],(1 if i<matrix_cut-1 else 1-matrix_cut) if i==j else 0)
    close(sum(truncated_diagonal),0)
    top_weight_coh=pn_coh[-1]
    top_weight_thermal=pthermal[-1]
    report={'result':'PASS','model':'exact free Gaussian Fourier density and ideal harmonic oscillator',
            'single_thread':True,'h_J_s':H,'hbar_J_s':HBAR,'frequency_Hz':F,
            'thermal_same_mean_temperature_K':H*F/(KB*math.log(2)),
            'thermal_20mK_occupation':1/math.expm1(H*F/(KB*0.020)),
            'continuous_gaussian':{'kappa_mean':1,'kappa_sd':0.5,'negative_momentum_probability':pneg,
                                    'energy_window_probability':pwindow,'norm_window_kappa':[-5,7],
                                    'norm_quadrature_segments':4000,'probability_quadrature_segments':8000},
            'hermite_checks':{'xi_window':[-10,10],'quadrature_segments':4000,'n_checked':[0,1,2,3],
                              'max_orthogonality_error':max(orthogonality),'difference_delta_xi':delta,
                              'max_dimensionless_energy_residual':max(energy_residual),
                              'max_dimensionless_lowering_residual':max(ladder_residual)},
            'occupation_stats':stats,'n_cutoff_exclusive':N_CUT,
            'finite_commutator':{'matrix_shape':[matrix_cut,matrix_cut],'diagonal':truncated_diagonal,'trace':sum(truncated_diagonal),
                                 'coherent_expectation_error':N_CUT*top_weight_coh,
                                 'thermal_expectation_error':N_CUT*top_weight_thermal},
            'figure_tail_n_ge_13':{'thermal':2**-13,'coherent':sum(pn_coh[13:])},
            'numeric_tail_n_ge_64':{'thermal_probability':2**-64,'thermal_missing_mean_n':(64+1)*2**-64},
            'not_tested':['self-adjointness theorem proof','general continuous spectral theorem',
                          'hardware','readout fidelity','Obsidian display','learner understanding']}
    draw_occupations([[abs(c)**2 for c in fock],pn_coh,pthermal])
    (OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ['result','thermal_same_mean_temperature_K','thermal_20mK_occupation','hermite_checks']}))


if __name__=='__main__':
    main()
