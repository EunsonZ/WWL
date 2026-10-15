---
type: practice
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 35
domain: computer-science
tags:
  - computer-science/string-matching
  - computer-science/kmp
---

# KMP 与重叠匹配

目标：先构造最长真前后缀表（LPS），再在完整命中后按 LPS 回退，从而找出重叠而非只找不相交的匹配。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/07-KMP与重叠匹配"
python3 --version
python3 -m unittest -v
~~~

预期为 `Ran 4 tests ... OK`。在 `aaaaa` 中找 `aa` 的正确起点为 `[0, 1, 2, 3]`。与稳定课统一，本实验把空模式定义为匹配文本的全部 `n+1` 个边界：`"abc"` 返回 `[0,1,2,3]`，空文本返回 `[0]`。恢复/清理：本实验不访问网络、不写用户文件，只可能生成同目录 `__pycache__/`；确认路径后才可删除它，源码恢复使用编辑器撤销或 Git diff。

## 不变量到可执行证据

- 第 `i` 个 LPS 介于 `0` 与 `i` 之间 → `prefix_lengths` 的 `assert` → `test_prefix_table_invariant_on_repeated_prefixes`。
- 当前已匹配长度始终是有效、未完成的模式前缀 → `find_all_overlapping` 的 `assert` → `test_full_match_fallback_preserves_overlapping_matches`。
- 空模式匹配全部 `n+1` 个文本边界 → 显式早返回 → `test_empty_pattern_matches_every_text_boundary`。

相关稳定课：[[计算机知识/50-数据结构与算法/13-字符串匹配前缀函数与自动机|字符串匹配、前缀函数与自动机]]。

<!-- code-sync: ./kmp.py -->
~~~python
"""KMP 前缀函数与允许重叠的字符串匹配。"""

from __future__ import annotations


def prefix_lengths(pattern: str) -> list[int]:
    """lps[i] 是 pattern[:i + 1] 的最长真前后缀长度。"""
    if not isinstance(pattern, str):
        raise TypeError("pattern must be a string")
    lps = [0] * len(pattern)
    matched = 0
    for index in range(1, len(pattern)):
        while matched and pattern[index] != pattern[matched]:
            matched = lps[matched - 1]
        if pattern[index] == pattern[matched]:
            matched += 1
        lps[index] = matched
        assert 0 <= lps[index] <= index
    return lps


def find_all_overlapping(text: str, pattern: str) -> list[int]:
    """返回所有起点；完整命中后回退到 lps，因而不会跳过重叠。"""
    if not isinstance(text, str) or not isinstance(pattern, str):
        raise TypeError("text and pattern must be strings")
    if not pattern:
        return list(range(len(text) + 1))
    lps = prefix_lengths(pattern)
    starts: list[int] = []
    matched = 0
    for index, character in enumerate(text):
        while matched and character != pattern[matched]:
            matched = lps[matched - 1]
        if character == pattern[matched]:
            matched += 1
        if matched == len(pattern):
            starts.append(index - len(pattern) + 1)
            matched = lps[matched - 1]
        assert 0 <= matched < len(pattern)
    return starts
~~~

<!-- code-sync: ./test_kmp.py -->
~~~python
"""kmp 的前缀不变量、重叠命中和边界测试。"""

from __future__ import annotations

import unittest

from kmp import find_all_overlapping, prefix_lengths


class KmpTests(unittest.TestCase):
    def test_prefix_table_invariant_on_repeated_prefixes(self) -> None:
        self.assertEqual(prefix_lengths("ababaca"), [0, 0, 1, 2, 3, 0, 1])

    def test_full_match_fallback_preserves_overlapping_matches(self) -> None:
        self.assertEqual(find_all_overlapping("aaaaa", "aa"), [0, 1, 2, 3])
        self.assertEqual(find_all_overlapping("abababa", "aba"), [0, 2, 4])

    def test_empty_text_and_pattern_longer_than_text(self) -> None:
        self.assertEqual(find_all_overlapping("", "a"), [])
        self.assertEqual(find_all_overlapping("ab", "aba"), [])

    def test_empty_pattern_matches_every_text_boundary(self) -> None:
        self.assertEqual(find_all_overlapping("abc", ""), [0, 1, 2, 3])
        self.assertEqual(find_all_overlapping("", ""), [0])
        with self.assertRaises(TypeError):
            prefix_lengths(123)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/22-平衡树区间结构与结构扩展地图|数据结构深化：树旋转、区间聚合与扩展地图]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
