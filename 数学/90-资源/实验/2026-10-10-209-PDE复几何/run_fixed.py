from pathlib import Path
import subprocess,os,sys,json,time,platform,resource
BASE=Path(__file__).resolve().parent;cwd=BASE/'snapshot/candidate'
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(HOME=str(BASE/'home'),TMPDIR=str(BASE/'tmp'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
r={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'environment':{k:env[k] for k in ['HOME','TMPDIR','PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'timeout_seconds':60,'dependency_preparation':'None; stdlib only, no compiler/install/service/network','runs':[]}
for name,path in [('pde','数学/46-数理方程/30-正则性与非线性演化/pde_regularities.py'),('complex','数学/45-复变函数/30-多复变量与复流形/complex_chart_checks.py')]:
 cmd=[sys.executable,'-B',path];start=time.time()
 try:
  p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=60);entry={'name':name,'argv':cmd,'cwd':str(cwd),'started_unix':start,'elapsed_seconds':time.time()-start,'exit':p.returncode};(BASE/'logs'/f'{name}.stdout').write_text(p.stdout);(BASE/'logs'/f'{name}.stderr').write_text(p.stderr)
 except subprocess.TimeoutExpired as error:entry={'name':name,'argv':cmd,'error':'TimeoutExpired','elapsed_seconds':time.time()-start}
 r['runs'].append(entry);r['children_ru_maxrss_bytes_macos']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss;r['resource_scope']='Cumulative child rusage observation, not hard memory cap or measured OS thread count';(BASE/'fixed-runs.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(entry,flush=True)
 if entry.get('exit',1)!=0:break
