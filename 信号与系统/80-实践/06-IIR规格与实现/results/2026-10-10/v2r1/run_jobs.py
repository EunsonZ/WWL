from pathlib import Path
import subprocess,os,sys,json,time,platform,resource,shutil,hashlib,uuid
BASE=Path(__file__).resolve().parent;IIR=BASE/'snapshot/candidate-v2/信号与系统/80-实践/06-IIR规格与实现'
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(HOME=str(BASE/'home'),TMPDIR=str(BASE/'tmp'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
out=Path('/private/tmp')/('wwl-recovery-178v2-'+uuid.uuid4().hex)
report={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'environment':{k:env[k] for k in ['HOME','TMPDIR','PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'dependency_preparation':'None; stdlib Decimal/Fraction only','runs':[]}
jobs=[('bounded-preflight',[sys.executable,'-B',str(BASE/'preflight.py')],60),('iir-tests',[sys.executable,'-B','-m','unittest','-v','test_iir_lab.py'],60),('iir-cli',[sys.executable,'-B','iir_lab.py','--output',str(out)],300)]
for name,cmd,timeout in jobs:
 start=time.time();stdout='';stderr='';record={'name':name,'argv':cmd,'cwd':str(IIR),'started_unix':start,'timeout_seconds':timeout}
 try:
  result=subprocess.run(cmd,cwd=IIR,env=env,capture_output=True,text=True,timeout=timeout);stdout=result.stdout;stderr=result.stderr;record['exit']=result.returncode
 except subprocess.TimeoutExpired as error:
  stdout=error.stdout or b'';stderr=error.stderr or b'';stdout=stdout.decode() if isinstance(stdout,bytes) else stdout;stderr=stderr.decode() if isinstance(stderr,bytes) else stderr;record['error']='TimeoutExpired';record['exit']=None
 record['elapsed_seconds']=time.time()-start;(BASE/'logs'/f'{name}.stdout').write_text(stdout);(BASE/'logs'/f'{name}.stderr').write_text(stderr)
 if name=='iir-cli':
  record['transient_output']=str(out)
  if out.exists():
   shutil.copytree(out,BASE/'raw/iir-cli');record['durable_files']=[{'path':str(p.relative_to(BASE)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted((BASE/'raw/iir-cli').rglob('*')) if p.is_file()]
 report['runs'].append(record);report['cumulative_children_ru_maxrss_bytes_macos']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss;report['resource_scope']='Cumulative child observation; not hard cap or OS thread count';(BASE/'jobs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False),flush=True)
 if record['exit']!=0:break
