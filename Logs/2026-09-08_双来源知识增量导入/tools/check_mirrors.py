from pathlib import Path
import re, json, sys, hashlib

def without_inline_code(line):
    """Blank backtick code spans without hiding real HTML comments."""
    out=list(line); index=0
    while index < len(line):
        if line[index] != '`':
            index+=1;continue
        width=1
        while index+width < len(line) and line[index+width] == '`':width+=1
        marker='`'*width; end=line.find(marker,index+width)
        if end < 0:
            index+=width;continue
        stop=end+width
        out[index:stop]=' '*(stop-index)
        index=stop
    return ''.join(out)

def active_markers(text):
    fence=None; offset=0
    for line in text.splitlines(keepends=True):
        mark=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
        if mark:
            token=mark[1]
            if fence is None:fence=token
            elif token[0]==fence[0] and len(token)>=len(fence) and not line[mark.end():].strip():fence=None
        elif fence is None:
            active=without_inline_code(line)
            for m in re.finditer(r'<!--\s*code-sync:\s*(.*?)\s*-->',active):
                yield offset+m.start(),offset+m.end(),m[1]
        offset+=len(line)

def check(root):
    result={'checked':0,'missing':[],'mismatched':[],'unparsed':[]}
    for p in sorted(root.rglob('*.md')):
        if any(s.startswith('.') for s in p.relative_to(root).parts):continue
        text=p.read_text()
        for start,end,target in active_markers(text):
            path=target.strip(); tail=text[end:]
            block=re.match(r'\s*(`{3,}|~{3,})[^\n]*\n(.*?)\n\1\s*(?:\n|$)',tail,re.S)
            item={'path':str(p.relative_to(root)),'line':text[:start].count('\n')+1,'source':path}
            if not block:
                result['unparsed'].append(item);continue
            src=(p.parent/path) if path.startswith('.') else (root/path)
            if not src.is_file() and not path.startswith('.'):
                src=p.parent/path
            if not src.is_file():result['missing'].append(item);continue
            result['checked']+=1
            expected=src.read_text().rstrip('\n');actual=block[2].rstrip('\n')
            if actual!=expected:
                result['mismatched'].append(item)
    return result
if __name__=='__main__':
    out=check(Path(sys.argv[1]).resolve());print(json.dumps(out,ensure_ascii=False,indent=2))
    sys.exit(bool(out['missing'] or out['mismatched'] or out['unparsed']))
