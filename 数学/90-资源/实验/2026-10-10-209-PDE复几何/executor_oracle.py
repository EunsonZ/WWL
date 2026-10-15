"""Finite independent expectations, constructed before reading actual JSON.
No candidate import or call. Fractions, exponentials, roots-of-unity identity,
and coordinate arithmetic supplement independent mathematical source review.
"""
from pathlib import Path
from fractions import Fraction as Q
import json,math,time,resource,sys,os
BASE=Path(__file__).resolve().parent

def close(a,b,tol=1e-14):
 assert abs(a-b)<=tol*max(1,abs(b)),(a,b,abs(a-b),tol)

def cpair(z):return [z.real,z.imag]
def complex_close(actual,expected):
 close(actual[0],expected.real);close(actual[1],expected.imag)

def main():
 started=time.time();entropy=[]
 # [q]-s[eta], defined independently through jumps of u^3/3 and u^2/2.
 for left,right in [(2,-2),(-2,2),(3,1),(1,3)]:
  l,r=Q(left),Q(right);speed=(r*r/2-l*l/2)/(r-l);rh=(r*r/2-l*l/2)-speed*(r-l);D=(r**3-l**3)/3-speed*(r*r-l*l)/2
  assert rh==0;entropy.append({'left':left,'right':right,'speed':float(speed),'RH_residual':float(rh),'entropy_jump':float(D),'entropy_admissible':D<=0})
 expected_shock=[]
 for xi in [-.1,0,.1]:
  e=math.exp(20*xi);u=2*(1-e)/(1+e);du=-80*e/(1+e)**2
  expected_shock.append({'xi':xi,'U':u,'U_prime':du,'epsilon_U_prime':.1*du,'product_rhs':(u*u-4)/2})
 alpha=Q(2,3);radial_h1=float(Q(1,4))**float(2*alpha)/float(2*alpha);corners=[]
 for eps in [.1,.01,.001]:
  # Integrate r^(2alpha-3) using exponent 2alpha-2, not subject integrator.
  exponent=2*alpha-2;radial=(.25**float(exponent)-eps**float(exponent))/float(exponent)
  coefficient=2*alpha**2*(alpha-1)**2;full=float(coefficient)*1.5*math.pi*radial
  corners.append({'cutoff':eps,'radial_factor':radial,'hessian_frobenius_coefficient':str(coefficient),'full_H2_seminorm_on_sector_annulus':full})
 assert corners[0]['radial_factor']<corners[1]['radial_factor']<corners[2]['radial_factor']
 hessian=[]
 for radius,theta in [(.1,.3),(.2,1.1),(.05,2.4)]:
  factor=float(alpha*(alpha-1))*radius**float(alpha-2);xx=factor*math.sin(float(alpha-2)*theta);xy=factor*math.cos(float(alpha-2)*theta);yy=-xx
  norm=xx*xx+2*xy*xy+yy*yy;expected=float(2*alpha**2*(alpha-1)**2)*radius**float(2*alpha-4);close(norm,expected)
  hessian.append({'radius':radius,'theta':theta,'entries':[xx,xy,yy],'frobenius_squared':norm,'radial_expected':expected})
 heat=[{'t':t,'amplitude':math.exp(-4*4*t),'mean_square':1+math.exp(-2*4*4*t)/2} for t in [0,.1,.25]]
 explicit=[]
 for r in [Q(2,5),Q(3,5)]:
  gain=1-4*r
  for steps in [1,2]:
   amp=gain**steps;explicit.append({'r':float(r),'steps':steps,'gain':str(gain),'amplitude':float(amp),'values':[float(amp*((-1)**j)) for j in range(8)],'mean_square':float(amp**2)})
 reaction=[{'t':float(t),'u':float(1/(Q(1,2)-t))} for t in [Q(0),Q(1,10),Q(1,4),Q(2,5)]]
 # Independent finite initial-average arithmetic; no time evolution solver.
 neumann_nodes=[(j+.5)/64 for j in range(64)];data=[2+math.cos(math.pi*x) for x in neumann_nodes];mean=math.fsum(data)/64;mean_square=math.fsum(x*x for x in data)/64;close(mean,2);close(mean_square,4.5)
 average={'boundary_example':'Supplementary zero-Neumann compatible u0=2+cos(pi*x) on[0,1]; main text/script use periodic data','initial_mean':mean,'initial_mean_square':mean_square,'variance':mean_square-mean**2,'ODE_bound_1_over_initial_mean':1/mean,'endpoint_derivative':[0.0,math.sin(math.pi)*(-math.pi)],'scope':'Finite initial averages and boundary derivatives only; no Neumann/PDE blowup solver or theorem certification'}
 # Roots-of-unity mean keeps powers k divisible by N. Constant and zeta^2
 # numerator leave respectively C/(1-q^N) and w^2/(1-q^N), for N>2.
 truth=Q(5,8)+Q(1,25);ratio=Q(2,7);hartogs=[]
 for n in [16,32]:
  alias=ratio**n;ideal=truth/(1-alias);error=truth*alias/(1-alias);hartogs.append({'N':n,'ideal_exact_fraction':str(ideal),'error_exact_fraction':str(error),'ideal':float(ideal),'ideal_error':float(error)})
 membership={'z':.4,'w':.2,'r':.5,'epsilon':.25,'rho':.7,'inside_bidisk':True,'original_H_membership':(.5<.2<1) or (.4<.25),'all_quadrature_points_in_annulus':.5<.7<1}
 assert membership['original_H_membership'] is False and membership['all_quadrature_points_in_annulus']
 # Expectations frozen before actual output inspection.
 expected={'entropy_RH':entropy,'shock':expected_shock,'material':[{'a':1,'slope':1,'flux':1},{'a':2,'slope':.5,'flux':1}],'corner':{'alpha':float(alpha),'laplace_coefficient':float(alpha*(alpha-1)+alpha-alpha*alpha),'H1_radial':radial_h1,'H2':corners,'full_H1_gradient_factor':float(alpha*alpha)*1.5*math.pi,'Hessian_samples':hessian},'heat':heat,'explicit_heat':explicit,'reaction':reaction,'average_initial_example':average,'Hartogs_membership':membership,'Hartogs_exact_discrete':hartogs,'true_filled_value':float(truth),'derivation':'(1/N)sum exp(2pi i j k/N) = 1 for N|k else0; C=5/8,w^2=1/25,q=2/7; ideal=(C+w²)/(1-q^N) for N>2'}
 (BASE/'expected-before-output.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2)+'\n')
 pde=json.loads((BASE/'logs/pde.stdout').read_text());comp=json.loads((BASE/'logs/complex.stdout').read_text())
 close(pde['burgers']['speed'],entropy[0]['speed']);close(pde['burgers']['entropy_production'],entropy[0]['entropy_jump'])
 for actual,want in zip(pde['burgers']['samples'],expected_shock):
  for key in want:close(actual[key],want[key])
 assert pde['material']==expected['material'];close(pde['corner']['alpha'],float(alpha));close(pde['corner']['laplace_coefficient'],0);close(pde['corner']['H1_radial_integral_0_to_quarter'],radial_h1)
 for actual,want in zip(pde['corner']['H2_radial_truncations'],corners):close(actual['cutoff'],want['cutoff']);close(actual['integral'],want['radial_factor'])
 for actual,want in zip(pde['heat_mode'],heat):
  for key in want:close(actual[key],want[key])
 for actual,want in zip(pde['explicit_heat'],explicit):
  assert actual['steps']==want['steps'];close(actual['r'],want['r']);close(actual['mean_square'],want['mean_square'])
  for u,v in zip(actual['values'],want['values']):close(u,v)
 close(pde['constant_reaction']['c'],2);close(pde['constant_reaction']['blowup_time'],.5)
 for actual,want in zip(pde['constant_reaction']['samples'],reaction):close(actual['t'],want['t']);close(actual['u'],want['u'])
 complex_close(comp['triangular_map']['output'][0],1+1j);complex_close(comp['triangular_map']['output'][1],2+1j)
 for actual,want in zip(comp['triangular_map']['inverse'],[1+1j,2-1j]):complex_close(actual,want)
 cp=comp['projective_chart'];cp_expected={'z':1+1j,'w':.5-.5j,'dw_dz':.5j,'vector_z':2+0j,'vector_w':1j,'form_z':1+0j,'form_w':-2j,'pairing_z':2+0j,'pairing_w':2+0j}
 for key,want in cp_expected.items():complex_close(cp[key],want)
 fill_rows=[]
 for actual,want in zip(comp['hartogs_fill'],hartogs):
  assert actual['samples']==want['N'];complex_close(actual['computed'],complex(want['ideal']));close(actual['absolute_error_against_formula'],abs(complex(*actual['computed'])-float(truth)))
  fill_rows.append({'N':want['N'],'computed':actual['computed'],'ideal':want['ideal'],'theoretical_error':want['ideal_error'],'measured_error_to_true':actual['absolute_error_against_formula'],'distance_to_ideal':abs(complex(*actual['computed'])-want['ideal']),'tolerance':1e-14,'rounding_dominates_theoretical_error':want['ideal_error']<sys.float_info.epsilon})
 # Supplementary finite coordinate identities; these have no subject-code interface.
 vectorfields=[]
 for coeff in [(1,0,0),(0,1,0),(0,0,1),(1+1j,2,-1j)]:
  aa,bb,cc=coeff
  for z in [1+1j,2-.5j,-.3+.7j]:
   w=1/z;direct=-(w*w)*(aa+bb*z+cc*z*z);expanded=-(aa*w*w+bb*w+cc);assert abs(direct-expanded)<1e-14
   vectorfields.append({'coefficients':[cpair(complex(v)) for v in coeff],'z':cpair(z),'transition_value':cpair(direct),'polynomial_in_w':cpair(expanded),'value_at_w0':cpair(complex(-cc))})
 torus=[]
 z=.17+.23j
 for m,n in [(0,0),(1,0),(0,1),(-2,2),(2,-2)]:
  shift=complex(m,n);translated=z+shift;representative=complex(translated.real-math.floor(translated.real),translated.imag-math.floor(translated.imag));assert abs(representative-z)<1e-14
  torus.append({'lattice_shift':[m,n],'translated':cpair(translated),'representative':cpair(representative),'translation_derivative':1,'dz_coefficient_preserved':True})
 report={'status':'PASS','started_unix':started,'elapsed_seconds':time.time()-started,'pid':os.getpid(),'fixed_comparisons':'All actual PDE and complex fixed fields match independent expectations','entropy_RH_reverse_counterexamples':entropy,'corner_full_coefficient_checks':hessian,'initial_average_supplement':average,'Hartogs_membership':membership,'Hartogs_error_comparisons':fill_rows,'CP1_fixed_expected':{k:cpair(v) for k,v in cp_expected.items()},'CP1_vectorfield_finite_supplement':vectorfields,'torus_translation_finite_supplement':torus,'supplement_scope':'Vectorfield coefficients/torus translations/Neumann initial average are own finite arithmetic, not execution of nonexistent candidate interfaces or general topology/classification/blowup proofs','resource_self_ru_maxrss_bytes_macos':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Finite formula checks only; source reviewer owns general mathematics. No real PDE integration, plot generation, GUI, devices or human learning.'}
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
