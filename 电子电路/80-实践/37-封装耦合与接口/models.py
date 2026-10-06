"""Finite teaching budgets; standard-library only, no import-time work."""
import math,cmath

def real(x,name,lo,hi):
 if type(x) not in (int,float):raise ValueError(name+' requires real scalar')
 try:x=float(x)
 except (OverflowError,ValueError):raise ValueError(name+' range') from None
 if not math.isfinite(x) or not lo<=x<=hi:raise ValueError(name+' range')
 return x

def integer(x,name,lo,hi):
 if type(x) is not int or not lo<=x<=hi:raise ValueError(name+' integer range')
 return x

def interface(lanes,rate_bps,coding,payload_bytes,frame_bytes,utilization,message_bytes,fixed_s,energy_J_per_wire_bit,idle_W):
 n=integer(lanes,'lanes',1,256);r=real(rate_bps,'NRZ bit/s/lane',1e8,64e9);ce=real(coding,'coding efficiency',.25,1);p=integer(payload_bytes,'payload bytes',1,4096);f=integer(frame_bytes,'frame bytes',p,8192);u=real(utilization,'scheduled duty',.01,1);msg=integer(message_bytes,'message bytes',1,1048576);fixed=real(fixed_s,'nonserialization fixed delay s',0,1e-3);en=real(energy_J_per_wire_bit,'energy J/wire bit',1e-15,1e-9);idle=real(idle_W,'idle W',0,10)
 frames=(msg+p-1)//p;wire_bits=frames*f*8/ce;raw=n*r
 return {'raw_bps_one_direction':raw,'useful_bps':raw*ce*(p/f)*u,'frames':frames,'wire_bits':wire_bits,'serialization_s_no_queue':wire_bits/raw,'latency_s_no_queue':fixed+wire_bits/raw,'dynamic_W_at_duty':en*raw*u,'total_link_W':idle+en*raw*u,'message_dynamic_J':en*wire_bits,'note':'all bytes before adapter overhead are protocol information, not necessarily application payload; no retries/queue/training in delay'}

def rlc_parameters(R,L,C):
 r=real(R,'total series ohm',.1,200);l=real(L,'loop H',1e-12,1e-8);c=real(C,'shunt F',1e-14,1e-10);w=1/math.sqrt(l*c);z=r/2*math.sqrt(c/l)
 if not .1<=z<=.9:raise ValueError('step teaching domain requires underdamped .1<=zeta<=.9')
 return r,l,c,w,z

def rlc_transfer(R,L,C,f_Hz):
 r,l,c,w,z=rlc_parameters(R,L,C);f=real(f_Hz,'Hz',0,1e12);s=2j*math.pi*f
 return 1/(l*c*s*s+r*c*s+1)

def rlc_step(R,L,C,t_s):
 r,l,c,w,z=rlc_parameters(R,L,C);t=real(t_s,'s',0,1e-6);u=w*t
 if 0<u<.001:raise ValueError('startup smaller than normalized .001 unsupported')
 if t==0:return {'voltage_per_V':0.,'current_A_per_V':0.}
 b=math.sqrt(1-z*z);q=math.exp(-z*u);a=b*u
 return {'voltage_per_V':1-q*(math.cos(a)+z/b*math.sin(a)),'current_A_per_V':c*w*q*math.sin(a)/b}

def thermal(P1,P2,Rambient,Rcouple,C,t_s,ambient_K=300):
 p=real(P1,'P1 W',0,100);q=real(P2,'P2 W',0,100);r=real(Rambient,'each ambient K/W',.1,20);rc=real(Rcouple,'between nodes K/W',.1,100);cap=real(C,'each J/K',.01,100);t=real(t_s,'seconds',0,1e4);amb=real(ambient_K,'ambient K',250,400);g=1/r;h=1/rc
 if any(0<v<1e-6 for v in [p,q,t]):raise ValueError('thermal nonzero power/time minimum 1e-6 W/s')
 mean=(p+q)/(2*g);half=(p-q)/(2*(g+2*h));em=-math.expm1(-g*t/cap);ed=-math.expm1(-(g+2*h)*t/cap)
 return {'steady_rise_K':[mean+half,mean-half],'rise_K':[mean*em+half*ed,mean*em-half*ed],'temperature_K':[amb+mean*em+half*ed,amb+mean*em-half*ed],'time_constants_s':[cap/g,cap/(g+2*h)],'initial_rise_K':[0.,0.]}

def thermo_mechanical(alpha1_per_K,alpha2_per_K,delta_K,distance_m,joint_height_m):
 a=real(alpha1_per_K,'alpha1 1/K',0,50e-6);b=real(alpha2_per_K,'alpha2 1/K',0,50e-6);d=real(delta_K,'delta K',-100,100);x=real(distance_m,'neutral distance m',1e-4,.05);h=real(joint_height_m,'height m',1e-5,.001);u=(a-b)*d*x
 return {'free_mismatch_m':u,'kinematic_shear_estimate':u/h,'lifetime_claim':False}

def leakage_equilibrium(P0_per_die,alpha_W_per_K,Rambient):
 p=real(P0_per_die,'baseline per die W',0,100);a=real(alpha_W_per_K,'linearized leakage W/K',0,1);r=real(Rambient,'K/W',.1,20);g=1/r
 if g-a<.01 or p/(g-a)>200:raise ValueError('unstable or outside teaching linearized equilibrium domain')
 return {'uniform_rise_K':p/(g-a),'stability_margin_W_per_K':g-a,'linearization_only':True}

def yield_cost(die_areas_cm2,defect_per_cm2,wafer_cost_per_cm2,test_cost_each,assembly_cost,assembly_yield):
 if type(die_areas_cm2) not in (list,tuple) or not 1<=len(die_areas_cm2)<=8:raise ValueError('1..8 die areas')
 areas=[real(x,'die cm2',.01,10) for x in die_areas_cm2];d=real(defect_per_cm2,'defects/cm2',0,2);cost=real(wafer_cost_per_cm2,'cost/processed cm2',1,1000);test=real(test_cost_each,'test/die cost',0,100);ass=real(assembly_cost,'assembly cost',0,1000);y=real(assembly_yield,'assembly yield',.1,1)
 ys=[math.exp(-d*a) for a in areas];known=sum((cost*a+test)/yi for a,yi in zip(areas,ys));return {'die_yields':ys,'known_good_die_input_cost':known,'cost_per_good_assembly':(known+ass)/y,'assumptions':'independent Poisson defects; perfect sorting, no repair, one die of each area per system, homogeneous cost; no shared-correlated losses'}
