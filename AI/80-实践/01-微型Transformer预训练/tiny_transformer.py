"""No-download CPU pretraining loop for a tiny decoder-only Transformer.

Exit code 77 means the optional PyTorch dependency is unavailable.  The script
never installs dependencies and writes artifacts only below --output-dir.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

from data_pipeline import (
    CharTokenizer,
    block_fingerprint,
    documents_for_split,
    file_sha256,
    load_corpus,
    pack_documents,
    shuffled_blocks,
)
from preflight import load_config, run_preflight


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    torch = None
    nn = None
    F = None


HERE = Path(__file__).resolve().parent
VAULT_ROOT = HERE.parents[2]
SAFE_OUTPUT_ROOT = (HERE / "outputs").resolve()
SKIP_EXIT_CODE = 77
CHECKPOINT_NAME_PATTERN = re.compile(r"checkpoint-step-(\d+)\.pt")


def require_torch() -> bool:
    if torch is None:
        print(
            "SKIP: PyTorch is not installed in this Python environment. "
            "No dependency was installed; run `python preflight.py` for the "
            "pure-standard-library checks."
        )
        return False
    return True


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if torch is not None:

    def apply_rope(query: torch.Tensor, key: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Apply rotary position embedding to [batch, heads, time, head_dim]."""

        sequence_length = query.size(-2)
        head_dimension = query.size(-1)
        if head_dimension % 2:
            raise ValueError("RoPE head dimension must be even")
        positions = torch.arange(sequence_length, device=query.device, dtype=torch.float32)
        frequencies = 1.0 / (
            10000.0
            ** (torch.arange(0, head_dimension, 2, device=query.device, dtype=torch.float32) / head_dimension)
        )
        angles = torch.outer(positions, frequencies)
        cosine = angles.cos().to(dtype=query.dtype)[None, None, :, :]
        sine = angles.sin().to(dtype=query.dtype)[None, None, :, :]

        def rotate(tensor: torch.Tensor) -> torch.Tensor:
            even, odd = tensor[..., 0::2], tensor[..., 1::2]
            return torch.stack((even * cosine - odd * sine, even * sine + odd * cosine), dim=-1).flatten(-2)

        return rotate(query), rotate(key)


    class CausalSelfAttention(nn.Module):
        def __init__(self, d_model: int, n_heads: int, dropout: float):
            super().__init__()
            if d_model % n_heads:
                raise ValueError("d_model must be divisible by n_heads")
            self.n_heads = n_heads
            self.head_dimension = d_model // n_heads
            if self.head_dimension % 2:
                raise ValueError("RoPE requires an even head dimension")
            self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
            self.output = nn.Linear(d_model, d_model, bias=False)
            self.attention_dropout = nn.Dropout(dropout)
            self.residual_dropout = nn.Dropout(dropout)

        def forward(self, hidden: torch.Tensor) -> torch.Tensor:
            batch, sequence_length, d_model = hidden.shape
            qkv = self.qkv(hidden).view(
                batch, sequence_length, 3, self.n_heads, self.head_dimension
            )
            query, key, value = qkv.unbind(dim=2)
            query = query.transpose(1, 2)
            key = key.transpose(1, 2)
            value = value.transpose(1, 2)
            query, key = apply_rope(query, key)
            scores = query @ key.transpose(-2, -1) / math.sqrt(self.head_dimension)
            causal = torch.ones(
                sequence_length, sequence_length, dtype=torch.bool, device=hidden.device
            ).tril()
            scores = scores.masked_fill(~causal, torch.finfo(scores.dtype).min)
            probabilities = self.attention_dropout(F.softmax(scores, dim=-1))
            context = probabilities @ value
            context = context.transpose(1, 2).contiguous().view(batch, sequence_length, d_model)
            return self.residual_dropout(self.output(context))


    class FeedForward(nn.Module):
        def __init__(self, d_model: int, multiplier: int, dropout: float):
            super().__init__()
            hidden_dimension = d_model * multiplier
            self.layers = nn.Sequential(
                nn.Linear(d_model, hidden_dimension, bias=False),
                nn.GELU(),
                nn.Linear(hidden_dimension, d_model, bias=False),
                nn.Dropout(dropout),
            )

        def forward(self, hidden: torch.Tensor) -> torch.Tensor:
            return self.layers(hidden)


    class TransformerBlock(nn.Module):
        def __init__(self, config: dict[str, Any]):
            super().__init__()
            d_model = int(config["d_model"])
            self.attention_norm = nn.LayerNorm(d_model)
            self.attention = CausalSelfAttention(
                d_model, int(config["n_heads"]), float(config["dropout"])
            )
            self.ffn_norm = nn.LayerNorm(d_model)
            self.ffn = FeedForward(
                d_model, int(config["ffn_multiplier"]), float(config["dropout"])
            )

        def forward(self, hidden: torch.Tensor) -> torch.Tensor:
            hidden = hidden + self.attention(self.attention_norm(hidden))
            return hidden + self.ffn(self.ffn_norm(hidden))


    class TinyDecoderOnlyTransformer(nn.Module):
        def __init__(self, config: dict[str, Any], vocab_size: int, pad_id: int):
            super().__init__()
            self.config = dict(config)
            self.pad_id = pad_id
            d_model = int(config["d_model"])
            self.token_embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
            self.blocks = nn.ModuleList(
                [TransformerBlock(config) for _ in range(int(config["n_layers"]))]
            )
            self.final_norm = nn.LayerNorm(d_model)
            self.lm_head = nn.Linear(d_model, vocab_size, bias=False)
            self.lm_head.weight = self.token_embedding.weight
            self.apply(self._initialize)

        @staticmethod
        def _initialize(module: nn.Module) -> None:
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.padding_idx is not None:
                    with torch.no_grad():
                        module.weight[module.padding_idx].zero_()

        def forward(
            self, input_ids: torch.Tensor, targets: torch.Tensor | None = None
        ) -> tuple[torch.Tensor, torch.Tensor | None, torch.Tensor | None]:
            hidden = self.token_embedding(input_ids)
            for block in self.blocks:
                hidden = block(hidden)
            logits = self.lm_head(self.final_norm(hidden))
            if targets is None:
                return logits, None, None
            loss_sum = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
                ignore_index=self.pad_id,
                reduction="sum",
            )
            valid_tokens = targets.ne(self.pad_id).sum()
            return logits, loss_sum, valid_tokens


