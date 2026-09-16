---
type: lesson
domain: computer-science
stage: 13
status: ready
difficulty: 进阶
estimated_minutes: 50
topics:
  - Python
  - 标准库
  - 第三方包
  - Web
  - 数据分析
  - 测试
tags:
  - computer-science/python
  - computer-science/package-ecosystem
---

# 常用 Package 生态与用法

> 学习路径：[[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|11：uv 项目、依赖与工具管理]] → [[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|12：包管理器选择、锁定与迁移]] → **13：本课** → [[计算机知识/10-编程语言/01-Python/14-测试调试与代码质量|14：测试、调试与代码质量]]
>
> 返回：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础 MOC]]

## 本课目标

这不是第三方包的 API 百科，而是一张“遇到问题时从哪里开始”的生态地图。完成后，你应能优先检查标准库，再按任务选择一类包；能在项目环境中安装它、跑通一个最小例子，并知道何时应停止堆叠依赖、回到官方文档。

以下链接均指向项目官方文档或 PyPA；包的版本、支持的 Python 范围和安装细节会变化。示例不固定版本号，实际项目应按[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|上一课]]的锁定策略审查并固定版本。除明确写成“可运行”的完整代码块外，速查表中的一行代码是说明某个 API 形状的片段；不要把不同片段直接拼成一个程序。

## 1. 默认从标准库开始

标准库随 Python 发行，不需要 `pip install`。它常已足以完成文件、路径、JSON、日期、命令行参数、日志、单元测试和小型 HTTP 请求等工作；少一个依赖，就少一份升级、许可证和供应链审查负担。

