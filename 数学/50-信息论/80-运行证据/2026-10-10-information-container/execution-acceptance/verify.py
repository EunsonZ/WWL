"""Standalone formal-layout acceptance; only writes beneath this file's directory."""
import ast,difflib,hashlib,json,os,pathlib,resource,subprocess,sys,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3]
CAND=ROOT/'.wwl-recovery/2026-10-10-crash/assembled-candidates/information-r1'
OLD=ROOT/'.wwl-recovery/2026-10-10-crash/experiments-a/2026-10-10-information-container'
DEPLOY=pathlib.Path('数学/50-信息论/80-运行证据')
FORMAL=DEPLOY/'2026-10-10-information-container'
OVERLAY=OUT/'formal-overlay';OVERLAY.mkdir()
expected={'run.py':'aea3ce0fe7002e377b4ecddcf3111f5c5173d16d667fb1135e975db86f674fb2','oracle.py':'3eb934305f52d46677ab7f8c15c4c791baad50055b70efcd8da417d5731c562d','information_container_practice.py':'7a4d8824b776e11810038dca5010ffb31c2dd564178158a54f9e85f60d78b31d'}
bindings=[];imports={}
paths=[DEPLOY/'information_container_practice.py',DEPLOY/'information_container_practice.md',FORMAL/'run.py',FORMAL/'oracle.py',pathlib.Path('AGENTS.md')]
for rel in paths:
    src=CAND/rel;data=src.read_bytes();sha=hashlib.sha256(data).hexdigest()
    if rel.name in expected:assert sha==expected[rel.name],(rel,sha)
    dst=OVERLAY/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
    bindings.append(dict(candidate_path=str(src),formal_path=str(rel),sha256=sha,bytes=len(data)))
    if rel.suffix=='.py':
        tree=ast.parse(data.decode());imports[str(rel)]=[ast.unparse(node) for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
for name in ('run.py','oracle.py'):
    old=(OLD/name).read_text();new=(CAND/FORMAL/name).read_text()
    assert '.wwl-recovery/' not in new and 'assembled-candidates' not in new
    (OUT/(name+'.adaptation.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='first-experiment/'+name,tofile='formal/'+name)))
oldoracle=(OLD/'oracle.py').read_text()
assert (CAND/FORMAL/'oracle.py').read_text()==oldoracle.replace("SOURCE=ROOT/'.wwl-recovery/2026-10-10-crash/assembled-candidates/information-r1/数学/50-信息论/80-运行证据/information_container_practice.py'","SOURCE=ROOT/'数学/50-信息论/80-运行证据/information_container_practice.py'")
# Only external runtime is the already installed interpreter environment, linked locally.
(OVERLAY/'.venv-issues-111plus').symlink_to(ROOT/'.venv-issues-111plus',target_is_directory=True)
assert not (OVERLAY/'.wwl-recovery').exists()
env=os.environ.copy();threadkeys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
env.update({k:'4' for k in threadkeys});env['PYTHONDONTWRITEBYTECODE']='1'
command=[str(OVERLAY/'.venv-issues-111plus/bin/python'),'-B',str(FORMAL/'run.py')]
t=time.monotonic()
with (OUT/'portable-command.stdout').open('x') as stdout,(OUT/'portable-command.stderr').open('x') as stderr:
    try:rc=subprocess.run(command,cwd=OVERLAY,env=env,stdout=stdout,stderr=stderr,timeout=60).returncode;timed=False
    except subprocess.TimeoutExpired:rc=None;timed=True
elapsed=time.monotonic()-t
assert rc==0,('portable collector failed',rc)
evidence=json.loads((OVERLAY/FORMAL/'2026-10-10-information-container.json').read_text())
assert evidence['status']=='pass' and all(j['returncode']==0 for j in evidence['jobs'])
result=json.loads((OVERLAY/FORMAL/'independent-checks.json').read_text())
assert result['status']=='pass' and result['total_finite_encode_decode_cases']==680 and result['rejected_cases']==25 and result['accepted_boundary_cases']==4
assert json.loads((OVERLAY/FORMAL/'fixed-inputs-and-results.json').read_text())==json.loads((OLD/'fixed-inputs-and-results.json').read_text())
assert (OVERLAY/FORMAL/'default.stdout').read_bytes()==(OLD/'default.stdout').read_bytes()
for b in bindings:
    b['candidate_unchanged_after']=hashlib.sha256(pathlib.Path(b['candidate_path']).read_bytes()).hexdigest()==b['sha256']
    b['overlay_unchanged_after']=hashlib.sha256((OVERLAY/b['formal_path']).read_bytes()).hexdigest()==b['sha256']
assert all(b['candidate_unchanged_after'] and b['overlay_unchanged_after'] for b in bindings)
receipt=dict(schema='wwl-information-portable-acceptance-v1',status='pass',candidate_root=str(CAND),formal_deployment_directory=str(FORMAL),actual_overlay_root=str(OVERLAY),source_bindings=bindings,static_imports=imports,oracle_adaptation='Exactly one SOURCE path replacement; assertions, fixed inputs, independent packing, trie, 680/25/4 cases unchanged',collector_adaptation='CAND=ROOT; source bindings collect only formal business py/md; fixed SHA gate replaces private assembly metadata',hidden_runtime_dependencies=[],runtime_environment_link=dict(path=str(OVERLAY/'.venv-issues-111plus'),target=str(ROOT/'.venv-issues-111plus'),scope='Existing interpreter and standard library only'),command=command,cwd=str(OVERLAY),returncode=rc,timeout_seconds=60,timed_out=timed,elapsed_seconds=elapsed,thread_environment={k:env[k] for k in threadkeys},cumulative_children_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,resource_gaps='No OS thread count or hard RSS limit; cumulative peak measures completed child set',finite_results=dict(short_cases=680,rejected_cases=25,accepted_boundary_cases=4,all_fixed_inputs_results_equal_first_experiment=True,raw_default_stdout_identical_first_experiment=True),scope='Formal-layout current execution and finite algorithm/accounting behavior; no actual channel, BER, error correction, throughput or general algorithm correctness claim')
(OUT/'portable-acceptance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
