"""Read-only static vault checks. No execution, installs, repairs or baseline exemptions."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime
import importlib
import json
import math
import os
from pathlib import Path
import re

import check_mirrors
from config_checks import check_codex_config, tomllib
from links import audit, check_reference, diagnostic, inventory, references, split_frontmatter


def load_yaml():
    try:
        return importlib.import_module("yaml")
    except ImportError:
        return None


def strict_json(text):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError("nonfinite JSON number")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON number")
        return number
    return json.loads(text, object_pairs_hook=object_pairs,
                      parse_constant=reject_constant, parse_float=finite_float)


def yaml_check(notes, yaml):
    issues, metadata, aliases = [], {}, {}
    if yaml is None:
        for path, text in notes.items():
            if split_frontmatter(text)[2] < 0:
                issues.append(diagnostic("frontmatter_unclosed", path, 1))
        return issues, metadata, None
    # SafeLoader plus duplicate mapping detection; exception text is never
    # returned because YAML errors may quote a private property value.
    class UniqueLoader(yaml.SafeLoader):
        pass
    def construct_mapping(loader, node, deep=False):
        seen = set()
        for key, _ in node.value:
            name = loader.construct_object(key, deep=deep)
            if name in seen:
                raise ValueError("duplicate YAML property")
            seen.add(name)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    scalar_fields = {"domain", "type", "course_role", "content_status", "evidence_status", "subject_note"}
    list_fields = {"aliases", "sources", "prerequisites"}
    enums = {"content_status": {"draft", "usable", "deprecated"},
             "evidence_status": {"unreviewed", "partial", "reviewed"}}
    property_types = defaultdict(lambda: defaultdict(list))
    for path, text in notes.items():
        front, _, closing = split_frontmatter(text)
        if front is None:
            continue
        if closing < 0:
            issues.append(diagnostic("frontmatter_unclosed", path, 1))
            continue
        try:
            data = yaml.load(front, Loader=UniqueLoader)
        except Exception:
            issues.append(diagnostic("yaml_invalid", path, 1))
            continue
        if data is None:
            data = {}
        if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
            issues.append(diagnostic("properties_not_mapping", path, 1))
            continue
        metadata[path] = data
        aliases[path] = data.get("aliases", []) if isinstance(data.get("aliases", []), list) else []
        aliases[path] = [a for a in aliases[path] if isinstance(a, str)]
        for key, value in data.items():
            if value is None:
                continue  # Missing has meaning; never fill missing values.
            if isinstance(value, bool):
                kind = "checkbox"
            elif isinstance(value, (int, float)):
                kind = "number"
            elif isinstance(value, list):
                kind = "list"
            elif isinstance(value, datetime.datetime):
                kind = "datetime"
            elif isinstance(value, datetime.date):
                kind = "date"
            elif isinstance(value, str):
                kind = "text"
            else:
                kind = "mapping"
            property_types[key][kind].append(path)
            wrong = ((key in scalar_fields and not isinstance(value, str)) or
                     (key in list_fields and (not isinstance(value, list) or any(not isinstance(v, str) for v in value))) or
                     (key == "stage" and (type(value) is not int or value < 0)))
            if wrong:
                issues.append(diagnostic("property_type", path, 1, field=key))
            if key in enums and (not isinstance(value, str) or value not in enums[key]):
                issues.append(diagnostic("property_value", path, 1, field=key))
        for field in ("prerequisites", "subject_note"):
            values = data.get(field)
            if values is None:
                continue
            if field == "subject_note":
                values = [values]
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str) and not list(references(value)):
                        issues.append(diagnostic("property_link_required", path, 1, field=field))
    for field, types in property_types.items():
        if len(types) > 1:
            # Paths/types only; never print original metadata values.
            issues.append(diagnostic("property_type_conflict", sorted(next(iter(types.values())))[0],
                                     field=field, uses=dict(types)))
    return issues, metadata, aliases


def config_check(root, paths, index, notes, yaml, metadata=None):
    issues, checked = [], 0
    allowlist = {"app", "appearance", "graph", "types", "templates", "core-plugins", "community-plugins"}
    targets = [root / ".obsidian" / (name + ".json") for name in sorted(allowlist)]
    targets += [root / p for p in paths if p.startswith("config/") and p.endswith(".json")]
    parsed = {}
    for path in targets:
        if not path.exists():
            continue
        rel = path.relative_to(root).as_posix()
        inside = path.relative_to(root).parts
        if any(root.joinpath(*inside[:end]).is_symlink() for end in range(1, len(inside) + 1)):
            issues.append(diagnostic("config_symlink_not_read", rel))
            continue
        checked += 1
        try:
            data = strict_json(path.read_text(encoding="utf-8"))
            if path.stem in {"app", "appearance", "graph", "types", "templates"} and path.parent == root / ".obsidian" and not isinstance(data, dict):
                raise ValueError("configuration object required")
            parsed[rel] = data
        except (ValueError, OSError, UnicodeError):
            issues.append(diagnostic("config_json_invalid", rel))
    declarations = parsed.get(".obsidian/types.json", {}).get("types", {}) if isinstance(parsed.get(".obsidian/types.json", {}), dict) else None
    if not isinstance(declarations, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in declarations.items()):
        issues.append(diagnostic("property_declarations_invalid", ".obsidian/types.json"))
    else:
        supported_types = {"text", "number", "checkbox", "multitext", "aliases", "tags", "date", "datetime"}
        for field, declared in declarations.items():
            if declared not in supported_types:
                issues.append(diagnostic("property_declaration_unknown_type", ".obsidian/types.json", field=field))
            if field == "stage" and declared != "number":
                issues.append(diagnostic("property_declaration_contract", ".obsidian/types.json", field=field))
    if isinstance(declarations, dict) and metadata:
        checks = {"text": lambda v: isinstance(v, str),
                  "number": lambda v: type(v) in (int, float),
                  "checkbox": lambda v: type(v) is bool,
                  "multitext": lambda v: isinstance(v, list),
                  "aliases": lambda v: isinstance(v, list),
                  "tags": lambda v: isinstance(v, (list, str)),
                  "date": lambda v: isinstance(v, (str, datetime.date)),
                  "datetime": lambda v: isinstance(v, (str, datetime.datetime))}
        for path, data in metadata.items():
            for field, value in data.items():
                declared = declarations.get(field)
                if value is not None and declared in checks and not checks[declared](value):
                    issues.append(diagnostic("declared_property_type", path, 1, field=field))
    enabled = parsed.get(".obsidian/community-plugins.json", [])
    if not isinstance(enabled, list) or any(not isinstance(x, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", x) for x in enabled):
        issues.append(diagnostic("plugin_list_invalid", ".obsidian/community-plugins.json"))
    else:
        for plugin in enabled:
            # No plugin data.json, JS, styles or secret values are read.
            for filename in ("manifest.json", "main.js"):
                path = root / ".obsidian" / "plugins" / plugin / filename
                rel = path.relative_to(root).as_posix()
                if not path.is_file() or path.is_symlink() or path.parent.is_symlink():
                    issues.append(diagnostic("enabled_plugin_file_missing_or_symlink", rel))
    for rel in paths:
        path = root / rel
        if rel.endswith(".canvas"):
            checked += 1
            try:
                data = strict_json(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or not isinstance(data.get("nodes", []), list):
                    raise ValueError()
                for node in data.get("nodes", []):
                    if isinstance(node, dict) and node.get("type") == "file":
                        if not isinstance(node.get("file"), str):
                            raise ValueError()
                        found, _ = check_reference(index, notes, rel, None, node["file"], "wiki")
                        issues.extend(found)
            except (ValueError, OSError, UnicodeError):
                issues.append(diagnostic("canvas_invalid", rel))
        elif rel.endswith(".base") and yaml is not None:
            checked += 1
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError()
            except Exception:
                issues.append(diagnostic("base_yaml_invalid", rel))
    return issues, checked


def check(root, require_yaml=False):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("root must be an existing directory")
    paths, issues = inventory(root)
    link_report, notes, index = audit(root, paths)
    yaml = load_yaml()
    yaml_issues, metadata, aliases = yaml_check(notes, yaml)
    if yaml is not None:
        link_report, _, index = audit(root, paths, aliases)
    else:
        issues.append(diagnostic("yaml_unavailable", "", severity="error" if require_yaml else "review"))
    issues.extend(link_report["issues"])
    issues.extend(yaml_issues)
    config_issues, config_count = config_check(root, paths, index, notes, yaml, metadata)
    issues.extend(config_issues)
    for item in check_codex_config(root):
        issues.append(diagnostic(item["code"], item["path"], severity=item["level"], message=item["message"]))
    mirrors = check_mirrors.check(root, paths=paths, notes=notes)
    issues.extend(mirrors["issues"])
    counts = dict(Counter(x["severity"] for x in issues))
    blocking = sum(counts.get(key, 0) for key in ("critical", "error"))
    return dict(schema="wwl-static-check-v1", root=str(root),
                status="failed" if blocking else "partial" if issues else "passed",
                counts=counts, issues=issues,
                scope={"visible_files": len(paths), "markdown_files": len(notes),
                       "links_checked": link_report["checked"], "configs_checked": config_count,
                       "mirrors_checked": mirrors["checked"], "mirror_markers": mirrors["markers"]},
                layers={"links": "checked", "mirrors": "checked", "json": "checked_allowlist",
                        "yaml_properties": "checked" if yaml else "not_run_missing_PyYAML",
                        "base_syntax": "checked_yaml_only" if yaml else "not_run_missing_PyYAML",
                        "toml_roles": "checked_declarations_only" if tomllib and (root / ".codex/config.toml").is_file() else "not_run",
                        "obsidian_ui": "not_run", "mathematical_numeric": "not_run",
                        "experiment_runtime": "not_run", "source_semantics": "not_run"},
                resolved_links=link_report["resolved_links"])


def write_report(report, root, target):
    if target is None:
        return
    target = Path(target)
    root = Path(root).resolve()
    if target.resolve().is_relative_to(root) or not target.parent.is_dir():
        raise ValueError("evidence must be outside root")
    # Exclusive creation prevents overwriting a previous run or following an
    # existing output symlink. This is not a complete filesystem sandbox.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(target, flags, 0o600), "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="vault or integration tree")
    parser.add_argument("--json", type=Path, help="new report path outside --root (private local evidence)")
    parser.add_argument("--require-yaml", action="store_true", help="fail if PyYAML is unavailable; never installs it")
    args = parser.parse_args(argv)
    try:
        report = check(args.root, args.require_yaml)
        write_report(report, args.root, args.json)
    except (ValueError, OSError):
        parser.error("invalid root or output; --json requires a new file outside --root in an existing directory")
    print(json.dumps({k: report[k] for k in ("schema", "status", "counts", "scope", "layers")}, ensure_ascii=False, indent=2))
    return int(any(x["severity"] in {"critical", "error"} for x in report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
