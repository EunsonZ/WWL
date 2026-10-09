import hashlib,json,os,pathlib,platform,resource,subprocess,sys,time
OUT=pathlib.Path(__file__).resolve().parent; ROOT=OUT.parents[3]
CAND=ROOT
REL=pathlib.Path('数学/50-信息论/80-运行证据/information_container_practice.py')
PY=ROOT/'.venv-issues-111plus/bin/python'
env=os.environ.copy();threadkeys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
env.update({k:'4' for k in threadkeys});env['PYTHONDONTWRITEBYTECODE']='1'
bindings=[]
for rel in (REL,REL.with_suffix('.md')):
    src=CAND/rel;data=src.read_bytes();dst=OUT/'sources'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
    bindings.append(dict(source_path=str(src),snapshot=str(dst.relative_to(OUT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
# Accepted business source identity; no private assembly metadata is needed.
assert bindings[0]['sha256']=='7a4d8824b776e11810038dca5010ffb31c2dd564178158a54f9e85f60d78b31d'
jobs=[]
for name,argv in [('default',[str(PY),'-B',str(CAND/REL)]),('oracle',[str(PY),'-B',str(OUT/'oracle.py')])]:
    t=time.monotonic()
    with (OUT/(name+'.stdout')).open('x') as stdout,(OUT/(name+'.stderr')).open('x') as stderr:
        try:rc=subprocess.run(argv,cwd=CAND,env=env,stdout=stdout,stderr=stderr,timeout=60).returncode;timed=False
        except subprocess.TimeoutExpired:rc=None;timed=True
    jobs.append(dict(name=name,argv=argv,cwd=str(CAND),returncode=rc,timeout_seconds=60,timed_out=timed,elapsed_seconds=time.monotonic()-t,cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss))
for row in bindings:row['unchanged_after_run']=hashlib.sha256(pathlib.Path(row['source_path']).read_bytes()).hexdigest()==row['sha256']
result=dict(schema='wwl-information-container-current-bound-v1',date_local='2026-10-10 Asia/Shanghai',source_bindings=bindings,jobs=jobs,thread_environment={k:env[k] for k in threadkeys},environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),third_party_dependencies=[]),resource_method='Sequential child execution; cumulative RUSAGE_CHILDREN peak RSS in bytes on macOS; 60 s timeout; five numerical runtime thread environment limits set to 4',resource_gaps='No hard memory limit or OS thread count observation; stdlib-only format task; RSS is peak over completed child set',status='pass' if all(j['returncode']==0 for j in jobs) and all(b['unchanged_after_run'] for b in bindings) else 'needs_review',scope='Finite IC v1 encode/decode and symbolic accounting; no physical channel, decoder error correction, BER, throughput or general coding-theorem result')
(OUT/'2026-10-10-information-container.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
