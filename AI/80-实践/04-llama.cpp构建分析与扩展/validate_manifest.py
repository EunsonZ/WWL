#!/usr/bin/env python3
"""Validate a llama.cpp experiment record without network access."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
PHASE_STATES = {"not-run", "passed", "failed", "skipped"}
FORBIDDEN_EXACT_KEYS = {
    "model_url",
}
FORBIDDEN_KEY_FRAGMENTS = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "authorization",
    "bearer_token",
    "cookie",
    "credential",
    "hf_token",
    "password",
    "private_key",
    "private_url",
    "prompt",
    "secret",
    "session_token",
    "signed_url",
    "webhook",
}
FORBIDDEN_VALUE = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~+/=-]+|\bhf_[A-Za-z0-9]{16,}|"
    r"\bsk-[A-Za-z0-9]{16,}|[?&](?:X-Amz-Signature|Signature|token|access_token)=)",
    re.IGNORECASE,
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def at(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_text = key.lower()
            safe_negative_declaration = (
                child_path == "$.privacy.credentials_recorded" and child is False
            )
            if not safe_negative_declaration and (key_text in FORBIDDEN_EXACT_KEYS or any(
                fragment in key_text for fragment in FORBIDDEN_KEY_FRAGMENTS
            )):
                findings.append(child_path)
            findings.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return findings


def find_forbidden_values(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            findings.extend(find_forbidden_values(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_forbidden_values(child, f"{path}[{index}]"))
    elif isinstance(value, str) and FORBIDDEN_VALUE.search(value):
        findings.append(path)
    return findings


def validate_cpu_evidence(cpu: dict[str, Any], errors: list[str]) -> None:
    """Require structured proof that the accepted baseline is CPU-only."""

    options = cpu.get("cmake_options")
    require(isinstance(options, list), "builds.cpu.cmake_options must be a list", errors)
    if isinstance(options, list):
        for option in ("-DGGML_CUDA=OFF", "-DGGML_METAL=OFF"):
            require(option in options, f"CPU acceptance requires {option}", errors)

    backend = cpu.get("backend_evidence")
    require(isinstance(backend, dict), "CPU acceptance requires backend_evidence", errors)
    if isinstance(backend, dict):
        require(backend.get("intended_backend") == "cpu",
                "CPU backend_evidence.intended_backend must be cpu", errors)
        disabled = backend.get("explicitly_disabled")
        require(isinstance(disabled, list)
                and {"GGML_CUDA", "GGML_METAL"}.issubset(set(disabled)),
                "CPU backend_evidence must explicitly disable CUDA and Metal", errors)
        require(bool(backend.get("fixed_commit_option_inventory_record")),
                "CPU acceptance requires fixed_commit_option_inventory_record", errors)
        require(backend.get("enabled_accelerator_backends") == [],
                "CPU acceptance requires no enabled accelerator backends", errors)
        require(isinstance(backend.get("cpu_libraries"), list),
                "CPU backend_evidence.cpu_libraries must be a list", errors)

    runtime = cpu.get("runtime_evidence")
    require(isinstance(runtime, dict), "CPU acceptance requires runtime_evidence", errors)
    if isinstance(runtime, dict):
        require(runtime.get("observed_backend") == "cpu",
                "CPU runtime_evidence.observed_backend must be cpu", errors)
        require(bool(runtime.get("device_inventory_record")),
                "CPU acceptance requires a device_inventory_record", errors)
        require(bool(runtime.get("runtime_version_record")),
                "CPU acceptance requires a runtime_version_record", errors)

    targets = cpu.get("target_evidence")
    require(isinstance(targets, dict), "CPU acceptance requires target_evidence", errors)
    if isinstance(targets, dict):
        for key in ("configured_targets_record", "built_targets_record", "tested_targets_record"):
            require(bool(targets.get(key)), f"CPU acceptance requires target_evidence.{key}", errors)


def validate_phase(name: str, phase: Any, errors: list[str]) -> None:
    require(isinstance(phase, dict), f"{name} must be an object", errors)
    if not isinstance(phase, dict):
        return
    status = phase.get("status")
    require(status in PHASE_STATES, f"{name}.status must be one of {sorted(PHASE_STATES)}", errors)
    if status == "passed":
        require(bool(phase.get("command_redacted")), f"{name}: passed requires command_redacted", errors)
        require(bool(phase.get("log")), f"{name}: passed requires a log reference", errors)
        require(phase.get("exit_code") == 0, f"{name}: passed requires exit_code 0", errors)
    if status == "skipped":
        require(bool(phase.get("skip_reason")), f"{name}: skipped requires skip_reason", errors)


def validate(data: Any, require_cpu: bool, require_complete: bool) -> list[str]:
    errors: list[str] = []
    require(isinstance(data, dict), "manifest root must be an object", errors)
    if not isinstance(data, dict):
        return errors

    require(data.get("schema_version") == 1, "schema_version must be 1", errors)
    require(data.get("status") in {"planned", "partial", "complete"},
            "status must be planned, partial, or complete", errors)
    forbidden = find_forbidden_keys(data)
    require(not forbidden, "forbidden secret/raw-input keys: " + ", ".join(forbidden), errors)
    forbidden_values = find_forbidden_values(data)
    require(not forbidden_values,
            "credential-like or signed-URL values: " + ", ".join(forbidden_values), errors)

    status = data.get("status")
    commit = at(data, "source.base_commit")
    head = at(data, "source.verified_head")
    if status != "planned" or require_cpu or require_complete:
        require(isinstance(commit, str) and bool(COMMIT.fullmatch(commit)),
                "source.base_commit must be a lowercase full 40-hex commit", errors)
        require(head == commit, "source.verified_head must exactly match base_commit", errors)
        require(isinstance(at(data, "source.dirty"), bool), "source.dirty must be true or false", errors)
    if at(data, "source.dirty") is True:
        require(bool(at(data, "source.patch_file")), "dirty source requires patch_file", errors)
        patch_hash = at(data, "source.patch_sha256")
        require(isinstance(patch_hash, str) and bool(SHA256.fullmatch(patch_hash)),
                "dirty source requires a lowercase 64-hex patch_sha256", errors)

    for key in ("model.local_only", "input.local_only"):
        require(at(data, key) is True, f"{key} must be true", errors)
    for key in ("model_uploaded", "input_uploaded", "credentials_recorded",
                "absolute_private_paths_recorded"):
        require(at(data, f"privacy.{key}") is False, f"privacy.{key} must be false", errors)
    require(at(data, "runs.server.host") == "127.0.0.1",
            "runs.server.host must be exactly 127.0.0.1", errors)

    phase_paths = [
        "runs.gguf_load",
        "runs.benchmark",
        "runs.server",
        "runs.trace",
    ]
    for path in phase_paths:
        validate_phase(path, at(data, path), errors)

    for backend in ("cpu", "cuda"):
        phase = at(data, f"builds.{backend}")
        require(isinstance(phase, dict), f"builds.{backend} must be an object", errors)
        if not isinstance(phase, dict):
            continue
        phase_status = phase.get("status")
        require(phase_status in PHASE_STATES,
                f"builds.{backend}.status must be one of {sorted(PHASE_STATES)}", errors)
        if phase_status == "passed":
            for action in ("configure", "build", "test"):
                require(bool(phase.get(f"{action}_command_redacted")),
                        f"builds.{backend}: passed requires {action}_command_redacted", errors)
                require(bool(phase.get(f"{action}_log")),
                        f"builds.{backend}: passed requires {action}_log", errors)
                require(phase.get(f"{action}_exit_code") == 0,
                        f"builds.{backend}: passed requires {action}_exit_code 0", errors)
            if backend == "cpu":
                validate_cpu_evidence(phase, errors)
        if phase_status == "skipped":
            require(bool(phase.get("skip_reason")),
                    f"builds.{backend}: skipped requires skip_reason", errors)

    if at(data, "runs.gguf_load.status") == "passed":
        model_hash = at(data, "model.sha256")
        require(isinstance(model_hash, str) and bool(SHA256.fullmatch(model_hash)),
                "a passed GGUF load requires model.sha256", errors)
        require(bool(at(data, "model.source_revision")),
                "a passed GGUF load requires model.source_revision", errors)

    if at(data, "runs.benchmark.status") == "passed":
        require(bool(at(data, "runs.benchmark.metric_definitions")),
                "a passed benchmark requires metric_definitions", errors)
        require(isinstance(at(data, "runs.benchmark.sample_count"), int)
                and at(data, "runs.benchmark.sample_count") > 0,
                "a passed benchmark requires positive sample_count", errors)
        require(bool(at(data, "runs.benchmark.results_record")),
                "a passed benchmark requires results_record", errors)

    if at(data, "runs.trace.status") == "passed":
        require(bool(at(data, "runs.trace.actual_symbols_record")),
                "a passed trace requires actual_symbols_record", errors)
        require(bool(at(data, "runs.trace.probability_stage")),
                "a passed trace requires probability_stage", errors)
        require(bool(at(data, "runs.trace.timing_boundaries_record")),
                "a passed trace requires timing_boundaries_record", errors)
        require(at(data, "runs.trace.trace_off_on_token_match") is True,
                "a passed trace requires trace_off_on_token_match true", errors)

    if require_cpu or require_complete:
        require(at(data, "builds.cpu.status") == "passed",
                "CPU acceptance requires builds.cpu.status passed", errors)
    if require_complete:
        require(status == "complete", "--require-complete requires status complete", errors)
        for path in phase_paths:
            require(at(data, f"{path}.status") == "passed", f"complete run requires {path} passed", errors)
        require(at(data, "builds.cuda.status") in {"passed", "skipped"},
                "complete run requires CUDA passed or explicitly skipped", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-cpu-acceptance", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"manifest read error: {error}", file=sys.stderr)
        return 2
    errors = validate(data, args.require_cpu_acceptance, args.require_complete)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"manifest valid: status={data['status']} id={data['experiment_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
