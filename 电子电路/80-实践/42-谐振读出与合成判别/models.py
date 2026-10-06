"""Finite classical resonator/IQ bench with explicitly symmetrized noise budget.
No quantum-state dynamics, hardware fidelity, global state or import-time work.
"""
import math,cmath,numbers
H=6.62607015e-34
KB=1.380649e-23

def real(x,name,lo,hi):
 if isinstance(x,bool) or not isinstance(x,numbers.Real):raise ValueError(name+' real scalar required')
 try:
  if not lo<=x<=hi:raise ValueError(name+' outside finite teaching domain')
  v=float(x)
 except (OverflowError,TypeError):raise ValueError(name+' outside convertible finite domain') from None
 if not math.isfinite(v):raise ValueError(name+' finite required')
 return v

def wave(z,name,limit):
 if isinstance(z,bool) or not isinstance(z,numbers.Complex):raise ValueError(name+' complex scalar required')
 return complex(real(z.real,name+' real',-limit,limit),real(z.imag,name+' imag',-limit,limit))

def cavity_parameters(kappa,eta,delta):
 kappa=real(kappa,'kappa',1e5,1e9);eta=real(eta,'external fraction',.01,1);delta=real(delta,'delta',-5*kappa,5*kappa)
 return kappa,eta,delta

def reflection(kappa=2*math.pi*5e6,eta=.8,delta=0):
 """Dimensionless one-port coefficient, detuning omega_r-omega_d [rad/s]."""
 kappa,eta,delta=cavity_parameters(kappa,eta,delta)
 return 1-eta*kappa/(kappa/2+1j*delta)

def cavity_step(a,b,dt,kappa=2*math.pi*5e6,eta=.8,delta=0):
 """a sqrt(J), b sqrt(W), dt seconds; exact interval-end state & output bout sqrt(W).
 Drive held constant. dt1ps..1us, |a components|<=1e-9, |b components|<=1e-3.
 """
 kappa,eta,delta=cavity_parameters(kappa,eta,delta);dt=real(dt,'dt',1e-12,1e-6)
 a=wave(a,'a',1e-9);b=wave(b,'b',1e-3);lam=kappa/2+1j*delta;x=kappa*dt/2;y=delta*dt
 # Stable 1-exp(-lam*dt), including startup rather than subtracting two steady states.
 one_minus=complex(-math.expm1(-x)+math.exp(-x)*2*math.sin(y/2)**2,math.exp(-x)*math.sin(y))
 state=a*cmath.exp(-lam*dt)+math.sqrt(eta*kappa)*b/lam*one_minus
 return state,b-math.sqrt(eta*kappa)*state

def occupation(f=6e9,temperature=.02):
 """Bose n; f1..20GHz, T=0 or .01..300K. Zero is the analytic T=0 limit."""
 f=real(f,'f',1e9,20e9);temperature=real(temperature,'T',0,300)
 if temperature==0:return 0.
 if temperature<.01:raise ValueError('finite temperature domain .01..300K or exact zero')
 return 1/math.expm1(H*f/(KB*temperature))

def sym_noise(f=6e9,temperature=.02):
 """Matched symmetrized equivalent energy per Hz [J=W/Hz], hf(n+1/2), not emission power."""
 return H*real(f,'f',1e9,20e9)*(occupation(f,temperature)+.5)

