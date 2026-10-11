#!/usr/bin/env python3
"""Finite two-subsystem Born rules and exact 1D delta matching. Standard library only.
No packet time stepping, hardware data, or particle-label entanglement claims.
"""
import cmath
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'assets'
HBAR = 6.62607015e-34 / (2 * math.pi)  # J s; h is exact
MU = 1e-30  # kg, selected relative mass
ELL = 1e-9  # m, teaching length
G = HBAR**2/(MU*ELL)  # J m; repulsive in plotted example
I2 = [[1,0],[0,1]]
X = [[0,1],[1,0]]
Y = [[0,-1j],[1j,0]]
Z = [[1,0],[0,-1]]
SWAP = [[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]]


def mm(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(len(b))) for j in range(len(b[0]))]
            for i in range(len(a))]


def dagger(a):
    return [[complex(a[j][i]).conjugate() for j in range(len(a))] for i in range(len(a[0]))]


def kron(a,b):
    # Row/column indices = dim(B)*index(A) + index(B).
    return [[a[i][j]*b[k][l] for j in range(len(a[0])) for l in range(len(b[0]))]
            for i in range(len(a)) for k in range(len(b))]


def outer(v):
    return [[x*complex(y).conjugate() for y in v] for x in v]


def trace(a):
    return sum(a[i][i] for i in range(len(a)))


def expect(rho,operator):
    value=trace(mm(rho,operator))
    assert abs(value.imag)<1e-13
    return value.real


def partial(rho,side):
    if side=='B':
        return [[sum(rho[2*i+j][2*k+j] for j in range(2)) for k in range(2)] for i in range(2)]
    if side=='A':
        return [[sum(rho[2*i+j][2*i+l] for i in range(2)) for l in range(2)] for j in range(2)]
    raise ValueError('Trace out A or B')


def difference(a,b):
    return max(abs(x-y) for ar,br in zip(a,b) for x,y in zip(ar,br))


def projector(axis,sign):
    return [[((1 if i==j else 0)+sign*axis[i][j])/2 for j in range(2)] for i in range(2)]


def pjoint(rho,a,b):
    return [expect(rho,kron(projector(a,s),projector(b,t))) for s,t in [(1,1),(1,-1),(-1,1),(-1,-1)]]


def amplitudes(zeta):
    return -1j*zeta/(1+1j*zeta),1/(1+1j*zeta)


def simpson(f,lo,hi,n):
    assert n>0 and n%2==0
    dx=(hi-lo)/n
    return dx/3*math.fsum((1 if i in (0,n) else 4 if i%2 else 2)*f(lo+i*dx) for i in range(n+1))


def svg_start(title,subtitle,width,height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{escape(title)}</title>',f'<desc>{escape(subtitle)}</desc>',
            '<rect width="100%" height="100%" fill="white"/>',
            '<g font-family="Arial, sans-serif" fill="#172b3c">',
            f'<text x="80" y="34" font-size="22" font-weight="bold">{escape(title)}</text>',
            f'<text x="80" y="59" font-size="13">{escape(subtitle)}</text>']


def plot(parts,box,bounds,xticks,yticks,xlabel,ylabel,curves):
    left,top,w,h=box;xmin,xmax,ymin,ymax=bounds
    def xy(x,y):return left+w*(x-xmin)/(xmax-xmin),top+h*(ymax-y)/(ymax-ymin)
    for x,label in xticks:
        px,_=xy(x,ymin)
        parts.extend([f'<path d="M{px:.2f},{top}v{h}" stroke="#e1e8ee"/>',
                      f'<text x="{px:.2f}" y="{top+h+22}" text-anchor="middle" font-size="12">{escape(label)}</text>'])
    for y in yticks:
        _,py=xy(xmin,y)
        parts.extend([f'<path d="M{left},{py:.2f}h{w}" stroke="#e1e8ee"/>',
                      f'<text x="{left-12}" y="{py+4:.2f}" text-anchor="end" font-size="12">{y:g}</text>'])
    if ymin<=0<=ymax:
        _,py=xy(xmin,0);parts.append(f'<path d="M{left},{py:.2f}h{w}" stroke="#6b7b89"/>')
    parts.extend([f'<path d="M{left},{top}v{h}h{w}" stroke="#172b3c" fill="none"/>',
                  f'<text x="{left+w/2}" y="{top+h+46}" text-anchor="middle" font-size="14">{escape(xlabel)}</text>',
                  f'<text transform="translate({left-62},{top+h/2}) rotate(-90)" text-anchor="middle" font-size="14">{escape(ylabel)}</text>'])
    for vals,color,dash in curves:
        d=' '.join(('M' if i==0 else 'L')+f'{px:.2f},{py:.2f}' for i,(px,py) in enumerate(xy(x,y) for x,y in vals))
        parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')


