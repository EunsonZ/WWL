import os,pathlib,json,time,sys,hashlib,signal,platform,importlib.metadata
root=pathlib.Path(__file__).resolve().parent
original=pathlib.Path('.wwl-recovery/2026-10-10-crash/author153/candidate/数学/25-高等代数/60-交换代数与代数几何').resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['code/affine_exact.py','code/examples.py','code/fixed-inputs.json','code/independent-expected.json']
freeze=pathlib.Path('.wwl-recovery/2026-10-10-crash/author153/freeze-r2.json').resolve()
def source():return {f:sha(original/f) for f in files}
if sys.argv[1]=='snapshot':
    assert sha(freeze)=='a208bc3d61f5df6c693cad8fed4bc63739e314a23cbd2c18592b1c9be2aadf11'
    expected={v['path']:v['sha256'] for v in json.loads(freeze.read_text())['files']}
    before=source();snap=root/'snapshot';snap.mkdir(exist_ok=False)
    for f in files:
        assert before[f]==expected[str((original/f).relative_to(freeze.parent/'candidate'))]
        p=snap/f;p.parent.mkdir(exist_ok=True);p.write_bytes((original/f).read_bytes())
    after=source();copied={f:sha(snap/f) for f in files};assert before==after==copied
    (root/'identity.json').write_text(json.dumps({'original_directory':str(original),'freeze_sha256':sha(freeze),'before':before,'after_copy':after,'snapshot':copied},indent=2))
    (root/'freeze-r2.json').write_bytes(freeze.read_bytes())
    env={k:'4' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']};env.update(PYTHONDONTWRITEBYTECODE='1',WWL_CHILD_TIMEOUT_SECONDS='60')
    (root/'environment.json').write_text(json.dumps({'machine':platform.machine(),'platform':platform.platform(),'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'dependencies':sorted(({'name':d.metadata.get('Name'),'version':d.version} for d in importlib.metadata.distributions()),key=lambda d:d['name'] or ''),'requested_environment':env,'hard_os_thread_limit':False,'aggregate_memory_peak_observed':False},indent=2));print(json.dumps(before));raise SystemExit(0)
label=sys.argv[1];cmd=[sys.executable,'-B']+sys.argv[2:];cwd=root/'snapshot' if label in ['fixed-cli','examples-cli'] else root
env=os.environ.copy();env.update(json.loads((root/'environment.json').read_text())['requested_environment']);start=time.time();pid=os.fork()
if pid==0:
    os.chdir(cwd)
    for fd,name in [(1,label+'-stdout.json'),(2,label+'-stderr.txt')]:
        out=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644);os.dup2(out,fd);os.close(out)
    os.execve(sys.executable,cmd,env)
timeout=False
while True:
    done,status,usage=os.wait4(pid,os.WNOHANG)
    if done:break
    if time.time()-start>60:timeout=True;os.kill(pid,signal.SIGKILL);done,status,usage=os.wait4(pid,0);break
    time.sleep(.005)
record={'command':cmd,'cwd':str(cwd),'start_unix':start,'end_unix':time.time(),'elapsed_seconds':time.time()-start,'exit_code':os.waitstatus_to_exitcode(status),'timeout':timeout,'timeout_seconds':60,'child_rusage':{'maxrss_bytes_macos':usage.ru_maxrss,'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime},'source_final':source(),'source_stable':source()==json.loads((root/'identity.json').read_text())['before'],'stdout_sha256':sha(root/(label+'-stdout.json')),'stderr_sha256':sha(root/(label+'-stderr.txt'))}
(root/(label+'-execution.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
