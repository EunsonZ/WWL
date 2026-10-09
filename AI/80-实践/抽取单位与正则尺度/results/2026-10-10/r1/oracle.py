"""Independent trigonometric and Fraction quadratic oracle. No course imports."""
from fractions import Fraction as F
from math import cos,sin,pi,sqrt,hypot
from pathlib import Path
import json,sys
P=Path(__file__).resolve().parent

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def mv(a,v):return [dot(row,v) for row in a]
def trans(a):return list(map(list,zip(*a)))
def product(a,b):return [[dot(row,col) for col in zip(*b)] for row in a]
def quad(m,x):return dot(x,mv(m,x))
def objective(x,y,r,lam,w):
 residual=[a-b for a,b in zip(mv(x,w),y)]
 return quad(r,residual)+quad(lam,w)
def close(actual,expected):
 assert len(actual)==len(expected)
 errors=[abs(a-b) for a,b in zip(actual,expected)]
 assert max(errors,default=0)<1e-11
 return max(errors,default=0)
def expectations():
 n=24
 low=[cos(2*pi*t/8) for t in range(n)];high=[cos(2*pi*3*t/8) for t in range(n)]
 a={'low_first_eight':low[:8],'high_first_eight':high[:8],'low_downsampled':[cos(pi*m/2) for m in range(12)],'high_downsampled':[cos(pi*m/2) for m in range(12)],'gains':[cos(pi/8),cos(3*pi/8),0.],'square_downsampled':[(1+cos(4*pi*m/3))/2 for m in range(12)],'filter_square_downsampled':[(1+cos(4*pi*m/3))/2 for m in range(12)],'square_filter_downsampled':[.5]*12}
 s=[]
 # Minimize scalar quadratic via completed square: q(v)=Av²-2Bv+C.
 for d in [F(100),F(10)]:
  A=d*d+1;B=d;Ap=2*d*d
  s.append({'scale':d,'untransformed_coefficient':B/A,'untransformed_prediction':d*B/A,'transformed_penalty':d*d,'preserved_coefficient':B/Ap,'preserved_prediction':d*B/Ap})
 return {'aliasing':a,'scaling':{'scalar':s,'hessian_v':[[F(1),F(0)],[F(0),F(1)]],'dd_transpose':[[F(1),F(0)],[F(0),F(1,100)]],'ordinary_w_step':[F(99,100),F(0)],'mapped_v_step':[F(99,100),F(99,100)]}}
