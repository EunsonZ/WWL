"""Read-only, pure-standard-library preflight for the tiny Transformer lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from data_pipeline import (
    CharTokenizer,
    block_fingerprint,
    documents_for_split,
    file_sha256,
    load_corpus,
    pack_documents,
    shuffled_blocks,
)


HERE = Path(__file__).resolve().parent


def load_config(path: Path) -> dict[str, object]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required_positive_ints = {
        "seed",
        "block_size",
        "batch_size",
        "d_model",
        "n_heads",
        "n_layers",
        "ffn_multiplier",
        "max_steps",
        "eval_interval",
        "checkpoint_interval",
        "generation_tokens",
        "top_k",
    }
    for key in required_positive_ints:
        if not isinstance(config.get(key), int) or config[key] <= 0:
            raise ValueError(f"config {key} must be a positive integer")
    for key in ("dropout", "learning_rate", "weight_decay", "temperature"):
        value = config.get(key)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"config {key} must be a non-negative number")
    if config["d_model"] % config["n_heads"] != 0:
        raise ValueError("d_model must be divisible by n_heads")
    head_dim = config["d_model"] // config["n_heads"]
    if head_dim % 2 != 0:
        raise ValueError("RoPE requires an even attention head dimension")
    if not 0 <= config["dropout"] < 1:
        raise ValueError("dropout must be in [0, 1)")
    if config["temperature"] <= 0:
        raise ValueError("temperature must be positive")
    return config


def run_preflight(config_path: Path, corpus_path: Path) -> dict[str, object]:
    config = load_config(config_path)
    documents = load_corpus(corpus_path)
    split_documents = {
        split: documents_for_split(documents, split) for split in ("train", "dev", "test")
    }
    tokenizer = CharTokenizer.fit(split_documents["train"])
    for document in split_documents["train"]:
        decoded = tokenizer.decode(tokenizer.encode(document.text))
        if decoded != document.text:
            raise ValueError(f"train tokenizer round-trip failed for {document.document_id}")
    packed = {
        split: pack_documents(items, tokenizer, int(config["block_size"]))
        for split, items in split_documents.items()
    }
    source_tokens: dict[str, int] = {}
    next_token_targets: dict[str, int] = {}
    for split, items in split_documents.items():
        stream = [
            token_id
            for document in items
            for token_id in tokenizer.encode(document.text, add_boundaries=True)
        ]
        packed_targets = [
            token_id
            for block in packed[split]
            for token_id in block[1:]
            if token_id != tokenizer.pad_id
        ]
        expected_targets = stream[1:]
        if packed_targets != expected_targets:
            raise ValueError(
                f"packing target coverage failed for {split}: expected every stream target once"
            )
        source_tokens[split] = len(stream)
        next_token_targets[split] = len(packed_targets)
    train_order_a = shuffled_blocks(packed["train"], int(config["seed"]))
    train_order_b = shuffled_blocks(packed["train"], int(config["seed"]))
    if train_order_a != train_order_b:
        raise ValueError("fixed-seed block order is not deterministic")
    unknown_counts = {
        split: sum(
            token_id == tokenizer.unk_id
            for document in items
            for token_id in tokenizer.encode(document.text)
        )
        for split, items in split_documents.items()
    }
    return {
        "status": "PASS",
        "writes": 0,
        "corpus_sha256": file_sha256(corpus_path),
        "config_sha256": file_sha256(config_path),
        "documents": {split: len(items) for split, items in split_documents.items()},
        "vocab_size": len(tokenizer.tokens),
        "tokenizer_sha256": tokenizer.fingerprint(),
        "blocks": {split: len(items) for split, items in packed.items()},
        "source_tokens": source_tokens,
        "next_token_targets": next_token_targets,
        "train_blocks_sha256": block_fingerprint(train_order_a),
        "unknown_tokens": unknown_counts,
        "packing_boundary": (
            "continuous stream; stride=block_size with one-token input overlap; "
            "every target covered exactly once; EOS separates documents; "
            "cross-document attention allowed"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--corpus", type=Path, default=HERE / "corpus.jsonl")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = run_preflight(args.config.resolve(), args.corpus.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
