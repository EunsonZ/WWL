#!/usr/bin/env python3
"""Audit an Obsidian folder without treating missing external-vault targets as deleted.
Uses the standard library only. It does not execute any notebook code.
Usage: python audit_vault.py ROOT [--original ORIGINAL_ROOT] [--output-dir DIRECTORY] [--repair-table-aliases]
"""
from __future__ import annotations
import argparse, collections, hashlib, json, posixpath, re, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

FENCE = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
WIKI = re.compile(r'(!?)\[\[([^\]\n]+)\]\]')
INLINE = re.compile(r'(`+)(.+?)\1')

def without_code(text: str) -> tuple[str, list[int]]:
    lines = text.splitlines(keepends=True); out=[]; fence=None; start=0
    for n,line in enumerate(lines, 1):
        m=FENCE.match(line)
        if m:
            token=m.group(1)
            if fence is None: fence=token; start=n
            elif token[0]==fence[0] and len(token)>=len(fence): fence=None
            out.append('\n' if line.endswith('\n') else ''); continue
        if fence:
            out.append('\n' if line.endswith('\n') else ''); continue
        out.append(INLINE.sub(lambda m:' ' * len(m.group(0)),line))
    return ''.join(out), [start] if fence else []

def wiki_parts(body: str) -> tuple[str,str]:
    target = re.split(r'\\?\|', body, maxsplit=1)[0].strip()
    file, _, anchor = target.partition('#')
    return unquote(file).replace('\\','/'), unquote(anchor)

def repair_aliases(p: Path) -> int:
    text=p.read_text(encoding='utf-8'); fence=None; count=0; output=[]
    for line in text.splitlines(keepends=True):
        m=FENCE.match(line)
        if m:
            t=m.group(1)
            if fence is None: fence=t
            elif t[0]==fence[0] and len(t)>=len(fence): fence=None
        if not fence and line.lstrip().startswith('|'):
            def repair(m):
                nonlocal count
                body,n=re.subn(r'(?<!\\)\|',r'\\|',m.group(2))
                count+=n
                return m.group(1)+'[['+body+']]'
            line=WIKI.sub(repair,line)
        output.append(line)
    if count: p.write_text(''.join(output),encoding='utf-8')
    return count

def norm(path: str) -> str:
    # Never strip leading dots: .hidden and ../outside are meaningful paths.
    return posixpath.normpath(path).removeprefix('./')

