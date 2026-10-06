class ReadOnly:
    def __get__(self, obj, owner=None):
        return "descriptor"
    def __set__(self, obj, value):
        raise AttributeError("read-only")

class Example:
    x = ReadOnly()
    def method(self):
        return "method"

obj = Example()
obj.__dict__["x"] = "instance"
obj.__dict__["method"] = "shadow"
assert obj.x == "descriptor"
assert obj.method == "shadow"

class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass
assert D.__mro__ == (D, B, C, A, object)

import asyncio

async def child(started: asyncio.Event, cleaned: list[str]) -> None:
    try:
        started.set()
        await asyncio.Event().wait()
    finally:
        cleaned.append("released")

async def demonstration() -> None:
    started = asyncio.Event()
    cleaned: list[str] = []
    async with asyncio.TaskGroup() as group:
        task = group.create_task(child(started, cleaned))
        await started.wait()
        task.cancel()
    assert task.cancelled()
    assert cleaned == ["released"]

async def consume(queue: asyncio.Queue[int | None], output: list[int]) -> None:
    while True:
        item = await queue.get()
        try:
            if item is None:
                return
            output.append(item * item)
        finally:
            queue.task_done()
