import subprocess,os,time,json,signal
from pathlib import Path
base=Path(__file__).resolve().parent
argv=['/usr/bin/qlmanage','-t','-s','1620','-o',str(base/'native-preview-approved'),str(base/'snapshot/assets/noise-paths.svg')];start=time.monotonic();timed=False
with (base/'qlmanage-approved.stdout').open('xb') as out,(base/'qlmanage-approved.stderr').open('xb') as err:
 p=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
 while True:
  pid,status,r=os.wait4(p.pid,os.WNOHANG)
  if pid:break
  if time.monotonic()-start>55:timed=True;os.killpg(p.pid,signal.SIGKILL);pid,status,r=os.wait4(p.pid,0);break
  time.sleep(.01)
 p.returncode=os.waitstatus_to_exitcode(status)
result={'argv':argv,'exit_code':p.returncode,'timeout':timed,'wall_seconds':time.monotonic()-start,'child_max_rss_bytes_Darwin':r.ru_maxrss};(base/'qlmanage-approved-observation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(p.returncode)
