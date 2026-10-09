import os,pathlib,json,time,sys,hashlib,signal
root=pathlib.Path(__file__).resolve().parent
snapshot=root/'snapshot';env=os.environ.copy()
env.update(json.loads((root/'environment.json').read_text())['requested_environment'])
cmd=[sys.executable,'-B','learning_theory.py','--input','inputs.json']; start=time.time()
pid=os.fork()
if pid==0:
    os.chdir(snapshot)
    out=os.open(root/'stdout-direct.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    err=os.open(root/'stderr-direct.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    os.dup2(out,1);os.dup2(err,2);os.close(out);os.close(err)
    os.execve(sys.executable,cmd,env)
timeout=False
while True:
    done,status,usage=os.wait4(pid,os.WNOHANG)
    if done:break
    if time.time()-start>60:timeout=True;os.kill(pid,signal.SIGKILL);done,status,usage=os.wait4(pid,0);break
    time.sleep(.005)
end=time.time(); original=pathlib.Path(json.loads((root/'identity.json').read_text())['original_directory'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
final={f:sha(original/f) for f in ['learning_theory.py','inputs.json']}
record={'command':cmd,'cwd':str(snapshot),'start_unix':start,'end_unix':end,'elapsed_seconds':end-start,'exit_code':os.waitstatus_to_exitcode(status),'timeout':timeout,'timeout_seconds':60,'child_rusage':{'maxrss_bytes_macos':usage.ru_maxrss,'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime},'source_final':final,'source_stable':final==json.loads((root/'identity.json').read_text())['before'],'stdout_sha256':sha(root/'stdout-direct.json'),'stderr_sha256':sha(root/'stderr-direct.txt'),'aggregate_memory_peak_observed':False,'hard_os_thread_limit':False}
(root/'execution-direct.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
