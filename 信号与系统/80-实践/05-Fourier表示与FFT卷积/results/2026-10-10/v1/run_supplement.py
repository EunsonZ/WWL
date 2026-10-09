import json,os,pathlib,resource,subprocess,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];PY=ROOT/'.venv-issues-111plus/bin/python';env=os.environ.copy();env.update({k:'4' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')});env['PYTHONDONTWRITEBYTECODE']='1';jobs=[]
for name in ('supplementary_delay','render_svg'):
    argv=[str(PY),'-B',str(OUT/(name+'.py'))];t=time.monotonic()
    with (OUT/(name+'.stdout')).open('x') as stdout,(OUT/(name+'.stderr')).open('x') as stderr:
        try:rc=subprocess.run(argv,cwd=OUT,env=env,stdout=stdout,stderr=stderr,timeout=60).returncode;timed=False
        except subprocess.TimeoutExpired:rc=None;timed=True
    row=dict(name=name,argv=argv,cwd=str(OUT),returncode=rc,timed_out=timed,timeout_seconds=60,elapsed_seconds=time.monotonic()-t,cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss);jobs.append(row);(OUT/'supplementary-jobs.json').write_text(json.dumps(jobs,indent=2)+'\n');print(json.dumps(row),flush=True)
