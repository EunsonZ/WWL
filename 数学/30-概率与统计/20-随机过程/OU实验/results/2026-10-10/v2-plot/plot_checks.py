import os,json,hashlib,difflib,ast,copy,math,time,resource,argparse
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET
parser=argparse.ArgumentParser(description='Check restored v2 plots against preserved v1 inputs in a fresh work area.')
parser.add_argument('--new-dir',type=Path,required=True)
parser.add_argument('--v1-dir',type=Path,required=True)
args=parser.parse_args()
base=args.new_dir.resolve();old=args.v1_dir.resolve();start=time.monotonic()
if any((base/name).exists() or (base/name).is_symlink() for name in ('plots','independent-diff.txt','plot-checks.json')):
 raise FileExistsError('plot outputs already exist; use a fresh work area')
oldbytes=(old/'snapshot/ou_lab.py').read_bytes();newbytes=(base/'snapshot/ou_lab.py').read_bytes()
assert oldbytes.split(b'def error_svg(report):')[0]==newbytes.split(b'def error_svg(report):')[0]
assert oldbytes.split(b'def main():')[1]==newbytes.split(b'def main():')[1]
oldtree=ast.parse(oldbytes);newtree=ast.parse(newbytes)
olddefs={n.name:ast.dump(n) for n in oldtree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};newdefs={n.name:ast.dump(n) for n in newtree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
changed=[n for n in olddefs if olddefs[n]!=newdefs[n]];assert changed==['error_svg']
(base/'independent-diff.txt').write_text(''.join(difflib.unified_diff(oldbytes.decode().splitlines(True),newbytes.decode().splitlines(True),fromfile='executed-v1/ou_lab.py',tofile='v2/ou_lab.py')))
assert (base/'independent-diff.txt').read_bytes()==(base/'PLOT_REVISION.diff').read_bytes()
manifest=json.loads((old/'artifact-hashes.json').read_text());assert all(hashlib.sha256((old/p).read_bytes()).hexdigest()==v for p,v in manifest.items())
spec=importlib.util.spec_from_file_location('ou_v2',base/'snapshot/ou_lab.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
report=json.loads((old/'output/report.json').read_text())
plots=base/'plots';plots.mkdir()
(plots/'actual-v1-report-v2-plot.svg').write_text(module.error_svg(report)+'\n')
# Synthetic reporting boundaries: deterministic analytic values only, zero samples.
def boundary(T,zero=False):
 c=copy.deepcopy(report['config']);c['T']=T
 if zero:c['sigma']=0;c['x0']=c['mu']
 rows=[]
 # Independent interval kernel integral of the same exact model for deterministic mock values.
 from decimal import Decimal,localcontext
 with localcontext() as ctx:
  ctx.prec=60
  D=lambda x:Decimal(str(x));k=D(c['kappa']);sigma=D(c['sigma']);tm=D(T)
  mean0=D(c['x0'])-D(c['mu']); exact=mean0*(-k*tm).exp()
  for m in c['steps']:
   h=tm/D(m);a=1-k*h;mse=(mean0*a**m-exact)**2
   for i in range(m):
    w=a**(m-1-i);l=D(i)*h;u=D(i+1)*h
    k1=((-k*(tm-u)).exp()-(-k*(tm-l)).exp())/k
    k2=((-2*k*(tm-u)).exp()-(-2*k*(tm-l)).exp())/(2*k)
    mse+=sigma*sigma*(w*w*h-2*w*k1+k2)
   assert mse>=0
   value=float(mse.sqrt())
   rows.append({'theory':{'steps':m,'h':float(h),'strong_rmse':value},'strong_rmse':{'estimate':value,'delta_method_se':0.0}})
 return {'config':c,'rows':rows,'provenance':'SYNTHETIC_PLOT_BOUNDARY_ONLY; deterministic analytic rows; zero MC samples; orange markers mock estimates'}
for name,synthetic in [('synthetic-T2-boundary',boundary(2)),('synthetic-zero-boundary',boundary(1,True))]:
 (plots/(name+'.json')).write_text(json.dumps(synthetic,indent=2)+'\n')
 (plots/(name+'.svg')).write_text(module.error_svg(synthetic)+'\n')
checks=[]
for name in ['actual-v1-report-v2-plot','synthetic-T2-boundary','synthetic-zero-boundary']:
 root=ET.fromstring((plots/(name+'.svg')).read_text());texts=[x.text for x in root.findall('.//{http://www.w3.org/2000/svg}text')]
 steps=[x.text for x in root.findall('.//{http://www.w3.org/2000/svg}text') if x.attrib.get('y')=='290']
 target=['0.25','0.125','0.0625','0.03125'] if name=='synthetic-T2-boundary' else ['0.125','0.0625','0.03125','0.015625']
 assert steps==target
 if name=='synthetic-zero-boundary':
  assert all(float(x.attrib['cy'])==265 for x in root.findall('.//{http://www.w3.org/2000/svg}circle'))
  assert any('linear (zero error included)' in x for x in texts if x)
 if name=='synthetic-T2-boundary':assert any('T=2;' in x for x in texts if x)
 checks.append({'file':name,'tick_labels':steps,'pass':True})
 import cairosvg
 cairosvg.svg2png(url=str(plots/(name+'.svg')),write_to=str(plots/(name+'.png')),output_width=1300,output_height=680)
result={'status':'PASS','changed_function_only':changed,'before_error_svg_bytes_identical':True,'main_and_after_bytes_identical':True,'numerical_core_reused':True,'fixed_MC_rerun':False,'old_26_manifest_files_match':True,'plot_checks':checks,'render_engine':'installed CairoSVG; 1300x680 PNG','wall_seconds':time.monotonic()-start,'self_max_rss_bytes_Darwin':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(base/'plot-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
