---
type: lesson
domain: computer-science
stage: 9
status: ready
difficulty: 入门
estimated_minutes: 35
topics:
  - python
  - venv
  - virtual-environment
  - dependency-isolation
tags:
  - computer-science/python
  - computer-science/virtual-environment
---

# venv 与虚拟环境原理

> [!abstract] 本课目标
> 学完后，你能解释虚拟环境隔离了什么、`sys.prefix` 和 `site-packages` 如何参与隔离、为什么“激活”不是必需步骤，并能安全地创建、诊断、停用、删除和重建一个 `.venv`。

## 1. 为什么每个项目都应该有自己的环境

假设两个项目依赖同一个库的不同版本：

- 项目 A 只能使用 `examplelib 1.x`；
- 项目 B 已经升级到 `examplelib 2.x`；
- 操作系统或其他工具还可能依赖它自己的 Python 包。

如果所有包都安装到同一个 Python 中，升级 B 可能破坏 A，项目安装也可能污染系统 Python。虚拟环境为每个项目提供独立的第三方包安装位置，让它们可以同时存在。

隔离能解决的是“这个 Python 看见并安装到哪一组包”的问题。它不会自动完成下面这些事：

- 不会替你声明项目依赖；
- 不会自动锁定每个依赖的精确版本；
- 不会让不可信的包变安全；
- 不是容器，也不隔离文件、网络、进程权限或操作系统。

