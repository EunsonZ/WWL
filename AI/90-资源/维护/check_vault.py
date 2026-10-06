"""Obsidian AI 子目录静态检查。仅标准库；不请求网络，不修改笔记。"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
from urllib.parse import unquote


def prose(text: str) -> tuple[str, bool]:
    lines = []; fence = None
    for line in text.splitlines():
        m = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence):
                fence = None
            lines.append(''); continue
        lines.append('' if fence else re.sub(r'(`+).*?\1', '', line))
    return '\n'.join(lines), fence is not None


def formulas(text: str, source: str) -> tuple[list[dict], list[dict]]:
    result = []; errors = []; pattern = re.compile(r'(?<!\\)(\$\$|\$)')
    cursor = 0
    while (match := pattern.search(text, cursor)):
        delimiter = match[0]; start = match.end()
        close = re.compile(r'(?<!\\)'+re.escape(delimiter)).search(text, start)
        if close is None:
            errors.append({'source': source, 'line': text[:match.start()].count('\n')+1,
                           'reason': 'unmatched '+delimiter}); break
        formula = text[start:close.start()]
        result.append({'source': source, 'line': text[:match.start()].count('\n')+1,
                       'display': len(delimiter) == 2, 'tex': formula})
        cursor = close.end()
    return result, errors


def check(root: Path) -> tuple[dict, list[dict]]:
    root = root.resolve(); files = [p for p in root.rglob('*') if p.is_file()]
    names = defaultdict(list)
    for p in files:
        names[p.stem].append(p)
    notes = sorted(root.rglob('*.md'))
    result = {key: [] for key in ['missing_internal_links', 'ambiguous_links', 'external_vault_links',
              'missing_images', 'remote_image_embeds', 'bad_fences', 'math_delimiters',
              'unescaped_table_aliases', 'missing_heading_anchors', 'yaml_errors', 'missing_markdown_files']}
    formula_list = []; wiki_count = 0; image_count = 0
    def resolve(target: str, source: Path) -> list[Path]:
        target = unquote(target)
        candidates = set()
        for base in [root.parent, root, source.parent]:
            p = base/target
            for q in [p, Path(str(p)+'.md')]:
                if q.is_file(): candidates.add(q.resolve())
        if not candidates and '/' not in target:
            candidates.update(names.get(target.removesuffix('.md'), []))
        return sorted(candidates)
    for p in notes:
        source = str(p.relative_to(root)); text = p.read_text(encoding='utf-8')
        clean, bad_fence = prose(text)
        if bad_fence: result['bad_fences'].append(source)
        f, e = formulas(clean, source); formula_list.extend(f); result['math_delimiters'].extend(e)
        if text.startswith('---\n'):
            try:
                import yaml  # Optional: without PyYAML, only the YAML delimiter is checked.
                yaml.safe_load(text.split('---', 2)[1])
            except ImportError:
                pass
            except Exception as error:
                result['yaml_errors'].append({'source': source, 'error': str(error)})
        for m in re.finditer(r'(!?)\[\[([^\]\n]+)\]\]', clean):
            wiki_count += 1
            raw = m[2].replace('\\|', '|').split('|', 1)[0].strip()
            target, _, heading = raw.partition('#')
            found = resolve(target, p) if target else [p]
            if not found:
                bucket = 'missing_internal_links' if target.startswith('AI/') or '/' not in target else 'external_vault_links'
                result[bucket].append({'source': source, 'target': target})
            elif len(found) > 1:
                result['ambiguous_links'].append({'source': source, 'target': target})
            elif heading and not heading.startswith('^'):
                headings = re.findall(r'^#{1,6}\s+(.+?)\s*#*\s*$', found[0].read_text(encoding='utf-8'), re.M)
                if unquote(heading) not in headings:
                    result['missing_heading_anchors'].append({'source': source, 'target': raw})
            if m[1]:
                image_count += 1
                if not found: result['missing_images'].append({'source': source, 'target': target})
        for m in re.finditer(r'(!?)\[([^\]\n]*)\]\(([^)\n]+)\)', clean):
            url = m[3].strip().strip('<>')
            url = re.sub(r'\s+"[^\"]*"$', '', url)
            if m[1]:
                image_count += 1
                if re.match(r'(?:https?:)?//', url):
                    result['remote_image_embeds'].append({'source': source, 'target': url}); continue
                if not resolve(url.split('#')[0], p):
                    result['missing_images'].append({'source': source, 'target': url})
            elif not re.match(r'[a-zA-Z][\w+.-]*:|#', url):
                target = url.split('#')[0]
                if target and not resolve(target, p):
                    result['missing_markdown_files'].append({'source': source, 'target': target})
        for number, line in enumerate(clean.splitlines(), 1):
            if line.lstrip().startswith('|'):
                for m in re.finditer(r'\[\[[^\]]+\]\]', line):
                    if re.search(r'(?<!\\)\|', m[0]):
                        result['unescaped_table_aliases'].append({'source': source, 'line': number})
    result['summary'] = {'markdown_files': len(notes), 'markdown_characters': sum(len(p.read_text(encoding='utf-8')) for p in notes),
             'wiki_links': wiki_count, 'image_embeds': image_count,
             'png_figures': len(list((root/'90-资源/图示').rglob('*.png'))),
             'svg_figures': len(list((root/'90-资源/图示').rglob('*.svg'))),
             'display_formulas': sum(f['display'] for f in formula_list),
             'inline_formulas': sum(not f['display'] for f in formula_list),
             'external_unique_targets': len(set(x['target'] for x in result['external_vault_links']))}
    return result, formula_list


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, help='写 JSON 报告；不指定时只打印')
    parser.add_argument('--formulas', type=Path, help='导出 MathJax 输入 JSON')
    args = parser.parse_args(); report, extracted = check(args.root)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output: args.output.write_text(payload, encoding='utf-8')
    else: print(payload)
    if args.formulas: args.formulas.write_text(json.dumps(extracted, ensure_ascii=False), encoding='utf-8')
    critical = ['missing_internal_links', 'ambiguous_links', 'missing_images', 'remote_image_embeds',
                'bad_fences', 'math_delimiters', 'unescaped_table_aliases', 'missing_heading_anchors',
                'yaml_errors', 'missing_markdown_files']
    raise SystemExit(1 if any(report[key] for key in critical) else 0)

if __name__ == '__main__':
    main()
