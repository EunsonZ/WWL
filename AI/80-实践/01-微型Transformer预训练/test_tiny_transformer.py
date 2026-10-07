"""Standard-library and optional PyTorch tests for the tiny Transformer lab."""

from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from data_pipeline import CharTokenizer, Document, load_corpus, pack_documents
from preflight import load_config, run_preflight
from tiny_transformer import (
    checkpoint_payload_step,
    prepare_output_dir,
    save_checkpoint,
    sha256_text,
    validate_resume_path,
)


HERE = Path(__file__).resolve().parent

try:
    import torch

    from tiny_transformer import (
        BatchStream,
        TinyDecoderOnlyTransformer,
        load_checkpoint,
        set_reproducible_seed,
    )

    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


class DataPipelineTests(unittest.TestCase):
    def assert_all_stream_targets_once(
        self,
        documents: list[Document],
        tokenizer: CharTokenizer,
        block_size: int,
    ) -> list[list[int]]:
        blocks = pack_documents(documents, tokenizer, block_size)
        stream = [
            token_id
            for document in documents
            for token_id in tokenizer.encode(document.text, add_boundaries=True)
        ]
        packed_targets = [
            token_id
            for block in blocks
            for token_id in block[1:]
            if token_id != tokenizer.pad_id
        ]
        self.assertEqual(packed_targets, stream[1:])
        return blocks

    def test_text_digest_is_stable_without_exposing_raw_text(self) -> None:
        self.assertEqual(
            sha256_text("小猫"),
            "3ecbdba2ef9bc82ddee2f58cbc9845700ee78ef390be8f557261e8a407eafb6e",
        )

    def test_output_inside_vault_must_use_ignored_practice_directory(self) -> None:
        unsafe = HERE / "unsafe-output-test-never-create"
        self.assertFalse(unsafe.exists())
        with self.assertRaisesRegex(ValueError, "ignored outputs"):
            prepare_output_dir(unsafe, None)
        self.assertFalse(unsafe.exists())

    def test_preflight_is_read_only_and_complete(self) -> None:
        report = run_preflight(HERE / "config.json", HERE / "corpus.jsonl")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["writes"], 0)
        self.assertEqual(report["documents"], {"train": 16, "dev": 4, "test": 4})
        self.assertGreater(report["blocks"]["train"], 0)
        for split in ("train", "dev", "test"):
            self.assertEqual(
                report["next_token_targets"][split],
                report["source_tokens"][split] - 1,
            )
        self.assertIn("every target covered exactly once", report["packing_boundary"])

    def test_preflight_rejects_non_finite_numeric_fields(self) -> None:
        config = load_config(HERE / "config.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for key in ("dropout", "learning_rate", "weight_decay", "temperature"):
                for value in (float("nan"), float("inf"), float("-inf")):
                    with self.subTest(key=key, value=value):
                        changed = dict(config, **{key: value})
                        path.write_text(json.dumps(changed), encoding="utf-8")
                        with self.assertRaisesRegex(ValueError, "finite"):
                            run_preflight(path, HERE / "corpus.jsonl")

    def test_preflight_rejects_boolean_numbers(self) -> None:
        config = load_config(HERE / "config.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for key in config:
                if type(config[key]) not in (int, float):
                    continue
                for value in (False, True):
                    with self.subTest(key=key, value=value):
                        path.write_text(json.dumps(dict(config, **{key: value})), encoding="utf-8")
                        with self.assertRaises(ValueError):
                            load_config(path)

    def test_preflight_preserves_large_integer_hyperparameters(self) -> None:
        config = load_config(HERE / "config.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for key in ("learning_rate", "weight_decay", "temperature"):
                with self.subTest(key=key):
                    path.write_text(json.dumps(dict(config, **{key: 10**400})), encoding="utf-8")
                    self.assertEqual(load_config(path)[key], 10**400)
                    self.assertEqual(run_preflight(path, HERE / "corpus.jsonl")["status"], "PASS")

    def test_preflight_preserves_finite_numeric_boundaries(self) -> None:
        config = load_config(HERE / "config.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for dropout in (0.0, math.nextafter(1.0, 0.0)):
                changed = dict(config, dropout=dropout, learning_rate=0.0,
                               weight_decay=0.0, temperature=1e-12)
                path.write_text(json.dumps(changed), encoding="utf-8")
                self.assertEqual(run_preflight(path, HERE / "corpus.jsonl")["status"], "PASS")
            for key, value in (("dropout", 1.0), ("dropout", -1e-12),
                               ("temperature", 0.0), ("learning_rate", -1e-12),
                               ("weight_decay", -1e-12), ("seed", 0)):
                with self.subTest(key=key, value=value):
                    path.write_text(json.dumps(dict(config, **{key: value})), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_config(path)

    def test_tokenizer_is_fitted_only_on_supplied_train_text(self) -> None:
        tokenizer = CharTokenizer.fit(
            [Document("train", "train", "created-for-this-tutorial", "甲乙")]
        )
        self.assertEqual(tokenizer.decode(tokenizer.encode("甲乙")), "甲乙")
        self.assertEqual(tokenizer.encode("丙"), [tokenizer.unk_id])

    def test_packing_target_count_divisible_by_block_size(self) -> None:
        tokenizer = CharTokenizer.fit(
            [Document("train", "train", "created-for-this-tutorial", "甲乙丙")]
        )
        documents = [Document("train", "train", "created-for-this-tutorial", "甲乙丙")]
        blocks = self.assert_all_stream_targets_once(documents, tokenizer, block_size=4)
        self.assertEqual(len(blocks), 1)
        self.assertNotEqual(blocks[-1][-1], tokenizer.pad_id)

    def test_packing_one_target_remainder_keeps_boundary_target(self) -> None:
        tokenizer = CharTokenizer.fit(
            [Document("train", "train", "created-for-this-tutorial", "甲乙丙丁")]
        )
        documents = [Document("train", "train", "created-for-this-tutorial", "甲乙丙丁")]
        blocks = self.assert_all_stream_targets_once(documents, tokenizer, block_size=4)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(all(len(block) == 5 for block in blocks))
        self.assertEqual(blocks[0][-1], blocks[1][0])
        self.assertEqual(blocks[-1][-1], tokenizer.pad_id)

    def test_packing_preserves_eos_to_bos_document_boundary(self) -> None:
        documents = [
            Document("a", "train", "created-for-this-tutorial", "甲"),
            Document("b", "train", "created-for-this-tutorial", "乙"),
        ]
        tokenizer = CharTokenizer.fit(documents)
        blocks = self.assert_all_stream_targets_once(documents, tokenizer, block_size=3)
        packed_targets = [
            token_id
            for block in blocks
            for token_id in block[1:]
            if token_id != tokenizer.pad_id
        ]
        self.assertIn(
            [tokenizer.eos_id, tokenizer.bos_id],
            [packed_targets[index : index + 2] for index in range(len(packed_targets) - 1)],
        )

    def test_in_place_resume_rejects_non_latest_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "run"
            checkpoint_dir = output_dir / "checkpoints"
            checkpoint_dir.mkdir(parents=True)
            old = checkpoint_dir / "checkpoint-step-0020.pt"
            latest = checkpoint_dir / "checkpoint-step-0040.pt"
            old.write_bytes(b"old")
            latest.write_bytes(b"latest")
            with self.assertRaisesRegex(ValueError, "latest complete checkpoint"):
                validate_resume_path(old, output_dir)
            self.assertEqual(validate_resume_path(latest, output_dir), (latest.resolve(), "in-place"))

    def test_old_checkpoint_can_branch_only_into_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_checkpoint_dir = root / "source" / "checkpoints"
            source_checkpoint_dir.mkdir(parents=True)
            old = source_checkpoint_dir / "checkpoint-step-0020.pt"
            old.write_bytes(b"old")

            branch = root / "branch"
            prepared = prepare_output_dir(branch, old)
            self.assertEqual(validate_resume_path(old, prepared), (old.resolve(), "branch"))

            occupied = root / "occupied"
            occupied.mkdir()
            (occupied / "existing.txt").write_text("do not mix", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "new or empty"):
                prepare_output_dir(occupied, old)

    def test_checkpoint_filename_step_must_match_payload(self) -> None:
        path = Path("checkpoint-step-0020.pt")
        self.assertEqual(checkpoint_payload_step({"step": 20}, path), 20)
        with self.assertRaisesRegex(ValueError, "filename step"):
            checkpoint_payload_step({"step": 19}, path)

    def test_checkpoint_save_refuses_existing_destination_without_torch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checkpoint-step-0001.pt"
            path.write_bytes(b"preserve-me")
            with self.assertRaises(FileExistsError):
                save_checkpoint(path, None, None, 1, 0, {}, None, "corpus", "blocks")
            self.assertEqual(path.read_bytes(), b"preserve-me")

    def test_config_is_rope_compatible(self) -> None:
        config = load_config(HERE / "config.json")
        self.assertEqual(config["d_model"] % config["n_heads"], 0)
        self.assertEqual((config["d_model"] // config["n_heads"]) % 2, 0)

    def test_corpus_has_no_exact_cross_split_duplicates(self) -> None:
        documents = load_corpus(HERE / "corpus.jsonl")
        self.assertEqual(len(documents), 24)


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed; CPU model tests skipped safely")
class TorchModelTests(unittest.TestCase):
    def small_config(self) -> dict[str, object]:
        config = load_config(HERE / "config.json")
        config.update(
            {
                "block_size": 8,
                "batch_size": 2,
                "d_model": 16,
                "n_heads": 2,
                "n_layers": 1,
                "ffn_multiplier": 2,
                "dropout": 0.0,
            }
        )
        return config

    def test_causal_mask_blocks_future_information(self) -> None:
        config = self.small_config()
        set_reproducible_seed(7)
        model = TinyDecoderOnlyTransformer(config, vocab_size=16, pad_id=0).eval()
        first = torch.tensor(((2, 4, 5, 6),), dtype=torch.long)
        second = torch.tensor(((2, 4, 9, 10),), dtype=torch.long)
        with torch.no_grad():
            first_logits, _, _ = model(first)
            second_logits, _, _ = model(second)
        self.assertTrue(torch.equal(first_logits[:, :2], second_logits[:, :2]))

    def test_checkpoint_resume_matches_uninterrupted_next_step(self) -> None:
        config = self.small_config()
        tokenizer = CharTokenizer.fit(
            [Document("train", "train", "created-for-this-tutorial", "甲乙丙丁")]
        )
        blocks = [[2, 4, 5, 6, 7, 3, 0, 0, 0], [2, 5, 6, 7, 4, 3, 0, 0, 0]]

        def update(model: object, optimizer: object, stream: BatchStream) -> None:
            inputs, targets = stream.next_batch()
            optimizer.zero_grad(set_to_none=True)
            _, loss_sum, valid = model(inputs, targets)
            (loss_sum / valid).backward()
            optimizer.step()

        set_reproducible_seed(11)
        continuous = TinyDecoderOnlyTransformer(config, len(tokenizer.tokens), tokenizer.pad_id)
        continuous_optimizer = torch.optim.AdamW(continuous.parameters(), lr=0.001)
        stream = BatchStream(blocks, batch_size=1)
        update(continuous, continuous_optimizer, stream)

        with tempfile.TemporaryDirectory() as temporary:
            checkpoint_path = Path(temporary) / "checkpoint.pt"
            save_checkpoint(
                checkpoint_path,
                continuous,
                continuous_optimizer,
                1,
                stream.cursor,
                config,
                tokenizer,
                "corpus-hash",
                "block-hash",
            )
            with self.assertRaises(FileExistsError):
                save_checkpoint(
                    checkpoint_path,
                    continuous,
                    continuous_optimizer,
                    1,
                    stream.cursor,
                    config,
                    tokenizer,
                    "corpus-hash",
                    "block-hash",
                )
            update(continuous, continuous_optimizer, stream)
            expected_state = copy.deepcopy(continuous.state_dict())

            resumed = TinyDecoderOnlyTransformer(config, len(tokenizer.tokens), tokenizer.pad_id)
            resumed_optimizer = torch.optim.AdamW(resumed.parameters(), lr=0.001)
            checkpoint = load_checkpoint(checkpoint_path)
            resumed.load_state_dict(checkpoint["model_state"])
            resumed_optimizer.load_state_dict(checkpoint["optimizer_state"])
            resumed_stream = BatchStream(blocks, batch_size=1, cursor=checkpoint["stream_cursor"])
            update(resumed, resumed_optimizer, resumed_stream)
            for name, expected in expected_state.items():
                self.assertTrue(torch.equal(expected, resumed.state_dict()[name]), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
