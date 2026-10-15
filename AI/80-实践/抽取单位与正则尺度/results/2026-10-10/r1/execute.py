import os,sys,json,subprocess,time,signal,resource,hashlib,platform
from pathlib import Path
P=Path(__file__).resolve().parent;PY=Path(sys.executable).absolute();env=os.environ.copy();vars=['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']
for k in vars:env[k]='4'
env['PYTHONDONTWRITEBYTECODE']='1'
def execute(label,argv,timeout=60,stdin=None):
 t=time.monotonic();timedout=False
 with (P/(label+'.stdout')).open('xb') as so,(P/(label+'.stderr')).open('xb') as se:
  inp=None if stdin is None else (P/stdin).open('rb')
  proc=subprocess.Popen(argv,stdout=so,stderr=se,stdin=inp,env=env,cwd=P,start_new_session=True)
  try:rc=proc.wait(timeout)
  except subprocess.TimeoutExpired:timedout=True;os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
  finally:
   if inp:inp.close()
 r={'argv':list(map(str,argv)),'cwd':str(P),'stdin_file':stdin,'returncode':rc,'timed_out':timedout,'timeout_seconds':timeout,'elapsed_seconds':time.monotonic()-t,'environment':{k:env[k] for k in vars},'python':sys.version,'platform':platform.platform(),'peak_child_rss_macos_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'resource_limits':'library thread requests only; no hard OS thread cap or count established; no hard memory cap; child peak RSS is cumulative maximum of completed children in this sequential supervisor'}
 (P/(label+'-receipt.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return rc
if __name__=='__main__':
 for label,source,stdin,timeout in [('aliasing','aliasing.py',None,60),('scaling','scaling.py',None,60),('verify-aliasing','verify_aliasing.py','aliasing.stdout',300),('verify-scaling','verify_scaling.py','scaling.stdout',300),('independent',None,None,300)]:
  argv=[str(PY),'-B',str(P/'snapshot'/source)] if source else [str(PY),'-B',str(P/'oracle.py'),'verify']
  rc=execute(label,argv,timeout,stdin)
  if rc:raise SystemExit(rc)
