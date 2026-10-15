#!/usr/bin/env python3
"""Extract common Obsidian LaTeX delimiters outside fenced and inline code."""
import argparse,json,re
from datetime import datetime
from pathlib import Path
from audit_vault import without_code

def vault_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / 'AGENTS.md').is_file():
            return candidate
    raise RuntimeError(f'Cannot locate vault root from {start}')

def default_output_dir() -> Path:
    stamp=datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    return vault_root(Path(__file__).resolve().parent)/'Logs/运行/math-extract'/stamp/'计算机知识'

def extract(root):
    expressions=[]; delimiter_review=[]
    for p in sorted(root.rglob('*.md')):
        if '_meta' in p.relative_to(root).parts:continue
        text,_=without_code(p.read_text('utf-8'));pos=0
        delimiters=re.compile(r'(?<!\\)(\$\$|\$)|\\\(|\\\[')
        while (m:=delimiters.search(text,pos)) is not None:
            opening=m.group(0);closing={'$':'$','$$':'$$',r'\(':r'\)',r'\[':r'\]'}[opening]
            endpattern=re.compile((r'(?<!\\)' if opening.startswith('$') else '')+re.escape(closing))
            end=endpattern.search(text,m.end())
            if not end:
                delimiter_review.append({'source':p.relative_to(root).as_posix(),'line':text.count('\n',0,m.start())+1,'delimiter':opening});pos=m.end();continue
            tex=text[m.end():end.start()]
            if opening=='$' and '\n\n' in tex:
                delimiter_review.append({'source':p.relative_to(root).as_posix(),'line':text.count('\n',0,m.start())+1,'delimiter':opening,'reason':'inline math spans a paragraph'});pos=m.end();continue
            expressions.append({'source':p.relative_to(root).as_posix(),'line':text.count('\n',0,m.start())+1,'display':opening in ('$$',r'\['),'tex':tex})
            pos=end.end()
    return {'expressions':expressions,'delimiter_review':delimiter_review}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--output-dir',type=Path);a=ap.parse_args();data=extract(a.root)
    default_dir=default_output_dir()
    out=a.output or (a.output_dir or default_dir)/'math_expressions.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('expressions',len(data['expressions']),'delimiter review',len(data['delimiter_review']))
