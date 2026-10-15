from pathlib import Path
import subprocess,sys,os,uuid,time,json,shutil,hashlib,resource
BASE=Path(__file__).resolve().parent;cwd=BASE/'snapshot/candidate-v2/信号与系统/80-实践/06-IIR规格与实现';out=Path('/private/tmp')/('wwl-recovery-178v2-'+uuid.uuid4().hex)
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(HOME=str(BASE/'home'),TMPDIR=str(BASE/'tmp'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
cmd=[sys.executable,'-B','iir_lab.py','--output',str(out)];start=time.time();r={'argv':cmd,'cwd':str(cwd),'timeout_seconds':300,'started_unix':start,'transient_output':str(out)}
try:
 p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=300);stdout=p.stdout;stderr=p.stderr;r['exit']=p.returncode
except subprocess.TimeoutExpired as e:
 stdout=e.stdout or b'';stderr=e.stderr or b'';stdout=stdout.decode() if isinstance(stdout,bytes) else stdout;stderr=stderr.decode() if isinstance(stderr,bytes) else stderr;r.update(exit=None,error='TimeoutExpired')
r['elapsed_seconds']=time.time()-start;(BASE/'logs/iir-cli.stdout').write_text(stdout);(BASE/'logs/iir-cli.stderr').write_text(stderr)
if out.exists():
 shutil.copytree(out,BASE/'raw/iir-cli');r['durable_files']=[{'path':str(p.relative_to(BASE)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted((BASE/'raw/iir-cli').rglob('*')) if p.is_file()]
r['children_ru_maxrss_bytes_macos']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss;r['thread_environment']={k:env[k] for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']};(BASE/'cli-run.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False),flush=True)