因此，虚拟环境是依赖管理的基础边界，不是完整的安全沙箱。若要理解“包路径隔离”与 Linux 从内核层改变进程所见目录树的差别，可对照 [[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统#5. 挂载与 mount namespace：谁看到哪棵树|mount namespace]]；两者都可能被简称为“隔离”，实现和安全性质却完全不同。

## 2. `.venv` 里面有什么

用标准库 `venv` 创建的环境通常包含：

```text
.venv/
├── pyvenv.cfg
├── bin/                 # POSIX：python、pip、activate 等
│   └── python
├── Scripts/             # Windows：python.exe、pip.exe、Activate.ps1 等
│   └── python.exe
└── lib/.../site-packages/  # 第三方包；Windows 通常是 Lib/site-packages
```

实际环境只会出现 `bin/` 或 `Scripts/` 中与当前平台对应的一种布局。环境中的 Python 可执行文件可能是复制，也可能是指向基础 Python 的符号链接；`pyvenv.cfg` 记录基础解释器等信息。

> [!note] 不是完整复制一套 Python
> `venv` 环境拥有自己的解释器入口和独立的 `site-packages`，但通常仍与创建它的基础 Python 共享标准库。因此它轻量，却也依赖基础 Python 和原来的路径，不能当作可随意搬运的成品目录。

### `sys.prefix`：运行时真正认哪一个环境

下面的命令会同时打印当前解释器、环境前缀和基础前缀：

```bash
python -c "import sys; print('executable =', sys.executable); print('prefix =', sys.prefix); print('base_prefix =', sys.base_prefix); print('in_venv =', sys.prefix != sys.base_prefix)"
```

- `sys.executable`：当前真正运行的 Python 可执行文件；
- `sys.prefix`：当前环境的前缀；
- `sys.base_prefix`：创建该环境的基础 Python 前缀；
- `sys.prefix != sys.base_prefix`：标准且可靠的“当前是否运行在虚拟环境中”判断。

某些平台还会用到 `sys.exec_prefix` 和 `sys.base_exec_prefix`，判断方式相同。不要只看终端提示符中的 `(.venv)`，也不要只靠 `VIRTUAL_ENV`：激活是可选的，而程序实际由哪个解释器运行才是事实。

### `site-packages`：第三方包落在哪里

Python 启动时会建立模块搜索路径，并通过 `site` 机制加入环境自己的 `site-packages`。可以直接观察：

```bash
python -c "import site, sys; print('python =', sys.executable); print('site-packages ='); print(*site.getsitepackages(), sep='\n- ')"
python -m pip --version
```

第二条命令不仅显示 pip 版本，还会显示它所属的路径。路径应落在预期的 `.venv` 中。使用 `python -m pip` 的好处是：先明确选择 Python，再让这个 Python 运行对应的 pip，减少“`pip` 和 `python` 来自两个环境”的误装。

## 3. 激活只是 `PATH` 的便利层

激活脚本的核心工作，是把环境的可执行文件目录放到当前 shell 的 `PATH` 前面。于是输入短命令 `python`、`pip` 或环境中安装的命令时，shell 会优先找到 `.venv` 中的版本。

```text
激活前：PATH → 系统或用户 Python
激活后：PATH → .venv/bin（或 .venv\Scripts）→ 其余路径
```

激活不会“打开”一个常驻虚拟机，也不会修改项目源码。它只影响当前 shell 会话；关闭终端后效果自然消失。

这个过程本质上是 shell 环境变量和命令查找顺序的变化。如果对“子进程会继承哪些变量”、“为什么只影响当前终端”或 `PATH` 的先后顺序还不清楚，先阅读 [[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|环境变量、Shell 启动与 PATH]]。

更重要的是：**不激活也能使用虚拟环境。** 直接调用环境中的解释器即可。

POSIX（macOS / Linux）：

```bash
.venv/bin/python -c "import sys; print(sys.executable)"
.venv/bin/python -m pip --version
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pip --version
```

Windows `cmd.exe`：

```bat
.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.venv\Scripts\python.exe -m pip --version
```

这种显式写法尤其适合自动化脚本、编辑器任务和排错，因为它不依赖调用者是否记得激活。

## 4. 从创建到停用

以下命令都应在项目根目录执行，并约定环境名为 `.venv`。

### 4.1 创建

| 平台 | 命令 |
| --- | --- |
| macOS / Linux | `python3 -m venv .venv` |
| Windows（Python Launcher） | `py -m venv .venv` |

`venv` 使用“执行创建命令的那个 Python”作为基础 Python。若项目要求特定版本，先检查创建者：

```bash
python3 --version       # macOS / Linux
py --list               # Windows：查看 Launcher 能找到的版本
```

Windows 也可以用例如 `py -3.12 -m venv .venv` 明确指定已经安装的 Python 3.12。

### 4.2 激活

| 平台 / shell | 命令 |
| --- | --- |
| macOS / Linux，bash 或 zsh | `source .venv/bin/activate` |
| macOS / Linux，fish | `source .venv/bin/activate.fish` |
| Windows，PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Windows，`cmd.exe` | `.venv\Scripts\activate.bat` |

> [!tip] PowerShell 执行策略报错怎么办
> 这通常是 PowerShell 的脚本执行策略在阻止 `Activate.ps1`，并不表示环境损坏。不要为了激活而盲目降低整台机器的安全策略；可以直接运行 `.\.venv\Scripts\python.exe`，或在理解组织策略后仅按需要调整当前用户范围。

### 4.3 验证

POSIX：

```bash
command -v python
python -c "import sys; print(sys.executable); print(sys.prefix != sys.base_prefix)"
python -m pip --version
```

Windows：

```powershell
where.exe python
python -c "import sys; print(sys.executable); print(sys.prefix != sys.base_prefix)"
python -m pip --version
```

不要只以终端出现 `(.venv)` 为成功标准。至少确认解释器路径包含项目的 `.venv`，并且比较结果为 `True`。

### 4.4 停用

```bash
deactivate
```

这会撤销当前 shell 中由激活脚本做的便利设置，不会删除环境或卸载包。关闭当前终端也相当于离开激活状态。

## 5. 删除与重建：把环境当作可再生物

虚拟环境中的脚本可能记录解释器的绝对路径，环境又依赖创建它的基础 Python。因此：

- 不要把 `.venv` 移到另一个目录；
- 不要复制给同事或另一台机器；
- 不要压缩后当作跨平台交付物；
- 不要提交到 Git。

项目移动、Python 升级、环境损坏或依赖严重漂移时，稳妥做法是“保存依赖描述 → 删除环境 → 原地重建”。

### 安全删除检查

1. 先运行 `deactivate`（若尚未激活，提示命令不存在也不代表有故障）。
2. 确认当前目录是预期项目根目录。
3. 确认 `.venv/pyvenv.cfg` 存在。
4. 只删除精确的 `.venv` 目录，不使用变量、通配符或上级目录。

POSIX：

```bash
if [ -d .venv ] && [ ! -L .venv ] && [ -f .venv/pyvenv.cfg ]; then
  if rm -rf -- .venv && [ ! -e .venv ]; then
    python3 -m venv .venv
  else
    printf '%s\n' '删除未完成：停止，不在残留目录上重建。' >&2
  fi
else
  printf '%s\n' '拒绝删除：.venv 必须是非符号链接目录，且包含 pyvenv.cfg。' >&2
fi
```

Windows PowerShell：

```powershell
$venvPath = Join-Path (Get-Location) '.venv'
$venvItem = Get-Item -Force -LiteralPath $venvPath -ErrorAction Stop
$isReparsePoint = [bool]($venvItem.Attributes -band [IO.FileAttributes]::ReparsePoint)

if ($venvItem.PSIsContainer -and -not $isReparsePoint -and
    (Test-Path -LiteralPath (Join-Path $venvPath 'pyvenv.cfg') -PathType Leaf)) {
  Remove-Item -LiteralPath $venvPath -Recurse -Force -ErrorAction Stop
  if (Test-Path -LiteralPath $venvPath) {
    throw '删除未完成：停止，不在残留目录上重建。'
  }
  py -m venv $venvPath
  if ($LASTEXITCODE -ne 0) { throw 'venv 重建失败。' }
} else {
  throw '.venv 必须是非重解析点目录，且包含 pyvenv.cfg。'
}
```

删除前先人工确认检查结果；`rm -rf` 和 `Remove-Item -Recurse` 都不可撤销。环境本身可重建，但其中未记录的临时安装状态会丢失。

### 恢复依赖

如果项目使用 requirements 文件：

```bash
# 激活后，POSIX 与 Windows 都可以使用这组 Python 命令
python -m pip install -r requirements.txt
```

如果项目本身由 `pyproject.toml` 描述：

```bash
python -m pip install .
# 开发项目常用：python -m pip install -e .
```

若项目使用 uv、Conda 或其他带锁定能力的工作流，应使用该工具和它的锁定文件恢复，而不是把旧环境搬回来。

## 6. `.gitignore`：提交“配方”，不提交“厨房”

项目的 `.gitignore` 至少应包含：

```gitignore
.venv/
```

Python 3.13 起，标准库 `venv` 默认还会在环境目录内部生成一个让 Git 忽略整个环境的 `.gitignore`（可用 `--without-scm-ignore-files` 关闭）。项目根目录继续明确写 `.venv/` 仍然有价值：意图一目了然，也兼容较旧的 Python 和其他环境创建工具。

应该进入版本控制的是用于重建的资料，例如：

- 源代码与测试；
- `pyproject.toml`；
- 团队选定的 requirements 或锁定文件；
- 支持的 Python 版本说明；
- 必要的构建和运行文档。

不应提交 `.venv/`，因为它体积大、包含平台相关文件和绝对路径，而且会制造没有意义的二进制差异。PyPA 和 Python 官方文档都明确建议虚拟环境不进入源码版本控制。

## 7. venv、pip 与 `pyproject.toml` 各管什么

| 部件 | 回答的问题 | 不负责什么 |
| --- | --- | --- |
| `venv` | 包安装到哪一个隔离环境？ | 不解析项目依赖，不锁定版本 |
| `pip` | 把哪些分发包装进当前解释器的环境？ | 不创建完整项目工作流，不天然保证跨机器完全复现 |
| `pyproject.toml` | 这个项目如何构建、有哪些元数据和声明依赖？ | 它是描述文件，本身不是已安装的环境 |
| requirements / constraints | 声明要安装的依赖、版本范围或对求解的附加约束 | 不必然包含全部传递依赖的精确版本，也不提供解释器隔离 |
| 精确锁定文件 | 记录团队已解析并批准的直接与传递依赖，用于可审查地重建 | 不是 `.venv/` 的拷贝，也不提供解释器隔离 |

一个常见流程是：

```text
选择 Python → venv 创建隔离环境 → pip 读取项目或依赖文件并安装 → 用测试验证
```

除非创建时使用 `--without-pip`，`venv` 会通过标准库 `ensurepip` 在新环境中引导安装 pip；这只是准备好安装工具，并不表示项目依赖已经安装。

`pyproject.toml` 可以声明项目及其依赖，但标准文件与不同工具的锁定能力要区分看待。是否需要 requirements、lock 文件或平台矩阵，取决于项目类型与所选工具。接下来可在 [[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]] 中做选择。

## 8. 环境诊断清单

遇到“明明装了却无法导入”时，不要先反复重装。依次确认：

```bash
python -c "import sys; print(sys.executable); print(sys.version); print(sys.prefix); print(sys.base_prefix)"
python -m pip --version
python -m pip list
python -c "import site; print(*site.getsitepackages(), sep='\n')"
```

再回答四个问题：

1. 当前 `python` 的绝对路径是什么？
2. `python -m pip --version` 指向同一个环境吗？
3. `sys.prefix != sys.base_prefix` 是否符合预期？
4. 目标包是否真的出现在这个环境的 `site-packages` 中？

如果 `VIRTUAL_ENV` 已设置而 `sys.executable` 却不在该目录，说明 shell 的激活状态或 `PATH` 可能混乱。此时先 `deactivate` 或开启新终端，再用 `.venv/bin/python` / `.\.venv\Scripts\python.exe`（PowerShell）显式调用，通常比继续猜测更可靠。

> [!warning] 安装第三方包仍需做来源判断
> 虚拟环境只能减少包之间的相互污染，不能限制恶意安装脚本或运行时代码。安装前核对包名、来源和版本；不要把未知来源的安装命令交给高权限 shell，也不要为了绕过系统保护而随意使用 `sudo pip install`。

## 9. 练习：不用提示符证明环境真的隔离

在一个无重要数据的练习目录中完成：

1. 创建 `.venv`，但先不要激活。
2. 直接用环境中的 Python 打印 `sys.executable`、`sys.prefix` 和 `sys.base_prefix`。
3. 用环境中的 `python -m pip --version` 找出 `site-packages` 所在位置。
4. 激活环境，再运行同样的诊断命令并对比结果。
5. 执行 `deactivate`，确认普通 `python` 的路径恢复。
6. 确认 `.gitignore` 包含 `.venv/`。
7. 在确认练习目录和 `pyvenv.cfg` 后删除 `.venv`，然后重建一次。

为了避免不必要的网络和供应链风险，本练习不要求安装任何第三方包。

### 成功标准

- [ ] 不依赖 `(.venv)` 提示符，也能用 `sys.executable` 说出当前解释器；
- [ ] 能说明 `sys.prefix != sys.base_prefix` 为什么表示正在使用虚拟环境；
- [ ] 能指出当前环境的 `site-packages` 路径；
- [ ] 未激活时，能用完整路径运行环境中的 Python 和 pip；
- [ ] 停用后环境目录仍存在，删除后则能根据依赖资料重建；
- [ ] `.venv/` 不会进入 Git。

## 10. 恢复与安全边界

- **激活错了环境**：先 `deactivate` 或关闭终端，再显式调用目标环境的解释器。
- **包安装错了位置**：用对应解释器的 `python -m pip uninstall 包名` 处理；先确认路径，不要删除系统 Python 的文件。
- **环境无法修复**：保留源码和依赖描述，确认精确路径后删除 `.venv` 并重建。
- **误删 `.venv`**：通常无需恢复目录本身；依据 `pyproject.toml`、requirements 或锁定文件重建。未记录的临时安装只能重新确认。
- **不要做的事**：不要搬运环境、提交环境、在环境目录中保存源码或唯一数据，也不要把虚拟环境当安全沙箱。

## 11. 继续学习

- 上一站：[[计算机知识/10-编程语言/01-Python/08-pip与PyPI依赖管理|pip 与 PyPI 依赖管理]]
- 下一站：[[计算机知识/10-编程语言/01-Python/10-Conda-Anaconda与Miniconda|Conda、Anaconda 与 Miniconda]]
- 更快的项目工作流：[[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|uv 项目依赖与工具管理]]
- 工具选择：[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]
- 返回：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础 MOC]]

## 官方资料

- [Python 标准库：`venv` — Creation of virtual environments](https://docs.python.org/3/library/venv.html)
- [Python Packaging User Guide：Python Virtual Environments](https://packaging.python.org/en/latest/specifications/virtual-environments/)
- [Python Packaging User Guide：Install packages in a virtual environment using pip and venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
- [Python Packaging User Guide：Writing your `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

> [!info] 核对说明
> 本页关于隔离边界、`sys.prefix` / `sys.base_prefix`、`site-packages`、激活可选性、平台命令、不可搬运性和版本控制的表述，依据以上 Python 与 PyPA 官方资料核对（2026-09-01）。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/04-Python-课程地图|Python · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/01-Python/16-异步并发取消性能与可靠工程|Python 深化：异步并发、取消与可靠工程]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
