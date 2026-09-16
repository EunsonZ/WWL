#!/usr/bin/env python3
"""Static Python/shell/frontmatter/table checks. Never runs example programs.
PyYAML is optional; without it, YAML checks are explicitly skipped.
"""
from pathlib import Path
from datetime import datetime
import argparse,json,re,subprocess,shutil
try:import yaml
except ImportError:yaml=None

def check(root):
 result={'python':[],'shell':[],'yaml':[],'table_review':[]}
 for p in sorted(root.rglob('*.py')):
  try:compile(p.read_text('utf-8'),str(p),'exec');item={'status':'PASS'}
  except Exception as e:item={'status':'FAIL','error':str(e)}
  result['python'].append({'source':p.relative_to(root).as_posix(),**item})
 for p in sorted(root.rglob('*.sh')):
  if not shutil.which('bash'):item={'status':'SKIP','reason':'bash unavailable'}
  else:
   r=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True,timeout=10);item={'status':'PASS' if r.returncode==0 else 'FAIL','stderr':r.stderr}
  result['shell'].append({'source':p.relative_to(root).as_posix(),**item})
 for p in sorted(root.rglob('*.md')):
  text=p.read_text('utf-8');lines=text.splitlines()
  if text.startswith('---\n'):
   try:
    if yaml:yaml.safe_load(text.split('---',2)[1]);item={'status':'PASS'}
    else:item={'status':'SKIP','reason':'PyYAML unavailable'}
   except Exception as e:item={'status':'FAIL','error':str(e)}
   result['yaml'].append({'source':p.relative_to(root).as_posix(),**item})
  fence=None;i=0
  def ncols(line):return len(re.split(r'(?<!\\)\|',line.strip().removeprefix('|').removesuffix('|')))
  while i<len(lines)-1:
   line=lines[i];m=re.match(r'^\s{0,3}(`{3,}|~{3,})',line)
   if m:
    t=m.group(1)
    if fence is None:fence=t
    elif t[0]==fence[0] and len(t)>=len(fence):fence=None
   if not fence and line.strip().startswith('|') and re.fullmatch(r'[\s|:\-]+',lines[i+1]) and '---' in lines[i+1]:
    cols=ncols(line);j=i+1
    while j<len(lines) and lines[j].strip().startswith('|'):
     n=ncols(lines[j])
     if n!=cols:result['table_review'].append({'source':p.relative_to(root).as_posix(),'line':j+1,'columns':n,'expected':cols,'text':lines[j]})
     j+=1
    i=j;continue
   i+=1
 return result

def vault_root(start: Path) -> Path:
 for candidate in (start,*start.parents):
  if (candidate/'AGENTS.md').is_file():return candidate
 raise RuntimeError(f'Cannot locate vault root from {start}')
def default_output_dir() -> Path:
 stamp=datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
 return vault_root(Path(__file__).resolve().parent)/'Logs/运行/source-syntax'/stamp/'计算机知识'
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--output-dir',type=Path);a=ap.parse_args();data=check(a.root)
 output_dir=a.output_dir or default_output_dir();output_dir.mkdir(parents=True,exist_ok=True)
 (output_dir/'source_syntax_results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 for k,v in data.items():print(k,len(v),'fail',sum(x.get('status')=='FAIL' for x in v))
