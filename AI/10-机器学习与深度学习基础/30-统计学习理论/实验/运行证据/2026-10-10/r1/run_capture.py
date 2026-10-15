import hashlib,json,os,pathlib,platform,subprocess,sys,time,importlib.metadata
root=pathlib.Path(__file__).resolve().parent
original=pathlib.Path('.wwl-recovery/2026-10-10-crash/author158/candidate/AI/10-机器学习与深度学习基础/30-统计学习理论/实验').resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['learning_theory.py','inputs.json']
before={f:sha(original/f) for f in files}
snapshot=root/'snapshot';snapshot.mkdir(exist_ok=False)
for f in files:(snapshot/f).write_bytes((original/f).read_bytes())
after={f:sha(original/f) for f in files}
copy={f:sha(snapshot/f) for f in files}
identity={'original_directory':str(original),'before':before,'after_copy':after,'snapshot':copy}
(root/'identity.json').write_text(json.dumps(identity,indent=2))
if before!=after or before!=copy:raise RuntimeError('SOURCE_DRIFT; stop instance')
env=os.environ.copy()
overrides={k:'4' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']}
overrides.update({'PYTHONDONTWRITEBYTECODE':'1','WWL_CHILD_TIMEOUT_SECONDS':'60'})
env.update(overrides)
metadata={'platform':platform.platform(),'machine':platform.machine(),'python':sys.version,'executable':sys.executable,'venv_prefix':sys.prefix,'dependencies':sorted([{'name':d.metadata.get('Name'),'version':d.version} for d in importlib.metadata.distributions()],key=lambda d:d['name'] or ''),'requested_environment':overrides,'hard_os_thread_limit':False,'aggregate_memory_peak_observed':False}
(root/'environment.json').write_text(json.dumps(metadata,indent=2))
cmd=[sys.executable,'-B','learning_theory.py','--input','inputs.json']
start=time.time(); timed=['/usr/bin/time','-l']+cmd
with (root/'stdout.json').open('wb') as out,(root/'stderr-time.txt').open('wb') as err:
    p=subprocess.Popen(timed,cwd=snapshot,env=env,stdout=out,stderr=err)
    try:exit_code=p.wait(timeout=60);timeout=False
    except subprocess.TimeoutExpired:p.kill();p.wait();exit_code=p.returncode;timeout=True
end=time.time()
final={f:sha(original/f) for f in files}
record={'command':cmd,'measurement_command':timed,'cwd':str(snapshot),'start_unix':start,'end_unix':end,'elapsed_seconds':end-start,'exit_code':exit_code,'timeout':timeout,'timeout_seconds':60,'source_final':final,'source_stable':before==final,'stdout_sha256':sha(root/'stdout.json'),'stderr_sha256':sha(root/'stderr-time.txt')}
(root/'execution.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
