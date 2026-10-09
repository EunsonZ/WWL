"""Finite checks for nonlinear flow, feedback and random products.

Standard library, deterministic inputs, no network or import-time execution.
Default prints JSON only. --output-dir NEW_DIR creates that new directory and
writes report.json and pendulum-phase.svg; an existing destination is refused.
Numerical RK4 trajectories are approximations, not proofs of a global basin.
"""
from fractions import Fraction as F
from math import sin, cos, pi, exp, expm1, log, sqrt, hypot, comb, isfinite
from pathlib import Path
import argparse
import json


def rk4(field, initial, step, steps):
    if not isfinite(step) or step <= 0 or type(steps) is not int or steps < 0:
        raise ValueError('positive finite step and nonnegative integer steps required')
    z = tuple(float(v) for v in initial)
    if not z or not all(isfinite(v) for v in z):
        raise ValueError('finite nonempty initial state required')
    if steps > 100000:
        raise ValueError('outside bounded teaching workload; at most 100000 steps')
    def evaluate(state):
        values = tuple(field(state))
        if len(values) != len(z) or not all(isfinite(v) for v in values):
            raise ValueError('field must preserve state dimension and return finite values')
        return values
    out = [z]
    for _ in range(steps):
        k1 = evaluate(z)
        k2 = evaluate(tuple(a+step*b/2 for a, b in zip(z, k1)))
        k3 = evaluate(tuple(a+step*b/2 for a, b in zip(z, k2)))
        k4 = evaluate(tuple(a+step*b for a, b in zip(z, k3)))
        z = tuple(a+step*(b+2*c+2*d+e)/6 for a, b, c, d, e in zip(z, k1, k2, k3, k4))
        if not all(isfinite(v) for v in z):
            raise ArithmeticError('nonfinite trajectory; no physical conclusion')
        out.append(z)
    return out


def pendulum(z, gamma=0.5):
    theta, v = z
    return (v, -sin(theta)-gamma*v)


def energy(z):
    theta, v = z
    return v*v/2+1-cos(theta)


def pendulum_checks(config):
    gamma = float(config['gamma'])
    initial = tuple(config['initial'])
    duration = float(config['duration_tau'])
    field = lambda z: pendulum(z, gamma)
    if gamma <= 0 or duration <= 0 or not isfinite(duration):
        raise ValueError('positive damping and finite positive duration required')
    runs = []
    for step in config['steps']:
        trace = rk4(field, initial, step, round(duration/step))
        energies = [energy(z) for z in trace]
        max_increase = max(b-a for a, b in zip(energies, energies[1:]))
        assert max_increase < 1e-9
        assert max(abs(z[0]) for z in trace) < pi
        runs.append(dict(step=step, steps=len(trace)-1, endpoint=trace[-1],
                         initial_energy=energies[0], final_energy=energies[-1],
                         max_energy_increase=max_increase))
    defects = []
    for z in ((pi/2, 0.), (0., 1.), (pi/2, -2.), (0.4, -0.7)):
        dtheta, dv = field(z)
        observed = sin(z[0])*dtheta+z[1]*dv
        expected = -gamma*z[1]**2
        assert abs(observed-expected) < 1e-12
        defects.append(dict(state=z, field=(dtheta, dv), energy_derivative=observed,
                            analytic_derivative=expected))
    differences = [hypot(*(a-b for a,b in zip(runs[i]['endpoint'], runs[i+1]['endpoint'])))
                   for i in range(2)]
    assert differences[1] < differences[0]
    return dict(gamma=gamma, initial=initial, duration_tau=duration, runs=runs,
                adjacent_endpoint_differences=differences, derivative_checks=defects,
                evidence='RK4 refinement and energy checks; no exact pendulum orbit oracle')


def radial_exact(mu, alpha, r0, t):
    if not all(isfinite(x) for x in (mu, alpha, r0, t)) or mu <= 0 or r0 < 0 or t < 0:
        raise ValueError('finite mu>0, r0>=0, t>=0 required')
    # Bounded teaching interface: avoid underflow pretending to be blow-up,
    # and overflow in alpha*r0^2/mu. This is not the mathematical ODE domain.
    if not (1e-6 <= mu <= 100 and abs(alpha) <= 100 and
            (r0 == 0 or 1e-6 <= r0 <= 10) and t <= 100 and mu*t <= 100):
        raise ValueError('outside teaching numerical domain; no stability conclusion')
    if r0 == 0:
        return 0.
    decay = exp(-2*mu*t)
    nonlinear = (alpha*r0*r0/mu)*(-expm1(-2*mu*t))
    denominator = decay + nonlinear
    if denominator <= 0:
        raise ValueError('nonpositive resolved denominator: beyond blow-up or numerically unresolved')
    # A conservative cancellation guard; rejecting is not a physical blow-up diagnosis.
    uncertainty = 32*2.220446049250313e-16*(abs(decay)+abs(nonlinear))
    if denominator <= uncertainty:
        raise ValueError('positive denominator numerically unresolved near cancellation; no radius certified')
    return r0/sqrt(denominator)


