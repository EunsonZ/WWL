import os,pathlib,json,time,sys,hashlib,signal,platform,importlib.metadata,datetime
root=pathlib.Path(__file__).resolve().parent
original=pathlib.Path('.wwl-recovery/2026-10-10-crash/author179180/candidate-v2/信号与系统/80-实践/07-Wiener估计与预测').resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['wiener_lab.py','test_wiener_lab.py','README.md','04-源码与验证.md','assets/information-windows.svg']
freeze=pathlib.Path('.wwl-recovery/2026-10-10-crash/author179180/TARGETS_V2.json').resolve()
def source():return {f:sha(original/f) for f in files}
if sys.argv[1]=='snapshot':
    assert sha(freeze)=='97858c52b24366c85666f5fb0c0ba96a93742392247128a5c33fe753d4cf0845'
    expected={v['path']:v['candidate_sha256'] for v in json.loads(freeze.read_text())}
    before=source();snap=root/'snapshot';snap.mkdir(exist_ok=False)
    for f in files:
        assert before[f]==expected[str((original/f).relative_to(freeze.parent/'candidate-v2'))]
        p=snap/f;p.parent.mkdir(exist_ok=True);p.write_bytes((original/f).read_bytes())
    after=source();copied={f:sha(snap/f) for f in files};assert before==after==copied
    (root/'identity.json').write_text(json.dumps({'original_directory':str(original),'freeze_sha256':sha(freeze),'before':before,'after_copy':after,'snapshot':copied},indent=2))
    (root/'TARGETS_V2.json').write_bytes(freeze.read_bytes())
    env={k:'4' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']};env['PYTHONDONTWRITEBYTECODE']='1'
    (root/'environment.json').write_text(json.dumps({'machine':platform.machine(),'platform':platform.platform(),'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'dependencies':sorted(({'name':d.metadata.get('Name'),'version':d.version} for d in importlib.metadata.distributions()),key=lambda d:d['name'] or ''),'requested_environment':env,'hard_os_thread_limit':False,'aggregate_memory_peak_observed':False},indent=2));print(json.dumps(before));raise SystemExit(0)
label=sys.argv[1];timeout_limit=int(sys.argv[2]);cmd=[sys.executable,'-B']+sys.argv[3:];cwd=root/'snapshot' if label in ['suite','preflight','standard'] else root
env=os.environ.copy();env.update(json.loads((root/'environment.json').read_text())['requested_environment']);env['WWL_CHILD_TIMEOUT_SECONDS']=str(timeout_limit)
command_sources={}
for token in sys.argv[3:]:
    p=cwd/token
    if p.is_file():command_sources[str(p)]=sha(p)
start=time.time();pid=os.fork()
if pid==0:
    os.chdir(cwd)
    for fd,name in [(1,label+'-stdout.txt'),(2,label+'-stderr.txt')]:
        out=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644);os.dup2(out,fd);os.close(out)
    os.execve(sys.executable,cmd,env)
timeout=False
while True:
    done,status,usage=os.wait4(pid,os.WNOHANG)
    if done:break
    if time.time()-start>timeout_limit:timeout=True;os.kill(pid,signal.SIGKILL);done,status,usage=os.wait4(pid,0);break
    time.sleep(.01)
end=time.time()
record={'command':cmd,'command_sources_before':command_sources,'cwd':str(cwd),'requested_environment':{**json.loads((root/'environment.json').read_text())['requested_environment'],'WWL_CHILD_TIMEOUT_SECONDS':str(timeout_limit)},'start_unix':start,'end_unix':end,'start_utc':datetime.datetime.fromtimestamp(start,datetime.timezone.utc).isoformat(),'elapsed_seconds':end-start,'exit_code':os.waitstatus_to_exitcode(status),'timeout':timeout,'timeout_seconds':timeout_limit,'child_rusage':{'maxrss_bytes_macos':usage.ru_maxrss,'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime},'source_final':source(),'source_stable':source()==json.loads((root/'identity.json').read_text())['before'],'stdout_sha256':sha(root/(label+'-stdout.txt')),'stderr_sha256':sha(root/(label+'-stderr.txt'))}
(root/(label+'-execution.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
