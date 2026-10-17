"""Small local rebuild with raw stdout/stderr; no network or legal decisions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists() or a.out.is_symlink():p.exit(2,'new run directory required\n')
a.out.mkdir(parents=True);base=Path(__file__).parent;rows=[]
for name,argv in [('energy',[str(base/'energy.py'),'--input',str(base/'energy.json'),'--out',str(a.out/'energy-results.json')]),('tests',['-m','unittest','-v','test_energy.py'])]:
    start=time.monotonic();cmd=[sys.executable,'-B',*argv];r=subprocess.run(cmd,cwd=base,capture_output=True,text=True,timeout=10)
    (a.out/(name+'.stdout')).write_text(r.stdout);(a.out/(name+'.stderr')).write_text(r.stderr)
    rows.append({'name':name,'argv':cmd,'cwd':str(base),'exit_code':r.returncode,'elapsed_s':time.monotonic()-start})
    if r.returncode:raise RuntimeError('failed '+name)
(a.out/'run.json').write_text(json.dumps({'python':sys.version,'threads':1,'stages':rows,'input_sha256':hashlib.sha256((base/'energy.json').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((base/'energy.py').read_bytes()).hexdigest(),'scope':'synthetic exact arithmetic; no hardware energy or legal applicability measurement'},indent=2)+'\n')
print(json.dumps({'status':'PASS','stages':len(rows),'elapsed_s':sum(r['elapsed_s'] for r in rows)}))