def hopf_checks(config):
    mu, alpha = float(config['mu']), float(config['alpha'])
    omega = float(config['omega_over_pi'])*pi
    r0, duration = float(config['r0']), float(config['duration'])
    if mu <= 0 or alpha <= 0 or omega <= 0:
        raise ValueError('the stable radial profile requires mu, alpha, omega positive')
    def field(z):
        x,y=z
        growth=mu-alpha*(x*x+y*y)
        return (growth*x-omega*y, omega*x+growth*y)
    exact_r=radial_exact(mu, alpha, r0, duration)
    exact=(exact_r*cos(omega*duration), exact_r*sin(omega*duration))
    runs=[]
    for h in config['steps']:
        endpoint=rk4(field,(r0,0.),h,round(duration/h))[-1]
        error=hypot(*(x-y for x,y in zip(endpoint,exact)))
        runs.append(dict(step=h,endpoint=endpoint,error_to_exact=error))
    assert runs[-1]['error_to_exact'] < runs[0]['error_to_exact']
    assert runs[-1]['error_to_exact'] < 1e-7
    stable_radius, period = sqrt(mu/alpha), 2*pi/omega
    delta = float(config['finite_difference_delta'])
    multiplier_fd=(radial_exact(mu,alpha,stable_radius+delta,period)-radial_exact(mu,alpha,stable_radius-delta,period))/(2*delta)
    assert abs(multiplier_fd-exp(-2*mu*period)) < 1e-8
    blow=log(101)/2  # mu=1, alpha=-1, r0=.1
    before=radial_exact(1,-1,.1,blow-1e-4)
    try:
        radial_exact(1,-1,.1,blow+1e-4)
    except ValueError as e:
        rejected=str(e)
    else:
        raise AssertionError('post-blow-up request must be rejected')
    return dict(mu=mu,alpha=alpha,omega=omega,r0=r0,duration=duration,
                exact_endpoint=exact,runs=runs,period=period,stable_radius=stable_radius,
                radial_multiplier=exp(-2*mu*period),finite_difference_multiplier=multiplier_fd,
                negative_alpha=dict(mu=1.,alpha=-1.,r0=.1,blow_time=blow,
                                    radius_before_blow=before,post_blow_rejection=rejected),
                zero_seed=[radial_exact(1,a,0,1) for a in (1,0,-1)])


def euler_checks(config):
    a, count = F(config['a_per_second']), int(config['updates'])
    if a <= 0 or not 1 <= count <= 100:
        raise ValueError('positive decay and 1..100 Euler updates required')
    rows=[]
    for h in map(F,config['step_seconds']):
        if h <= 0:
            raise ValueError('positive step required')
        factor=1-a*h
        values=[factor**k for k in range(count+1)]
        rows.append(dict(a_per_second=a,step_seconds=h,factor=factor,
                         modulus=abs(factor),states=values,
                         exact_final=exp(-float(a*count*h))))
    return rows


def feedback(a, rounds=6):
    a=F(a)
    if not 1 <= rounds <= 100 or type(rounds) is not int:
        raise ValueError('1..100 integer rounds required')
    if a < 0:
        raise ValueError('this lesson uses nonnegative response coefficients')
    z=(F(1),F(0));rows=[z]
    for k in range(1,rounds+1):
        z=(a*sum(z),a*sum(z))
        oracle=(a*(2*a)**(k-1),)*2
        assert z==oracle
        rows.append(z)
    cumulative=None
    if 2*a < 1:
        tail=a/(1-2*a)
        cumulative=(1+tail,tail)
        # Solve (I-W)c=l0 independently, no summation approximation.
        assert (1-a)*cumulative[0]-a*cumulative[1]==1
        assert -a*cumulative[0]+(1-a)*cumulative[1]==0
    return dict(a=a,isolated_multiplier=a,common_multiplier=2*a,
                first_seven_increments=rows,infinite_cumulative=cumulative)


