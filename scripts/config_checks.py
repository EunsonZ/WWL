"""Read-only checks for the C1 project configuration; not a runtime capability probe."""
from pathlib import Path
try:
    import tomllib
except ImportError:
    tomllib = None

WWL_ROLES = ("wwl_scout", "wwl_author", "wwl_reviewer", "wwl_expert")


def check_codex_config(root: Path) -> list[dict]:
    root = Path(root).resolve()
    diagnostics = []

    def add(level, code, path, message):
        diagnostics.append(dict(level=level, code=code, path=path, message=message))

    def read_toml(rel):
        path = root / rel
        ancestors = [root.joinpath(*path.relative_to(root).parts[:n]) for n in range(1, len(path.relative_to(root).parts) + 1)]
        if any(part.is_symlink() for part in ancestors):
            add("error", "config_symlink", rel, "Configuration path contains a symlink; not read.")
            return None
        if not path.is_file():
            add("error", "config_missing", rel, "Required C1 configuration is absent.")
            return None
        if path.stat().st_size > 256 * 1024:
            add("error", "config_too_large", rel, "Configuration exceeds this checker's size limit.")
            return None
        try:
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            add("error", "config_parse", rel, "Cannot parse configuration as UTF-8 TOML.")
            return None

    if tomllib is None:
        add("review", "toml_unavailable", ".codex/config.toml", "TOML layer not_run; Python 3.11+ required.")
        return diagnostics
    config_path = root / ".codex/config.toml"
    if not config_path.exists() and not config_path.is_symlink():
        add("review", "codex_config_absent", ".codex/config.toml", "No project configuration; C1 configuration layer not_run.")
        return diagnostics
    config = read_toml(".codex/config.toml")
    if config is not None:
        agents = config.get("agents")
        if not isinstance(agents, dict):
            add("error", "agents_table", ".codex/config.toml", "Expected an agents table.")
        else:
            caps = [agents[k] for k in ("max_concurrent_threads_per_session", "max_threads") if k in agents]
            if not caps or any(type(cap) is not int or cap < 1 or cap > 32 for cap in caps):
                add("error", "agent_capacity", ".codex/config.toml", "C1 capacity must be an integer from 1 through 32; this is a request, not observed concurrency.")
            if len(caps) == 2 and caps[0] != caps[1]:
                add("error", "agent_capacity_conflict", ".codex/config.toml", "Current and legacy capacity keys disagree.")
            model = agents.get("default_subagent_model")
            if not isinstance(model, str) or not model.strip():
                add("error", "agent_default_model", ".codex/config.toml", "An explicit nonempty default model is required.")
            if agents.get("default_subagent_reasoning_effort") not in ("low", "medium", "high"):
                add("error", "agent_default_effort", ".codex/config.toml", "C1 daily default effort must be low, medium, or high.")
    for role in WWL_ROLES:
        rel = f".codex/agents/{role}.toml"
        data = read_toml(rel)
        if data is None:
            continue
        for field in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                add("error", "role_required_field", rel, f"Missing or empty role field: {field}.")
        if data.get("name") != role:
            add("error", "role_name", rel, "Role name must match its C1 filename.")
        if data.get("sandbox_mode") != "read-only":
            add("error", "role_permissions", rel, "C1 proposal/review roles must request read-only mode.")
        if "model" in data or "model_reasoning_effort" in data:
            add("error", "role_fixed_routing", rel, "Fixed model/effort overrides task routing; remove it from C1 roles.")
        if any(k in data for k in ("mcp_servers", "hooks", "permissions", "sandbox_workspace_write", "approval_policy")):
            add("error", "role_extra_capabilities", rel, "C1 roles must not add services or permission/approval overrides.")
    return diagnostics
