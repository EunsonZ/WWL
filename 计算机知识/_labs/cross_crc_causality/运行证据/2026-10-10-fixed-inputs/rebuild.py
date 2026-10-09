"""Static-only author recipe. Run explicitly with a NEW nonexistent work directory.
Copies executable sources/inputs only; no historical logs/results are consumed.
"""
from pathlib import Path
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,time
P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('work',type=Path)
args=parser.parse_args();work=args.work.resolve()
if work.exists():raise SystemExit('work must be a new nonexistent directory')
work.mkdir(parents=True)
# Bind fresh executable sources to the archived execution package before copying.
bindings={row['target']:row for row in json.loads((P/'copy-map.json').read_text())['items']}
labrel=Path('snapshot/计算机知识/_labs/cross_crc_causality')
paths=[labrel/name for name in ('crc.py','verify_crc.py','crc_inputs.json','crc_expected.json')]+[Path('oracle-retry.py'),Path('interface-oracle.py')]
for rel in paths:
 data=(P/rel).read_bytes()
 if hashlib.sha256(data).hexdigest()!=bindings[str(rel)]['sha256']:raise SystemExit(f'archive source mismatch: {rel}')
 target=work/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
lab=work/labrel;python=sys.executable;env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):env[key]='4'
(work/'environment.json').write_text(json.dumps({'python':sys.version,'executable':python,'platform':platform.platform(),'scope':'thread environment requests only; no hard cap'},indent=2)+'\n')
receipts={}
def task(label,argv,limit):
 started=time.monotonic();error=None;rc=None
 with (work/(label+'.stdout')).open('xb') as stdout,(work/(label+'.stderr')).open('xb') as stderr:
  try:
   result=subprocess.run(argv,cwd=work,env=env,stdout=stdout,stderr=stderr,timeout=limit,check=False);rc=result.returncode
  except (OSError,subprocess.TimeoutExpired) as exc:error=repr(exc)
 receipt={'label':label,'argv':argv,'cwd':str(work),'returncode':rc,'error':error,'timeout_seconds':limit,'elapsed_seconds':time.monotonic()-started,'stdout':label+'.stdout','stderr':label+'.stderr'}
 receipts[label]=receipt;(work/(label+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 # Reject child failures even if an outer supervisor happens to exit zero.
 if error is not None or rc!=0:raise SystemExit(f'{label} failed; inspect receipt and both streams')
 if (work/receipt['stderr']).stat().st_size!=0:raise SystemExit(f'{label} unexpected stderr')
 if (work/receipt['stdout']).stat().st_size==0:raise SystemExit(f'{label} empty stdout')
def gate(expected):
 if set(receipts)!=set(expected) or len(receipts)!=len(expected):raise SystemExit('task set/count mismatch')
 for label in expected:
  r=json.loads((work/(label+'-receipt.json')).read_text())
  if r['label']!=label or r['returncode']!=0 or r['error'] is not None:raise SystemExit('child receipt failure')
  if not (work/r['stdout']).is_file() or (work/r['stderr']).read_bytes()!=b'':raise SystemExit('child stream failure')
task('prepare',[python,'-B',str(work/'oracle-retry.py'),'prepare'],60)
gate(['prepare'])
json.loads((work/'expectations-before-run.json').read_text())
task('crc',[python,'-B',str(lab/'crc.py')],60)
gate(['prepare','crc']);json.loads((work/'crc.stdout').read_text())
task('author-verify',[python,'-B',str(lab/'verify_crc.py'),str(work/'crc.stdout')],300)
gate(['prepare','crc','author-verify'])
task('independent',[python,'-B',str(work/'oracle-retry.py'),'verify'],300)
gate(['prepare','crc','author-verify','independent']);json.loads((work/'independent-results.json').read_text())
task('interface',[python,'-B',str(work/'interface-oracle.py')],60)
gate(['prepare','crc','author-verify','independent','interface']);json.loads((work/'interface-results.json').read_text())
(work/'completion.json').write_text(json.dumps({'expected_tasks':['prepare','crc','author-verify','independent','interface'],'actual_tasks':list(receipts),'count':len(receipts),'result':'all individual child outcomes and streams checked'},indent=2)+'\n')
print('Five fresh tasks checked; results belong only to this new work directory.')
