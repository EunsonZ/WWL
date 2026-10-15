---
type: lesson
domain: computer-science
stage: 8
status: ready
difficulty: 入门
estimated_minutes: 55
verified: 2026-09-01
topics:
  - Python
  - pip
  - PyPI
  - 依赖管理
  - 虚拟环境
  - 供应链安全
tags:
  - computer-science/python
  - computer-science/dependency-management
---

# pip 与 PyPI 依赖管理

## 本课目标

学完本课，你应该能够：

- 区分 PyPI、package index、distribution package 与 import package；
- 解释 wheel、sdist，以及 pip 从解析需求到安装文件的大致过程；
- 正确使用版本说明符、requirements 文件、constraints 文件和 editable install；
- 用 `python -m pip` 把操作绑定到明确的 Python 解释器与虚拟环境；
- 判断 `pip check`、`list`、`show`、`freeze` 各自能证明什么、不能证明什么；
- 检查 pip 的缓存与配置来源，并识别哈希、索引混用、`sudo pip` 和 PEP 668 的安全边界。

适用场景：你已经能导入模块，准备为项目安装第三方库、保存依赖或排查“明明装了却 import 不到”。本课先讲 pip 本身；环境隔离会在[[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|下一课]]进一步拆解。

> [!important] 一句话心智模型
> PyPI 是默认的公共索引，pip 是安装器，wheel/sdist 是分发文件，虚拟环境是安装目标的隔离边界。它们彼此配合，但不是同一个东西。

## 1. PyPI 与 package index：pip 去哪里找候选文件

