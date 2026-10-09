from pathlib import Path
import importlib.util,json
from math import cos,pi,hypot,exp
p=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('business',p/'snapshot/dynamics_lab.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
observed=json.loads((p/'cli-output/report.json').read_text());rows=[]
for step in [.05,.025,.0125]:
 trace=m.rk4(m.pendulum,(pi/2,0),step,round(20/step))
 energies=[v*v/2+1-cos(theta) for theta,v in trace]
 rec={'step':step,'length':len(trace),'endpoint':trace[-1],'max_energy_increase':max(y-x for x,y in zip(energies,energies[1:])),'max_abs_angle':max(abs(z[0]) for z in trace),'initial_energy':energies[0],'final_energy':energies[-1]}
 assert rec['max_energy_increase']<1e-9 and rec['max_abs_angle']<pi
 actual=next(r for r in observed['pendulum']['runs'] if r['step']==step)
 assert rec['final_energy']==actual['final_energy'] and list(rec['endpoint'])==actual['endpoint'];rows.append(rec)
diffs=[hypot(*(x-y for x,y in zip(rows[i]['endpoint'],rows[i+1]['endpoint']))) for i in range(2)]
assert diffs[1]<diffs[0]
delta=1e-5;actual=(m.radial_exact(1,1,1+delta,1)-m.radial_exact(1,1,1-delta,1))/(2*delta)
assert abs(actual-exp(-2))<1e-8
r={'pendulum_recomputed_from_full_traces':rows,'endpoint_adjacent_differences':diffs,'Poincare_radius_derivative_actual_finite_difference':actual,'independent_variational_derivative':exp(-2),'scope':'Independent energy/angle computation over frozen RK4 trajectory outputs; does not prove invariant basin or general return-map theorem.'}
(p/'trajectory-results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
