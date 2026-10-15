import cmath,json,math,pathlib
import numpy as np
from scipy import signal
OUT=pathlib.Path(__file__).resolve().parent;data=json.loads((OUT/'iir-cli-output/results.json').read_text());sections=np.array(data['design']['sections']);edge=math.pi/4;grid=np.linspace(0,edge,32769);results={}
for label,sos in [('binary64_fixed',sections),('binary32_fixed',sections.astype(np.float32).astype(float))]:
    poles=[];zeros=[]
    for row in sos:
        order=1 if row[2]==row[5]==0 else 2
        poles.extend(np.roots(row[3:3+order+1]));zeros.extend(np.roots(row[:order+1]))
    poles=np.array(poles);zeros=np.array(zeros);assert len(poles)==len(zeros)==27 and max(abs(poles))<1 and max(abs(zeros+1))<1e-14
    q=np.exp(-1j*grid);N=sos[:,0,None]+sos[:,1,None]*q+sos[:,2,None]*q*q;D=1+sos[:,4,None]*q+sos[:,5,None]*q*q
    actual=np.real(np.sum(q*(sos[:,1,None]+2*sos[:,2,None]*q)/N-q*(sos[:,4,None]+2*sos[:,5,None]*q)/D,axis=0))
    poleformula=.5*np.sum((1-abs(poles)**2)[:,None]/abs(1-poles[:,None]*q)**2,axis=0);error=float(max(abs(actual-poleformula)));assert error<1e-12
    distances=[abs(1-p*cmath.exp(-1j*min(edge,max(0.,float(np.angle(p)))))) for p in poles]
    K=float(sum((1-abs(p)**2)*abs(p)/d**4 for p,d in zip(poles,distances)));margin=K*edge/(2*32768);upper=float(max(actual)+margin);assert upper<=96
    results[label]=dict(poles=[[float(p.real),float(p.imag)] for p in poles],zeros=[[float(p.real),float(p.imag)] for p in zeros],max_grid_samples=float(max(actual)),dc_samples=float(actual[0]),minimum_grid_samples=float(min(actual)),global_derivative_bound=K,grid_margin=margin,continuous_model_float_upper_samples=upper,budget_samples=96,analytic_section_log_derivative_vs_actual_poles_grid_error=error)
result=dict(status='pass',models=results,limitation='Supplement independently uses roots/log derivative of actual fixed SOS coefficients. Ordinary floating bound is numerical evidence, no outward arithmetic enclosure. Does not alter the V1 CLI claim, which used design.poles.')
(OUT/'fixed-coefficient-delay-observations.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
