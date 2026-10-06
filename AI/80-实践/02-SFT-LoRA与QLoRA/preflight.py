#!/usr/bin/env python3
"""Offline, read-only validation for this practice's data and PEFT contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PRACTICE_ROOT = Path(__file__).resolve().parent
PLACEHOLDER = "REPLACE_"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def practice_file(relative_path: Any, label: str, root: Path = PRACTICE_ROOT) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError(f"{label} must be a non-empty practice-relative path")
    raw_candidate = root / relative_path
    if raw_candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    candidate = raw_candidate.resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} must stay inside the practice directory") from error
    return candidate


def validate_data(contract: dict[str, Any], root: Path = PRACTICE_ROOT) -> list[str]:
    errors: list[str] = []
    required = contract.get("required_record_fields", [])
    roles = set(contract.get("allowed_roles", []))
    allowed_splits = set(contract.get("allowed_splits", []))
    approved_licenses = set(contract.get("approved_licenses", []))
    template = contract.get("chat_template", {})
    try:
        data_path = practice_file(contract.get("train_path"), "data contract train_path", root)
        license_path = practice_file(contract.get("license_record"), "data contract license_record", root)
        lines = data_path.read_text(encoding="utf-8").splitlines()
        license_text = license_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        return [f"cannot read fixture or license record: {error}"]
    except ValueError as error:
        return [str(error)]
    if contract.get("schema_version") != "sft-chat-v1":
        errors.append("unsupported data contract schema_version")
    expected_required = {"id", "messages", "license", "split", "split_group"}
    if not isinstance(required, list) or not expected_required.issubset(set(required)):
        errors.append(f"required_record_fields must include {sorted(expected_required)}")
    if allowed_splits != {"train", "dev", "test"}:
        errors.append("allowed_splits must be exactly train, dev, and test")
    if not approved_licenses or not all(isinstance(item, str) and item.strip() for item in approved_licenses):
        errors.append("approved_licenses must contain explicit non-empty identifiers")
    if not license_text:
        errors.append("fixture license record must not be empty")
    if not lines:
        errors.append("teaching fixture must contain at least one record")
    ids: set[str] = set()
    groups: dict[str, str] = {}
    observed_splits: set[str] = set()
    for number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"fixture line {number}: invalid JSON: {error.msg}")
            continue
        missing = [field for field in required if field not in record]
        if missing:
            errors.append(f"fixture line {number}: missing fields {missing}")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"fixture line {number}: id must be non-empty text")
        elif record_id in ids:
            errors.append(f"fixture line {number}: duplicate id {record_id}")
        else:
            ids.add(record_id)
        license_id = record.get("license")
        if not isinstance(license_id, str) or license_id not in approved_licenses:
            errors.append(f"fixture line {number}: license must be one of {sorted(approved_licenses)}")
        split = record.get("split")
        if not isinstance(split, str) or split not in allowed_splits:
            errors.append(f"fixture line {number}: split must be one of {sorted(allowed_splits)}")
        else:
            observed_splits.add(split)
        split_group = record.get("split_group")
        if not isinstance(split_group, str) or not split_group.strip():
            errors.append(f"fixture line {number}: split_group must be non-empty text")
        elif isinstance(split, str):
            previous_split = groups.setdefault(split_group, split)
            if previous_split != split:
                errors.append(
                    f"fixture line {number}: split_group {split_group} crosses {previous_split} and {split}"
                )
        messages = record.get("messages")
        if not isinstance(messages, list) or not messages:
            errors.append(f"fixture line {number}: messages must be a non-empty list")
            continue
        if not isinstance(messages[-1], dict) or messages[-1].get("role") != "assistant":
            errors.append(f"fixture line {number}: final message must be assistant for SFT")
        for message in messages:
            if not isinstance(message, dict) or set(message) != {"role", "content"}:
                errors.append(f"fixture line {number}: each message must contain only role and content")
            elif message.get("role") not in roles or not isinstance(message.get("content"), str):
                errors.append(f"fixture line {number}: invalid role or non-string content")
    missing_splits = allowed_splits - observed_splits
    if missing_splits:
        errors.append(f"teaching fixture is missing splits {sorted(missing_splits)}")
    if template.get("loss_scope") != "assistant-only":
        errors.append("teaching contract must explicitly use assistant-only loss")
    if template.get("truncation") != "reject samples whose supervised assistant span would be truncated":
        errors.append("teaching contract must state the supervised-span truncation policy")
    return errors


def validate_run(run: dict[str, Any], allow_placeholders: bool) -> list[str]:
    errors: list[str] = []
    if run.get("schema_version") != "peft-run-v1":
        errors.append("unsupported run schema_version")
    if run.get("run_enabled") is not False:
        errors.append("teaching configurations must keep run_enabled false")
    if run.get("method") not in {"lora", "qlora"}:
        errors.append("method must be lora or qlora")
    quantization = run.get("quantization")
    if not isinstance(quantization, dict):
        errors.append("quantization must be an object")
    elif run.get("method") == "qlora" and quantization.get("load_in_4bit") is not True:
        errors.append("QLoRA requires an explicit 4-bit frozen-base intent")
    lora = run.get("lora")
    if not isinstance(lora, dict) or not isinstance(lora.get("rank"), int) or lora["rank"] <= 0:
        errors.append("LoRA rank must be a positive integer")
    elif not isinstance(lora.get("target_modules"), list) or not lora["target_modules"]:
        errors.append("LoRA target_modules must be an explicit non-empty list")
    base = run.get("base_model", {})
    for field in ("repository", "revision"):
        value = base.get(field)
        if not isinstance(value, str) or not value:
            errors.append(f"base_model.{field} must be a non-empty string")
        elif value.startswith(PLACEHOLDER) and not allow_placeholders:
            errors.append(f"base_model.{field} is a template placeholder; pin a reviewed identity before training")
    license_review = base.get("license_review")
    if not isinstance(license_review, dict) or set(license_review) != {"status", "record"}:
        errors.append("base_model.license_review must contain exactly status and record")
    else:
        status = license_review.get("status")
        record = license_review.get("record")
        if allow_placeholders:
            if status not in {"not_reviewed", "reviewed"}:
                errors.append("template license review status must be not_reviewed or reviewed")
            if not isinstance(record, str) or not record.strip():
                errors.append("base_model.license_review.record must be non-empty text")
        else:
            if status != "reviewed":
                errors.append("base model license must be reviewed before this config can pass")
            if not isinstance(record, str) or not record.strip() or record.startswith(PLACEHOLDER):
                errors.append("base_model.license_review.record must identify the completed review")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="practice-relative run JSON")
    parser.add_argument("--allow-template-placeholders", action="store_true", help="validate teaching templates without authorizing a real run")
    args = parser.parse_args()
    run_path = (PRACTICE_ROOT / args.config).resolve()
    try:
        run = load_json(run_path)
        contract_path = practice_file(run["data_contract"], "run data_contract")
        contract = load_json(contract_path)
        errors = validate_data(contract) + validate_run(run, args.allow_template_placeholders)
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        errors = [str(error)]
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    print(f"STATIC VALID: {args.config}; run_enabled=false; no framework import, model access, or training performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
