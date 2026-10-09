"""Bounded evidence collector. Writes only next to this file."""
import ast, hashlib, json, os, pathlib, platform, resource, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[4]
OUT = pathlib.Path(__file__).resolve().parent
PY = ROOT / '.venv-issues-111plus/bin/python'
TOP = ROOT / '数学/40-微积分与优化/convex_duality_certificate.py'
LAB = ROOT / 'AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py'
ENV = os.environ.copy()
ENV.update({k:'4' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')})
ENV['PYTHONDONTWRITEBYTECODE']='1'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def job(name, args, timeout=60):
    started=time.monotonic(); peak=0; samples=0; reason=None; sampling_error=None
    with (OUT/(name+'.stdout')).open('x') as stdout, (OUT/(name+'.stderr')).open('x') as stderr:
        p=subprocess.Popen(args, cwd=ROOT, env=ENV, stdout=stdout, stderr=stderr, start_new_session=True)
        while p.poll() is None:
            if sampling_error is None:
                try:
                    observation=subprocess.run(['ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True)
                    if observation.returncode==0 and observation.stdout.strip():
                        peak=max(peak,int(observation.stdout.strip())*1024); samples+=1
                    elif observation.returncode: sampling_error=observation.stderr.strip()
                except PermissionError as e: sampling_error=str(e)
            if time.monotonic()-started>timeout: reason='timeout'
            if peak>4*1024**3: reason='rss_limit'
            if reason:
                import signal
                os.killpg(p.pid,signal.SIGKILL); break
            time.sleep(.02)
        rc=p.wait()
    return dict(name=name,argv=[str(a) for a in args],returncode=rc,timeout_seconds=timeout,elapsed_seconds=time.monotonic()-started,sampled_peak_rss_bytes=peak if samples else None,rss_samples=samples,rss_sampling_error=sampling_error,cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,termination_reason=reason)
bindings=[]
for p in (TOP,LAB):
    content=p.read_bytes(); rel=p.relative_to(ROOT)
    target=OUT/'sources'/rel; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(content)
    bindings.append(dict(path=str(p),relative_path=str(rel),sha256=digest(p),bytes=len(content),snapshot=str(target.relative_to(OUT))))
jobs=[job('default',[str(PY),'-B',str(TOP)]),job('qp',[str(PY),'-B',str(TOP),'--qp-vault-root',str(ROOT)])]
jobs.append(job('oracle',[str(PY),'-B',str(OUT/'oracle.py')]))
for b in bindings: b['unchanged_after_runs']=digest(pathlib.Path(b['path']))==b['sha256']
evidence=dict(schema='wwl147-current-bound-v1',date_local='2026-10-10 Asia/Shanghai',source_bindings=bindings,jobs=jobs,thread_environment={k:ENV[k] for k in ENV if k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')},resource_method='Attempt ps RSS sampling every nominal 20 ms; preserve denial; cumulative RUSAGE_CHILDREN max RSS and oracle RUSAGE_SELF; 60 s timeout kills process group',resource_gaps='ps denied by sandbox so no instantaneous RSS or OS thread count; attempted RLIMIT_DATA raised child preexec exception and was removed; no hard memory limit enforced, observed cumulative peak compared with 4 GiB target; numerical runtime thread limits requested through environment',status='pass' if all(j['returncode']==0 for j in jobs) and all(b['unchanged_after_runs'] for b in bindings) else 'needs_review',scope='Current default rational finite examples and current fixed floating QP; no general theory proof or interval roundoff certification')
(OUT/'2026-10-10-current-bound.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(evidence,ensure_ascii=False,indent=2))
