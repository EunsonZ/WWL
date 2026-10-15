---
type: practice
stage: 1
status: ready
difficulty: 入门到中级
estimated_minutes: 35
domain: computer-science
tags:
  - computer-science/greedy
  - computer-science/counterexample
---

# 贪心选择与失败反例

目标：在不相交活动中用“最早结束”最大化数量，并用相同兼容性检查证明“最早开始”不是可替换规则。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/06-贪心选择与失败反例"
python3 --version
python3 -m unittest -v
~~~

预期为 `Ran 4 tests ... OK`。`(0, 3)` 会让错误规则只选一个活动，最早结束规则能选 `(1, 2)` 和 `(2, 3)`。默认 `validate=False` 保留排序加线性扫描的 `O(n log n)` 路径；小输入测试可用 `validate=True` 在每次接受后全量核对兼容性，该调试模式最坏会增加二次扫描成本。恢复/清理：本实验不访问网络、不写用户文件，只可能生成同目录 `__pycache__/`；确认路径后才可删除它，源码恢复使用编辑器撤销或 Git diff。

## 不变量到可执行证据

- 每次接受的活动都在上一个结束时刻之后 → 两个选择函数的 `validate=True` 显式兼容性检查 → `test_earliest_finish_keeps_selected_schedule_compatible`。
- 标准贪心按结束时间排序，而不是按开始时间排序 → 两个排序 key 与反例 → `test_earliest_start_counterexample_is_not_optimal`。
- 活动必须满足 `start < finish` 且字段类型完整 → `_validated` 的拒绝 → `test_rejects_invalid_activity_preconditions`。

相关稳定课：[[计算机知识/50-数据结构与算法/10-贪心算法与正确性证明|贪心算法与正确性证明]]。

<!-- code-sync: ./greedy_activity.py -->
~~~python
"""活动选择的正确贪心规则，以及一个刻意保留的错误规则。"""

from __future__ import annotations

from typing import Iterable

Activity = tuple[int, int, str]


def _validated(activities: Iterable[Activity]) -> list[Activity]:
    items = list(activities)
    for start, finish, name in items:
        if type(start) is not int or type(finish) is not int or not isinstance(name, str):
            raise TypeError("each activity must be (int start, int finish, str name)")
        if start >= finish:
            raise ValueError("each activity must satisfy start < finish")
    return items


def select_by_earliest_finish(activities: Iterable[Activity], *, validate: bool = False) -> list[Activity]:
    """最大化兼容活动数；已选活动始终与 last_finish 相容。"""
    selected: list[Activity] = []
    last_finish: int | None = None
    for activity in sorted(_validated(activities), key=lambda item: (item[1], item[0], item[2])):
        start, finish, _ = activity
        if last_finish is None or start >= last_finish:
            selected.append(activity)
            last_finish = finish
            if validate and not all(left[1] <= right[0] for left, right in zip(selected, selected[1:])):
                raise AssertionError("selected activities are not mutually compatible")
    return selected


def select_by_earliest_start_wrong(activities: Iterable[Activity], *, validate: bool = False) -> list[Activity]:
    """刻意错误：最早开始不能保证最大数量，供反例测试使用。"""
    selected: list[Activity] = []
    last_finish: int | None = None
    for activity in sorted(_validated(activities), key=lambda item: (item[0], item[1], item[2])):
        start, finish, _ = activity
        if last_finish is None or start >= last_finish:
            selected.append(activity)
            last_finish = finish
            if validate and not all(left[1] <= right[0] for left, right in zip(selected, selected[1:])):
                raise AssertionError("selected activities are not mutually compatible")
    return selected
~~~

<!-- code-sync: ./test_greedy_activity.py -->
~~~python
"""greedy_activity 的正确性边界和错误规则反例。"""

from __future__ import annotations

import unittest

from greedy_activity import select_by_earliest_finish, select_by_earliest_start_wrong


class GreedyActivityTests(unittest.TestCase):
    def test_earliest_finish_keeps_selected_schedule_compatible(self) -> None:
        activities = [(1, 4, "a"), (3, 5, "b"), (0, 6, "c"), (5, 7, "d"), (8, 9, "e")]
        self.assertEqual(
            select_by_earliest_finish(activities, validate=True),
            [(1, 4, "a"), (5, 7, "d"), (8, 9, "e")],
        )

    def test_empty_and_touching_boundaries(self) -> None:
        self.assertEqual(select_by_earliest_finish([]), [])
        self.assertEqual(select_by_earliest_finish([(0, 2, "a"), (2, 4, "b")]), [(0, 2, "a"), (2, 4, "b")])

    def test_earliest_start_counterexample_is_not_optimal(self) -> None:
        counterexample = [(0, 3, "long"), (1, 2, "short-a"), (2, 3, "short-b")]
        self.assertEqual(select_by_earliest_start_wrong(counterexample), [(0, 3, "long")])
        self.assertEqual(select_by_earliest_finish(counterexample), [(1, 2, "short-a"), (2, 3, "short-b")])

    def test_rejects_invalid_activity_preconditions(self) -> None:
        with self.assertRaises(ValueError):
            select_by_earliest_finish([(3, 3, "instant")])
        with self.assertRaises(TypeError):
            select_by_earliest_finish([(1, 2, 3)])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/11-算法设计-课程地图|算法设计 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/23-正确性证明反例与复杂度边界|算法设计深化：证明、反例与复杂度边界]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
