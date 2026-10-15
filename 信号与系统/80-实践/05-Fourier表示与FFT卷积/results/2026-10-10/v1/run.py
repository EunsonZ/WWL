import hashlib,json,os,pathlib,platform,resource,shutil,subprocess,sys,time,uuid
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3]
AUTHOR=ROOT/'.wwl-recovery/2026-10-10-crash/author177178';SOURCE=OUT/'source-layout'
FOURIER=pathlib.Path('信号与系统/80-实践/05-Fourier表示与FFT卷积');IIR=pathlib.Path('信号与系统/80-实践/06-IIR规格与实现')
PY=ROOT/'.venv-issues-111plus/bin/python'
bindings=[]
for item in json.loads((AUTHOR/'evidence/targets.json').read_text()):
    src=AUTHOR/'candidate'/item['path'];data=src.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha==item['candidate_sha256']
    dst=SOURCE/item['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
    bindings.append(dict(path=item['path'],source=str(src),sha256=sha,bytes=len(data)))
for name in ('AGENTS.md','HANDOFF.md','EXECUTOR.md'):
    (SOURCE/name).write_bytes((AUTHOR/name).read_bytes())
(OUT/'source-bindings.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2)+'\n')
env=os.environ.copy();keys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS');env.update({k:'4' for k in keys});env['PYTHONDONTWRITEBYTECODE']='1'
tmp=pathlib.Path('/private/tmp')/('wwl-recovery-177178-'+uuid.uuid4().hex[:12]);tmp.mkdir()
jobs=[]
def job(name,argv,cwd,transient=None,timeout=60):
    t=time.monotonic()
    with (OUT/(name+'.stdout')).open('x') as stdout,(OUT/(name+'.stderr')).open('x') as stderr:
        try:rc=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,stdout=stdout,stderr=stderr,timeout=timeout).returncode;timed=False
        except subprocess.TimeoutExpired:rc=None;timed=True
    row=dict(name=name,argv=[str(x) for x in argv],cwd=str(cwd),returncode=rc,timed_out=timed,timeout_seconds=timeout,elapsed_seconds=time.monotonic()-t,cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    if transient and transient.exists():
        copied=OUT/(name+'-output');shutil.copytree(transient,copied);items=[]
        for p in sorted(transient.rglob('*')):
            if p.is_file():
                rel=p.relative_to(transient);a=p.read_bytes();b=(copied/rel).read_bytes();assert a==b
                items.append(dict(path=str(rel),bytes=len(a),sha256=hashlib.sha256(a).hexdigest(),copy_identical=True))
        row['transient_output']=str(transient);row['durable_copy']=str(copied);row['copied_files']=items
    jobs.append(row)
    (OUT/'jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(row,ensure_ascii=False),flush=True)
job('fourier-tests',[PY,'-B','-m','unittest','-v','test_fourier_lab.py'],SOURCE/FOURIER)
job('fourier-cli',[PY,'-B','fourier_lab.py','--output',tmp/'fourier'],SOURCE/FOURIER,tmp/'fourier')
job('iir-tests',[PY,'-B','-m','unittest','-v','test_iir_lab.py'],SOURCE/IIR)
job('iir-cli',[PY,'-B','iir_lab.py','--output',tmp/'iir'],SOURCE/IIR,tmp/'iir')
for name in ('oracle_fourier.py','oracle_iir.py','render_svg.py'):
    if (OUT/name).exists():job(name[:-3],[PY,'-B',OUT/name],OUT,timeout=60)
for b in bindings:b['author_unchanged_after']=hashlib.sha256(pathlib.Path(b['source']).read_bytes()).hexdigest()==b['sha256']
receipt=dict(schema='wwl177178-current-bound-v1',source_bindings=bindings,jobs=jobs,transient_root=str(tmp),environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),thread_limits={k:env[k] for k in keys}),resource_scope='Sequential A-slot child execution, 60 s per job, completed children RSS peaks; no observed OS thread count or hard RSS limit',status='all_jobs_exit0' if all(j['returncode']==0 for j in jobs) else 'needs_review')
(OUT/'execution-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
