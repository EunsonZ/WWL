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
