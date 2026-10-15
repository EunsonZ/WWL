"""Regression tests execute only two explicitly selected, reviewed Markdown blocks."""
import asyncio
from pathlib import Path
import re
def vault_root(start: Path) -> Path:
    """Find the vault by its active AGENTS.md marker after directory moves."""
    for candidate in (start, *start.parents):
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError(f"Cannot locate vault root from {start}")

ROOT=vault_root(Path(__file__).resolve().parent)

def selected_block(relative: str, marker: str) -> dict:
    text=(ROOT/relative).read_text(encoding="utf8")
    blocks=re.findall(r"(?m)^(?P<f>`{3,}|~{3,})python[^\n]*\n(?P<body>.*?)(?m:^)(?P=f)\s*$",text,re.S)
    hits=[body for _,body in blocks if marker in body]
    assert len(hits)==1, (relative,len(hits))
    ns={"__name__":"__reviewed_lab__"}
    exec(compile(hits[0],relative,"exec"),ns)
    return ns

async def taskgroup_test():
    ready=asyncio.Event();cleaned=[]
    async def waiting():
        try:
            ready.set()
            await asyncio.Event().wait()
        finally:cleaned.append(True)
    async def failing():
        await ready.wait()
        raise ValueError("expected")
    caught=False
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(waiting());group.create_task(failing())
    except* ValueError:
        caught=True
    assert caught and cleaned==[True]

def main():
    ns=selected_block("计算机知识/10-编程语言/01-Python/03-控制流函数与作用域.md","def classify_readings")
    f=ns['classify_readings']
    assert f([True,False,{"value":True},{"value":False}])==(0,0)
    assert f([0,{"value":0},2,{"value":3}])==(5,4)
    ns=selected_block("计算机知识/10-编程语言/01-Python/06-面向对象数据类与类型标注.md","class Celsius:")
    C=ns['Celsius'];c=C(20)
    for bad in (float('nan'),float('inf'),float('-inf'),-300,10**10000):
        try:c.value=bad
        except ValueError:pass
        else:raise AssertionError(bad)
        assert c.value==20
    for bad in (True,"20",None):
        try:c.value=bad
        except TypeError:pass
        else:raise AssertionError(bad)
    a=[[1],[2]];b=a.copy();b[0].append(3);assert a==[[1,3],[2]]
    asyncio.run(taskgroup_test())
    print("PASS: actual Markdown regressions, aliasing, TaskGroup cancellation cleanup")
if __name__=='__main__':main()
