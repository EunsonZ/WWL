from pathlib import Path
import subprocess,os,json,time,platform,sys,sqlite3
BASE=Path(__file__).resolve().parent
SOURCE=BASE/'snapshot/计算机知识/75-软件工程与人机交互'
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
env.update(HOME=str(BASE/'home'),XDG_CONFIG_HOME=str(BASE/'home'),TMPDIR=str(BASE/'tmp'),GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_TERMINAL_PROMPT='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.hooksPath',GIT_CONFIG_VALUE_0=str(BASE/'empty-hooks'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
commands=[('unittest',[sys.executable,'-B','-m','unittest','-v','test_reservation.py','test_reservation_v2.py','test_git_evolution_lab.py']),('default-demo',[sys.executable,'-B','reservation_v2.py']),('git-lab',[sys.executable,'-B','git_evolution_lab.py','--parent',str(BASE/'git-scratch')])]
meta={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'git':subprocess.check_output(['git','--version'],text=True,env=env).strip(),'environment':{k:env[k] for k in ['HOME','XDG_CONFIG_HOME','TMPDIR','GIT_CONFIG_NOSYSTEM','GIT_CONFIG_GLOBAL','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'preflight_timeout_seconds':60,'dependency_preparation':'None; installed Python/Git/stdlib SQLite only','runs':[]}
for name,cmd in commands:
 started=time.time()
 try:
  p=subprocess.run(cmd,cwd=SOURCE,env=env,capture_output=True,text=True,timeout=60)
  record={'name':name,'command':cmd,'cwd':str(SOURCE),'started_unix':started,'elapsed_seconds':time.time()-started,'exit':p.returncode}
  (BASE/'logs'/f'{name}.stdout').write_text(p.stdout); (BASE/'logs'/f'{name}.stderr').write_text(p.stderr)
 except subprocess.TimeoutExpired as e:
  record={'name':name,'command':cmd,'elapsed_seconds':time.time()-started,'error':'TimeoutExpired'}
 meta['runs'].append(record)
 (BASE/'fixed-runs.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(record,ensure_ascii=False),flush=True)
 if record.get('exit',1)!=0: break