[PyPI（Python Package Index）](https://pypi.org/) 是 Python 生态最常用的公共软件索引。一个索引按**项目名**组织 release；一个 release 可以发布多个 distribution file，例如面向不同 Python、ABI、操作系统的 wheel，以及一个 sdist。

pip 默认通过 PyPI 的 Simple Repository API 查找候选，也可以被配置为使用其他索引或本地文件：

```bash
python -m pip install SomeProject
python -m pip install --index-url https://packages.example.invalid/simple SomeProject
python -m pip install --no-index --find-links ./wheelhouse SomeProject
```

这里后两个地址只是语法示例，不应直接执行。实际使用时先确认索引归属、HTTPS、认证方式和包名。

几个容易混淆的事实：

- `--index-url` 替换主索引；`--no-index` 禁用索引；`--find-links` 从给定页面或目录找归档文件；
- `--extra-index-url` 不是“私有索引永远优先”。pip 会把多个来源中的候选一起比较，不为来源设置优先级，然后选出满足条件的“最佳”候选；
- 因此把私有包与 PyPI 通过 `--extra-index-url` 混用会产生 **dependency confusion（依赖混淆）** 风险：攻击者可能在公共索引抢注同名、更高版本的包；
- 项目名比较会规范化大小写以及连字符、下划线等形式，但不要因此放松对拼写、维护者和来源的核对。

对私有依赖，更稳妥的起点是使用受控的单一 `--index-url` 或内部代理仓库，并设计好名称保留策略，而不是默认把公开与私有索引混成一个候选池。不要把访问令牌写进课程笔记、requirements 文件、共享的 pip 配置或会被保留的命令历史。

这里的 PyPI distribution 与 Linux 发行版软件包不是同一种交付边界：系统软件、共享库和系统 Python 应优先遵循发行版仓库、签名、事务与升级策略。横向比较见 [[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|pacman、apt、dnf 与 yum 包管理]]。

## 2. 安装名不一定等于导入名

Python 社区常把很多不同概念都叫“包”。至少要分清：

| 概念 | 出现在哪里 | 例子 |
| --- | --- | --- |
| distribution package / project | PyPI、`pip install`、依赖元数据 | `Pillow`、`sampleproject` |
| import package / module | Python 代码的 `import` 语句 | `PIL`、`sample` |
| distribution file | 下载和安装的归档文件 | `.whl`、`.tar.gz` |

二者同名只是惯例，不是索引强制规则：

```bash
python -m pip install Pillow
```

```python
from PIL import Image
```

同样，PyPA 的示例 distribution 名为 `sampleproject`，安装后导入的是 `sample`。所以看到 `import foo` 时，不要未经核对就执行 `pip install foo`：这可能装错项目，甚至落入拼写抢注或恶意包。先从项目官方文档、已安装元数据或可信源码确认 distribution 名：

```bash
python -m pip show sampleproject
python -c "import sample; print(sample.__file__)"
```

第一条查的是已安装 distribution 元数据；第二条查的是这个解释器最终导入的模块位置。两条信息互补，不能相互替代。模块发现与导入路径参见[[计算机知识/10-编程语言/01-Python/07-模块包导入与项目结构|模块、包、导入与项目结构]]。

## 3. wheel 与 sdist：同一 release 的两种交付形态

### wheel：面向安装的构建分发

wheel 文件以 `.whl` 结尾，本质上是带标准目录与元数据的 ZIP 归档。文件名中的 tag 描述它兼容的 Python、ABI 和平台，例如：

```text
sampleproject-4.0.0-py3-none-any.whl
```

`py3-none-any` 表示它面向 Python 3、不依赖特定 Python ABI、也不限定操作系统。包含本机扩展的 wheel 往往有更具体的 tag。pip 会根据当前解释器版本、实现、ABI、平台和 `Requires-Python` 等元数据过滤不兼容文件。

wheel 通常无需在目标机器重新编译，安装更快、结果更可预测。但“有 wheel”不等于“可信”或“已审计”：文件仍来自外部供应链，安装后的代码在导入或运行时仍能执行。

### sdist：源代码分发

sdist 通常是 `{name}-{version}.tar.gz`，包含项目源文件、`pyproject.toml` 和发布元数据。pip 找不到合适 wheel 而选择 sdist 时，通常会：

1. 建立隔离的构建环境；
2. 安装项目声明的构建依赖；
3. 调用构建后端把 sdist 构建成 wheel；
4. 再安装生成的 wheel。

这条路径可能需要编译器、系统头文件或外部库，也扩大了构建阶段执行代码和下载构建依赖的范围。`--only-binary :all:` 可以拒绝 sdist；代价是没有兼容 wheel 的项目会直接安装失败：

```bash
python -m pip install --only-binary=:all: SomeProject
```

选择原则不是“sdist 一定坏、wheel 一定好”，而是明确自己接受的构建与信任边界。生产部署若要求可重复和较小攻击面，通常会预先审阅、固定并保存适配目标平台的 wheel。

## 4. `pip install` 实际做了什么

pip 官方文档把一次安装概括为四个阶段：

1. **识别基础需求**：解析命令行、requirements、URL、本地目录或归档；
2. **解析依赖**：读取候选版本的元数据，为直接依赖与传递依赖寻找一组同时满足条件的版本；
3. **构建 wheel**：为可以构建、但没有现成兼容 wheel 的项目生成 wheel；
4. **安装**：把选定 distribution 安装到目标环境，并卸载被升级或替换的版本。

解析器会考虑项目名、版本、依赖、environment marker、extras、`Requires-Python`、wheel tag 与用户 constraints。它通常偏好满足条件的较新版本；遇到冲突时会**回溯**，尝试其他候选。因此日志里重复下载同一项目的多个版本不一定是故障，而可能是解析器正在回溯。

```text
输入需求
  → 从索引/本地来源发现候选
  → 按 Python、平台和版本规则过滤
  → 读取依赖元数据并回溯求解
  → 选择 wheel，或从 sdist 构建 wheel
  → 安装到这个 Python 的环境
```

几个重要边界：

- pip 求得的是“满足已知元数据的一组版本”，不是业务测试通过的证明；
- pip 依赖项目发布的元数据，无法替你发现未声明的系统库、运行时服务或隐含兼容问题；
- 安装顺序不是 requirements 文件的行顺序；不要用文件行顺序表达初始化依赖；
- `--dry-run` 只是不修改目标环境，仍可能访问网络、读取元数据或下载文件；
- 先解析成功再安装，也不等于包来源可信、代码安全或许可证符合要求。

## 5. 为什么优先写 `python -m pip`

机器上可能同时存在系统 Python、Homebrew Python、多个版本和多个虚拟环境。裸命令 `pip` 由 `PATH` 决定，可能并不属于你随后运行的 `python`。写成：

```bash
python -m pip --version
python -c "import sys; print(sys.executable)"
```

意思是“让这个 `python` 解释器加载并运行它能找到的 pip”。`pip --version` 输出还会显示 pip 所在路径和对应 Python 版本，便于验证两者是否一致。

Windows 的 Python Launcher 常用：

```powershell
py -m pip --version
py -3.13 -m pip --version
```

但当你已经知道虚拟环境路径时，最不含糊的写法是直接调用它的解释器，即使没有 activate 也能工作：

```bash
.venv/bin/python -m pip install SomeProject
```

```powershell
.venv\Scripts\python.exe -m pip install SomeProject
```

## 6. pip 与虚拟环境是什么关系

pip **不会因为项目目录存在就自动创建或选择虚拟环境**。它把包安装到“运行它的那个 Python 所属环境”的安装路径。`venv` 负责创建隔离的解释器环境，pip 负责向这个环境安装 distribution。

激活虚拟环境主要是把它的可执行目录放到 `PATH` 前面；激活不是隔离本身，也不是必需步骤。下面的显式路径不依赖当前 shell 是否激活：

```bash
python -m venv .venv
.venv/bin/python -m pip --version
.venv/bin/python -c "import sys; print(sys.prefix); print(sys.base_prefix)"
```

通常在虚拟环境中 `sys.prefix != sys.base_prefix`。同时要记住：

- 虚拟环境隔离已安装文件，但不自动固定版本、不校验哈希，也不审计代码；
- requirements 或锁定结果描述“装什么”，虚拟环境描述“装到哪里”；
- 删除或重建虚拟环境不会改变 requirements 文件，反之亦然；
- Conda 也能创建环境，并能管理 Python 以外的二进制依赖；不要在不理解所有权时让多个工具反复改同一套包。

环境原理见[[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|venv 与虚拟环境原理]]，Conda 的边界见[[计算机知识/10-编程语言/01-Python/10-Conda-Anaconda与Miniconda|Conda、Anaconda 与 Miniconda]]，uv 的项目工作流见[[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|uv 项目依赖与工具管理]]。

## 7. 版本说明符：表达允许集合，不是描述愿望

依赖字符串的主体是 distribution 名，可加 extras、版本说明符和 environment marker：

```text
requests[socks]>=2.32,<3; python_version >= "3.10"
```

常用说明符：

| 写法 | 大意 | 适合表达 |
| --- | --- | --- |
| `==1.4.2` | 只接受这一版本 | 已验证部署的精确 pin |
| `==1.4.*` | 接受 1.4 系列 | 兼容系列的前缀匹配 |
| `>=1.4,<2` | 区间交集 | 已知最低版本且尚未兼容 2.x |
| `~=1.4.2` | 约等于 `>=1.4.2,==1.4.*` | 允许同一 minor 的兼容更新 |
| `!=1.5.*` | 排除 1.5 系列 | 避开已知有问题的 release |

逗号表示“同时满足”。在 shell 里应给含 `<`、`>`、`!`、空格或 extras 的 specifier 加引号，避免它们被 shell 当作重定向、历史展开或 glob：

```bash
python -m pip install "SomeProject>=1.4,<2"
```

预发布版本通常不会被普通 specifier 自动选中；只有显式包含预发布版本、没有合适稳定版或使用相应选项时才会进入候选。不要为了“永远最新”只写没有上界的宽泛规则，也不要为了“绝不变化”盲目复制一份未经测试的 freeze：版本范围应来自兼容性承诺和实际测试。

## 8. requirements 与 constraints：一个决定装什么，一个只收窄候选

### requirements 文件

requirements 文件是 pip 的安装输入列表，逻辑上类似把多条 `pip install` 参数放进文件：

```text
# requirements.in
requests>=2.32,<3
pytest==8.4.*
```

```bash
python -m pip install -r requirements.in
```

它可以包含直接需求、URL、本地路径、editable 项目和部分 pip 选项。完整格式与 pip 内部选项紧密相关，不应假设所有工具都支持全部语法。pip 解析第三方项目的依赖时看项目发布元数据，而不是去找它仓库里恰好存在的 `requirements.txt`。

### constraints 文件

constraints 只限制“如果某个 distribution 被选中，允许用哪些版本”，它本身**不会让包进入安装集合**：

```text
# constraints.txt
urllib3<3
setuptools<81
```

```bash
python -m pip install -r requirements.in -c constraints.txt
```

如果依赖图没有用到 `setuptools`，仅在 constraints 中出现它不会导致安装。constraints 必须写项目名，不能包含 extras，也不能做 editable install。它适合组织级兼容上限、临时避开问题版本或收窄解析范围，不是 requirements 的替代品。

| 文件 | 是否触发安装 | 主要问题 |
| --- | --- | --- |
| requirements | 是 | “这次要安装哪些直接输入？” |
| constraints | 否 | “若解析到这个项目，允许哪些版本？” |
| lock / 带哈希的完整固定结果 | 视工具与格式而定 | “在指定目标上怎样重现已解析结果？” |

依赖锁定、跨平台结果和迁移策略会在[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]统一比较。

## 9. editable install：开发时让环境指向源码

在含有 `pyproject.toml` 的本地项目根目录，可以做普通安装：

```bash
python -m pip install .
```

也可以做 editable install：

```bash
python -m pip install -e .
```

editable 模式通常不把 Python 源文件复制进环境，而是让导入系统指向你的工作目录。因此修改纯 Python 源码后往往立即可见，适合本地开发。

它不是“完全不用重装”：修改项目版本、依赖、入口脚本等元数据后通常要重新执行安装；C/C++ 等非 Python 扩展仍可能需要重新构建。不同构建后端的 editable 行为也可能与普通 wheel 安装不同，所以 CI、发布前测试和部署应验证普通安装：

```bash
python -m pip install .
```

不要用已经废弃的 `python setup.py install` 或 `python setup.py develop` 代替现代构建接口。

## 10. 查看当前环境：四个命令、四种边界

| 命令 | 能回答 | 不能证明 |
| --- | --- | --- |
| `python -m pip list` | pip 在当前环境识别到哪些已安装 distribution；可列 outdated/editable | 为什么被安装、导入一定成功、运行时正确 |
| `python -m pip show NAME` | 某个已安装 distribution 的版本、位置、依赖等元数据 | 任意 import 名与 distribution 名的完整对应、文件可信 |
| `python -m pip check` | 已安装元数据声明的依赖是否缺失或版本冲突 | 重新求解、自动修复、源码兼容、系统库或安全漏洞 |
| `python -m pip freeze` | 把当前已安装状态输出为 requirements 风格文本 | 计算锁文件、区分直接/传递依赖、生成哈希、保证跨平台可复现 |

推荐的诊断顺序：

```bash
python -m pip --version
python -c "import sys; print(sys.executable)"
python -m pip show SomeProject
python -m pip check
python -m pip list
```

`pip freeze` 是**观察到的环境快照**，不是解析器的锁定结果。它可能包含临时安装、传递依赖和与当前平台绑定的版本；默认还可能省略部分 bootstrap packaging tools。若确实需要完整盘点，可阅读当前 pip 版本的 `freeze --help` 和 `--all` 行为，但不要把输出不经审阅就当成长期依赖设计。

## 11. 缓存与配置：先检查来源，再怀疑网络

pip 默认缓存 HTTP 响应和本机构建的 wheel，以减少重复下载与构建。缓存是性能机制，不是锁文件、离线镜像或信任根：过期响应仍可能触发网络请求，缓存内容也不会替你判断包是否恶意。

以下命令只读取信息，适合排查：

```bash
python -m pip cache dir
python -m pip cache info
python -m pip cache list
python -m pip config debug
python -m pip config list
```

缓存内部目录结构是实现细节，不要自己依赖其文件布局。通常也不应习惯性加 `--no-cache-dir`：它会增加下载与重复构建；只有上层已有缓存或正在定位确定的缓存问题时才考虑。

pip 配置可来自 global、user、当前环境 site 配置和 `PIP_CONFIG_FILE`，后加载的文件覆盖先前文件。总体优先级是：

```text
命令行选项 > PIP_* 环境变量 > 配置文件
```

`pip config debug` 能显示实际读取的配置位置，是排查“为什么偷偷换了索引/代理”的第一步。输出也可能暴露带凭据的索引 URL；不要把未经脱敏的结果贴到 issue、聊天或日志。修改或清空缓存、配置之前先记录精确来源和影响范围，本课不使用 `cache purge` 或全局 `config set`。

## 12. 供应链与权限安全

### 安装外部包就是接受外部代码

pip 官方安全指南明确指出，默认安装过程涉及来自 distribution 的任意代码。风险不仅是下载被篡改，还包括：名字拼错、维护者账号被接管、恶意新版本、被替换的构建依赖、sdist 构建代码和不可信私有索引。

最低限度的检查包括：

1. 从项目官方文档确认 distribution 名，不根据一条陌生 `import` 猜包名；
2. 核对索引、项目主页、维护者、源码仓库、目标版本和发行文件；
3. 在隔离环境安装，先用 `--dry-run` 看候选，再运行测试与 `pip check`；
4. 自动部署使用完整 pin、经审阅的 SHA-256 哈希，并保存生成过程；
5. 能接受只用 wheel 时加 `--only-binary=:all:`，让缺少 wheel 的项目明确失败；
6. 私有依赖避免把公开 PyPI 作为无优先级的额外候选池。

### 哈希能证明完整性，不能证明善意

hash-checking mode 的典型 requirements 行：

```text
sampleproject==4.0.0 \
    --hash=sha256:c23e447ea90d796d1e645c35c4b2de125040add12a845825546f91c93f391b6b
peppercorn==0.6 \
    --hash=sha256:46125cad688a9cf3b08e463bcb797891ee73ece93602a8ea6f14e40d1042d454
```

```bash
python -m pip install --require-hashes --only-binary=:all: -r requirements-hashed.txt
```

在 `--require-hashes` 模式下，每个直接与传递依赖都必须固定并提供允许的哈希；多平台允许多个 wheel 时，通常要为每个允许文件记录哈希。以上是未启用 extras 时的完整示例：`sampleproject` 4.0.0 还依赖 `peppercorn`，后者同样必须固定版本并提供哈希。两个 SHA-256 对应各自的通用 Python wheel，分别依据 [sampleproject 4.0.0 官方元数据](https://pypi.org/pypi/sampleproject/4.0.0/json) 与 [peppercorn 0.6 官方元数据](https://pypi.org/pypi/peppercorn/0.6/json) 于 2026-09-06 复核。本轮核对了元数据与锁定清单，未在联网环境重新执行安装；示例要求 Python 3.9+，还需满足本机 pip、网络与索引配置条件。

哈希能证明“下载字节与预先审阅并记录的字节一致”，不能证明这些字节没有恶意代码、没有漏洞、许可证合规或适合你的平台。若哈希与文件都来自同一个已被攻破的远端，信任仍可能一起失效；关键在于哈希清单的生成、审阅与保存链条。

### 不要 `sudo pip install`

不要用下面的方式解决权限报错：

```text
sudo python -m pip install SomeProject
```

root 权限会放大覆盖系统文件、破坏操作系统包管理器记录和执行不可信构建代码的后果。优先创建项目虚拟环境；系统级软件优先使用操作系统/发行版包管理器；命令行应用可考虑由隔离环境管理的专用工具。`--user` 也不是所有系统 Python 的通用修复，因为用户 site 仍可能遮蔽系统包，并且 PEP 668 环境通常仍会阻止这种修改。

### PEP 668：`EXTERNALLY-MANAGED` 不是故障

Linux 发行版、Homebrew 或应用内置 Python 可能放置 `EXTERNALLY-MANAGED` 标记，告诉 pip：这个基础解释器由外部包管理器负责。在虚拟环境外且标记存在时，pip 应拒绝修改默认环境，并引导用户使用虚拟环境或发行版方案。

这里的“外部包管理器”管理的是系统软件包及其文件所有权，不是另一种 pip。发行版层的仓库、签名和事务模型见 [[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|pacman、apt、dnf 与 yum 包管理]]。

看到这类报错时：

1. 阅读发行版给出的原始提示；
2. 为项目运行 `python -m venv .venv`，再用 `.venv` 中的 Python 调 pip；
3. 若需求确实属于系统软件，使用该发行版的包管理器；
4. 不删除标记文件，不把 `--break-system-packages` 设成全局默认，也不要用 `sudo` 绕过保护。

`--break-system-packages` 的名字就是风险说明：它是特殊、受控场景的显式越权开关，不是入门安装命令。虚拟环境之所以能正常安装，是因为 PEP 668 的判断同时检查当前是否位于虚拟环境。

## 13. 练习：在隔离环境验证完整安装链

练习使用 PyPA 维护的 `sampleproject==4.0.0`。它要求 Python 3.9 或更高，官方 release 同时提供 sdist 与 `py3-none-any` wheel，且 distribution 名 `sampleproject`、import 名 `sample` 不同。

### 第一步：创建并确认隔离目标

macOS / Linux：

```bash
python3 -m venv pip-lab/.venv
pip-lab/.venv/bin/python -m pip --version
pip-lab/.venv/bin/python -c "import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix)"
```

Windows PowerShell：

```powershell
py -m venv pip-lab\.venv
pip-lab\.venv\Scripts\python.exe -m pip --version
pip-lab\.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix)"
```

先确认输出路径确实位于 `pip-lab/.venv`，并且 `sys.prefix != sys.base_prefix`。若不是，停止安装并检查命令路径。

> [!important] 后续命令的 Windows 统一替换规则
> 第 2、3、4 步和“恢复”中的命令以 macOS / Linux 路径展示。Windows PowerShell 请把每一处命令开头的 `pip-lab/.venv/bin/python` 替换为 `pip-lab\.venv\Scripts\python.exe`；若输入 requirements 路径，也可写成 `pip-lab\requirements-hashed.txt`。除此之外，`-m pip` 及其参数保持不变。这个规则适用于下面所有命令，不只适用于安装步骤。

### 第二步：只解析，不修改环境

macOS / Linux：

```bash
pip-lab/.venv/bin/python -m pip install --dry-run --only-binary=:all: "sampleproject==4.0.0"
```

`--dry-run` 不安装，但可能访问 PyPI、下载文件或更新缓存。观察 pip 选择的文件名，确认它以 `.whl` 结尾。

### 第三步：用固定版本与本地哈希安装

在 `pip-lab` 中新建 `requirements-hashed.txt`，内容为：

```text
sampleproject==4.0.0 \
    --hash=sha256:c23e447ea90d796d1e645c35c4b2de125040add12a845825546f91c93f391b6b
peppercorn==0.6 \
    --hash=sha256:46125cad688a9cf3b08e463bcb797891ee73ece93602a8ea6f14e40d1042d454
```

执行：

```bash
pip-lab/.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r pip-lab/requirements-hashed.txt
```

Windows 按上面的统一规则替换解释器和 requirements 路径，其余参数相同。

### 第四步：从多个角度验证

```bash
pip-lab/.venv/bin/python -m pip show sampleproject
pip-lab/.venv/bin/python -c "import sample; print(sample.__file__)"
pip-lab/.venv/bin/python -m pip list
pip-lab/.venv/bin/python -m pip check
pip-lab/.venv/bin/python -m pip freeze
pip-lab/.venv/bin/python -m pip cache dir
pip-lab/.venv/bin/python -m pip config debug
```

请用自己的话回答：

1. 哪条输出证明了 distribution 已安装？哪条证明了 import 实际成功？
2. wheel 文件名的三个 tag 是什么？
3. 为什么哈希匹配仍不能证明代码安全？
4. `pip check` 成功为什么仍不能证明程序业务正确？
5. `pip freeze` 为什么不是锁文件？

> [!warning] 不要泄露配置
> `pip config debug` 的输出可能带有内部索引或凭据相关信息。只在本机查看，不要把未脱敏输出粘贴到笔记、issue 或聊天。

### 恢复

先再次确认解释器路径位于 `pip-lab/.venv`，再卸载练习包：

```bash
pip-lab/.venv/bin/python -m pip uninstall sampleproject
```

需要完全重置时，关闭使用该环境的终端或编辑器，在文件管理器中核对精确路径后把整个 `pip-lab` 目录移到废纸篓。不要用 `sudo`，也不要删除系统 Python 的目录、PEP 668 标记或全局 pip 配置。

## 常见坑

| 现象 | 根因 | 更稳妥的做法 |
| --- | --- | --- |
| `pip install` 成功，运行时仍 `ModuleNotFoundError` | pip 与运行程序的 Python 不是同一个解释器，或安装名不等于 import 名 | 比对 `sys.executable`、`pip --version`，查官方导入名 |
| requirements 每行都写了，却认为会按顺序安装 | 文件是需求集合，不是安装脚本 | 用项目元数据表达依赖，不依赖行顺序 |
| constraints 中写了包却没有安装 | constraints 只收窄候选，不触发安装 | 把直接需求写入 requirements |
| sdist 在一台机器成功、另一台失败 | 构建工具链、系统头文件或平台不同 | 优先适配 wheel，或固定并复现构建环境 |
| `pip freeze` 在 CI 仍无法跨平台复现 | freeze 是当前环境快照，没有哈希和跨平台求解语义 | 使用经测试的锁定流程或分平台产物 |
| `pip check` 为 0 但程序崩溃 | 它只检查已安装依赖元数据 | 继续做 import、单元测试与集成测试 |
| 私有包被公共同名包替代 | `--extra-index-url` 候选没有来源优先级 | 使用受控单一索引/代理与名称保留策略 |
| 权限报错后用 `sudo pip` | 把第三方安装写入系统环境 | 使用虚拟环境或发行版包管理器 |
| `externally-managed-environment` | 基础 Python 由外部包管理器维护 | 按提示建 venv，不默认使用破坏保护的开关 |
| 清缓存后问题短暂消失又回来 | 缓存不是依赖或来源配置本身 | 先查 `cache info`、`config debug` 与索引来源 |

## 成功标准

- [ ] 能画出“索引 → release → wheel/sdist → pip → 某个 Python 环境”的链条；
- [ ] 能举例说明 distribution 名与 import 名不必相同；
- [ ] 能解释 pip 的识别、解析、构建 wheel、安装四个阶段及回溯现象；
- [ ] 能写出至少三种版本说明符，并解释 requirements 与 constraints 的语义差异；
- [ ] 能用明确的虚拟环境解释器执行 `python -m pip`，不依赖裸 `pip` 的 `PATH` 猜测；
- [ ] 能准确陈述 `check`、`list`、`show`、`freeze` 的证明边界；
- [ ] 能检查 cache/config 来源，并说明缓存不是离线镜像或信任根；
- [ ] 能用固定版本、SHA-256 哈希和 `--only-binary` 完成隔离练习；
- [ ] 遇到 PEP 668 报错时会创建 venv，而不是使用 `sudo`、删除标记或默认开启 `--break-system-packages`。

## 导航

- 上一篇：[[计算机知识/10-编程语言/01-Python/07-模块包导入与项目结构|模块、包、导入与项目结构]]
- 返回 MOC：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础 MOC]]
- 下一篇：[[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|venv 与虚拟环境原理]]
- 横向比较：[[计算机知识/10-编程语言/01-Python/10-Conda-Anaconda与Miniconda|Conda、Anaconda 与 Miniconda]] · [[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|uv 项目依赖与工具管理]] · [[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]

## 一手参考

以下内容仅依据 pip、PyPA / PyPI 与 Python 官方资料核对，核对日期为 2026-09-01：

- [pip User Guide：运行 pip、requirements 与 constraints](https://pip.pypa.io/en/stable/user_guide/)
- [`pip install`：安装阶段、候选来源与选项](https://pip.pypa.io/en/stable/cli/pip_install/)
- [pip：Dependency Resolution](https://pip.pypa.io/en/stable/topics/dependency-resolution/)
- [pip：Local project installs 与 editable](https://pip.pypa.io/en/stable/topics/local-project-installs/)
- [pip：Secure installs 与 hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/)
- [pip：Caching](https://pip.pypa.io/en/stable/topics/caching/)
- [pip：Configuration](https://pip.pypa.io/en/stable/topics/configuration/)
- [pip 命令参考：`list`、`show`、`freeze`、`check`](https://pip.pypa.io/en/stable/cli/)
- [PyPA：Distribution package vs. import package](https://packaging.python.org/en/latest/discussions/distribution-package-vs-import-package/)
- [PyPA：Package Formats](https://packaging.python.org/en/latest/discussions/package-formats/)
- [PyPA：Version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)
- [PyPA：Externally Managed Environments](https://packaging.python.org/en/latest/specifications/externally-managed-environments/)
- [Python PEP 668：Marking Python base environments as externally managed](https://peps.python.org/pep-0668/)
- [Python 标准库：`venv`](https://docs.python.org/3/library/venv.html)
- [PyPI：PyPA `sampleproject` 4.0.0 的 wheel、sdist 与 SHA-256](https://pypi.org/project/sampleproject/4.0.0/)


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/04-Python-课程地图|Python · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/01-Python/16-异步并发取消性能与可靠工程|Python 深化：异步并发、取消与可靠工程]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
