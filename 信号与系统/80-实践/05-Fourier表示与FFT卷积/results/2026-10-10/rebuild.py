"""Explicit fresh-directory reproduction interface. Never run while packaging.
Original sources/drivers/oracles remain unchanged; inspect fixed-runs and actual receipts.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,time

def main():
 p=argparse.ArgumentParser();p.add_argument('--work',required=True);p.add_argument('--kind',choices=['v1','v2r1'],required=True);a=p.parse_args()
 work=Path(a.work).resolve();assert work.is_dir() and not any(work.iterdir()),'work must be new and empty'
 base=Path(__file__).resolve().parent
 source=base/'v1' if a.kind=='v1' else base.parents[2]/'06-IIR规格与实现/results/2026-10-10/v2r1'
 runs=[];env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
 for d in ('logs','raw','home','tmp'): (work/d).mkdir()
 def job(name,argv,cwd,receipt=None):
  start=time.monotonic();record={'name':name,'argv':list(map(str,argv)),'cwd':str(cwd)}
  try:
   with (work/'logs'/f'{name}.stdout').open('x') as out,(work/'logs'/f'{name}.stderr').open('x') as err:
    r=subprocess.run(argv,cwd=cwd,env=env,stdout=out,stderr=err,timeout=300 if name=='iir-cli' else 60)
   record['exit']=r.returncode
   if receipt:
    actual=json.loads((work/receipt).read_text());record['actual_receipt_exit']=actual['exit'];assert actual['exit']==0 and not actual.get('error'),actual
   assert r.returncode==0,record
   if name=='executor-oracle':assert json.loads((work/'logs/executor-oracle.stdout').read_text())['status']=='PASS'
  except Exception as e:
   record['error']=type(e).__name__;raise
  finally:
   record['elapsed_seconds']=time.monotonic()-start;runs.append(record);(work/'fixed-runs.json').write_text(json.dumps({'kind':a.kind,'runs':runs},ensure_ascii=False,indent=2)+'\n')
 if a.kind=='v1':
  shutil.copytree(source/'source-layout',work/'source-layout')
  for name in ('oracle_fourier.py','oracle_iir.py','supplementary_delay_retry.py'):shutil.copyfile(source/name,work/name)
  env.update(NUMEXPR_NUM_THREADS='4',VECLIB_MAXIMUM_THREADS='4')
  for name,folder,lab in [('fourier','05-Fourier表示与FFT卷积','fourier_lab'),('iir','06-IIR规格与实现','iir_lab')]:
   cwd=work/'source-layout/信号与系统/80-实践'/folder
   job(name+'-tests',[sys.executable,'-B','-m','unittest','-v','test_'+lab+'.py'],cwd)
   job(name+'-cli',[sys.executable,'-B',lab+'.py','--output',str(work/(name+'-cli-output'))],cwd)
  for name in ('oracle_fourier','oracle_iir','supplementary_delay_retry'):job(name,[sys.executable,'-B',str(work/(name+'.py'))],work)
  expected={'fourier-tests','fourier-cli','iir-tests','iir-cli','oracle_fourier','oracle_iir','supplementary_delay_retry'}
 else:
  for name in ('snapshot','snapshot-r1'):shutil.copytree(source/name,work/name)
  for name in ('run_cli.py','run_tests_r1.py','executor_oracle.py'):shutil.copyfile(source/name,work/name)
  job('iir-cli',[sys.executable,'-B',str(work/'run_cli.py')],work,'cli-run.json')
  job('iir-tests-r1',[sys.executable,'-B',str(work/'run_tests_r1.py')],work,'r1-test-run.json')
  job('executor-oracle',[sys.executable,'-B',str(work/'executor_oracle.py')],work)
  expected={'iir-cli','iir-tests-r1','executor-oracle'}
 assert {r['name'] for r in runs}==expected and len(runs)==len(expected)
 assert all(r.get('exit')==0 and not r.get('error') for r in runs)
 print(json.dumps({'status':'PASS','expected_tasks':sorted(expected),'receipt':str(work/'fixed-runs.json')},ensure_ascii=False))
if __name__=='__main__':main()