def nonnormal(coupling, diagonal="4/5", rounds=12):
    a,b=F(diagonal),F(coupling)
    if not 0 < a < 1 or not 1 <= rounds <= 100 or type(rounds) is not int:
        raise ValueError('0<diagonal<1 and 1..100 integer rounds required')
    z=(F(0),F(1)); rows=[dict(k=0,state=z)]
    for k in range(1,rounds+1):
        z=(a*z[0]+b*z[1],a*z[1])
        assert z==(b*k*a**(k-1),a**k)
        rows.append(dict(k=k,state=z))
    peak=max(row['state'][0] for row in rows)
    return dict(diagonal=a,coupling=b,initial=(0,1),spectral_radius=a,
                rows=rows,first_component_peak=peak,
                first_component_peak_steps=[r['k'] for r in rows if r['state'][0]==peak])


def random_product(n, config):
    if type(n) is not int or not 1 <= n <= 100:
        raise ValueError('enumerate counts only for 1<=n<=100')
    p, up, down = F(config['up_probability']), F(config['up_multiplier']), F(config['down_multiplier'])
    if not 0 <= p <= 1 or min(up, down) <= 0:
        raise ValueError('probability in [0,1] and positive multipliers required')
    rows=[]
    for k in range(n+1):
        mass=comb(n,k)*p**k*(1-p)**(n-k)
        ratio=up**k*down**(n-k)
        rows.append(dict(up_count=k,probability=mass,growth_ratio=ratio))
    total=sum(row['probability'] for row in rows)
    mean=sum(row['probability']*row['growth_ratio'] for row in rows)
    assert total==1 and mean==(p*up+(1-p)*down)**n
    return dict(n=n,up_probability=p,up_multiplier=up,down_multiplier=down,
                count_distribution=rows,mean_ratio=mean,
                probability_ratio_below_one=sum(row['probability'] for row in rows if row['growth_ratio']<1),
                expected_log_ratio=n*(float(p)*log(float(up))+float(1-p)*log(float(down))),
                log_expected_ratio=n*log(float(p*up+(1-p)*down)),
                almost_sure_log_growth=float(p)*log(float(up))+float(1-p)*log(float(down)),
                evidence='finite binomial enumeration; a.s. limit proved in lesson, not by enumeration')


