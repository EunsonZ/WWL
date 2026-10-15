import os,subprocess,time,json,signal
from pathlib import Path
base=Path(__file__).resolve().parent;python=str(base.parents[3]/'.venv-issues-111plus/bin/python');env=os.environ.copy()
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
argv=[python,'-B',str(base/'render_boundary_previews.py')];started=time.monotonic()
with (base/'previews.stdout').open('wb') as out,(base/'previews.stderr').open('wb') as err:
 p=subprocess.Popen(argv,stdout=out,stderr=err,env=env,start_new_session=True)
 while True:
  pid,status,usage=os.wait4(p.pid,os.WNOHANG)
  if pid:break
  if time.monotonic()-started>300:os.killpg(p.pid,signal.SIGKILL);pid,status,usage=os.wait4(p.pid,0);break
  time.sleep(.01)
 p.returncode=os.waitstatus_to_exitcode(status)
record={'name':'boundary-audit-previews','argv':argv,'exit_code':p.returncode,'wall_seconds':time.monotonic()-started,'child_max_rss_bytes':usage.ru_maxrss,'child_user_seconds':usage.ru_utime,'child_system_seconds':usage.ru_stime};records=json.loads((base/'process-observations.json').read_text());records.append(record);(base/'process-observations.json').write_text(json.dumps(records,indent=2));print(json.dumps(record));raise SystemExit(p.returncode)