def joint_plot():
    parts=svg_start('Same local state, different joint probability',
                    'Addressable A,B two-level subsystems; pure Bell phase vs separable classical mixture',900,510)
    samples=[2*math.pi*i/600 for i in range(601)]
    # Evaluate Born probabilities with the same matrix functions as the checks.
    pure=[(theta,pjoint(outer([1/math.sqrt(2),0,0,cmath.exp(1j*theta)/math.sqrt(2)]),X,X)[0]) for theta in samples]
    mix=outer([1,0,0,0]);mix[0][0]=.5;mix[3][3]=.5
    mixed=[(theta,pjoint(mix,X,X)[0]) for theta in samples]
    plot(parts,(105,120,710,285),(0,2*math.pi,0,.55),
         [(0,'0'),(math.pi/2,'pi/2'),(math.pi,'pi'),(3*math.pi/2,'3pi/2'),(2*math.pi,'2pi')],
         [0,.1,.2,.3,.4,.5],'theta (rad)','Joint probability p(x+, x+)',
         [(pure,'#1763a6',False),(mixed,'#b05d2a',True)])
    for x,color,label,dash in [(115,'#1763a6','pure: (1+cos theta)/4',False),(440,'#b05d2a','classical mixture: 1/4',True)]:
        parts.extend([f'<path d="M{x},91h30" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="7 5"' if dash else '')+'/>',
                      f'<text x="{x+40}" y="96" font-size="14">{label}</text>'])
    parts.extend(['<text x="105" y="479" font-size="13">Each local x+ probability stays 1/2; at theta=pi/2 choose X on A and Y on B.</text>','</g></svg>'])
    return '\n'.join(parts)+'\n'


def scattering_plot():
    parts=svg_start('Contact scattering: flux and exchange parity',
                    'Real repulsive g=hbar^2/(mu ell); q=k ell > 0; mathematical 1D relative-motion model',900,740)
    qs=[.05+3.95*i/600 for i in range(601)]
    trans=[(q,abs(amplitudes(1/q)[1])**2) for q in qs]
    refl=[(q,abs(amplitudes(1/q)[0])**2) for q in qs]
    ticks=[(q,f'{q:g}') for q in [0,1,2,3,4]]
    plot(parts,(105,120,710,245),(0,4,0,1),ticks,[0,.25,.5,.75,1],
         'q = k ell (dimensionless)','Flux ratio',[(trans,'#1763a6',False),(refl,'#b05d2a',True)])
    for x,color,label,dash in [(130,'#1763a6','T: transmitted',False),(450,'#b05d2a','R: reflected',True)]:
        parts.extend([f'<path d="M{x},91h30" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="7 5"' if dash else '')+'/>',
                      f'<text x="{x+40}" y="96" font-size="14">{label}</text>'])
    parts.extend(['<text x="130" y="459" font-size="14" fill="#1763a6">even phase: -atan(1/q)</text>',
                  '<text x="455" y="459" font-size="14" fill="#3d865b">odd phase: 0</text>'])
    plot(parts,(105,485,710,155),(0,4,-1.6,.12),ticks,[-1.5,-1,-.5,0],
         'q = k ell (dimensionless)','Parity phase shift (rad)',
         [([(q,-math.atan(1/q)) for q in qs],'#1763a6',False),([(q,0) for q in qs],'#3d865b',True)])
    parts.extend(['<text x="105" y="713" font-size="13">Samples begin at q=0.05; q=0 is a threshold limit, not an incident state in this plot.</text>','</g></svg>'])
    return '\n'.join(parts)+'\n'