def run():
 ex=expectations();a=json.loads((P/'aliasing.stdout').read_text());s=json.loads((P/'scaling.stdout').read_text())
 errs={k:close(a[k],v) for k,v in ex['aliasing'].items()}
 def fractions(v):
  if isinstance(v,list):return [fractions(x) for x in v]
  if isinstance(v,dict):return {k:fractions(x) for k,x in v.items()}
  return F(v)
 assert fractions(s)==ex['scaling']
 low=[cos(pi*t/4) for t in range(24)];high=[cos(3*pi*t/4) for t in range(24)]
 assert max(abs(x-y) for x,y in zip(low,high))>1
 p1low=low[1::2];p1high=high[1::2];assert max(abs(x+y) for x,y in zip(p1low,p1high))<1e-11
 filters=[]
 for omega in [pi/4,3*pi/4]:
  # Causal two-tap periodic convolution; analytic phase matters as well as gain.
  signal=[cos(omega*n) for n in range(24)];y=[(signal[n]+signal[(n-1)%24])/2 for n in range(24)]
  analytic=[cos(omega/2)*cos(omega*(n-.5)) for n in range(24)]
  err=close(y,analytic)
  zero_boundary=(signal[0]+0)/2
  filters.append({'omega':omega,'gain':cos(omega/2),'phase':-omega/2,'periodic_vs_phase_error':err,'periodic_first':y[0],'zero_extended_first':zero_boundary})
 phase0=low[::2];shift1=[low[(2*m-1)%24] for m in range(12)]
 mismatch=[max(abs(shift1[m]-phase0[(m-q)%12]) for m in range(12)) for q in range(12)]
 assert min(mismatch)>.1
 even=[low[(2*m-2)%24] for m in range(12)];assert close(even,[phase0[(m-1)%12] for m in range(12)])<1e-11
 energy0=sum(x*x for x in phase0);energy1=sum(x*x for x in shift1);assert abs(energy0-energy1)<1e-12
 # General finite example: corresponding predictions/objectives, all exact.
 X=[[F(1),F(2)],[F(3),F(-1)]];D=[[F(2),F(1)],[F(0),F(1,5)]];R=[[F(2),F(0)],[F(0),F(3)]];L=[[F(2),F(1)],[F(1),F(3)]];y=[F(1),F(-2)]
 XD=product(X,D);Lv=product(product(trans(D),L),D);rows=[]
 for v in [[F(0),F(0)],[F(2,3),F(-1,5)],[F(-2),F(3)]]:
  w=mv(D,v);assert mv(X,w)==mv(XD,v)
  original=objective(X,y,R,L,w);mapped=objective(XD,y,R,Lv,v);assert original==mapped
  rows.append({'v':v,'w':w,'prediction':mv(X,w),'objective':original})
 # Derive gradient from exact central differences of a scalar quadratic, without course matrix route.
 H=[[F(1),F(0)],[F(0),F(100)]];eta=F(1,100);trajectories=[]
 for d in [F(1,10),F(1,5)]:
  D2=[[F(1),F(0)],[F(0),d]];Hv=product(product(D2,H),D2);v=[F(1),1/d];w=[F(1),F(1)];mapped=[];plain=[]
  for k in range(11):
   mapped.append(mv(D2,v));plain.append(w[:])
   grad=[]
   for j in range(2):
    vp=v[:];vm=v[:];vp[j]+=1;vm[j]-=1;grad.append((quad(Hv,vp)-quad(Hv,vm))/4)
   v=[x-eta*g for x,g in zip(v,grad)];w=[w[0]*(1-eta),w[1]*(1-100*eta)]
  trajectories.append({'D_diagonal':[1,d],'hessian_v':Hv,'mapped_steps':mapped,'ordinary_steps':plain})
 assert trajectories[1]['hessian_v']==[[1,0],[0,4]] and trajectories[1]['mapped_steps'][1]==[F(99,100),F(24,25)]
 # Same physical solution/error despite bare matrix condition becoming 1.
 A=[[F(1),F(0)],[F(0),F(100)]];Dc=[[F(1),F(0)],[F(0),F(1,100)]];w=[F(1),F(1)];dw=[F(0),F(1,100)];v=[F(1),F(100)];dv=[F(0),F(1)]
 assert product(A,Dc)==[[1,0],[0,1]] and mv(Dc,dv)==dw
 # Changing GD step destroys the claimed convergence for ordinary w even though coordinates remain invertible.
 changed={'eta_1_50_ordinary_second_factor':1-100*F(1,50),'eta_3_100_ordinary_second_factor':1-100*F(3,100),'eta_3_100_D_1_10_second_factor':1-F(3,100)}
 result={'aliasing_errors':errs,'original_arrays_max_difference':max(abs(x-y) for x,y in zip(low,high)),'p1_first_two':[p1low[:2],p1high[:2]],'two_tap_gain_phase_boundary':filters,'units':{'input_time_fs_Hz':8,'input_tones_Hz':[1,3],'output_fs_Hz':4,'folded_tone_Hz':1,'input_cycles_per_pixel':[F(1,8),F(3,8)],'output_cycles_per_pixel':F(1,4)},'nonlinear_spectral_reason':'cos²(pi*n/3)=(1+cos(2*pi*n/3))/2; harmonic outside pi/2 regenerates after input filtering; filtering squared signal retains DC only in this periodic example.','shift_equivariance':{'all_integer_output_shift_min_max_error':min(mismatch),'even_shift_two_matches_output_shift_one':True,'energy_task_statistic_original':energy0,'energy_task_statistic_shifted':energy1,'scope':'Scalar statistic invariance is not trained-model robustness.'},'scaling_general_corresponding_objectives':rows,'mapped_penalty':Lv,'two_coordinate_trajectories':trajectories,'physical_error_example':{'A_bare_kappa2':100,'AD_bare_kappa2':1,'delta_w':dw,'delta_v':dv,'physical_error_unchanged':True},'changed_step_counterexamples':changed,'scope':'Finite trigonometric and exact-rational instances; no all-band removal, perfect reconstruction, general conditioning theorem or CNN training claims.'}
 return result
if __name__=='__main__':
 if sys.argv[1]=='prepare':result=expectations();name='expectations-before-run.json'
 else:result=run();name='independent-results.json'
 text=json.dumps(result,default=str,ensure_ascii=False,indent=2)+'\n';(P/name).write_text(text);print(text)
