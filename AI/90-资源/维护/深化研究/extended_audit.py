from pathlib import Path
import re,json,sys
from collections import Counter,defaultdict,deque
import hashlib
from urllib.parse import unquote
from PIL import Image
from xml.etree import ElementTree
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'90-资源/维护'))
from check_vault import prose
inventory=json.loads((HERE/'original_inventory.json').read_text());originals={i['path']:i for i in inventory}
notes={str(p.relative_to(ROOT)):p for p in ROOT.rglob('*.md')}
stems=defaultdict(list)
for rel,p in notes.items():stems[p.stem].append(rel)

def resolve(raw,source):
 target=unquote(raw.replace('\\|','|').split('|',1)[0].split('#',1)[0].strip())
 if not target:return source
 for base in [ROOT.parent,ROOT,(ROOT/source).parent]:
  for suffix in ['', '.md']:
   q=(base/(target+suffix)).resolve()
   try:rel=str(q.relative_to(ROOT))
   except ValueError:continue
   if rel in notes:return rel
 if '/' not in target and len(stems.get(target.removesuffix('.md'),[]))==1:return stems[target.removesuffix('.md')][0]
 return None

adjacency={rel:set() for rel in notes};footnotes=[];artifacts=[]
for rel,p in notes.items():
 text=p.read_text();clean,_=prose(text)
 for target in re.findall(r'(?<!!)\[\[([^\]\n]+)\]\]',clean):
  dest=resolve(target,rel)
  if dest:adjacency[rel].add(dest)
 for label,target in re.findall(r'(?<!!)\[([^\]\n]+)\]\(([^)\n]+)\)',clean):
  if re.match(r'\w+://',target):continue
  dest=resolve(target,rel)
  if dest:adjacency[rel].add(dest)
 definitions=Counter(re.findall(r'^\[\^([^\]]+)\]:',clean,re.M))
 refs=Counter(re.findall(r'\[\^([^\]]+)\](?!:)',clean))
 if set(refs)-set(definitions) or any(v>1 for v in definitions.values()) or set(definitions)-set(refs):
  footnotes.append({'path':rel,'missing_definitions':list(set(refs)-set(definitions)),'duplicate_definitions':[k for k,v in definitions.items() if v>1],'unused_definitions':list(set(definitions)-set(refs))})
 for pattern in [r'\[\[@',r'\[\[ @',r'\[@\w+\]',r'\x00',r'\bTODO\b']:
  if re.search(pattern,clean) and rel not in originals:artifacts.append({'path':rel,'pattern':pattern})
seen={'README.md'};queue=deque(seen)
while queue:
 for dest in adjacency[queue.popleft()]-seen:seen.add(dest);queue.append(dest)
unreachable=sorted(set(notes)-seen)
figure_checks=[]
for p in (ROOT/'90-资源/图示').rglob('*'):
 if p.suffix=='.png':
  with Image.open(p) as im: size=list(im.size);im.verify()
  figure_checks.append({'path':str(p.relative_to(ROOT)),'kind':'PNG','size':size,'valid':True})
 elif p.suffix=='.svg':
  ElementTree.parse(p);figure_checks.append({'path':str(p.relative_to(ROOT)),'kind':'SVG','valid':True})
change_list=[]
for rel,p in sorted(notes.items()):
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 change_list.append({'path':rel,'status':'new' if rel not in originals else ('unchanged' if sha==originals[rel]['sha256'] else 'modified'),
                     'original_sha256':originals.get(rel,{}).get('sha256'),'sha256':sha,'characters':len(p.read_text())})
report={'markdown':len(notes),'original_paths_retained':sum(rel in notes for rel in originals),'missing_original_paths':sorted(set(originals)-set(notes)),
        'reachable_from_README':len(seen),'unreachable_from_README':unreachable,'footnote_issues':footnotes,'unfinished_markers':artifacts,
        'figure_checks':figure_checks,'change_counts':dict(Counter(x['status'] for x in change_list))}
maintenance=ROOT/'90-资源/维护/深化研究'
(maintenance/'extended_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(maintenance/'file_changes.json').write_text(json.dumps(change_list,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['figure_checks']},ensure_ascii=False,indent=2))

# 逐来源、逐目标、逐出现次数比较库外引用，不能只比较去重后的名称。
baseline=json.loads((HERE/'original_vault_audit.json').read_text())
current=json.loads((HERE/'vault_audit.json').read_text())
before=Counter((x['source'],x['target']) for x in baseline['external_vault_links'])
after=Counter((x['source'],x['target']) for x in current['external_vault_links'])
def records(counter):
 return [{'source':source,'target':target,'count':count} for (source,target),count in sorted(counter.items())]
external={'preserved_exactly':before==after,'original_occurrences':sum(before.values()),'current_occurrences':sum(after.values()),
          'unique_targets':len({target for source,target in before}),'missing':records(before-after),'added':records(after-before),
          'original_references':records(before)}
(HERE/'external_references.json').write_text(json.dumps(external,ensure_ascii=False,indent=2))
if (report['missing_original_paths'] or report['unreachable_from_README'] or report['footnote_issues']
    or report['unfinished_markers'] or not external['preserved_exactly']):
 raise SystemExit(1)
