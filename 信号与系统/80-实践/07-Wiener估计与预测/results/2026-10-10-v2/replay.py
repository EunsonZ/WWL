"""Static-reviewed replay interface; not executed in the recorded run.
POSIX macOS/Linux only, standard library. Writes to a new directory, stops on failed child.
"""
import argparse,hashlib,json,os,pathlib,shutil,signal,sys,time,platform

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=pathlib.Path,required=True);args=parser.parse_args()
    package=pathlib.Path(__file__).resolve().parent;dest=args.output.resolve();identity=json.loads((package/'identity.json').read_text());cfg=json.loads((package/'fixed-inputs.json').read_text())
    for file,digest in identity['snapshot'].items():
        if sha(package/'snapshot'/file)!=digest:raise ValueError('snapshot mismatch: '+file)
    # Protect the independent oracle and fixed assumptions as well as business source.
    expected_tools=json.loads((package/'replay-input-hashes.json').read_text())
    for file,digest in expected_tools.items():
        if sha(package/file)!=digest:raise ValueError('replay tool mismatch: '+file)
    dest.mkdir(parents=True,exist_ok=False);shutil.copytree(package/'snapshot',dest/'snapshot')
    for file in expected_tools:shutil.copy2(package/file,dest/file)
    env=os.environ.copy();overrides={k:'4' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']};overrides['PYTHONDONTWRITEBYTECODE']='1';env.update(overrides)
    (dest/'environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'executable':sys.executable,'requested_environment':overrides,'hard_os_thread_limit':False,'aggregate_memory_peak_observed':False},indent=2))
    def run(label,argv,cwd,limit):
        cmd=[sys.executable,'-B']+argv;env['WWL_CHILD_TIMEOUT_SECONDS']=str(limit);start=time.time();pid=os.fork()
        if pid==0:
            os.chdir(cwd)
            for fd,suffix in [(1,'stdout.txt'),(2,'stderr.txt')]:
                handle=os.open(dest/(label+'-'+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644);os.dup2(handle,fd);os.close(handle)
            os.execve(sys.executable,cmd,env)
        timedout=False
        while True:
            completed,status,usage=os.wait4(pid,os.WNOHANG)
            if completed:break
            if time.time()-start>limit:timedout=True;os.kill(pid,signal.SIGKILL);_,status,usage=os.wait4(pid,0);break
            time.sleep(.01)
        record={'command':cmd,'cwd':str(cwd),'elapsed_seconds':time.time()-start,'exit_code':os.waitstatus_to_exitcode(status),'timeout':timedout,'timeout_seconds':limit,'requested_environment':{**overrides,'WWL_CHILD_TIMEOUT_SECONDS':str(limit)},'child_maxrss_native':usage.ru_maxrss,'maxrss_units':'bytes on macOS; KiB on Linux','source_after':{f:sha(dest/'snapshot'/f) for f in identity['snapshot']}}
        (dest/(label+'-execution.json')).write_text(json.dumps(record,indent=2))
        if record['source_after']!=identity['snapshot']:raise RuntimeError('snapshot drift')
        if record['exit_code']!=0 or timedout:raise RuntimeError('child failed: '+label)
    run('suite',['-m','unittest','-v','test_wiener_lab.py'],dest/'snapshot',60)
    for label,limit in [('preflight',60),('standard',300)]:
        settings=cfg[label];run(label,['wiener_lab.py','--output',str(dest/label),'--repeats',str(settings['repeats']),'--train',str(settings['train']),'--test',str(settings['test'])],dest/'snapshot',limit)
    run('oracle',['independent_oracle.py'],dest,300);run('csv-oracle',['csv_oracle.py'],dest,60)
    for file in ['oracle-results.json','csv-oracle-results.json']:
        r=json.loads((dest/file).read_text())
        if not r['all_match'] or r['failed_checks']:raise RuntimeError('oracle mismatch: '+file)
    print(json.dumps({'output':str(dest),'five_children_completed':True,'independent_oracles_match':True,'diagram_rendering':'not replayed; use existing SVG and record fresh renderer/visual evidence separately'}))
if __name__=='__main__':main()
