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
