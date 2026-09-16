---
type: reference
domain: computer-science
stage: 90
status: ready
difficulty: 入门
estimated_minutes: 10
topics:
  - Python
  - 语法速查
  - 项目命令
  - 调试
tags:
  - computer-science/python
---

# Python 语法与项目速查

这是一张“先查命令和形状，再回课程深读”的桌面卡片。示例假定在项目根目录执行；`python` 若不是目标解释器，改用对应解释器或先查 [[计算机知识/10-编程语言/01-Python/01-安装配置与运行模型|运行模型]]。语法块中的 `items`、`value`、`condition`、`package` 等名称是占位符；它们说明代码形状，不是可以不加准备直接合并运行的完整程序。

## 语法与类型

```python
# 注释；缩进（推荐 4 个空格）定义代码块
name = "Ada"             # 名称指向对象，不是固定盒子
count = 3
enabled = True
missing = None
total = count * 2 + 1

if enabled and count > 0:
    print(f"{name}: {total}")
```

- 比较：`< <= == != >= >`；值比较用 `==`，检查 `None` 用 `is None`。
- 真值：`False`、`None`、`0`、`""`、空容器为假；`and`/`or` 可能返回操作数本身。
- 类型：`int`、`float`、`bool`、`str`、`bytes`；文本与字节用 `text.encode("utf-8")` / `data.decode("utf-8")` 转换。
- 转换：`int(s)`、`float(s)`、`str(x)`、`bool(x)`；`input()` 总返回 `str`，转换失败需处理 `ValueError`。
- 可变对象（如 `list`、`dict`）的原地修改会被别名看到；不可变对象（如 `int`、`str`、`bytes`）的“修改”会产生新值并重新绑定名称。

深入：[[计算机知识/10-编程语言/01-Python/02-基础语法与数据类型|基础语法与数据类型]]

## 控制流与函数

```python
for item in items:
    if item == "跳过":
        continue
    print(item)

def add_tax(price: float, rate: float = 0.13) -> float:
    return price * (1 + rate)

amount = add_tax(100)
```

- `if / elif / else` 选择分支；`for` 遍历可迭代对象；`while` 按条件重复。
- `break` 结束循环，`continue` 进入下一轮；避免忘记更新 `while` 的状态。
- 函数用 `def` 定义；参数是输入，`return` 是输出；局部名称不会自动成为全局名称。
- 需要修改外层绑定时，优先重构参数/返回值，谨慎使用 `global`；默认参数不要使用可变对象。

深入：[[计算机知识/10-编程语言/01-Python/03-控制流函数与作用域|控制流、函数与作用域]]

## 容器、迭代与推导式

```python
items = ["a", "b"]              # list：有序、可变
point = (10, 20)                 # tuple：有序、不可变
profile = {"name": "Ada"}       # dict：键到值
unique = {"python", "linux"}    # set：不重复元素

upper = [item.upper() for item in items]
names = {key: value for key, value in profile.items()}
```

- `seq[i]` 取索引，`seq[start:stop:step]` 切片（`stop` 不包含）。
- `list.append(x)` 原地追加；需要独立列表时用 `items.copy()` 或明确的深拷贝策略。
- `dict.get(key, default)` 安全取值；`key in mapping` 检查键；`set` 适合成员判断和去重。
- 迭代器一次消费一个值；生成器函数用 `yield` 延迟产生值，适合大数据流。

深入：[[计算机知识/10-编程语言/01-Python/04-容器迭代器生成器与推导式|容器、迭代器、生成器与推导式]]

## 异常、文件与上下文管理

```python
from pathlib import Path

try:
    value = int("42")
except ValueError as error:
    print(f"输入无效：{error}")
else:
    print(value)

path = Path("data.txt")
with path.open("r", encoding="utf-8") as stream:
    text = stream.read()
```

- 只捕获能处理的具体异常；不要用裸 `except:` 静默吞掉错误。
- `else` 在没有异常时执行；`finally` 用于必须清理的动作；`raise` 主动报告不变量被破坏。
- 文件默认文本模式；明确 `encoding="utf-8"`；`with` 结束时自动关闭资源。
- `Path.read_text()` / `write_text()` 适合小文件；大文件用迭代或分块读取。

深入：[[计算机知识/10-编程语言/01-Python/05-异常文件IO与上下文管理|异常、文件 I/O 与上下文管理]]

## 模块、包与项目结构

```python
# app.py
from package.text import normalize

if __name__ == "__main__":
    print(normalize(" Hello "))
```

```text
project/
├── pyproject.toml
├── src/package/__init__.py
├── src/package/__main__.py  # 提供 python -m package 入口
├── src/package/text.py
└── tests/
```

- `import package` 导入模块/包；`python -m package` 按模块名运行，通常比直接猜路径更稳。
- `__name__ == "__main__"` 保护脚本入口，避免被导入时立即执行。
- 导入错误先查当前工作目录、`sys.executable`、`sys.path` 和包是否安装在同一环境。

深入：[[计算机知识/10-编程语言/01-Python/07-模块包导入与项目结构|模块、包、导入与项目结构]]

## 项目命令：先确认环境，再操作

```bash
python --version
python -c "import sys; print(sys.executable); print(sys.prefix)"
python -m venv .venv
python -m pip --version
python -m pip install -r requirements.txt
python -m pip list
# 仅记录当前环境供比较；不要用它覆盖依赖声明或团队锁文件
python -m pip freeze > requirements.snapshot.txt
python -m pytest
# 仅当项目已安装且 package/__main__.py 存在时
python -m package
```

- 使用 `python -m pip` 让 pip 与当前解释器绑定；不要只看 PATH 中孤立的 `pip`。
- `.venv/` 通常不提交；提交项目声明和锁定文件，按团队约定重建环境。
- `requirements.snapshot.txt` 是诊断快照，不是项目依赖的唯一事实来源；不要用它覆盖人工维护的声明或已审查的锁文件。
- `python -m package` 需要项目先按自身构建配置安装（开发时常为 editable install），并且包提供 `__main__.py`；否则改用项目实际的模块入口。
- pip/PyPI、venv、Conda 和 uv 解决的问题不同；先看项目约定，再选择工具。

深入：[[计算机知识/10-编程语言/01-Python/08-pip与PyPI依赖管理|pip、PyPI 与依赖管理]] · [[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|venv 与虚拟环境原理]] · [[计算机知识/10-编程语言/01-Python/10-Conda-Anaconda与Miniconda|Conda、Anaconda 与 Miniconda]] · [[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|uv 项目、依赖与工具管理]] · [[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]

## 调试入口

```python
print(f"{value=}, {type(value)=}")
assert condition, "应满足的事实"
```

```bash
python -m pytest -q
python -m pdb app.py
python -m compileall src tests
```

- 先复现，再缩小输入和范围；记录实际解释器、工作目录、环境变量和完整异常类型。
- 用 `repr()` 看不可见字符，用 `type()` 验证类型；测试应覆盖成功路径和失败路径。
- `assert` 适合内部不变量，不要用它承担用户输入校验或必须执行的生产逻辑。

深入：[[计算机知识/10-编程语言/01-Python/14-测试调试与代码质量|测试、调试与代码质量]]

## 导航

- 返回 Python MOC：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础]]
- 返回计算机知识首页：[[计算机知识/00-开始/00-计算机知识-首页|计算机知识]]
