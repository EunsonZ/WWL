import json,os,pathlib,resource,subprocess,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];env=os.environ.copy();env.update({k:'4' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')});env['PYTHONDONTWRITEBYTECODE']='1';argv=[str(ROOT/'.venv-issues-111plus/bin/python'),'-B',str(OUT/'supplementary_delay_retry.py')];t=time.monotonic()
with (OUT/'supplementary_delay_retry.stdout').open('x') as stdout,(OUT/'supplementary_delay_retry.stderr').open('x') as stderr:
    try:rc=subprocess.run(argv,cwd=OUT,env=env,stdout=stdout,stderr=stderr,timeout=60).returncode;timed=False
    except subprocess.TimeoutExpired:rc=None;timed=True
row=dict(argv=argv,cwd=str(OUT),returncode=rc,timed_out=timed,timeout_seconds=60,elapsed_seconds=time.monotonic()-t,cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,reason='Independent helper first attempt used unstable generic numerical roots on repeated z=-1 zeros; retry validates numerator identity and uses exact repeated zeros. Course source unchanged.')
(OUT/'supplementary-delay-retry-job.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