class BatchStream:
    """Deterministic cyclic block stream whose cursor is checkpointed."""

    def __init__(self, blocks: list[list[int]], batch_size: int, cursor: int = 0):
        if not blocks:
            raise ValueError("batch stream requires at least one block")
        self.blocks = blocks
        self.batch_size = batch_size
        self.cursor = cursor % len(blocks)

    def next_batch(self) -> tuple[Any, Any]:
        selected: list[list[int]] = []
        for _ in range(self.batch_size):
            selected.append(self.blocks[self.cursor])
            self.cursor = (self.cursor + 1) % len(self.blocks)
        batch = torch.tensor(selected, dtype=torch.long)
        return batch[:, :-1], batch[:, 1:]


def set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch, "set_num_threads"):
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))


def parameter_count(model: Any) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def metrics_from_nll(nll: float, tokens: int) -> dict[str, Any]:
    """真实 PPL；超出浮点指数范围时保留 log-PPL 并用 JSON null 标识。"""
    if tokens <= 0 or not math.isfinite(nll) or nll < 0:
        raise ValueError("metrics require positive token count and finite non-negative NLL")
    try:
        ppl = math.exp(nll)
    except OverflowError:
        ppl = None
    return {"nll":nll, "log_ppl":nll, "ppl":ppl,
            "ppl_status":"overflow" if ppl is None else "finite", "tokens":tokens}


def format_ppl(metrics: dict[str, Any]) -> str:
    return f"{metrics['ppl']:.2f}" if metrics['ppl'] is not None else 'overflow (see log_ppl)'


def evaluate_model(
    model: Any, blocks: list[list[int]], batch_size: int
) -> dict[str, Any]:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for start in range(0, len(blocks), batch_size):
            batch = torch.tensor(blocks[start : start + batch_size], dtype=torch.long)
            _, loss_sum, valid_tokens = model(batch[:, :-1], batch[:, 1:])
            total_loss += float(loss_sum.item())
            total_tokens += int(valid_tokens.item())
    if total_tokens == 0:
        raise ValueError("evaluation split has no non-padding targets")
    nll = total_loss / total_tokens
    return metrics_from_nll(nll, total_tokens)


