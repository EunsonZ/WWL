#!/usr/bin/env python3
"""审计本地 Obsidian 数学子目录，不修改正文，不创建库外占位文件。
默认输出静态审计结果.json；--extract-formulas 仅输出公式片段供 MathJax 使用。
库外保留范围来自原始库外引用基线.json，不把未上传目录错误标成坏链。
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit
import yaml

DEFAULT_ROOT=Path(__file__).resolve().parents[2]

def mask(text: str,frontmatter: bool=False,inline: bool=True) -> str:
    """隐藏代码但保留换行位置；链接审计保留 YAML，公式审计不含 YAML。"""
    lines=text.splitlines(keepends=True);fence=None;out=[]
    for line in lines:
        clean=re.sub(r'^\s*(?:>\s*)+','',line)
        m=re.match(r'^\s*(`{3,}|~{3,})',clean)
        if fence:
            if m and m.group(1)[0]==fence[0] and len(m.group(1))>=len(fence):fence=None
            out.append('\n' if line.endswith('\n') else '');continue
        if m:fence=m.group(1);out.append('\n' if line.endswith('\n') else '');continue
        out.append(line)
    s=''.join(out)
    if frontmatter:
        s=re.sub(r'\A---\s*\n.*?\n---\s*\n',lambda m:'\n'*m.group().count('\n'),s,count=1,flags=re.S)
    if inline:s=re.sub(r'(`+)([^\n]*?)\1',lambda m:' '*len(m.group()),s)
    return s

def formulas(text: str,rel: str) -> tuple[list[dict],list[dict]]:
    s=mask(text,True);s=re.sub(r'(?m)^[ \t]*(?:> ?)+','',s)
    out=[];errors=[];pos=0
    pattern=re.compile(r'(?<!\\)(\$\$|\$)')
    while True:
        m=pattern.search(s,pos)
        if m is None:break
        delim=m.group(1);end=re.compile(r'(?<!\\)'+re.escape(delim)).search(s,m.end())
        line=s.count('\n',0,m.start())+1
        if end is None:
            errors.append({'path':rel,'line':line,'type':'unclosed_math','delimiter':delim});break
        tex=s[m.end():end.start()].strip()
        if not tex:errors.append({'path':rel,'line':line,'type':'empty_math'})
        else:out.append({'path':rel,'line':line,'display':delim=='$$','tex':tex})
        pos=end.end()
    return out,errors

def wiki_items(s: str):
    for m in re.finditer(r'!?\[\[([^\]\n]+)\]\]',s):
        raw=m.group(1);target=re.split(r'\\?\|',raw,maxsplit=1)[0].strip()
        yield m,target,raw

def heading_text(s: str) -> str:
    s=re.sub(r'\s+#+\s*$','',s.strip());return s

def audit(root: Path) -> dict:
    paths=sorted(root.rglob('*.md'));texts={p:p.read_text(encoding='utf-8') for p in paths}
    base=json.loads((root/'90-资源/维护/原始文件基线.json').read_text(encoding='utf-8'))
    extbase=json.loads((root/'90-资源/维护/原始库外引用基线.json').read_text(encoding='utf-8'))
    expected=Counter((r['source'],r['target']) for r in extbase);external_allowed={r['target'] for r in extbase}
    extseen=Counter();errors=[];warnings=[];edges=defaultdict(set);images=set();math=[];links=0;mdlinks=0;embeds=0;remote_images=0;anchors=0
    bystem=defaultdict(list)
    headings={}
    for p,s in texts.items():
        bystem[p.stem].append(p)
        headings[p]={heading_text(m.group(1)) for m in re.finditer(r'(?m)^#{1,6}\s+(.+)$',mask(s,True))}
    def resolve(raw: str,source: Path):
        dest=unquote(raw);part,sep,anchor=dest.partition('#')
        if not part:return source,anchor
        if part.startswith('数学/'):
            local=root/part[len('数学/'):]
            candidates=[local] if local.suffix else [local.with_suffix('.md'),local]
        elif '/' in part:
            local=source.parent/part;candidates=[local] if local.suffix else [local.with_suffix('.md'),local]
        else:
            local=source.parent/part;candidates=[local] if local.suffix else [local.with_suffix('.md'),local]
        for p in candidates:
            if p.is_file():return p.resolve(),anchor
        if '/' not in part:
            found=bystem.get(Path(part).stem,[])
            if len(found)==1:return found[0],anchor
            if len(found)>1:return 'ambiguous',anchor
        return None,anchor
    for p,s in texts.items():
        rel=p.relative_to(root).as_posix();clean=mask(s)
        if s.startswith('---\n'):
            m=re.match(r'\A---\n(.*?)\n---(?:\n|$)',s,re.S)
            if m is None:errors.append({'path':rel,'type':'unclosed_yaml'})
            else:
                try:
                    data=yaml.safe_load(m.group(1))
                    if data is not None and not isinstance(data,dict):errors.append({'path':rel,'type':'yaml_not_mapping'})
                except yaml.YAMLError as exc:errors.append({'path':rel,'type':'invalid_yaml','error':str(exc)})
        # Check fences independently to avoid masking an accidental unclosed fence.
        fence=None
        for n,line in enumerate(s.splitlines(),1):
            ln=re.sub(r'^\s*(?:>\s*)+','',line);m=re.match(r'^\s*(`{3,}|~{3,})',ln)
            if m:
                tok=m.group(1)
                if fence and tok[0]==fence[0] and len(tok)>=len(fence):fence=None
                elif not fence:fence=tok
        if fence:errors.append({'path':rel,'type':'unclosed_fence'})
        used=[]
        for m,target,raw in wiki_items(clean):
            links+=1;line=clean.count('\n',0,m.start())+1;used.append(m.span())
            normalized=raw.replace('\\|','|').split('|',1)[0]
            if normalized!=normalized.strip():errors.append({'path':rel,'line':line,'type':'wiki_target_whitespace','target':target})
            if target in external_allowed:
                extseen[(rel,target)]+=1;continue
            resolved,anchor=resolve(target,p)
            if resolved is None:errors.append({'path':rel,'line':line,'type':'missing_wiki_target','target':target});continue
            if resolved=='ambiguous':errors.append({'path':rel,'line':line,'type':'ambiguous_wiki_target','target':target});continue
            if resolved.suffix=='.md':edges[p].add(resolved)
            if anchor:
                anchors+=1
                if anchor.startswith('^'):
                    if re.search(r'\^'+re.escape(anchor[1:])+r'\s*$',texts.get(resolved,''),re.M) is None:errors.append({'path':rel,'line':line,'type':'missing_block_anchor','target':target})
                elif heading_text(anchor) not in headings.get(resolved,set()):errors.append({'path':rel,'line':line,'type':'missing_heading_anchor','target':target})
        remainder=re.sub(r'!?\[\[[^\]\n]+\]\]','',clean)
        if '[[' in remainder or ']]' in remainder:errors.append({'path':rel,'type':'unbalanced_wikilink'})
        # Local standard Markdown links. The vault uses simple unquoted relative paths.
        for m in re.finditer(r'(!?)\[([^\]\n]*)\]\(([^\n]*?)\)',clean):
            mdlinks+=1;image=bool(m.group(1));dest=m.group(3).strip().strip('<>');line=clean.count('\n',0,m.start())+1
            if image:embeds+=1
            if re.match(r'^[A-Za-z][\w+.-]*:',dest):
                if image:remote_images+=1;errors.append({'path':rel,'line':line,'type':'remote_image','target':dest})
                continue
            filename=unquote(dest.split('#',1)[0]);target=(p.parent/filename).resolve() if filename else p
            if not target.is_file():errors.append({'path':rel,'line':line,'type':'missing_markdown_file','target':dest})
            elif image:images.add(target)
            elif target.suffix=='.md':edges[p].add(target)
        # Column counts: escaped pipes are not separators.
        lines=mask(s,False,False).splitlines();i=0
        while i<len(lines)-1:
            if lines[i].lstrip().startswith('|') and re.match(r'^\s*\|?\s*:?-{3,}',lines[i+1]):
                split=lambda row:re.split(r'(?<!\\)\|',row.strip().strip('|'))
                count=len(split(lines[i]));j=i+1
                while j<len(lines) and lines[j].lstrip().startswith('|'):
                    actual=len(split(lines[j]))
                    if actual!=count:errors.append({'path':rel,'line':j+1,'type':'table_columns','expected':count,'actual':actual})
                    j+=1
                i=j
            else:i+=1
        fs,fe=formulas(s,rel);math.extend(fs);errors.extend(fe)
        for f in fs:
            if any(ord(c)<32 and c not in '\n\r' for c in f['tex']):errors.append({'path':rel,'line':f['line'],'type':'math_control_character'})
            if '\u200b' in f['tex']:errors.append({'path':rel,'line':f['line'],'type':'math_zero_width_character'})
    missing_original=[r['path'] for r in base if not (root/r['path']).is_file()]
    missing_external=[{'source':s,'target':t,'missing':n-extseen[(s,t)]} for (s,t),n in expected.items() if extseen[(s,t)]<n]
    for r in missing_original:errors.append({'type':'missing_original_path','path':r})
    for r in missing_external:errors.append({'type':'lost_external_reference',**r})
    # Check actual SVG XML and forbid remote assets/scripts inside it.
    svgs=sorted((root/'assets/figures').glob('*.svg'));svg_ok=0
    for p in svgs:
        try:
            tree=ET.parse(p)
            for el in tree.iter():
                if el.tag.split('}')[-1]=='script':raise ValueError('SVG含脚本')
                for key,value in el.attrib.items():
                    if key.split('}')[-1]=='href' and not value.startswith('#'):raise ValueError('SVG引用非本地定义: '+value)
            svg_ok+=1
        except Exception as exc:errors.append({'path':p.relative_to(root).as_posix(),'type':'invalid_svg','error':str(exc)})
    unreferred=[p.relative_to(root).as_posix() for p in svgs if p not in images]
    if unreferred:warnings.append({'type':'svg_not_embedded','paths':unreferred})
    reachable=set();queue=deque([root/'00-数学-首页.md'])
    while queue:
        p=queue.popleft()
        if p in reachable:continue
        reachable.add(p);queue.extend(edges[p]-reachable)
    orphans=[p.relative_to(root).as_posix() for p in paths if p not in reachable]
    if orphans:warnings.append({'type':'not_reachable_from_home','paths':orphans})
    report={'summary':{'markdown_files':len(paths),'wiki_references':links,'heading_or_block_anchors':anchors,'markdown_links':mdlinks,'image_embeds':embeds,'distinct_embedded_images':len(images),'svg_files':len(svgs),'valid_svg_xml':svg_ok,'remote_images':remote_images,'math_fragments':len(math),'original_paths_total':len(base),'original_paths_preserved':len(base)-len(missing_original),'external_occurrences_original':sum(expected.values()),'external_occurrences_preserved':sum(min(n,extseen[key]) for key,n in expected.items()),'reachable_markdown':len(set(paths)&reachable),'errors':len(errors),'warnings':len(warnings)},'errors':errors,'warnings':warnings,'limits':'只检查语法、存在性、相对路径与基线保留；不验证全部定理、不访问库外目标、不模拟用户的Obsidian插件环境。'}
    return report

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=DEFAULT_ROOT);parser.add_argument('--extract-formulas',action='store_true');args=parser.parse_args();root=args.root.resolve()
    if args.extract_formulas:
        all_formulas=[];all_errors=[]
        for p in sorted(root.rglob('*.md')):
            fs,fe=formulas(p.read_text(encoding='utf-8'),p.relative_to(root).as_posix());all_formulas.extend(fs);all_errors.extend(fe)
        print(json.dumps({'formulas':all_formulas,'delimiter_errors':all_errors},ensure_ascii=False));return 0 if not all_errors else 1
    report=audit(root);path=root/'90-资源/维护/静态审计结果.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['summary'],ensure_ascii=False));return 0 if not report['errors'] else 1

if __name__=='__main__':raise SystemExit(main())