def phase_svg(config):
    gamma, step, count = float(config['gamma']), float(config['step']), int(config['steps'])
    if gamma <= 0 or not isfinite(gamma):
        raise ValueError('phase portrait nullcline requires positive finite damping')
    field = lambda z: pendulum(z,gamma)
    width,height=1000,570
    left,top,w,h=65,45,570,450
    def xy(theta,v):return left+(theta+pi)/(2*pi)*w,top+(3-v)/6*h
    elements=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
              f'<title id="title">Damped pendulum phase portrait, gamma {gamma}</title>',
              f'<desc id="desc">Dimensionless angle theta and velocity v. Normalized direction arrows, two nullclines, V=1 contour, fixed RK4 trajectories with h={step}. Left and right boundaries identify the same cylinder angle.</desc>',
              '<rect width="1000" height="570" fill="#fffdf8"/>',
              '<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10" fill="#788493"/></marker></defs>',
              f'<rect x="{left}" y="{top}" width="{w}" height="{h}" fill="#f5f8fa" stroke="#7b8895"/>']
    def path(points,color,width=2,dash=None):
        points=list(points)
        if not points:return
        d='M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in points)
        style=f' stroke-dasharray="{dash}"' if dash else ''
        elements.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{style}/>')
    for theta in [-pi+i*pi/8 for i in range(17)]:
        for v in [-2.75+i*.5 for i in range(12)]:
            vx,vy=field((theta,v));dx,dy=vx*w/(2*pi),-vy*h/6
            norm=hypot(dx,dy)
            if norm<1e-10:continue
            x,y=xy(theta,v);dx,dy=dx/norm*11,dy/norm*11
            elements.append(f'<path d="M{x-dx/2:.2f},{y-dy/2:.2f} l{dx:.2f},{dy:.2f}" stroke="#99a5ae" stroke-width=".8" marker-end="url(#arr)"/>')
    path([xy(-pi,0),xy(pi,0)],'#245b92',2,'6 4')
    path([xy(-pi+2*pi*i/240,-sin(-pi+2*pi*i/240)/gamma) for i in range(241)],'#1f795c',2,'6 4')
    for sign in (-1,1):
        path([xy(-pi/2+pi*i/240,sign*sqrt(max(0,2*cos(-pi/2+pi*i/240)))) for i in range(241)],'#855da2',1.8,'2 4')
    initials=[tuple(z) for z in config['initials']]
    colors=['#c74831','#ce8d18','#b33c83','#007e9c']
    for initial,color in zip(initials,colors):
        trace=rk4(field,initial,step,count)
        segment=[];previous=None
        for theta,v in trace:
            angle=(theta+pi)%(2*pi)-pi
            if previous is not None and abs(angle-previous)>pi:
                path(segment,color,2.2);segment=[]
            segment.append(xy(angle,v));previous=angle
        path(segment,color,2.2)
        x,y=xy(*initial);elements.append(f'<rect x="{x-3:.2f}" y="{y-3:.2f}" width="6" height="6" fill="{color}"/>')
    for theta,fill in [(0,'#1d2935'),(-pi,'white'),(pi,'white')]:
        x,y=xy(theta,0);elements.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{fill}" stroke="#1d2935" stroke-width="2"/>')
    for theta,label in [(-pi,'-pi'),(-pi/2,'-pi/2'),(0,'0'),(pi/2,'pi/2'),(pi,'pi')]:
        x,_=xy(theta,0);elements.append(f'<text x="{x}" y="520" text-anchor="middle" font-family="sans-serif" font-size="14">{label}</text>')
    for v in (-3,-2,-1,0,1,2,3):
        _,y=xy(0,v);elements.append(f'<text x="52" y="{y+4}" text-anchor="end" font-family="sans-serif" font-size="14">{v}</text>')
    elements += ['<text x="345" y="553" font-family="sans-serif" font-size="17" text-anchor="middle">theta (rad; cylinder seam at +/-pi)</text>',
                 '<text x="20" y="30" font-family="sans-serif" font-size="17">v = d theta / d tau</text>']
    labels=[('Damped pendulum','#1d2935',22),(f'gamma = {gamma}; no forcing','#1d2935',16),('Dashed blue: theta prime = 0','#245b92',15),('Dashed green: v prime = 0','#1f795c',15),('Dotted purple: energy V = 1','#855da2',15),('Filled circle: stable bottom','#1d2935',15),('Open circles: same saddle','#1d2935',15),('Squares: initial states','#1d2935',15),(f'RK4: h = {step}, tau = 0..{step*count:g}','#1d2935',15),('Arrow lengths are normalized','#1d2935',15),('Trajectories are approximations','#1d2935',15),('Energy / LaSalle supply the proof','#1d2935',15)]
    for i,(label,color,size) in enumerate(labels):
        elements.append(f'<text x="665" y="{65+i*33}" font-family="sans-serif" font-size="{size}" fill="{color}">{label}</text>')
    elements.append('</svg>')
    return '\n'.join(elements)


def encode(value):
    if isinstance(value,F):return str(value)
    raise TypeError(type(value).__name__)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('fixed-inputs.json'),help='fixed profile JSON; default adjacent to source')
    parser.add_argument('--output-dir',type=Path,help='new external directory; existing directory refused')
    args=parser.parse_args()
    if args.output_dir is not None:
        destination = args.output_dir.expanduser().resolve()
        protected = [Path(__file__).resolve().parent]
        protected += [p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file()]
        if any(destination == p or p in destination.parents for p in protected):
            raise ValueError('output must be outside the course and instruction-bearing workspace')
        if destination.exists():
            raise FileExistsError('output directory already exists; choose a new path')
        args.output_dir = destination
    config=json.loads(args.inputs.read_text(encoding='utf-8'))
    if config.get('profile') != 'wwl-dynamics-fixed-v1':
        raise ValueError('unsupported fixed input profile')
    report=dict(profile=config['profile'],inputs=config,
                pendulum=pendulum_checks(config['pendulum']),hopf=hopf_checks(config['hopf']),euler=euler_checks(config['euler']),
                feedback=[feedback(a,config['feedback']['rounds']) for a in config['feedback']['a']],
                nonnormal=[nonnormal(b,config['nonnormal']['diagonal'],config['nonnormal']['rounds']) for b in config['nonnormal']['coupling']],
                random_products=[random_product(n,config['random_product']) for n in config['random_product']['n']])
    payload=json.dumps(report,ensure_ascii=False,indent=2,default=encode,allow_nan=False)+'\n' 
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True,exist_ok=False)
        (args.output_dir/'report.json').write_text(payload,encoding='utf-8')
        (args.output_dir/'pendulum-phase.svg').write_text(phase_svg(config['phase_svg']),encoding='utf-8')
    print(payload,end='')


if __name__=='__main__':
    main()
