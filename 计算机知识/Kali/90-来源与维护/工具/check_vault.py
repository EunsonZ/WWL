#!/usr/bin/env python3
"""Local, limited checker for this Kali topic, NOT a complete Obsidian parser.

Reads only ROOT/计算机知识/Kali. Writes only an explicitly requested JSON report.
No network, installations, services, automatic fixes, or secret-value reporting.
Requires PyYAML; a missing dependency is an error, never a silent skipped check.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing dependency: PyYAML. YAML checks were NOT run.") from exc

BASE = "计算机知识/Kali"
HOME = BASE + "/00-导航与方法/00-Kali知识地图.md"
WIKI = re.compile(r"!?\[\[([^\[\]\n]+)\]\]")
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
]

def active_markdown(body: str) -> tuple[str, bool]:
    """Ignore fenced/inline code and comments; return active text and fence state."""
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"%%.*?%%", "", body, flags=re.S)
    lines, fence = [], None
    for line in body.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append("")
        elif fence is None:
            lines.append(re.sub(r"(`+).*?\1", "", line))
        else:
            lines.append("")
    return "\n".join(lines), fence is not None

def split_note(text: str) -> tuple[dict, str]:
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)(.*)\Z", text, re.S)
    if not match:
        raise ValueError("missing/invalid frontmatter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a mapping")
    return metadata, match.group(2)

def target_parts(raw: str, source: str) -> tuple[str, str]:
    raw = raw.replace(r"\|", "|")
    target = raw.split("|", 1)[0]
    dest, sep, anchor = target.partition("#")
    if not dest:
        dest = source
    else:
        path = PurePosixPath(dest)
        if path.is_absolute() or ".." in path.parts or "\\" in dest:
            raise ValueError("unsafe/noncanonical path")
        if not dest.startswith(BASE + "/"):
            raise ValueError("expected an explicit path within this topic")
        if not path.suffix:
            dest += ".md"
    return dest, anchor

def validate(root: Path) -> dict:
    root = root.absolute()
    base = root / BASE
    issues = []
    def issue(rule: str, path: str, detail: str, level: str = "error") -> None:
        issues.append({"level": level, "rule": rule, "path": path, "detail": detail})
    files = sorted(base.rglob("*")) if base.is_dir() else []
    if not base.is_dir(): issue("scope", BASE, "topic directory does not exist")
    regular = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            issue("symlink", rel, "symlink is not allowed in export", "critical")
            continue
        if any(part in {".git", ".obsidian", "__pycache__", "node_modules", ".venv"} for part in p.parts):
            issue("export", rel, "excluded runtime/configuration content", "critical")
        if p.is_file(): regular.append(p)
    names = [p.relative_to(root).as_posix() for p in regular]
    collisions = [name for name, count in Counter(x.casefold() for x in names).items() if count > 1]
    for name in collisions: issue("case_collision", name, "case-insensitive path collision")
    data = {}; all_sources = set(); wiki_count = 0; heading_count = 0; block_count = 0
    for p in regular:
        rel = p.relative_to(root).as_posix()
        blob = p.read_bytes()
        for pattern in SECRET_PATTERNS:
            if pattern.search(blob): issue("secret_pattern", rel, "sensitive-pattern marker found; value withheld", "critical")
        if p.suffix == ".py":
            try: ast.parse(blob.decode("utf-8"), filename=rel)
            except (SyntaxError, UnicodeError) as exc: issue("python_syntax", rel, str(exc))
        if p.suffix != ".md": continue
        try:
            metadata, body = split_note(blob.decode("utf-8"))
        except (ValueError, yaml.YAMLError, UnicodeError) as exc:
            issue("yaml", rel, str(exc)); continue
        for field in ["domain", "type", "content_status"]:
            if not isinstance(metadata.get(field), str): issue("yaml_type", rel, field + " must be text")
        for field in ["sources", "prerequisites", "aliases"]:
            if field in metadata and (not isinstance(metadata[field], list) or any(not isinstance(x, str) for x in metadata[field])):
                issue("yaml_type", rel, field + " must be a list of strings")
        if "stage" in metadata and type(metadata["stage"]) is not int:
            issue("yaml_type", rel, "stage must be an integer, not bool/text")
        content_status = metadata.get("content_status")
        if not isinstance(content_status, str) or content_status not in {"usable", "draft", "deprecated"}:
            issue("status", rel, "invalid content_status")
        if "evidence_status" in metadata:
            evidence_status = metadata["evidence_status"]
            if not isinstance(evidence_status, str) or evidence_status not in {"partial", "unreviewed", "reviewed"}:
                issue("status", rel, "invalid evidence_status")
        active, unclosed = active_markdown(body)
        if unclosed: issue("fence", rel, "unclosed fenced code block")
        if re.search(r"\{\{[^{}]+\}\}", active): issue("placeholder", rel, "unexpanded build link")
        if not re.search(r"^# .+", active, re.M): issue("title", rel, "missing H1 title")
        headings = set(re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", active, re.M))
        blocks = set(re.findall(r"(?:^|\s)\^([A-Za-z0-9-]+)\s*$", active, re.M))
        footnotes = set(re.findall(r"^\[\^([^\]]+)\]:", active, re.M))
        used = set(re.findall(r"\[\^([^\]]+)\](?!:)", active))
        for missing in used - footnotes: issue("footnote", rel, "missing definition: " + missing)
        links = WIKI.findall(active)
        prerequisites = metadata.get("prerequisites", [])
        if isinstance(prerequisites, list):
            links += [s for x in prerequisites if isinstance(x,str) for s in WIKI.findall(x)]
        for line in active.splitlines():
            if line.lstrip().startswith("|"):
                for target in WIKI.findall(line):
                    if re.search(r"(?<!\\)\|", target):
                        issue("table_alias", rel, "unescaped wikilink alias separator inside Markdown table")
        md_links = re.findall(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)", active)
        for link in md_links:
            if urlsplit(link).scheme in {"http", "https", "mailto"}: continue
            local=unquote(link.split("#",1)[0])
            if local and not (p.parent/local).is_file(): issue("markdown_link", rel, "missing local Markdown-link target")
        if isinstance(metadata.get("sources"), list): all_sources.update(x for x in metadata["sources"] if isinstance(x,str))
        data[rel] = {"headings":headings,"blocks":blocks,"links":links,"metadata":metadata}
        wiki_count += len(links); heading_count += len(headings); block_count += len(blocks)
    if not data: issue("empty", BASE, "zero parsed Markdown notes is never a pass")
    graph={name:set() for name in data}; pregraph={name:set() for name in data}
    for name, info in data.items():
        for target in info["links"]:
            try: dest, anchor = target_parts(target,name)
            except ValueError as exc: issue("wikilink",name,str(exc)); continue
            if not (root/dest).is_file(): issue("wikilink",name,"missing explicit target: "+dest);continue
            if (root/dest).is_symlink(): issue("wikilink",name,"target must not be a symlink");continue
            if dest in data: graph[name].add(dest)
            if anchor:
                lookup=data.get(dest,{})
                if anchor.startswith("^"):
                    if anchor[1:] not in lookup.get("blocks",set()): issue("block",name,"missing block: "+dest+"#"+anchor)
                elif anchor not in lookup.get("headings",set()): issue("heading",name,"missing heading: "+dest+"#"+anchor)
        for ref in info["metadata"].get("prerequisites",[]) if isinstance(info["metadata"].get("prerequisites",[]),list) else []:
            for raw in WIKI.findall(ref):
                try: dest,_=target_parts(raw,name)
                except ValueError: continue
                if dest in data: pregraph[name].add(dest)
    reachable=set(); stack=[HOME]
    while stack:
        item=stack.pop()
        if item in reachable: continue
        reachable.add(item); stack.extend(graph.get(item,()))
    for name in set(data)-reachable: issue("navigation",name,"not reachable from the home note")
    visiting,done=set(),set()
    def visit(item):
        if item in visiting: issue("prerequisite_cycle",item,"prerequisite cycle");return
        if item in done:return
        visiting.add(item)
        for child in pregraph.get(item,()): visit(child)
        visiting.remove(item);done.add(item)
    for name in data: visit(name)
    canvases=0; canvas_nodes=0; canvas_edges=0
    for p in regular:
        if p.suffix != ".canvas":continue
        canvases+=1; rel=p.relative_to(root).as_posix()
        try:
            obj=json.loads(p.read_text());nodes=obj["nodes"];edges=obj["edges"]
            if not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError("nodes/edges must be lists")
            ids=[n["id"] for n in nodes]
            if len(ids)!=len(set(ids)):raise ValueError("duplicate node id")
            eids=[e["id"] for e in edges]
            if len(eids)!=len(set(eids)):raise ValueError("duplicate edge id")
            for n in nodes:
                for prop in ["x","y","width","height"]:
                    if not isinstance(n.get(prop),(int,float)):raise ValueError("node geometry must be numeric")
                if n.get("type")=="file":
                    dest=n["file"]
                    if not dest.startswith(BASE+"/") or ".." in PurePosixPath(dest).parts or not (root/dest).is_file():
                        raise ValueError("missing/out-of-scope file node: "+dest)
            for e in edges:
                if e["fromNode"] not in ids or e["toNode"] not in ids:raise ValueError("edge references missing node")
            canvas_nodes+=len(nodes);canvas_edges+=len(edges)
        except (ValueError,KeyError,TypeError) as exc: issue("canvas",rel,str(exc))
    return {"checker_version":"1.0","scope":BASE,"status":"passed" if not issues else "failed",
            "counts":{"markdown":len(data),"wikilinks_including_prerequisites":wiki_count,
                      "headings":heading_count,"block_ids":block_count,"reachable_notes":len(set(data)&reachable),
                      "unique_frontmatter_source_urls":len(all_sources),"canvas":canvases,
                      "canvas_nodes":canvas_nodes,"canvas_edges":canvas_edges,
                      "python_sources":sum(p.suffix=='.py' for p in regular),"files_at_check":len(regular)},
            "issues":issues,"not_run":["Obsidian UI/rendering","Kali tool execution","external URL availability sweep"],
            "limitations":["Limited Markdown dialect; not a full Obsidian parser",
                            "Specific secret patterns only, not a comprehensive secret detector",
                            "Reads this topic only, not the rest of an existing Vault",
                            "Trusted local filesystem assumed; not a race-resistant hostile-input sandbox"]}

def self_test() -> int:
    class CheckerTests(unittest.TestCase):
        def setUp(self):
            self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
            self.target=BASE+"/target.md"
            self.write(self.target,"## Target heading\n\nA target paragraph.\n^target-block\n")
            self.write(HOME,"[["+self.target[:-3]+"|Target]]\n")
        def tearDown(self):self.temp.cleanup()
        def write(self,name,body):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('---\ndomain: 计算机知识\ntype: course\ncontent_status: usable\nevidence_status: partial\n---\n# Test\n\n'+body)
        def rules(self):return {x['rule'] for x in validate(self.root)['issues']}
        def test_valid(self):self.assertEqual(self.rules(),set())
        def test_wrong_path_not_basename_fallback(self):
            self.write(HOME,"[["+BASE+"/wrong/target|bad]]\n");self.assertIn('wikilink',self.rules())
        def test_heading_valid(self):
            self.write(HOME,"[["+self.target[:-3]+"#Target heading|ok]]\n");self.assertEqual(self.rules(),set())
        def test_heading_missing(self):
            self.write(HOME,"[["+self.target[:-3]+"#missing|bad]]\n");self.assertIn('heading',self.rules())
        def test_block_valid(self):
            self.write(HOME,"[["+self.target[:-3]+"#^target-block|ok]]\n");self.assertEqual(self.rules(),set())
        def test_block_missing(self):
            self.write(HOME,"[["+self.target[:-3]+"#^missing|bad]]\n");self.assertIn('block',self.rules())
        def test_examples_ignored(self):
            self.write(HOME,"[["+self.target[:-3]+"|Target]]\n```md\n[[missing]]\n```\n`[[missing]]`\n<!-- [[missing]] -->\n")
            self.assertEqual(self.rules(),set())
        def test_unclosed_fence(self):
            self.write(self.target,"```bash\necho hi\n");self.assertIn('fence',self.rules())
        def test_empty_vault_not_pass(self):
            with tempfile.TemporaryDirectory() as empty:self.assertEqual(validate(Path(empty))['status'],'failed')
        def test_yaml_wrong_type(self):
            p=self.root/self.target;t=p.read_text();p.write_text(t.replace('type: course','type: course\nsources: not-a-list'))
            self.assertIn('yaml_type',self.rules())
        def test_invalid_status_values_reported(self):
            target = self.root / self.target
            original = target.read_text()
            for field, valid in [("content_status", "usable"), ("evidence_status", "partial")]:
                for literal in ["[]", "{}", "null", "true", "1", "unknown"]:
                    with self.subTest(field=field, literal=literal):
                        target.write_text(original.replace(field + ": " + valid, field + ": " + literal))
                        report = validate(self.root)
                        self.assertEqual(report["status"], "failed")
                        json.dumps(report)
                        matching = {x["rule"] for x in report["issues"]
                                    if x["path"] == self.target and field in x["detail"]}
                        self.assertIn("status", matching)
                        if field == "content_status" and literal != "unknown":
                            self.assertIn("yaml_type", matching)
                        if field == "evidence_status":
                            self.assertNotIn("yaml_type", matching)
        def test_status_presence_requirements(self):
            target = self.root / self.target
            original = target.read_text()
            target.write_text(original.replace("content_status: usable\n", ""))
            self.assertIn("status", self.rules())
            target.write_text(original.replace("evidence_status: partial\n", ""))
            self.assertEqual(self.rules(), set())
        def test_table_alias_escape(self):
            self.write(HOME,"| A | B |\n| --- | --- |\n| [["+self.target[:-3]+r"\|OK]] | text |"+"\n")
            self.assertEqual(self.rules(),set())
        def test_table_alias_unescaped(self):
            self.write(HOME,"| [["+self.target[:-3]+"|bad]] |\n");self.assertIn('table_alias',self.rules())
        def test_secret_pattern_values_not_reported(self):
            token='AK'+'IA'+'A'*16
            self.write(self.target,token+'\n')
            report=validate(self.root)
            self.assertIn('secret_pattern',{x['rule'] for x in report['issues']})
            self.assertNotIn(token,json.dumps(report))
        def test_broken_canvas_edge(self):
            p=self.root/BASE/'bad.canvas';p.write_text(json.dumps({'nodes':[],'edges':[{'id':'e','fromNode':'x','toNode':'y'}]}))
            self.assertIn('canvas',self.rules())
        def test_missing_footnote(self):
            self.write(self.target,'Claim.[^missing]\n');self.assertIn('footnote',self.rules())
        def test_prerequisite_cycle(self):
            for name,other in [(HOME,self.target),(self.target,HOME)]:
                p=self.root/name;t=p.read_text();p.write_text(t.replace('type: course','type: course\nprerequisites:\n  - "[['+other[:-3]+'|pre]]"'))
            self.assertIn('prerequisite_cycle',self.rules())
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CheckerTests))
    return 0 if result.wasSuccessful() else 1

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path,nargs='?')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:return self_test()
    if args.root is None:parser.error('root is required unless --self-test is used')
    report=validate(args.root)
    encoded=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.report:args.report.write_text(encoded,encoding='utf-8')
    print(encoded,end='')
    return 0 if report['status']=='passed' else 1
if __name__ == '__main__':
    raise SystemExit(main())
