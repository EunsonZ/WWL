from pathlib import Path
import subprocess,os,sys,json,time,platform,sqlite3,resource
BASE=Path(__file__).resolve().parent;cwd=BASE/'snapshot'
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(HOME=str(BASE/'home'),TMPDIR=str(BASE/'tmp'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
report={'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),'SQLite':sqlite3.sqlite_version,'env':{k:env[k] for k in ['HOME','TMPDIR','PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'timeout_seconds':60,'dependencies':'stdlib only; no prepare/install/compile/network','runs':[]}
for name,path in [('query','candidate/AI/13-搜索推理与规划/query_contract_examples.py'),('gcounter','candidate/计算机知识/65-分布式系统/gcounter_join_examples.py'),('author-batch-oracle','evidence/independent_batch_oracle.py')]:
 cmd=[sys.executable,'-B',path];started=time.time()
 try:
  p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=60);record={'name':name,'argv':cmd,'cwd':str(cwd),'started_unix':started,'elapsed_seconds':time.time()-started,'exit':p.returncode};(BASE/'logs'/f'{name}.stdout').write_text(p.stdout);(BASE/'logs'/f'{name}.stderr').write_text(p.stderr)
 except subprocess.TimeoutExpired as error: record={'name':name,'argv':cmd,'error':'TimeoutExpired','elapsed_seconds':time.time()-started}
 report['runs'].append(record);report['rusage_children']=dict(zip(['ru_maxrss','ru_utime','ru_stime'],[resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime,resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime]));report['resource_scope']='macOS ru_maxrss bytes; cumulative children observation, not hard memory cap or OS thread count';(BASE/'fixed-runs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(record,flush=True)
 if record.get('exit',1)!=0:break