def audit(root: Path, original: Path | None = None) -> dict:
    files={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
    markdown={k:v for k,v in files.items() if k.endswith('.md')}
    bodies={k:without_code(p.read_text('utf-8')) for k,p in markdown.items()}
    headings={k:set(re.findall(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$',p.read_text('utf-8'),re.M)) for k,p in markdown.items()}
    blocks={k:set(re.findall(r'\^([A-Za-z0-9-]+)\s*$',t,re.M)) for k,(t,_) in bodies.items()}
    stems=collections.defaultdict(list)
    for k in files:
        stems[Path(k).name].append(k)
        if k.endswith('.md'): stems[Path(k).stem].append(k)
    def resolve(target: str, source: str, wiki: bool = True):
        if not target: return [source]
        parent=posixpath.dirname(source)
        for prefix in [parent,'']:
            name=norm(posixpath.join(prefix,target))
            candidates=[name,name+'.md'] if not Path(name).suffix or Path(name).suffix.lower() not in {'.md','.svg','.png','.jpg','.jpeg','.pdf','.py','.cpp','.c','.rs','.ts','.sh','.txt','.dot','.json','.cu','.hpp'} else [name]
            # Obsidian filenames can contain periods, so also try .md unconditionally.
            if name+'.md' not in candidates:candidates.append(name+'.md')
            hits=[c for c in candidates if c in files]
            if hits:return sorted(set(hits))
        if wiki:
            if '/' not in target: return sorted(set(stems.get(target,[])))
            candidates=[k for k in files if k.endswith('/'+target) or k.endswith('/'+target+'.md')]
            return sorted(set(candidates))
        return []
    unresolved=[]; ambiguous=[]; anchorissues=[]; images=[]; remotemedia=[]; localmd=[]; fences=[]; odd=[]; wcount=0
    original_links=set()
    original_link_counts=collections.Counter()
    if original:
        for p in original.rglob('*.md'):
            text,_=without_code(p.read_text('utf-8'))
            source=p.relative_to(original).as_posix()
            entries=[(source,*wiki_parts(m.group(2))) for m in WIKI.finditer(text)]
            original_links.update(entries)
            original_link_counts.update(entries)
    for source,(text,unclosed) in bodies.items():
        fences.extend({'source':source,'line':n} for n in unclosed)
        raw=markdown[source].read_text('utf-8')
        if re.search(r'@@[A-Z][A-Z0-9_]*@@|PLACEHOLDER_DIAGRAM|\[\[@',raw): odd.append({'source':source,'issue':'unexpanded placeholder'})
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',raw):odd.append({'source':source,'issue':'control character'})
        for m in WIKI.finditer(text):
            wcount+=1; target,anchor=wiki_parts(m.group(2)); hits=resolve(target,source)
            entry={'source':source,'line':text.count('\n',0,m.start())+1,'target':target,'anchor':anchor,'in_original':(source,target,anchor) in original_links}
            if not hits: unresolved.append(entry)
            elif len(hits)>1: ambiguous.append({**entry,'candidates':hits})
            elif anchor and hits[0].endswith('.md'):
                h=anchor.split('#')[-1]
                if h.startswith('^'):
                    valid=h[1:] in blocks.get(hits[0],set())
                else:
                    hs=headings.get(hits[0],set())
                    valid=h in hs or any(re.sub(r'[*`_]','',x)==h for x in hs)
                if not valid:anchorissues.append({**entry,'resolved':hits[0]})
            if m.group(1):images.append({**entry,'resolved':hits})
        # Simple inline Markdown file links; complex parenthesized destinations are reviewed separately.
        for m in re.finditer(r'(!?)\[[^\]\n]*\]\(([^\s\n]+?)(?:\s+[\"\'][^\n]*[\"\'])?\)',text):
            dest=m.group(2).strip('<>'); parts=urlsplit(dest)
            if parts.scheme in {'http','https'}:
                if m.group(1): remotemedia.append({'source':source,'target':dest})
                continue
            if parts.scheme or dest.startswith('#'):continue
            target=unquote(parts.path);hits=resolve(target,source,False)
            localmd.append({'source':source,'target':dest,'resolved':hits,'image':bool(m.group(1))})
    svg=[]
    for k,p in files.items():
        if not k.endswith('.svg'):continue
        try:
            tree=ET.parse(p)
            external=[v for el in tree.iter() for a,v in el.attrib.items() if a.endswith('href') and v.startswith(('http:','https:','//'))]
            svg.append({'path':k,'xml_valid':True,'external_dependencies':external})
        except ET.ParseError as e:svg.append({'path':k,'xml_valid':False,'error':str(e)})
    originals={p.relative_to(original).as_posix():p for p in original.rglob('*') if p.is_file()} if original else {}
    missing=sorted(set(originals)-set(files)); changed=[]
    for k,p in originals.items():
        if k in files and hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(files[k].read_bytes()).digest():changed.append(k)
    current_links=set(); current_link_counts=collections.Counter()
    for source,(text,_) in bodies.items():
        entries=[(source,*wiki_parts(m.group(2))) for m in WIKI.finditer(text)]
        current_links.update(entries); current_link_counts.update(entries)
    lost_original_links=sorted(original_links-current_links)
    lost_occurrences=[{'source':k[0],'target':k[1],'anchor':k[2],'removed_count':v} for k,v in (original_link_counts-current_link_counts).items()]
    return {'counts':{'files':len(files),'markdown':len(markdown),'original_files':len(originals),'original_markdown':sum(k.endswith('.md') for k in originals),'original_paths_missing':len(missing),'original_files_changed':len(changed),'wiki_occurrences':wcount,'unresolved_wiki_occurrences':len(unresolved),'unresolved_wiki_unique_targets':len(set(x['target'] for x in unresolved)),'ambiguous_wiki_occurrences':len(ambiguous),'anchor_review_occurrences':len(anchorissues),'embedded_local_items':len(images),'external_image_links':len(remotemedia),'svg_files':len(svg),'unclosed_fences':len(fences),'missing_original_link_entries':len(lost_original_links),'missing_original_link_occurrences':sum(x['removed_count'] for x in lost_occurrences)},'unresolved_wiki':unresolved,'ambiguous_wiki':ambiguous,'anchor_review':anchorissues,'markdown_local_links':localmd,'missing_local_markdown_links':[x for x in localmd if not x['resolved']],'embedded_items':images,'remote_images':remotemedia,'svg':svg,'unclosed_fences':fences,'other_issues':odd,'original_missing_paths':missing,'original_changed_paths':changed,'original_link_entries_removed':lost_original_links,'original_link_occurrences_removed':lost_occurrences}

def vault_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / 'AGENTS.md').is_file():
            return candidate
    raise RuntimeError(f'Cannot locate vault root from {start}')

def default_output_dir() -> Path:
    stamp=datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    return vault_root(Path(__file__).resolve().parent)/'Logs/运行/static-audit'/stamp/'计算机知识'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--original',type=Path);ap.add_argument('--repair-table-aliases',action='store_true');ap.add_argument('--output',type=Path);ap.add_argument('--output-dir',type=Path)
    args=ap.parse_args(); root=args.root.resolve()
    if not root.is_dir():ap.error('root must be a directory')
    repairs={}
    if args.repair_table_aliases:
        for p in root.rglob('*.md'):
            n=repair_aliases(p)
            if n:repairs[p.relative_to(root).as_posix()]=n
    result=audit(root,args.original)
    result['table_alias_repairs']=repairs
    default_dir=default_output_dir()
    output=args.output or (args.output_dir or default_dir)/'static_audit.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['counts'],ensure_ascii=False,indent=2));print('table_alias_repairs',sum(repairs.values()))
    print('new_unresolved',len([x for x in result['unresolved_wiki'] if not x['in_original']]))
    print('local_md_missing',len(result['missing_local_markdown_links']))
if __name__=='__main__':main()
