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
        struct.pack_into("<Q", corrupted, relative_offset_position, 10_240)
        with self.assertRaisesRegex(toy.FormatError, "outside the file"):
            toy.parse_toy_gguf(bytes(corrupted))

    def test_rejects_unaligned_offset_even_with_sufficient_data(self) -> None:
        corrupted = bytearray(self.payload)
        name_offset = corrupted.index(b"toy.weight")
        offset_position = name_offset + len(b"toy.weight") + 4 + 8 + 4
        struct.pack_into("<Q", corrupted, offset_position, 1)
        corrupted.extend(b"\x00")
        # data starts at 160: [161,177) is in bounds, but offset 1 is unaligned.
        self.assertEqual(len(corrupted), 177)
        with self.assertRaisesRegex(toy.FormatError, "offset is not aligned to 32 bytes"):
            toy.parse_toy_gguf(bytes(corrupted))

    def test_each_tensor_offset_is_checked_and_aligned_gaps_are_allowed(self) -> None:
        # Two F32 tensors remain within the parser's existing count/type subset.
        buffer = bytearray(toy.MAGIC)
        buffer.extend(struct.pack("<IQQ", toy.VERSION, 2, 2))
        toy.append_metadata_string(buffer, "general.architecture", "toy")
        toy.append_metadata_u32(buffer, "general.alignment", 32)
        offset_positions = []
        for name, relative_offset in (("toy.first", 0), ("toy.second", 32)):
            toy.append_string(buffer, name)
            buffer.extend(struct.pack("<IQI", 1, 4, toy.GGML_TYPE_F32))
            offset_positions.append(len(buffer))
            buffer.extend(struct.pack("<Q", relative_offset))
        data_offset = toy.align_up(len(buffer), 32)
        buffer.extend(b"\x00" * (data_offset - len(buffer)))
        buffer.extend(struct.pack("<4f", -1.0, -0.25, 0.5, 1.25))
        buffer.extend(b"\x00" * 16)
        buffer.extend(struct.pack("<4f", 1.0, 2.0, 3.0, 4.0))
        parsed = toy.parse_toy_gguf(bytes(buffer))
        self.assertEqual([tensor.offset for tensor in parsed.tensors], [0, 32])
        self.assertEqual([tensor.byte_length for tensor in parsed.tensors], [16, 16])
        self.assertEqual(parsed.data_offset, data_offset)
        # Keep the second range in bounds and disjoint; reject its alignment alone.
        struct.pack_into("<Q", buffer, offset_positions[1], 33)
        buffer.extend(b"\x00")
        with self.assertRaisesRegex(toy.FormatError, "'toy.second' offset is not aligned"):
            toy.parse_toy_gguf(bytes(buffer))

    def test_four_bit_grid_has_bounded_error_without_out_of_range_codes(self) -> None:
        metrics = toy.symmetric_int4_error((-1.0, -0.25, 0.5, 1.25))
        self.assertGreater(metrics["scale"], 0.0)
        self.assertLessEqual(metrics["max_abs"], metrics["scale"] / 2.0 + 1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
