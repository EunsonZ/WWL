#!/usr/bin/env python3
"""Covariant fields and prescribed point-charge histories. Standard library, one thread.
Dimensionless field computations use c=T=q/(4*pi*epsilon)=1. SI outputs restore units.
This does not integrate self-force, build hardware, or infer a physical drive.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path

C, EPS, Q, L = 299792458.0, 8.8541878128e-12, 1e-9, 3.0
BETA_BOOST, BETA_PULSE = .6, .2


def add(a,b): return tuple(x+y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def mul(s,a): return tuple(s*x for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def norm(a): return math.sqrt(dot(a,a))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def transpose(a): return list(map(list,zip(*a)))
def matmul(a,b): return [[dot(row,col) for col in zip(*b)] for row in a]
def matvec(a,v): return tuple(dot(row,v) for row in a)


def boost(beta):
    if abs(beta)>=1: raise ValueError('An inertial boost requires |beta| < 1')
    g=1/math.sqrt(1-beta*beta)
    return [[g,-g*beta,0,0],[-g*beta,g,0,0],[0,0,1,0],[0,0,0,1]]


def tensor(e,b):
    # b is c*B in the same normalized units as E; tensor represents c*F.
    ex,ey,ez=e;bx,by,bz=b
    return [[0,-ex,-ey,-ez],[ex,0,-bz,by],[ey,bz,0,-bx],[ez,-by,bx,0]]


def extract(f): return (-f[0][1],-f[0][2],-f[0][3]),(-f[2][3],f[1][3],-f[1][2])


def transform_components(e,b,beta):
    g=1/math.sqrt(1-beta*beta)
    return (e[0],g*(e[1]-beta*b[2]),g*(e[2]+beta*b[1])),(b[0],g*(b[1]+beta*e[2]),g*(b[2]-beta*e[1]))


def uniform(s,beta=.6):
    return (beta*s,0.,0.),(beta,0.,0.),(0.,0.,0.)


def pulse(s,b=BETA_PULSE):
    if not 0<=b<1: raise ValueError('Prescribed pulse requires 0 <= b < 1')
    if s<=0:return (0.,0.,0.),(0.,0.,0.),(0.,0.,0.)
    if s>=1:return (b/2,0.,0.),(0.,0.,0.),(0.,0.,0.)
    x=b*(s/2-math.sin(2*math.pi*s)/(4*math.pi))
    return (x,0.,0.),(b*math.sin(math.pi*s)**2,0.,0.),(b*math.pi*math.sin(2*math.pi*s),0.,0.)


def retarded_time(pos,t,trajectory):
    def h(s): return s+norm(sub(pos,trajectory(s)[0]))-t
    if norm(sub(pos,trajectory(t)[0]))<1e-13:raise ValueError('Observation event is on the point-charge worldline')
    right=t;span=max(1.,norm(sub(pos,trajectory(t)[0])));left=t-span
    for _ in range(64):
        if h(left)<0:break
        span*=2;left=t-span
    else:raise ValueError('No past root bracket; source history or domain is incomplete')
    for _ in range(90):
        middle=(left+right)/2
        if h(middle)>0:right=middle
        else:left=middle
    s=(left+right)/2
    return s,h(s)


def geometry(pos,s,trajectory):
    source,beta,betadot=trajectory(s)
    rr=sub(pos,source);r=norm(rr)
    if r==0:raise ValueError('Point-source singularity')
    n=mul(1/r,rr);kappa=1-dot(n,beta)
    if norm(beta)>=1 or kappa<=0:raise ValueError('Sub-luminal prescribed source required')
    return r,n,kappa,beta,betadot


def at_source_time(pos,s,trajectory):
    r,n,kappa,beta,betadot=geometry(pos,s,trajectory)
    ev=mul((1-dot(beta,beta))/(kappa**3*r*r),sub(n,beta))
    ea=mul(1/(kappa**3*r),cross(n,cross(sub(n,beta),betadot)))
    e=add(ev,ea);b=cross(n,e)
    return e,b,ev,ea,r,kappa


def potentials(pos,t,trajectory):
    s,_=retarded_time(pos,t,trajectory)
    r,_,kappa,beta,_=geometry(pos,s,trajectory)
    phi=1/(kappa*r)
    return phi,mul(phi,beta)


def derivative(fun,pos,axis,h):
    lo=list(pos);hi=list(pos);lo[axis]-=h;hi[axis]+=h
    return (fun(hi)-fun(lo))/(2*h)


def curl(fun,pos,h):
    return tuple(derivative(lambda x:fun(x)[(j+2)%3],pos,(j+1)%3,h)
                 -derivative(lambda x:fun(x)[(j+1)%3],pos,(j+2)%3,h) for j in range(3))


def field_from_potentials(pos,t,trajectory,h):
    e=[]
    for j in range(3):
        grad=derivative(lambda x:potentials(x,t,trajectory)[0],pos,j,h)
        ad=(potentials(pos,t+h,trajectory)[1][j]-potentials(pos,t-h,trajectory)[1][j])/(2*h)
        e.append(-grad-ad)
    return tuple(e),curl(lambda x:potentials(x,t,trajectory)[1],pos,h)


def simpson(fun,a,b,n=800):
    if n<=0 or n%2:raise ValueError('Simpson requires positive even panel count')
    step=(b-a)/n
    return step/3*(fun(a)+fun(b)+sum((4 if j%2 else 2)*fun(a+j*step) for j in range(1,n)))


def svg_start(title,desc,w=1000,h=450):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<title>{title}</title><desc>{desc}</desc>',
            '<defs><marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="context-stroke"/></marker></defs>',
            '<rect width="100%" height="100%" fill="#fcfcfa"/>',
            '<g fill="#152b3b" font-family="sans-serif" font-size="15">',
            f'<text x="30" y="30" font-size="21">{title}</text>']

def text(x,y,s,size=15):return f'<text x="{x}" y="{y}" font-size="{size}">{s}</text>'
def line(x1,y1,x2,y2,color='#718390',width=1,dash='',arrow=False):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"'+(' marker-end="url(#arr)"' if arrow else '')+'/>'
def poly(points,color,dash=''):
    return '<polyline fill="none" stroke="'+color+'" stroke-width="2.8" stroke-dasharray="'+dash+'" points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+'"/>'
def circle(x,y,r=5,color='#a54b00'):return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'
def save_svg(p,s):p.write_text('\n'.join(s+['</g></svg>'])+'\n')


def figures(assets,rows,report):
    s=svg_start('One event, two frames: fields and force', 'S prime moves at +0.6c along x. E, cB and force use separate normalizations. A circled cross means negative z.')
    for ox,label in [(220,'S: charge instantaneously at rest'),(690,"S prime: observer moves at +0.6c")]:
        s += [text(ox-160,70,label),line(ox-80,330,ox+150,330),line(ox,370,ox,130),text(ox+140,355,'x'),text(ox+10,140,'y')]
    s += [line(220,325,220,225,'#006b8f',4,arrow=True),text(95,205,'E/E0 = +1 y'),line(280,325,280,225,'#a54b00',4,arrow=True),text(302,260,'f/(qE0) = +1 y'),text(130,390,'B = 0; u = 0')]
    s += [line(690,325,690,200,'#006b8f',4,arrow=True),text(520,175,'E prime/E0 = +1.25 y'),line(750,325,750,245,'#a54b00',4,arrow=True),text(765,285,'f prime/(qE0) = +0.8 y'),line(682,325,620,325,'#395c46',3,arrow=True),text(505,385,'u prime/c = -0.6 x')]
    s += ['<circle cx="855" cy="215" r="14" fill="none" stroke="#7b3e82" stroke-width="2"/>',line(847,207,863,223,'#7b3e82',2),line(847,223,863,207,'#7b3e82',2),text(765,185,'cB prime/E0 = -0.75 z'),text(70,430,'The magnetic force in S prime points along -y; it reduces the electric force.')]
    save_svg(assets/'frame-fields.svg',s)
    s=svg_start('Uniform charge: the retarded event is not its present position','Left: source worldline and the past-cone cut at y=0 for an observer at y=b. Right: spatial geometry at beta=0.6, t=0. Axes normalized by b.')
    px=lambda x:310+150*x;py=lambda ct:100-150*ct
    s += [text(60,65,'Space-time cut: source y=0, observer y=b'),line(70,100,430,100),line(310,100,310,410),text(320,400,'ct/b'),text(395,90,'x/b')]
    cone=[(px(x),py(-math.sqrt(1+x*x))) for x in [-1.45+1.85*j/150 for j in range(151)]]
    world=[(px(.6*t),py(t)) for t in [-2+j/100 for j in range(201)]]
    s += [text(px(-1)-8,88,'-1'),text(295,88,'0'),text(320,py(-1)-7,'-1'),text(280,py(-2)-5,'-2'),poly(cone,'#006b8f'),poly(world,'#a54b00'),circle(px(-.75),py(-1.25)),circle(px(0),py(0),4,'#152b3b'),text(332,290,'retarded:'),text(332,312,'(-0.75, -1.25)',14),line(px(-.75)+7,py(-1.25)+2,322,290,'#a54b00'),text(335,135,'t=0'),text(65,430,'Blue: ct/b = -sqrt(1+(x/b)^2)')]
    ox,oy,scale=755,350,175
    s += [text(545,65,'Spatial geometry: y/b versus x/b'),line(535,oy,950,oy),line(ox,oy+35,ox,95),text(927,375,'x/b'),text(765,110,'y/b')]
    sx=ox-.75*scale;obs_y=oy-scale
    s += [circle(sx,oy),circle(ox,oy,5,'#152b3b'),circle(ox,obs_y,5,'#006b8f'),line(sx,oy-5,ox,obs_y+6,'#718390',2,'5 4',True),line(ox,obs_y-10,ox,obs_y-65,'#006b8f',3,arrow=True),text(775,145,'E along +y'),text(770,190,'observer (0, 1)'),text(570,390,'past charge'),text(748,410,'present charge'),text(642,265,'R / n'),text(555,430,'R/b = 1.25; kappa = 0.64')]
    save_svg(assets/'retarded-worldline.svg',s)
    s=svg_start('A stopped source can still produce a delayed radiation pulse','Left: finite-distance Ex velocity, acceleration and total components. Right: asymptotic +y instantaneous angular power. Time axes differ as labeled.')
    left,right,top,bottom=75,450,100,350
    tx=lambda t:left+(t-.8)/1.45*(right-left)
    fy=lambda val:bottom-(val+1)/2.0*(bottom-top)
    s += [text(60,65,'Finite observer (0,L): Ex / E*'),line(left,top,left,bottom),line(left,bottom,right,bottom)]
    for v in [-1,0,1]:s += [line(left,fy(v),right,fy(v),'#dbe1e5'),text(left-34,fy(v)+5,str(v))]
    for t in [1,1.5,2]:s += [text(tx(t)-8,376,str(t))]
    for idx,color,dash in [(2,'#006b8f',''),(3,'#a54b00','7 4'),(4,'#395c46','2 4')]:s.append(poly([(tx(row[1]),fy(row[idx])) for row in rows],color,dash))
    s += [text(320,406,'t/T'),text(72,435,'solid: total; dashed: velocity; dotted: acceleration')]
    xl,xr=575,945;xx=lambda u:xl+u*(xr-xl);yy=lambda p:350-p*250
    s += [text(555,65,'Far +y direction: U/Umax'),line(xl,100,xl,350),line(xl,350,xr,350)]
    for v in [0,.5,1]:s += [line(xl,yy(v),xr,yy(v),'#dbe1e5'),text(xl-35,yy(v)+5,str(v))]
    s += [poly([(xx(j/200),yy(math.sin(2*math.pi*j/200)**2)) for j in range(201)],'#7b3e82')]
    for u in [0,.5,1]:s += [text(xx(u)-8,376,str(u))]
    s += [text(770,406,'(t-r/c)/T'),text(580,435,'Instantaneous power; no cycle average')]
    save_svg(assets/'motion-pulse.svg',s)


def generate(out):
    out.mkdir(parents=True,exist_ok=True);assets=out/'assets';assets.mkdir(exist_ok=True)
    lam=boost(.6);e=(0.,1.,0.);b=(0.,0.,0.)
    ep,bp=extract(matmul(matmul(lam,tensor(e,b)),transpose(lam)))
    uprime=matvec(lam,(1.,0.,0.,0.));up=mul(1/uprime[0],uprime[1:])
    force=add(ep,cross(up,bp));four=matvec(lam,(0.,0.,1.,0.));force4=mul(1/uprime[0],four[1:])
    assert norm(sub(force,force4))<1e-14
    metric=[[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,-1]]
    transformed_metric=matmul(matmul(transpose(lam),metric),lam)
    assert max(abs(transformed_metric[i][j]-metric[i][j]) for i in range(4) for j in range(4))<1e-14
    invariant_error=component_error=0.
    for vb in [-.85,-.2,.0,.6,.93]:
        for ee,bb in [((.4,.7,-.2),(.3,-.9,.1)),((0,1,0),(0,0,1)),((1,0,0),(0,0,0))]:
            la=boost(vb);ee1,bb1=extract(matmul(matmul(la,tensor(ee,bb)),transpose(la)))
            ee2,bb2=transform_components(ee,bb,vb)
            component_error=max(component_error,norm(sub(ee1,ee2)),norm(sub(bb1,bb2)))
            invariant_error=max(invariant_error,abs(dot(ee1,ee1)-dot(bb1,bb1)-dot(ee,ee)+dot(bb,bb)),abs(dot(ee1,bb1)-dot(ee,bb)))
    assert invariant_error<2e-14 and component_error<2e-14
    # Independently expand the covariant force for a moving test particle and mixed fields.
    ee,bb=(.4,.7,-.2),(.3,-.9,.1)
    uu=(.2,-.3,.1);gu=1/math.sqrt(1-dot(uu,uu));U=(gu,)+mul(gu,uu)
    lower=(U[0],)+mul(-1,U[1:]);K=matvec(tensor(ee,bb),lower)
    direct_force=add(ee,cross(uu,bb))
    assert norm(sub(mul(1/gu,K[1:]),direct_force))<1e-14
    assert abs(K[0]/gu-dot(ee,uu))<1e-14 and abs(dot(K,lower))<1e-14
    Up=matvec(lam,U);Kp=matvec(lam,K)
    Fp=matmul(matmul(lam,tensor(ee,bb)),transpose(lam))
    Kp2=matvec(Fp,(Up[0],)+mul(-1,Up[1:]))
    covariant_force_error=norm(sub(Kp,Kp2))
    assert covariant_force_error<1e-14
    J=(.8,.1,-.2,.3);Jp=matvec(lam,J)
    assert norm(sub(Jp,(1.25*(J[0]-.6*J[1]),1.25*(J[1]-.6*J[0]),J[2],J[3])))<1e-14
    # Uniform source: compare generic root/LW fields with a closed root and independent rest-frame boost.
    pos=(0.,1.,0.);s,res=retarded_time(pos,0.,uniform);g=1.25
    eu,bu,_,_,ru,ku=at_source_time(pos,s,uniform)
    rest_e=(0.,1.,0.);rest_b=(0.,0.,0.)
    eb,bb=extract(matmul(matmul(boost(-.6),tensor(rest_e,rest_b)),transpose(boost(-.6))))
    assert abs(s+g)<1e-14 and norm(sub(eu,eb))<1e-13 and norm(sub(bu,bb))<1e-13
    generic_errors=[]
    for point,tt in [((1.2,.7,.2),.3),((2.,-.8,1.),1.),((.2,1.2,-.3),-.5)]:
        ss,resid=retarded_time(point,tt,uniform);r0=sub(point,(.6*tt,0,0));vv=(.6,0,0)
        delay=(dot(r0,vv)+math.sqrt(dot(r0,vv)**2+.64*dot(r0,r0)))/.64
        exact=mul(.64/(dot(r0,r0)-dot(cross(vv,r0),cross(vv,r0)))**1.5,r0)
        calc=at_source_time(point,ss,uniform)[0]
        generic_errors.append(max(abs(ss-(tt-delay)),norm(sub(calc,exact)),abs(resid)))
    assert max(generic_errors)<1e-13
    pulse_checks=[];rows=[]
    for j in range(281):
        u=-.2+j*.005
        xp=pulse(u)[0][0];arrival=u+math.sqrt(1+xp*xp)
        solved,resid=retarded_time(pos,arrival,pulse)
        assert abs(solved-u)<3e-14 and abs(resid)<3e-14
        ee,bb,ev,ea,_,_=at_source_time(pos,solved,pulse)
        rows.append((u,arrival,ee[0],ev[0],ea[0],ee[1],xp))
    for u in [.25,.5,.75]:
        arrival=u+norm(sub(pos,pulse(u)[0]));ee,bb,ev,ea,_,_=at_source_time(pos,u,pulse)
        errs=[]
        for h in [2e-4,1e-4]:
            ed,bd=field_from_potentials(pos,arrival,pulse,h)
            errs.append(dict(step=h,e_relative=norm(sub(ed,ee))/norm(ee),b_relative=norm(sub(bd,bb))/max(norm(bb),.1)))
        assert max(errs[-1]['e_relative'],errs[-1]['b_relative'])<2e-6
        pulse_checks.append(dict(source_u=u,observer_tau=arrival,ex_velocity=ev[0],ex_acceleration=ea[0],ex_total=ee[0],finite_difference=errs))
    # Far transverse directional energy. Finite-distance acceleration-only diagnostic is not total flux.
    ideal_integral=BETA_PULSE**2*math.pi**2/2
    quadrature=simpson(lambda u:(BETA_PULSE*math.pi*math.sin(2*math.pi*u))**2,0,1)
    assert abs(quadrature-ideal_integral)<1e-14
    convergence=[]
    for distance in [10.,30.,100.,300.]:
        def integrand(u):
            _,_,_,ea,_,kappa=at_source_time((0,distance,0),u,pulse)
            return distance**2*dot(ea,ea)*kappa
        val=simpson(integrand,0,1)
        convergence.append(dict(r_over_L=distance,normalized_energy=val,relative_to_far_limit=val/ideal_integral-1))
    assert abs(convergence[-1]['relative_to_far_limit'])<abs(convergence[0]['relative_to_far_limit'])
    static_trajectory=lambda ss:pulse(ss,0.)
    static_s,_=retarded_time(pos,1.5,static_trajectory)
    static_e,static_b,*_=at_source_time(pos,static_s,static_trajectory)
    assert norm(sub(static_e,(0.,1.,0.)))<1e-14 and norm(static_b)<1e-14
    low_speed_errors=[]
    for speed in [.01,.005]:
        trajectory=lambda ss,speed=speed:uniform(ss,speed)
        ss,_=retarded_time(pos,0.,trajectory)
        low_speed_errors.append(norm(sub(at_source_time(pos,ss,trajectory)[0],(0.,1.,0.))))
    low_speed_ratio=low_speed_errors[0]/low_speed_errors[1]
    assert 3.99<low_speed_ratio<4.01
    # Explicit failure checks: superluminal boost and the singular observation event.
    rejected=[]
    for label,func in [('boost_beta_1',lambda:boost(1)),('on_worldline',lambda:retarded_time((0,0,0),0,uniform)),('pulse_beta_1',lambda:pulse(.5,1))]:
        try:func()
        except ValueError:rejected.append(label)
        else:raise AssertionError('Invalid domain accepted: '+label)
    tm=L/C;escale=Q/(4*math.pi*EPS*L*L)
    report=dict(si_inputs=dict(c_m_per_s=C,epsilon_F_per_m=EPS,q_C=Q,L_m=L,T_s=tm,beta_boost=.6,beta_pulse=.2),
                uniform_field=dict(Eprime_over_E0=ep,cBprime_over_E0=bp,Bprime_T_for_E0_1V_per_m=mul(1/C,bp),forceprime_over_qE0=force,invariant_1=dot(ep,ep)-dot(bp,bp),invariant_2=dot(ep,bp),matrix_component_max_error=component_error,mixed_field_invariant_max_error=invariant_error,covariant_force_max_error=covariant_force_error,four_current_example=Jp),
                test_particle_alpha_t_over_c_1=dict(u_y_over_c=1/math.sqrt(2),uprime_y_over_c=1/(g*math.sqrt(2)),uprime_magnitude_over_c=math.sqrt(.6**2+1/(2*g*g))),
                uniform_charge=dict(retarded_s_in_b_over_c=s,retarded_time_ns=s*tm*1e9,retarded_x_m=.6*s*L,R_m=ru*L,kappa=ku,E_V_per_m=mul(escale,eu),B_T=mul(escale/C,bu),phi_V=Q/(4*math.pi*EPS)/(ku*ru*L),generic_closed_form_max_error=max(generic_errors),root_residual=res),
                pulse=dict(arrival_window_tau=[1,1+math.sqrt(1+BETA_PULSE**2/4)],arrival_window_ns=[tm*1e9,(1+math.sqrt(1+BETA_PULSE**2/4))*tm*1e9],checks=pulse_checks,directional_energy_J_per_sr=Q*Q*BETA_PULSE**2/(32*EPS*C*tm),directional_peak_W_per_sr=Q*Q*BETA_PULSE**2/(16*EPS*C*tm*tm),far_energy_quadrature_abs_error=abs(quadrature-ideal_integral),finite_distance_acceleration_only_convergence=convergence),static_pulse_field=static_e,low_speed_error_ratio_when_beta_halved=low_speed_ratio,rejected_domains=rejected)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    with (out/'motion-pulse.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['source_u','observer_tau','Ex_total_over_Estar','Ex_velocity_over_Estar','Ex_acceleration_over_Estar','Ey_total_over_Estar','source_X']);w.writerows(rows)
    with (out/'far-direction.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['retarded_time_over_T','U_over_Umax']);w.writerows((j/200,math.sin(2*math.pi*j/200)**2) for j in range(201))
    figures(assets,rows,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    generate(parser.parse_args().out)
