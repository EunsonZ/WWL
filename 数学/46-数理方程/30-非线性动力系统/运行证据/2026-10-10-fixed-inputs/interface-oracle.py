from pathlib import Path
import importlib.util,subprocess,sys,json,hashlib
p=Path(__file__).resolve().parent;source=p/'snapshot/dynamics_lab.py'
s=importlib.util.spec_from_file_location('business',source);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
rows=[]
for label,call in [('negative radius',lambda:m.radial_exact(1,1,-.1,1)),('shape mismatch',lambda:m.rk4(lambda z:(1,), (0,0),.01,1)),('oversized RK4',lambda:m.rk4(lambda z:(0,), (0,),.01,100001))]:
 try:call()
 except ValueError as e:rows.append({'case':label,'expected':'ValueError','actual':str(e)})
 else:raise AssertionError(label)
for label,target in [('existing output',p/'cli-output'),('new inside workspace',p/'must-not-be-created')]:
 before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'snapshot').rglob('*') if f.is_file()}
 command=[sys.executable,'-B',str(source),'--output-dir',str(target)]
 r=subprocess.run(command,capture_output=True,text=True,timeout=30)
 (p/(label.replace(' ','-')+'.stdout')).write_text(r.stdout);(p/(label.replace(' ','-')+'.stderr')).write_text(r.stderr)
 assert r.returncode!=0
 if label=='new inside workspace':assert not target.exists()
 assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'snapshot').rglob('*') if f.is_file()}
 rows.append({'case':label,'command':command,'returncode':r.returncode,'refused_without_source_changes':True})
(p/'interface-results.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
