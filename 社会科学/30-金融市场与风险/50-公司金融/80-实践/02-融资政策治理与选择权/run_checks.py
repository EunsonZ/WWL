import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists() or a.out.is_symlink():p.exit(2,'fresh output directory required\n')
a.out.mkdir(parents=True);base=Path(__file__).parent;stages=[]
for name,args in [('fixed',[str(base/'financing.py'),'--input',str(base/'inputs.json'),'--out',str(a.out/'results.json')]),('tests',['-m','unittest','-v','test_financing.py'])]:
    argv=[sys.executable,'-B',*args];t=time.monotonic();r=subprocess.run(argv,cwd=base,capture_output=True,text=True,timeout=20)
    (a.out/(name+'.stdout')).write_text(r.stdout);(a.out/(name+'.stderr')).write_text(r.stderr);stages.append({'name':name,'argv':argv,'cwd':str(base),'exit_code':r.returncode,'elapsed_s':time.monotonic()-t})
    if r.returncode:raise RuntimeError(name+' failed')
(a.out/'run.json').write_text(json.dumps({'stages':stages,'python':sys.version,'threads':1,'source_sha256':hashlib.sha256((base/'financing.py').read_bytes()).hexdigest(),'input_sha256':hashlib.sha256((base/'inputs.json').read_bytes()).hexdigest(),'scope':'synthetic exact Fraction; no external market, tax or governance execution'},indent=2)+'\n')
print(json.dumps({'status':'PASS','stages':len(stages),'elapsed_s':sum(s['elapsed_s'] for s in stages)}))
