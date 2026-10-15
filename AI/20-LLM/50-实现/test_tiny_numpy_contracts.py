"""CPU-only regression contracts for the tiny NumPy decoder examples."""

from __future__ import annotations

import math
import unittest

import numpy as np

from tiny_decoder import CausalSelfAttention, TinyDecoderLM
from tiny_tokenizer_embedding import CharTokenizer, Embedding
from tiny_train_generate import sample_from_logits


class TinyNumpyContracts(unittest.TestCase):
    def test_causality_cache_and_invalid_cache_state(self) -> None:
        model = TinyDecoderLM(8)
        token_ids = np.array([[1, 2, 3]])
        full, _ = model.forward(token_ids)
        changed, _ = model.forward(np.array([[1, 2, 4]]))
        np.testing.assert_allclose(full[:, :2], changed[:, :2], atol=1e-12)

        cache = None
        pieces = []
        for position in range(3):
            output, cache = model.forward(
                token_ids[:, position : position + 1],
                start_pos=position,
                cache=cache,
                use_cache=True,
            )
            pieces.append(output)
        np.testing.assert_allclose(full, np.concatenate(pieces, axis=1), atol=1e-10)

        for position in (-1, 5):
            with self.assertRaises(ValueError):
                model.forward(token_ids, start_pos=position)
        invalid_caches = [
            (np.zeros((1, 2, 1, 4)), np.zeros((2, 2, 1, 4))),
            (np.zeros((1, 2, 1, 4), dtype=np.float32),) * 2,
        ]
        for invalid_cache in invalid_caches:
            with self.assertRaises(ValueError):
                model.forward(token_ids, start_pos=1, cache=invalid_cache)

    def test_causal_mask_is_not_a_finite_score_floor(self) -> None:
        attention = CausalSelfAttention(2, 1, np.random.default_rng(0))
        attention.query.weight = np.eye(2)
        attention.key.weight = -np.eye(2)
        attention.value.weight = np.eye(2)
        attention.output.weight = np.eye(2)
        values = np.array([[[1e20, 0.0], [0.0, 1e20]]])
        full, _ = attention.forward(values)
        prefix, _ = attention.forward(values[:, :1])
        np.testing.assert_allclose(full[:, :1], prefix, rtol=0.0, atol=0.0)

    def test_negative_and_out_of_range_token_ids_are_rejected(self) -> None:
        tokenizer = CharTokenizer("a")
        embedding = Embedding(2, 4)
        for token_ids in ([-1], [2]):
            with self.assertRaises((ValueError, IndexError)):
                tokenizer.decode(token_ids)
            with self.assertRaises((ValueError, IndexError)):
                embedding(np.array(token_ids))

    def test_sampling_boundaries_translation_ties_and_top_k(self) -> None:
        invalid = [
            (np.array([]), 1.0),
            (np.array([1.0]), math.nan),
            (np.array([1.0]), math.inf),
            (np.array([-1e308, 1e308]), 1.0),
        ]
        for logits, temperature in invalid:
            with self.assertRaises(ValueError):
                sample_from_logits(
                    logits, np.random.default_rng(1), temperature=temperature
                )
        self.assertEqual(
            sample_from_logits(
                np.array([1000.0, 999.0]),
                np.random.default_rng(1),
                temperature=1e-308,
            ),
            0,
        )
        baseline = [
            sample_from_logits(
                np.array([1.0, 2.0, 3.0]), np.random.default_rng(seed), top_k=2
            )
            for seed in range(8)
        ]
        translated = [
            sample_from_logits(
                np.array([10001.0, 10002.0, 10003.0]),
                np.random.default_rng(seed),
                top_k=2,
            )
            for seed in range(8)
        ]
        self.assertEqual(baseline, translated)
        self.assertEqual(
            sample_from_logits(
                np.array([2.0, 2.0, 1.0]), np.random.default_rng(2), top_k=1
            ),
            0,
        )
        for top_k in (0, -1, 4, 1.5, True):
            with self.assertRaises(ValueError):
                sample_from_logits(
                    np.array([1.0, 2.0, 3.0]),
                    np.random.default_rng(0),
                    top_k=top_k,
                )


if __name__ == "__main__":
    unittest.main()
