import json,os,pathlib,resource,subprocess,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];PY=ROOT/'.venv-issues-111plus/bin/python'
env=os.environ.copy();keys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS');env.update({k:'4' for k in keys});env['PYTHONDONTWRITEBYTECODE']='1'
receipt=json.loads((OUT/'execution-receipt.json').read_text());jobs=receipt['jobs']
for name in ('oracle_fourier','oracle_iir','render_svg'):
    path=OUT/(name+'.py')
    if not path.exists():continue
    t=time.monotonic();argv=[str(PY),'-B',str(path)]
    with (OUT/(name+'.stdout')).open('x') as stdout,(OUT/(name+'.stderr')).open('x') as stderr:
        try:rc=subprocess.run(argv,cwd=OUT,env=env,stdout=stdout,stderr=stderr,timeout=60).returncode;timed=False
        except subprocess.TimeoutExpired:rc=None;timed=True
    row=dict(name=name,argv=argv,cwd=str(OUT),returncode=rc,timed_out=timed,timeout_seconds=60,elapsed_seconds=time.monotonic()-t,cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    jobs.append(row);receipt['status']='all_jobs_exit0' if all(j['returncode']==0 for j in jobs) else 'needs_review'
    (OUT/'execution-receipt-with-independent.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(row),flush=True)
