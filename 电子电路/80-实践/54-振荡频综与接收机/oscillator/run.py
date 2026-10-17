from pathlib import Path
import subprocess,json,time,hashlib,os
r=Path(__file__).resolve().parent;ng=os.environ['NGSPICE'];runner=os.environ['WWL_RUNNER']
for name in json.loads((r/'fixed-inputs.json').read_text())['cases']:
 d=r/name;cmd=['python3',runner,'--timeout','300','--',ng,'-b','osc.cir'];start=time.monotonic()
 with (d/'run.log').open('w') as f:p=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT)
 log=(d/'run.log').read_text();valid=p.returncode==0 and 'simulation(s) aborted' not in log and 'Error:' not in log and (d/'waveform.txt').exists()
 (d/'command.json').write_text(json.dumps({'argv':cmd,'cwd':str(d),'returncode':p.returncode,'elapsed_s':time.monotonic()-start,'analysis_completed':valid},indent=2))
 if not valid:raise RuntimeError('failed actual analysis '+name)
 print(name,'complete',flush=True)