| 先考虑的模块 | 适用场景 | 最小用法 | 官方链接 |
| --- | --- | --- | --- |
| `pathlib`、`csv`、`json` | 路径、CSV 和 JSON 文件 | `data = json.loads('{"ok": true}')` | [文件与目录路径](https://docs.python.org/3/library/pathlib.html)、[JSON](https://docs.python.org/3/library/json.html) |
| `urllib.request`、`urllib.parse` | 依赖极少的同步 HTTP、URL 编码 | `from urllib.request import urlopen` 后：`with urlopen(url, timeout=5) as r: body = r.read()` | [urllib](https://docs.python.org/3/library/urllib.html) |
| `logging`、`argparse` | 脚本日志和简单 CLI 参数 | `logging.info("started")` | [logging](https://docs.python.org/3/library/logging.html)、[argparse](https://docs.python.org/3/library/argparse.html) |
| `unittest`、`sqlite3` | 基础单元测试、无服务器的本地关系数据 | `con = sqlite3.connect("app.db")` | [unittest](https://docs.python.org/3/library/unittest.html)、[sqlite3](https://docs.python.org/3/library/sqlite3.html) |

标准库优先不等于“永远不用第三方包”。当需求变成异步 HTTP、成熟的 DataFrame、数值数组、Web API、结构化验证或更好的测试体验时，选一个维护良好、目标明确的包通常比自己造轮子更安全。

## 2. 安装的共同前提：在项目环境中做

所有 `python -m pip install ...` 都应在项目自己的虚拟环境里执行。若项目使用 `uv`，把同一依赖写入项目声明而非只在当前 shell 临时安装：

```bash
# pip + venv 路线
python -m pip install httpx

# uv 项目路线：更新 pyproject.toml 和 uv.lock
uv add httpx
```

Conda 项目则使用该项目的 Conda environment 和团队约定的渠道/环境文件。不要把下面的包清单全装进一个“万能环境”；按当前项目的真实需求添加最少依赖，并更新、审查 lockfile。

## 3. 网络客户端：Requests 或 HTTPX，按并发模型二选一

### Requests：同步脚本与已有同步代码

适用场景：一次性脚本、同步爬取/调用、已有代码库已经使用 Requests。它的同步 API 简洁成熟；每次请求都设超时并检查 HTTP 错误，避免进程无限等待或把错误响应当成数据。

```bash
python -m pip install requests
```

```python
import requests

# 占位 URL：替换为你已获授权、确实会返回 JSON 的 API；不要直接请求此保留域名。
url = "https://api.example.test/items"
response = requests.get(url, timeout=10)
response.raise_for_status()
items = response.json()
print(len(items))
```

阅读 [Requests Quickstart](https://requests.readthedocs.io/en/latest/user/quickstart/)；真实服务请使用其认证与 TLS 文档，绝不要把 token 写进源代码或 notebook 输出。

### HTTPX：需要 async；HTTP/2 是按需开启的选项

适用场景：异步程序、并发 I/O、需要 HTTP/2，或服务端已使用 ASGI 生态。HTTPX 同时提供同步与异步 API，且有严格的默认超时；不要为了“新”在同一层同时混用 Requests 和 HTTPX。

```bash
python -m pip install httpx
```

下面的示例展示异步请求，**没有**启用 HTTP/2。确实需要尝试 HTTP/2 时，安装 `python -m pip install "httpx[http2]"`，并创建 `httpx.AsyncClient(http2=True)`；若服务端不支持，它会使用 HTTP/1.1。不要只因用了 HTTPX 就假定请求已经是 HTTP/2。

```python
import asyncio

import httpx

async def fetch_title(url: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text[:80]

async def main() -> None:
    # 此公开示例会发出网络请求；实际项目改为已获授权的目标地址。
    print(await fetch_title("https://example.com"))

if __name__ == "__main__":
    asyncio.run(main())
```

官方[HTTPX 文档](https://www.python-httpx.org/)覆盖同步/异步 API、连接池、代理和 HTTP/2。不要在同步函数里直接调用上述协程；交由异步应用框架或 `asyncio.run()` 的顶层入口运行。

### 二选一的判断

| 问题 | 选择 |
| --- | --- |
| 现有同步脚本、团队已经统一 Requests、没有并发 I/O 需求？ | Requests |
| 调用链已经是 `async`、需要高并发等待外部服务或 HTTP/2？ | HTTPX |
| 想用一个包替代标准库但没有特殊需求？ | 先评估 `urllib`；需要更舒适的同步 API 时选 Requests |

两个包都不是重试策略、速率限制、凭据保管或接口契约的替代品；这些应由项目协议和运行环境明确管理。

## 4. 科学计算与表格数据：按数据形状选

### NumPy：同类型、多维、数值数组

适用场景：向量化计算、矩阵、张量式数值数据、线性代数和数值模拟。NumPy 的价值不是“比 `list` 更短”，而是有形状、dtype 和批量运算语义的 `ndarray`。

```bash
python -m pip install numpy
```

```python
import numpy as np

scores = np.array([78, 92, 85])
normalized = (scores - scores.mean()) / scores.std()
print(normalized.round(2))
```

使用前确认 `shape` 和 `dtype`，不要把广播结果当作当然正确。入门从[NumPy 文档与 Beginner's Guide](https://numpy.org/doc/stable/)开始。

### pandas：带列名、索引和缺失值的表格

适用场景：CSV/Excel/数据库查询结果、按列清洗、分组汇总、时间序列和连接。DataFrame 不适合替代所有 Python 数据结构；特别大的数据或流式计算需要评估内存与执行模型。

```bash
python -m pip install pandas
```

```python
import pandas as pd

orders = pd.read_csv("orders.csv")
summary = orders.groupby("region", dropna=False)["amount"].sum()
print(summary)
```

读数据后先检查 `dtypes`、行数、缺失值和主键重复；不要在不知道副作用时原地覆盖源文件。见[pandas 入门指南](https://pandas.pydata.org/docs/getting_started/index.html)。

### Matplotlib：可复现的静态图是第一选择

适用场景：报告、实验记录、需要随代码生成的折线图、散点图和柱状图。先让坐标轴、单位、标题和数据来源可读，再讨论配色与样式。

```bash
python -m pip install matplotlib
```

```python
import matplotlib.pyplot as plt

plt.plot([1, 2, 3], [2, 5, 4], marker="o")
plt.xlabel("day")
plt.ylabel("orders")
plt.tight_layout()
plt.savefig("orders.png", dpi=150)
```

在自动化环境中优先 `savefig` 产生可审查文件，而不是依赖图形窗口。见[Matplotlib Quick start](https://matplotlib.org/stable/users/explain/quick_start.html)。

### SciPy：在 NumPy 之上使用成熟科学算法

适用场景：优化、统计、信号处理、插值、稀疏矩阵和数值积分。先用 NumPy 表达数组数据，再从 SciPy 的明确子模块选算法；不要因“科学计算”而把 SciPy 当作任何问题的默认依赖。

```bash
python -m pip install scipy
```

```python
from scipy import stats

result = stats.ttest_1samp([4.9, 5.1, 5.0, 5.2], popmean=5.0)
print(result.statistic, result.pvalue)
```

统计检验的前提、样本设计和多重比较不能由一个函数调用替你判断。参见[SciPy 用户指南](https://docs.scipy.org/doc/scipy/tutorial/index.html)。

### Jupyter：探索、解释和共享运行过程

适用场景：数据探索、教学、可视化原型和可复现实验笔记。Notebook 是代码、输出和说明的容器；它不是自动可复现的保证，仍需“从上到下重跑”、记录依赖，并把可复用逻辑移入 `.py` 模块和测试。

```bash
python -m pip install jupyterlab
jupyter lab
```

在 notebook 中记录数据来源、随机种子和执行顺序；不要把密码、访问令牌或未脱敏数据保存进输出单元。见[Project Jupyter 文档](https://docs.jupyter.org/en/latest/)。

## 5. 工程质量：测试、验证、服务与数据库

### pytest：以行为为中心的测试

适用场景：绝大多数 Python 项目的单元测试、参数化测试和 fixture。测试应覆盖可观察行为和错误路径，不应只证明内部实现刚好按当前写法调用。

```bash
python -m pip install pytest
```

```python
def add_tax(price: float, rate: float) -> float:
    return price * (1 + rate)

def test_add_tax() -> None:
    assert add_tax(100, 0.13) == pytest.approx(113)
```

将测试放进 `tests/`，执行 `python -m pytest`。更多 fixture、参数化和断言说明见[pytest 文档](https://docs.pytest.org/en/stable/)。

### Pydantic：外部数据进入系统时的结构化验证

适用场景：读取 JSON、配置、消息或 API 输入时，将不可信或松散数据解析为有类型、可验证的模型。它不等于数据库约束，也不会自动保证业务规则完整。

```bash
python -m pip install pydantic
```

```python
from pydantic import BaseModel, Field

class CreateUser(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(ge=0)

user = CreateUser.model_validate({"name": "Ada", "age": "37"})
print(user.age)  # 37
```

Pydantic 可能进行类型转换；对边界敏感的字段要明确审查接受什么输入。参见[Pydantic 验证入门](https://docs.pydantic.dev/latest/concepts/models/)。

### FastAPI：有明确 HTTP 契约的 Web API

适用场景：构建 API 服务，且希望以类型标注和模型生成请求/响应校验与交互文档。FastAPI 解决 Web 层，不代替认证、授权、限流、数据库事务、部署或监控设计。

```bash
python -m pip install "fastapi[standard]"
```

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str

@app.post("/items")
def create_item(item: Item) -> Item:
    return item
```

保存为 `main.py` 后，按当前[FastAPI 教程](https://fastapi.tiangolo.com/tutorial/)启动开发服务。生产部署应遵守组织的 ASGI 服务器、反向代理、密钥与安全审查规范，而不是直接暴露开发命令。

### SQLAlchemy：数据库访问的建模与查询层

适用场景：关系数据库、需要控制连接、事务、SQL 表达式或 ORM 映射的应用。它不会让数据库模式设计、索引、并发冲突和备份问题消失；先理解目标数据库的事务语义。

```bash
python -m pip install sqlalchemy
```

```python
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///app.db")
with engine.begin() as connection:
    value = connection.execute(text("SELECT 1")).scalar_one()
print(value)
```

参数化查询、最小权限的数据库账户和迁移审核仍是必须项。由[SQLAlchemy Unified Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)开始；连接 PostgreSQL/MySQL 等数据库时还需按该数据库的驱动与部署文档选用额外依赖。

## 6. 终端体验与脚本入口：Rich、Typer

### Rich：让可读输出成为脚本界面的一部分

适用场景：进度、表格、结构化异常、颜色与格式能实质提升命令行可读性的开发者工具。日志和机器可读输出仍需提供稳定格式；不要把带颜色的终端文本当作 API。

```bash
python -m pip install rich
```

```python
from rich.console import Console
from rich.table import Table

table = Table(title="Tasks")
table.add_column("name")
table.add_row("backup")
Console().print(table)
```

参见[Rich 文档](https://rich.readthedocs.io/en/stable/)；CI 或重定向输出时要验证颜色、终端宽度和进度条的降级行为。

### Typer：从类型标注开始定义 CLI

适用场景：把一次性脚本发展为有帮助信息、参数校验和子命令的命令行工具。命令行参数是外部输入，类型提示不等于完整的业务安全校验。

```bash
python -m pip install typer
```

```python
import typer

def greet(name: str, loud: bool = False) -> None:
    message = f"Hello {name}"
    typer.echo(message.upper() if loud else message)

if __name__ == "__main__":
    typer.run(greet)
```

保存为 `greet.py`，可运行 `python greet.py --help` 或 `python greet.py Ada --loud`。阅读[Typer 文档](https://typer.tiangolo.com/)了解参数、命令组与测试；面向用户发布时还应设计退出码、错误信息和稳定的兼容性策略。

## 7. 一份克制的组合参考

不要从包名流行度反推架构。按任务从最小集合开始：

| 任务 | 合理的起点 | 先别加的东西 |
| --- | --- | --- |
| 读取一个 JSON 并写出摘要 | `json`、`pathlib`、`argparse` | DataFrame、Web 框架、数据库 ORM |
| 调一个同步 REST API | `requests` **或** `httpx` | 两个 HTTP 客户端同时引入 |
| 清洗一个中小 CSV 并画图 | `pandas`、`matplotlib` | 为没有数值算法的任务强加 SciPy |
| 数组模拟或算法原型 | `numpy`，需要专门算法时加 `scipy` | 直接把 notebook 当生产程序 |
| 有输入模型的 JSON API | `fastapi`、`pydantic`、`pytest` | 未设计认证/部署前的公开上线 |
| 本地关系数据与服务 | `sqlalchemy`、`pytest`，视边界加 `pydantic` | 把 ORM 当作备份、权限和迁移方案 |
| 开发者命令行工具 | `typer`，需要格式输出时加 `rich` | 把彩色终端输出当机器接口 |

每多加一个包，都问四个问题：标准库是否足够？它解决的是当前真实问题吗？谁负责升级和安全公告？它在干净环境、目标 Python 和目标操作系统上能安装并通过测试吗？

## 8. 练习：把一个 CSV 小脚本升级为可验证工具

> [!note] 开放式自评
> 这道练习有多种合理的函数划分和错误信息，不提供唯一成品。按下面的成功标准复核，再对照[[计算机知识/80-实践/01-Python/03-练习答案与解释#开放式自评的答案思路|开放式自评的答案思路]]检查测试边界、重建步骤和数据文件副作用。

你有一个 `orders.csv`，包含 `region` 和 `amount` 两列。请构建一个小工具：按地区汇总金额，输出一张图，并在数据缺列时给出清晰错误。

1. 创建项目环境，安装 `pandas`、`matplotlib` 和 `pytest`；更新项目的依赖声明与锁定产物。
2. 把读取与汇总逻辑写成函数，先检查列名，再调用 `groupby`。
3. 用 Matplotlib 将结果保存为 PNG；在图中加入标题与轴标签。
4. 为“正常 CSV”和“缺少 `amount` 列”各写一个 pytest 测试。
5. 删除环境后，从锁定文件重建，运行 `python -m pytest`，确认图能生成。

### 成功标准

- 你能说明为什么该任务需要 `pandas` 与 `matplotlib`，而不需要 FastAPI 或 SQLAlchemy；
- 网络需求出现时，你能按同步/异步边界在 Requests 和 HTTPX 中选一个；
- 每个第三方包都安装在项目环境，并已写入可审查的依赖与锁定流程；
- 测试同时覆盖正常输入与一个可预期的坏输入；
- 从空环境重建后，测试通过并生成带标签的图；
- 你没有把任何密钥、真实个人数据或 notebook 输出中的敏感内容提交到仓库。

## 跨域使用边界

- **数学**：NumPy、SciPy、pandas 与 Matplotlib 是把数组、统计和图形变成程序的工具；它们不替代对向量、概率、优化和数值误差的理解。先从 [[数学/00-数学-首页|数学首页]] 选择需要的学科入口，再回来决定数据结构和库。
- **AI**：模型训练、推理和数据处理会使用 Python 生态，但 GPU、模型权重、数据许可和实验可复现性是额外边界。需要完整工作流时进入 [[AI/00-开始/00-AI-首页|AI 首页]]，不要把“成功导入一个包”当成模型已能可靠运行的证据。
- **正则表达式**：对文本格式做局部提取或替换时，可在 Python 中使用 `re`；模式语义、性能和 ReDoS 风险属于 [[编程知识/10-基础/01-正则表达式/00-正则表达式-MOC|正则表达式课程]]。不要用一个越来越长的正则替代 JSON、CSV、HTML 或明确的数据模型解析器。

## 导航

- 上一课：[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|12：包管理器选择、锁定与迁移]]
- 后续实践：[[计算机知识/10-编程语言/01-Python/14-测试调试与代码质量|14：测试、调试与代码质量]]
- 返回：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/04-Python-课程地图|Python · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/01-Python/15-对象协议描述符闭包与类型边界|Python 深化：名字、对象、协议与类型边界]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
