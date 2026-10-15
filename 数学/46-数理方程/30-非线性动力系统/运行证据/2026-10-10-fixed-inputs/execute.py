"""Bound subprocess recording; executes only copied frozen sources, never candidate."""
import sys,subprocess,os,json,time,resource,hashlib,platform,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON=ROOT.parents[2]/'.venv-issues-111plus/bin/python'
# ROOT parents: recovery date, .wwl-recovery, vault root.
ENV=os.environ.copy()
THREAD_VARS=['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']
for key in THREAD_VARS:ENV[key]='4'
ENV['PYTHONDONTWRITEBYTECODE']='1'
def execute(label,argv,timeout):
    out=ROOT/(label+'.stdout');err=ROOT/(label+'.stderr');assert not out.exists() and not err.exists()
    t=time.monotonic();timedout=False
    with out.open('xb') as so,err.open('xb') as se:
        proc=subprocess.Popen(argv,stdout=so,stderr=se,env=ENV,cwd=ROOT,start_new_session=True)
        try:rc=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timedout=True;os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
    record={'argv':list(map(str,argv)),'cwd':str(ROOT),'returncode':rc,'timeout_seconds':timeout,'timed_out':timedout,'elapsed_seconds':time.monotonic()-t,'child_peak_rss_macos_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'environment':{k:ENV[k] for k in THREAD_VARS},'python':sys.version,'platform':platform.platform(),'stdout_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(err.read_bytes()).hexdigest(),'limits':'Library thread requests only; no OS thread observation/hard memory cap. Child RSS is maximum over previously terminated children of this supervisor.'}
    (ROOT/(label+'-receipt.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False));return rc
if __name__=='__main__':
    if len(sys.argv)<4:raise SystemExit('label timeout argv...')
    raise SystemExit(execute(sys.argv[1],sys.argv[3:],int(sys.argv[2])))
