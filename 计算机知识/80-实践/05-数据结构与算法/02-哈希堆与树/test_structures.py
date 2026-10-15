"""structures 的正例、边界和错误输入。"""

from __future__ import annotations

import unittest

from structures import BinarySearchTree, top_k, word_frequencies


class StructuresTests(unittest.TestCase):
    def test_hash_frequency_and_heap_top_k(self) -> None:
        self.assertEqual(word_frequencies(["red", "blue", "red"]), {"red": 2, "blue": 1})
        self.assertEqual(top_k([4, 1, 9, 3, 9, 2], 3), [9, 9, 4])

    def test_empty_and_duplicate_tree_boundary(self) -> None:
        self.assertEqual(top_k([], 2), [])
        tree = BinarySearchTree()
        for key in [5, 2, 8, 1, 3]:
            self.assertTrue(tree.insert(key))
            tree.validate()
        self.assertFalse(tree.insert(3))
        self.assertEqual(tree.inorder(), [1, 2, 3, 5, 8])
        self.assertTrue(tree.contains(8))
        self.assertFalse(tree.contains(4))
        self.assertEqual(len(tree), 5)

    def test_tree_validator_rejects_a_deep_global_order_violation(self) -> None:
        tree = BinarySearchTree()
        for key in [10, 5, 15, 7]:
            tree.insert(key)
        assert tree._root is not None and tree._root.left is not None
        assert tree._root.left.right is not None
        tree._root.left.right.key = 12
        with self.assertRaises(AssertionError):
            tree.validate()

    def test_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            top_k([1], -1)
        with self.assertRaises(TypeError):
            word_frequencies(["ok", 3])  # type: ignore[list-item]
        with self.assertRaises(TypeError):
            BinarySearchTree().insert(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