def main():
    report={'model':{'tensor_shape':[2,2],'flat_basis':['00','01','10','11'],
                     'row_major_index':'2*i+j','units':'Bell probabilities dimensionless; scatter q=k ell',
                     'relative_mass_kg':MU,'ell_m':ELL,'g_J_m':G,'hbar_J_s':HBAR},'bell':[]}
    mix=[[0j]*4 for _ in range(4)];mix[0][0]=mix[3][3]=.5
    half=[[.5,0],[0,.5]]
    for theta in [0,math.pi/2,math.pi,3*math.pi/2,2*math.pi]:
        v=[1/math.sqrt(2),0,0,cmath.exp(1j*theta)/math.sqrt(2)]
        rho=outer(v)
        joint=pjoint(rho,X,X)
        predicted=[(1+math.cos(theta))/4,(1-math.cos(theta))/4,
                   (1-math.cos(theta))/4,(1+math.cos(theta))/4]
        maxerr=max(abs(x-y) for x,y in zip(joint,predicted))
        localerr=max(difference(partial(rho,'A'),half),difference(partial(rho,'B'),half))
        assert maxerr<1e-13 and localerr<1e-13 and abs(sum(joint)-1)<1e-13
        assert abs(expect(rho,kron(X,Y))-math.sin(theta))<1e-13
        u=kron(I2,[[1,0],[0,cmath.exp(.37j)]])
        rotated=mm(mm(u,rho),dagger(u))
        assert difference(partial(rotated,'B'),partial(rho,'B'))<1e-13
        report['bell'].append({'theta_rad':theta,'joint_xx_pp_pm_mp_mm':joint,
            'expect_xx':expect(rho,kron(X,X)),'expect_xy':expect(rho,kron(X,Y)),
            'global_purity':expect(rho,rho),'local_purity':expect(partial(rho,'B'),partial(rho,'B')),
            'local_half_identity_residual':localerr,'joint_analytic_residual':maxerr})
    # Asymmetric complex example exposes swapped subsystem indices hidden by Bell symmetry.
    unequal=outer([1/math.sqrt(8),2j/math.sqrt(8),-1/math.sqrt(8),(1+1j)/math.sqrt(8)])
    expected_a=[[5/8,(1+2j)/8],[(1-2j)/8,3/8]]
    expected_b=[[1/4,(-1-1j)/8],[(-1+1j)/8,3/4]]
    assert difference(partial(unequal,'B'),expected_a)<1e-13
    assert difference(partial(unequal,'A'),expected_b)<1e-13
    report['asymmetric_partial_trace']={'A_diag':[5/8,3/8],'A_offdiag_real_imag':[1/8,2/8],
        'B_diag':[1/4,3/4],'B_offdiag_real_imag':[-1/8,-1/8],
        'A_residual':difference(partial(unequal,'B'),expected_a),
        'B_residual':difference(partial(unequal,'A'),expected_b)}
    report['classical_mixture']={'joint_xx':pjoint(mix,X,X),'expect_xy':expect(mix,kron(X,Y)),
                                 'global_purity':expect(mix,mix),'local_purity':expect(partial(mix,'B'),partial(mix,'B'))}
    assert difference(partial(mix,'B'),half)<1e-13
    assert difference(mm(SWAP,SWAP),kron(I2,I2))==0
    singlet=[0,1/math.sqrt(2),-1/math.sqrt(2),0]
    triplet=[0,1/math.sqrt(2),1/math.sqrt(2),0]
    for sign,state in [(-1,singlet),(1,triplet)]:
        swapped=mm(SWAP,[[x] for x in state])
        assert max(abs(swapped[i][0]-sign*state[i]) for i in range(4))<1e-13
    # Nonorthogonal normalized u=(1,0), v=(1,i)/sqrt(2); correct symmetrization norm.
    uv=[1/math.sqrt(2),1j/math.sqrt(2),0,0]
    vu=[1/math.sqrt(2),0,1j/math.sqrt(2),0]
    norms={}
    for sign in [1,-1]:
        state=[(x+sign*y)/math.sqrt(2*(1+sign*.5)) for x,y in zip(uv,vu)]
        norms[str(sign)]=sum(abs(x)**2 for x in state)
        assert abs(norms[str(sign)]-1)<1e-13
    report['exchange']={'singlet_swap':-1,'triplet_swap':1,'nonorthogonal_overlap_abs2':.5,
                         'normalized_sym_antisym_norms':norms}
    report['scattering']=[]
    for q in [.1,.5,1,2,4]:
        zeta=1/q;r,t=amplitudes(zeta)
        s=[[r,t],[t,r]]
        unity=difference(mm(dagger(s),s),I2)
        continuity=abs(1+r-t)
        # Derivatives in coordinate xi=x/ell, so q and jump coefficient 2 are dimensionless.
        jump=abs(1j*q*t-1j*q*(1-r)-2*t)
        se=(1-1j*zeta)/(1+1j*zeta)
        parity=max(abs(r+t-se),abs(r-t+1))
        current=[]
        for xi in [-2.3,-.7,.4,1.8]:
            if xi<0:
                psi=cmath.exp(1j*q*xi)+r*cmath.exp(-1j*q*xi)
                derivative=1j*q*cmath.exp(1j*q*xi)-1j*q*r*cmath.exp(-1j*q*xi)
            else:
                psi=t*cmath.exp(1j*q*xi);derivative=1j*q*psi
            current.append((psi.conjugate()*derivative).imag/q)
        T=abs(t)**2;R=abs(r)**2
        assert max(unity,continuity,jump,parity,abs(R+T-1),*(abs(x-T) for x in current))<1e-13
        report['scattering'].append({'q':q,'zeta':zeta,'r_real_imag':[r.real,r.imag],
            't_real_imag':[t.real,t.imag],'R':R,'T':T,'even_phase_rad':-math.atan(zeta),
            'port_unitarity_residual':unity,'continuity_residual':continuity,
            'jump_residual_xi':jump,'parity_eigenvalue_residual':parity,'net_current_over_incoming':current})
    report['dimensional_example']={'q':1,'relative_energy_J':HBAR**2/(2*MU*ELL**2),
                                   'A_per_sqrt_m':ELL**(-.5),'incoming_current_per_s':HBAR/(MU*ELL**2)}
    # Attractive strength -G: U_b(xi)=exp(-|xi|), integral exactly 1, energy unit negative one.
    # Integrate half-axis and double to avoid sampling a cusp across a Simpson panel.
    coarse=2*simpson(lambda xi:math.exp(-2*xi),0,20,2000)
    fine=2*simpson(lambda xi:math.exp(-2*xi),0,20,4000)
    tail=math.exp(-40)
    d=1e-5
    bound=lambda xi:math.exp(-abs(xi))
    right_slope=(bound(d)-bound(0))/d
    left_slope=(bound(0)-bound(-d))/d
    bound_jump=abs(right_slope-left_slope+2*bound(0))
    bound_equation=max(abs(-(bound(x+d)-2*bound(x)+bound(x-d))/d**2+bound(x))
                       for x in [-2,-.4,.4,2])
    assert bound_jump<3e-5 and bound_equation<3e-6
    rn,tn=amplitudes(-1)
    rp,tp=amplitudes(1)
    assert abs(abs(tn)**2-abs(tp)**2)<1e-13 and abs(tn-tp)>0.5
    assert abs(fine-1)<1e-8 and abs(fine-coarse)<1e-8
    report['attractive_bound']={'g_J_m':-G,'kappa_per_m':1/ELL,'energy_J':-HBAR**2/(2*MU*ELL**2),
        'norm_coarse':coarse,'norm_fine':fine,'tail_probability':tail,
        'one_sided_fd_step_xi':d,'jump_residual_xi':bound_jump,
        'outside_origin_equation_residual':bound_equation,'continuous_spectrum_still_present':True}
    report['checks_passed']=True
    OUT.mkdir(exist_ok=True)
    (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'joint-probability.svg').write_text(joint_plot(),encoding='utf-8')
    (OUT/'contact-scattering.svg').write_text(scattering_plot(),encoding='utf-8')
    print(json.dumps({'checks_passed':True,'q1_R_T':[.5,.5],'output_dir':str(OUT)},ensure_ascii=False))


if __name__=='__main__':
    main()
