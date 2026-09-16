#!/usr/bin/env python3
"""Unit tests for the bounded toy GGUF format fixture."""

from __future__ import annotations

import struct
import unittest

import gguf_toy_validator as toy


class ToyGgufTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = toy.build_toy_gguf()

    def test_fixture_has_expected_header_metadata_tensor_and_alignment(self) -> None:
        parsed = toy.parse_toy_gguf(self.payload)
        self.assertEqual(parsed.version, 3)
        self.assertEqual(parsed.metadata["general.architecture"], "toy")
        self.assertEqual(parsed.metadata["general.alignment"], 32)
        self.assertEqual(parsed.data_offset % 32, 0)
        self.assertEqual(len(parsed.tensors), 1)
        self.assertEqual(parsed.tensors[0].name, "toy.weight")
        self.assertEqual(parsed.tensors[0].shape, (4,))
        self.assertEqual(parsed.tensors[0].byte_length, 16)

    def test_rejects_truncation_bad_magic_and_unsupported_version(self) -> None:
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(self.payload[:-1])
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(b"NOPE" + self.payload[4:])
        unsupported = bytearray(self.payload)
        struct.pack_into("<I", unsupported, 4, 99)
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(bytes(unsupported))

    def test_rejects_tensor_offset_outside_file(self) -> None:
        corrupted = bytearray(self.payload)
        marker = b"toy.weight"
        name_offset = corrupted.index(marker)
        # name starts after an eight-byte GGUF string length; then ndim and dim.
        relative_offset_position = name_offset + len(marker) + 4 + 8 + 4
        struct.pack_into("<Q", corrupted, relative_offset_position, 10_000)
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(bytes(corrupted))

    def test_four_bit_grid_has_bounded_error_without_out_of_range_codes(self) -> None:
        metrics = toy.symmetric_int4_error((-1.0, -0.25, 0.5, 1.25))
        self.assertGreater(metrics["scale"], 0.0)
        self.assertLessEqual(metrics["max_abs"], metrics["scale"] / 2.0 + 1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