def generate_text(
    model: Any,
    tokenizer: CharTokenizer,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    top_k: int,
    seed: int,
) -> str:
    model.eval()
    prompt_ids = tokenizer.encode(prompt)
    if not prompt_ids:
        prompt_ids = [tokenizer.bos_id]
    generated = torch.tensor([prompt_ids], dtype=torch.long)
    generator = torch.Generator(device="cpu").manual_seed(seed)
    with torch.no_grad():
        for _ in range(max_new_tokens):
            context = generated[:, -int(model.config["block_size"]) :]
            logits, _, _ = model(context)
            next_logits = logits[:, -1, :] / temperature
            next_logits[:, tokenizer.pad_id] = -float("inf")
            k = min(top_k, next_logits.size(-1))
            threshold = torch.topk(next_logits, k).values[:, -1, None]
            next_logits = next_logits.masked_fill(next_logits < threshold, -float("inf"))
            probabilities = F.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probabilities, 1, generator=generator)
            generated = torch.cat((generated, next_token), dim=1)
            if int(next_token.item()) == tokenizer.eos_id:
                break
    return tokenizer.decode(generated[0].tolist())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_metric(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def save_checkpoint(
    path: Path,
    model: Any,
    optimizer: Any,
    step: int,
    stream_cursor: int,
    config: dict[str, Any],
    tokenizer: CharTokenizer,
    corpus_sha256: str,
    train_blocks_sha256: str,
) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing checkpoint: {path}")
    payload = {
        "format": "tiny-transformer-full-state-v1",
        "step": step,
        "stream_cursor": stream_cursor,
        "config": dict(config),
        "tokenizer": tokenizer.to_dict(),
        "corpus_sha256": corpus_sha256,
        "train_blocks_sha256": train_blocks_sha256,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "python_rng_state": random.getstate(),
        "torch_rng_state": torch.get_rng_state(),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"refusing to overwrite stale checkpoint temporary: {temporary}")
    try:
        with temporary.open("xb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard link publishes the completed temporary without replacing an
        # existing destination, even if another writer raced this process.
        os.link(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    temporary.unlink()


def load_checkpoint(path: Path) -> dict[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError as error:
        raise RuntimeError(
            "Restricted checkpoint load failed; no unrestricted retry is permitted. "
            "Use a compatible PyTorch runtime and a trusted checkpoint."
        ) from error


def checkpoint_step_from_path(path: Path) -> int:
    match = CHECKPOINT_NAME_PATTERN.fullmatch(path.name)
    if match is None:
        raise ValueError("checkpoint filename must match checkpoint-step-NNNN.pt")
    return int(match.group(1))


def checkpoint_payload_step(checkpoint: dict[str, Any], path: Path) -> int:
    try:
        payload_step = int(checkpoint["step"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("resume checkpoint has an invalid step") from error
    if checkpoint_step_from_path(path) != payload_step:
        raise ValueError("resume checkpoint filename step does not match checkpoint payload")
    return payload_step


def validate_resume_path(checkpoint: Path, output_dir: Path) -> tuple[Path, str]:
    resolved_checkpoint = checkpoint.resolve()
    checkpoint_root = (output_dir / "checkpoints").resolve()
    if checkpoint.is_symlink() or not resolved_checkpoint.is_file():
        raise ValueError("resume checkpoint must be an existing regular non-symlink file")
    checkpoint_step_from_path(resolved_checkpoint)
    try:
        resolved_checkpoint.relative_to(checkpoint_root)
    except ValueError:
        return resolved_checkpoint, "branch"

    candidates = [
        candidate.resolve()
        for candidate in checkpoint_root.glob("checkpoint-step-*.pt")
        if candidate.is_file()
        and not candidate.is_symlink()
        and CHECKPOINT_NAME_PATTERN.fullmatch(candidate.name)
    ]
    if not candidates:
        raise ValueError("in-place resume requires at least one complete checkpoint")
    latest = max(candidates, key=checkpoint_step_from_path)
    if resolved_checkpoint != latest:
        raise ValueError(
            "in-place resume requires the latest complete checkpoint; "
            "use a new --output-dir to branch from an older checkpoint"
        )
    return resolved_checkpoint, "in-place"


def prepare_output_dir(output_dir: Path, resume: Path | None) -> Path:
    resolved = output_dir.resolve()
    if resolved == HERE:
        raise ValueError("--output-dir cannot be the source directory")
    try:
        resolved.relative_to(VAULT_ROOT)
    except ValueError:
        print(
            "WARNING: output is outside this Vault; confirm its privacy and Git-ignore policy "
            "before using private prompts."
        )
    else:
        try:
            resolved.relative_to(SAFE_OUTPUT_ROOT)
        except ValueError as error:
            raise ValueError(
                "an output directory inside this Vault must be below this practice's ignored outputs/"
            ) from error
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("--output-dir exists but is not a directory")
    resume_is_in_place = False
    if resume is not None:
        try:
            resume.resolve().relative_to((resolved / "checkpoints").resolve())
        except ValueError:
            pass
        else:
            resume_is_in_place = True
    if resolved.exists() and any(resolved.iterdir()) and not resume_is_in_place:
        if resume is None:
            raise ValueError("refusing to overwrite a non-empty output directory; choose a new run name")
        raise ValueError(
            "branch resume requires a new or empty --output-dir; "
            "do not mix lineage with an existing run"
        )
    resolved.mkdir(parents=True, exist_ok=True)
    (resolved / "checkpoints").mkdir(exist_ok=True)
    return resolved


def train(args: argparse.Namespace) -> int:
    config_path = args.config.resolve()
    corpus_path = args.corpus.resolve()
    config = load_config(config_path)
    max_steps = args.max_steps if args.max_steps is not None else int(config["max_steps"])
    if max_steps <= 0:
        raise ValueError("--max-steps must be positive")
    resume_path: Path | None = None
    resume_mode: str | None = None
    if args.resume:
        resume_path, resume_mode = validate_resume_path(args.resume, args.output_dir.resolve())
    output_dir = prepare_output_dir(args.output_dir, args.resume)

    preflight = run_preflight(config_path, corpus_path)
    documents = load_corpus(corpus_path)
    split_documents = {
        split: documents_for_split(documents, split) for split in ("train", "dev", "test")
    }
    tokenizer = CharTokenizer.fit(split_documents["train"])
    blocks = {
        split: pack_documents(items, tokenizer, int(config["block_size"]))
        for split, items in split_documents.items()
    }
    train_blocks = shuffled_blocks(blocks["train"], int(config["seed"]))
    train_fingerprint = block_fingerprint(train_blocks)
    corpus_fingerprint = file_sha256(corpus_path)

    set_reproducible_seed(int(config["seed"]))
    model = TinyDecoderOnlyTransformer(config, len(tokenizer.tokens), tokenizer.pad_id)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    start_step = 0
    stream_cursor = 0
    resume_lineage: dict[str, Any] | None = None
    if resume_path is not None:
        checkpoint = load_checkpoint(resume_path)
        expected = {
            "format": "tiny-transformer-full-state-v1",
            "config": config,
            "tokenizer": tokenizer.to_dict(),
            "corpus_sha256": corpus_fingerprint,
            "train_blocks_sha256": train_fingerprint,
        }
        for key, value in expected.items():
            if checkpoint.get(key) != value:
                raise ValueError(f"resume checkpoint {key} does not match current inputs")
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        random.setstate(checkpoint["python_rng_state"])
        torch.set_rng_state(checkpoint["torch_rng_state"])
        start_step = checkpoint_payload_step(checkpoint, resume_path)
        stream_cursor = int(checkpoint["stream_cursor"])
        if max_steps <= start_step:
            raise ValueError("--max-steps must be greater than the resumed checkpoint step")
        resume_lineage = {
            "mode": resume_mode,
            "parent_checkpoint": resume_path.name,
            "parent_checkpoint_sha256": file_sha256(resume_path),
            "parent_step": start_step,
        }

    stream = BatchStream(train_blocks, int(config["batch_size"]), stream_cursor)
    tokenizer_path = output_dir / "tokenizer.json"
    manifest_path = output_dir / "run-manifest.json"
    if resume_path is None or resume_mode == "branch":
        write_json(tokenizer_path, tokenizer.to_dict())
        manifest = {
            "format": "tiny-transformer-run-v1",
            "run_kind": "branch" if resume_mode == "branch" else "fresh",
            "device": "cpu",
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "parameter_count": parameter_count(model),
            "config": config,
            "config_sha256": file_sha256(config_path),
            "corpus_sha256": corpus_fingerprint,
            "tokenizer_sha256": tokenizer.fingerprint(),
            "train_blocks_sha256": train_fingerprint,
            "data_boundary": "tokenizer fitted on train only; exact normalized hashes separated",
            "packing_boundary": preflight["packing_boundary"],
        }
        if resume_lineage is not None:
            manifest["resume_lineage"] = resume_lineage
        write_json(manifest_path, manifest)

    metrics_path = output_dir / "metrics.jsonl"
    if start_step == 0:
        initial_dev = evaluate_model(model, blocks["dev"], int(config["batch_size"]))
        append_metric(metrics_path, {"event": "eval", "split": "dev", "step": 0, **initial_dev})
        print(f"step=0 dev_nll={initial_dev['nll']:.4f} dev_ppl={format_ppl(initial_dev)}")

    started = time.monotonic()
    for step in range(start_step + 1, max_steps + 1):
        model.train()
        inputs, targets = stream.next_batch()
        optimizer.zero_grad(set_to_none=True)
        _, loss_sum, valid_tokens = model(inputs, targets)
        loss = loss_sum / valid_tokens
        if not torch.isfinite(loss):
            raise FloatingPointError(f"non-finite loss at step {step}")
        loss.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        if not torch.isfinite(gradient_norm):
            raise FloatingPointError(f"non-finite gradient norm at step {step}")
        optimizer.step()

        if step == 1 or step % int(config["eval_interval"]) == 0 or step == max_steps:
            dev = evaluate_model(model, blocks["dev"], int(config["batch_size"]))
            append_metric(
                metrics_path,
                {
                    "event": "eval",
                    "split": "dev",
                    "step": step,
                    "train_batch_nll": float(loss.item()),
                    **dev,
                },
            )
            print(
                f"step={step} train_batch_nll={loss.item():.4f} "
                f"dev_nll={dev['nll']:.4f} dev_ppl={format_ppl(dev)}"
            )
        if step % int(config["checkpoint_interval"]) == 0 or step == max_steps:
            checkpoint_path = output_dir / "checkpoints" / f"checkpoint-step-{step:04d}.pt"
            save_checkpoint(
                checkpoint_path,
                model,
                optimizer,
                step,
                stream.cursor,
                config,
                tokenizer,
                corpus_fingerprint,
                train_fingerprint,
            )

    test = evaluate_model(model, blocks["test"], int(config["batch_size"]))
    generated = generate_text(
        model,
        tokenizer,
        args.prompt,
        int(config["generation_tokens"]),
        float(config["temperature"]),
        int(config["top_k"]),
        int(config["seed"]) + 1,
    )
    prompt_digest = sha256_text(args.prompt)
    generation_digest = sha256_text(generated)
    summary = {
        "status": "PASS",
        "start_step": start_step,
        "final_step": max_steps,
        "resume_mode": resume_mode,
        "elapsed_seconds": time.monotonic() - started,
        "test": test,
        "prompt_sha256": prompt_digest,
        "prompt_characters": len(args.prompt),
        "generation_sha256": generation_digest,
        "generation_characters": len(generated),
        "raw_text_included": args.include_raw_text,
        "warning": "toy-corpus result; not a production-quality language model",
    }
    if args.include_raw_text:
        summary.update({"prompt": args.prompt, "generation": generated})
    write_json(output_dir / "final-summary.json", summary)
    print(f"test_nll={test['nll']:.4f} test_ppl={format_ppl(test)}")
    if args.include_raw_text:
        print(f"generation={generated}")
    else:
        print(
            f"generation_sha256={generation_digest} generation_characters={len(generated)} "
            "(raw text omitted; use --include-raw-text only for public or reviewed text)"
        )
    print(f"PASS: artifacts isolated in {output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--corpus", type=Path, default=HERE / "corpus.jsonl")
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs" / "demo")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--prompt", default="小猫")
    parser.add_argument(
        "--include-raw-text",
        action="store_true",
        help="include prompt and generation verbatim in the summary and terminal output",
    )
    return parser


def main() -> int:
    if not require_torch():
        return SKIP_EXIT_CODE
    args = build_parser().parse_args()
    try:
        return train(args)
    except (OSError, ValueError, KeyError, FloatingPointError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
