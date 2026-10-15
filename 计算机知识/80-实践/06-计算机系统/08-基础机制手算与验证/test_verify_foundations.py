import unittest

from verify_foundations import (
    decode_toy_dram,
    detect_101,
    ripple_add,
    trace_lru_cache,
    translate_two_stage,
)


class DetectorTests(unittest.TestCase):
    def test_overlapping_101(self) -> None:
        trace = detect_101("10101")
        self.assertEqual([row["output"] for row in trace], [0, 0, 1, 0, 1])
        self.assertEqual([row["state"] for row in trace], ["1", "10", "101", "10", "101"])

    def test_rejects_non_binary_input(self) -> None:
        with self.assertRaises(ValueError):
            detect_101("10x01")


class ArithmeticTests(unittest.TestCase):
    def test_unsigned_carry_and_signed_overflow_are_distinct(self) -> None:
        signed_case = ripple_add(0b0111, 0b0001, 4)
        unsigned_case = ripple_add(0b1111, 0b0001, 4)
        self.assertEqual((signed_case["result"], signed_case["carry_out"]), (0b1000, 0))
        self.assertTrue(signed_case["signed_overflow"])
        self.assertEqual((unsigned_case["result"], unsigned_case["carry_out"]), (0, 1))
        self.assertFalse(unsigned_case["signed_overflow"])

    def test_subtraction_uses_same_adder(self) -> None:
        result = ripple_add(0b0011, 0b0101, 4, subtract=True)
        self.assertEqual(result["result"], 0b1110)
        self.assertEqual(result["carry_out"], 0)
        self.assertFalse(result["signed_overflow"])

    def test_rejects_operand_outside_width(self) -> None:
        with self.assertRaises(ValueError):
            ripple_add(16, 0, 4)


class AddressModelTests(unittest.TestCase):
    def test_true_lru_trace_matches_lesson(self) -> None:
        trace = trace_lru_cache([0x00, 0x10, 0x40, 0x00, 0x80, 0x40])
        self.assertEqual([row["hit"] for row in trace], [False, False, False, True, False, False])
        self.assertEqual([row["set"] for row in trace], [0, 1, 0, 0, 0, 0])
        self.assertEqual([row["evicted"] for row in trace], [None, None, None, None, 1, 0])

    def test_dram_decode_matches_declared_mapping(self) -> None:
        expected = {
            0x1234: {"row": 0x12, "bank": 0, "column": 6, "offset": 4},
            0x123C: {"row": 0x12, "bank": 0, "column": 7, "offset": 4},
            0x1274: {"row": 0x12, "bank": 1, "column": 6, "offset": 4},
            0x1334: {"row": 0x13, "bank": 0, "column": 6, "offset": 4},
        }
        self.assertEqual({address: decode_toy_dram(address) for address in expected}, expected)

    def test_two_stage_translation_preserves_offset(self) -> None:
        result = translate_two_stage(0xAC, {0xA: 0x5}, {0x5: 0x9})
        self.assertEqual(result["gpa"], 0x5C)
        self.assertEqual(result["hpa"], 0x9C)
        self.assertEqual(result["offset"], 0xC)

    def test_two_stage_translation_distinguishes_missing_stage(self) -> None:
        with self.assertRaisesRegex(KeyError, "guest VPN"):
            translate_two_stage(0xAC, {}, {0x5: 0x9})
        with self.assertRaisesRegex(KeyError, "stage-2 GPN"):
            translate_two_stage(0xAC, {0xA: 0x5}, {})

    def test_two_stage_translation_rejects_out_of_range_page_numbers_at_owner(self) -> None:
        with self.assertRaisesRegex(ValueError, "guest physical page number"):
            translate_two_stage(0xAC, {0xA: 0x10}, {})
        with self.assertRaisesRegex(ValueError, "host physical page number"):
            translate_two_stage(0xAC, {0xA: 0x5}, {0x5: 0x10})


if __name__ == "__main__":
    unittest.main()