def quantum_chain(f=6e9,t_source=.02,loss_efficiency=.5,t_loss=.02,g1=100.,added1=.5,g2=1000.,added2=20.):
 """Matched narrowband phase-preserving amplifiers; power gains, input-added sym quanta.
 Returns amplifier sym q and ideal heterodyne measurement-equivalent q separately.
 Final energy/Hz uses measurement q including +.5 at output. Independent baths.
 """
 f=real(f,'f',1e9,20e9);eff=real(loss_efficiency,'eff',.01,1)
 g1=real(g1,'G1',1,1e6);g2=real(g2,'G2',1,1e6)
 n1=real(added1,'added1',0,1000);n2=real(added2,'added2',0,1000)
 if n1<(1-1/g1)/2 or n2<(1-1/g2)/2:raise ValueError('added noise below declared phase-preserving bound')
 qi=occupation(f,t_source)+.5;qb=occupation(f,t_loss)+.5
 qloss=eff*qi+(1-eff)*qb;qout=g2*(g1*(qloss+n1)+n2);gain=eff*g1*g2
 return dict(power_gain=gain,output_sym_quanta=qout,source_referred_sym_quanta=qout/gain,ideal_heterodyne_output_added_quanta=.5,measurement_equiv_sym_quanta=qout+.5,measurement_source_referred_sym_quanta=(qout+.5)/gain,output_energy_per_Hz_J=H*f*(qout+.5))

def iq_forward(z,matrix=((1.,.08),(.02,.9)),offset=(2e-6,-3e-6)):
 """Peak voltage envelope affine map; each matrix element -2..2, offsets +/-1V."""
 z=wave(z,'z',1.)
 if not isinstance(matrix,(list,tuple)) or len(matrix)!=2 or any(not isinstance(r,(list,tuple)) or len(r)!=2 for r in matrix):raise ValueError('2x2 matrix required')
 if not isinstance(offset,(list,tuple)) or len(offset)!=2:raise ValueError('two offsets required')
 a,b,c,d=[real(v,'matrix',-2,2) for r in matrix for v in r];oi,oq=[real(v,'offset',-1,1) for v in offset]
 return complex(a*z.real+b*z.imag+oi,c*z.real+d*z.imag+oq)

def iq_inverse(z,matrix=((1.,.08),(.02,.9)),offset=(2e-6,-3e-6)):
 """Inverse of full affine I/Q map; reject det magnitude <.05 (finite calibration domain)."""
 iq_forward(0,matrix,offset);z=wave(z,'z',5.);a,b=matrix[0];c,d=matrix[1];det=a*d-b*c
 if abs(det)<.05:raise ValueError('ill-conditioned calibration domain')
 x=z.real-offset[0];y=z.imag-offset[1]
 return complex((d*x-b*y)/det,(-c*x+a*y)/det)

def mean_complex(samples):
 if not isinstance(samples,(list,tuple)) or not 1<=len(samples)<=4096:raise ValueError('finite flat sequence required')
 v=[wave(x,'sample',5) for x in samples];return complex(math.fsum(x.real for x in v)/len(v),math.fsum(x.imag for x in v)/len(v))

def gaussian_error(mu0,mu1,sigma):
 """Equal-prior/equal isotropic covariance centroids; sigma each I/Q coordinate V."""
 mu0=wave(mu0,'mu0',1);mu1=wave(mu1,'mu1',1);sigma=real(sigma,'sigma',1e-9,1)
 return .5*math.erfc(abs(mu1-mu0)/(2*math.sqrt(2)*sigma))

def classify(z,mu0,mu1):
 z=wave(z,'z',5);mu0=wave(mu0,'mu0',1);mu1=wave(mu1,'mu1',1)
 if abs(mu1-mu0)<1e-12:raise ValueError('unresolved centroids')
 return int(((z-(mu0+mu1)/2)*(mu1-mu0).conjugate()).real>=0)

def fit_iq(y0,yi,yq,amplitude=1e-4):
 """Three independent synthetic axis calibration points; amplitude peak V.
 No calibration uncertainty certificate; apply only same constant affine map.
 """
 amplitude=real(amplitude,'calibration amplitude',1e-5,.1)
 y0=wave(y0,'y0',1);yi=wave(yi,'yi',1);yq=wave(yq,'yq',1)
 c1=(yi-y0)/amplitude;c2=(yq-y0)/amplitude
 mat=((c1.real,c2.real),(c1.imag,c2.imag));off=(y0.real,y0.imag)
 iq_inverse(y0,mat,off)
 return mat,off
