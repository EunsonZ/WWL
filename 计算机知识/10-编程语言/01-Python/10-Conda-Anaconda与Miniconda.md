---
type: lesson
domain: computer-science
stage: 10
status: ready
difficulty: 入门
estimated_minutes: 45
topics:
  - Python
  - conda
  - Anaconda Distribution
  - Miniconda
  - 包管理
  - 环境管理
tags:
  - computer-science/python
  - computer-science/dependency-management
---

# Conda、Anaconda 与 Miniconda

## 本课目标

学完本课，你应该能够：

- 准确区分 `conda`、Anaconda Distribution 和 Miniconda，不再把三者当作同一个东西；
- 解释 channel、solver、`base` 环境、项目环境、`environment.yml` 和锁文件各自解决什么问题；
- 安全地创建、激活、检查、更新、导出和删除 conda 环境；
- 在必须混用 `pip` 时控制顺序和边界，并知道何时应重建环境；
- 在安装或接入 channel 前核对下载校验值、软件来源和当时有效的条款。

适用场景：数据科学、科学计算、GPU/CUDA 或其他同时涉及 Python 包与非 Python 二进制依赖的项目。如果项目只需要 PyPI 上的纯 Python 依赖，先回顾 [[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|venv 与虚拟环境原理]]，再对比 [[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|uv 项目依赖与工具管理]]。

> [!note] 核对边界
> 本页中会随版本变化的事实已于 2026-09-01 对照 Conda/Anaconda 官方文档。你实际操作时仍应先运行 `conda --version` 和相应命令的 `--help`；许可、商业条款与仓库访问政策必须以当时官方页面为准。

## 1. 先把三个名字分开

| 名称 | 它是什么 | 它不是什么 | 适合什么人 |
| --- | --- | --- | --- |
| `conda` | 跨平台的包管理器和环境管理器；能管理 Python、R 以及编译库、命令行工具等非 Python 依赖 | 不是 Anaconda Distribution 的简称，也不是只管 Python 包的 `pip` | 需要同时解决语言包、系统库和二进制兼容性的用户 |
| Anaconda Distribution | 由 Anaconda 提供的完整发行物；包含 conda、Python、大量预装的数据科学/AI 包以及 Anaconda Navigator | 不是 conda 命令本身，也不是每个项目都必需的依赖集 | 希望一次获得常用数据科学工具，或偏好 Navigator 图形界面的初学者 |
| Miniconda | 由 Anaconda 提供的轻量安装程序/`conda` 发行方式；主要安装 conda、Python 及其必需依赖 | 不是一种新的环境格式，也不代表“安装后永远不会下载其他包” | 熟悉命令行、希望按项目自己选包、想保持 `base` 轻量的用户 |

一句话心智模型：**Anaconda Distribution 和 Miniconda 是把 conda 安装到机器上的两种发行选择；`conda` 才是你之后用来创建环境和管理包的工具。**

## 2. 如何选择与安装

### 选择题，不是高低级排名

- 想用 Navigator，或希望常见数据科学工具预先就位：考虑 **Anaconda Distribution**。
- 习惯命令行，已知道项目要什么，或希望更小的初始安装：考虑 **Miniconda**。
- 已经能运行 `conda --version`：先找出现有安装的位置和渠道配置，不要盲目重复安装。

```bash
conda --version
conda info --base
conda config --show-sources
conda config --show channels
```

`conda info --base` 显示根安装/基础环境所在位置；`--show-sources` 能帮你看出配置是从哪些 `.condarc` 文件来的。不要在不知道现有配置的情况下直接覆盖它。

### 安装前的安全清单

1. 只从 [Conda 官方安装入口](https://docs.conda.io/projects/conda/en/stable/user-guide/install/) 或 [Anaconda 官方下载页](https://www.anaconda.com/download) 获取安装程序；确认操作系统和 CPU 架构。
2. 用官方发布的 SHA-256 校验值验证下载文件；不用来历不明的镜像或第三方“一键脚本”。
3. 优先选择当前用户可写的安装位置；官方文档说明这种安装不需要管理员/root 权限。
4. 在 Windows 上不要为了方便而盲目将整套 Anaconda 追加到全局 `PATH`；按安装器默认值和官方激活流程操作。
5. 安装完后新开一个终端，用 `conda --version`、`conda info --base` 和 `conda list -n base` 验证，不要仅凭图形安装器显示“完成”。

### 许可与商业条款：分清对象，当场核对

`conda` 项目、Miniconda/Anaconda 安装器、Anaconda 平台和包仓库访问不是同一个法律对象。条款可能因组织类型、规模、用途、订阅和访问的服务/channel 而不同，也可能修订。因此本课不写死“某类用户永远免费”或人数门槛，而是在每次组织部署、商业使用或改换 channel 前重新核对：

- [Anaconda 官方法律入口](https://www.anaconda.com/legal)
- [Anaconda 官方全部条款与政策](https://www.anaconda.com/legal/terms)
- [Anaconda Platform Terms of Service](https://www.anaconda.com/legal/terms/terms-of-service)

> [!warning] 许可与技术可用性是两件事
> 命令能下载包，不代表当前用法就符合条款。本页不构成法律意见；组织使用应由负责人核对当时有效的官方文本。

## 3. 六个核心概念的边界

### Environment：一个可切换的依赖目录

Conda environment 是一个目录，里面有一组特定的包、可执行文件和依赖。激活环境会调整当前 shell 的 `PATH` 并运行必要的激活逻辑；它不会把包“复制进终端”，也不会改掉其他项目的环境。

`conda activate <env>` 不只是在提示符前加一个名字：它会把目标环境的可执行文件目录放到 `PATH` 前面，并运行包提供的激活脚本；这些脚本可设置原生库所需的环境变量。因此“直接找到某个 `python`”不总等于完整激活了 Conda environment，Windows 和包含原生库的环境尤其需要正确激活。自动化中不想依赖交互式 shell 时，可根据本机 `conda run --help` 使用 `conda run --name <env> <command>`。Shell 变量和 `PATH` 原理参见 [[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|环境变量、Shell 启动与 PATH]]。

### `base`：安装根环境，不是默认项目抽屉

`base` 位于 conda 的根安装中，通常承载 conda 本身及其运行依赖。为每个项目创建独立环境，尽量不在 `base` 中堆叠项目库。这样即使某个实验解决失败，也不容易损坏管理器自身。

### Channel：包来自哪里

Channel 是 conda 查找和下载包的仓库位置/命名空间。同名包可能在多个 channel 中存在，但它们的编译选项、依赖关系和维护者可能不同。**Channel 是软件供应链边界，不是一个无害的搜索标签。**

### Channel priority：多个来源的候选顺序

Channel 列表从高优先级到低优先级排列。当多个来源都有同名包时，优先级策略会影响 solver 能看到哪些候选。官方当前建议全局默认尽量只选一个主 channel；确实必须混用时，用严格优先级降低混合二进制的风险：

```bash
conda config --show channels
conda config --show channel_priority
conda config --set channel_priority strict
```

`strict` 不是“一定能解决”：当高优先级 channel 有某个包名时，同名的低优先级候选会被排除，环境可能因此变得无解。不要为了让一次安装“凑合通过”就将优先级关闭。

### Solver：从约束和候选中找一个自洽组合

Solver 读取你要求的包/版本、当前环境状态、平台和 channel 候选，尝试找出同时满足依赖的最终包集。它不是 channel，也不是下载镜像。

Conda 可提供不同 solver 后端；当前默认和可用后端会随 conda 版本改变，不应从旧教程猜测。现场查看：

```bash
conda config --show solver
conda create --help
```

在不明白冲突原因时反复切换 solver，通常不如缩小版本约束、减少 channel 混用或从空环境重建更稳妥。

### `environment.yml`：可读、可重新求解的环境意图

`environment.yml` 通常记录环境名、channel 和直接依赖约束。它适合人工维护和跨平台分享，但每次创建时仍要由 solver 根据当时的 channel 内容求解，因此不天然保证每个间接依赖、build 和下载来源都一字不差。

### 锁文件与 `conda-lock`：保存已求解的结果

锁文件是机器生成的精确解，通常包含直接和间接依赖的版本、build、channel/来源及目标平台。`conda-lock` 同时是 conda 生态中一个独立工具的名称，它可从 `environment.yml` 等输入为多平台做求解并生成锁文件。

不要混淆三层：

| 层 | 记录什么 | 创建时是否还要求解 | 维护方式 |
| --- | --- | --- | --- |
| `environment.yml` | 项目需要什么，包含可选的版本范围和 pip 子列表 | 是 | 人工编辑后求解 |
| `conda-lock` 工具 | 读取输入规格，针对目标平台求解 | 它负责预先求解 | 规格改变后重新生成 |
| `conda-lock.yml` 等锁文件 | 已求解的精确包、build、来源与平台 | 通常不再求解 | 不手改，由工具更新 |

**Conda 26.5 及以上**已把多平台锁文件作为原生能力，可直接读写 `conda-lock.yaml` 和 `pixi.lock`，不需要为这两种格式另装插件。例如：

```bash
conda export --name my-env --file conda-lock.yaml
conda create --name my-env-copy --file conda-lock.yaml
```

这不会把独立的 `conda-lock` 工具变成 conda 子命令：`conda-lock` 仍是另一条生成/安装锁文件的工作流。旧版 conda 也不能假定具备 26.5+ 的原生能力。运行前检查 `conda --version`，并查阅 [Conda 管理环境与锁文件文档](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html) 与 [`conda-lock` 官方文档](https://conda.github.io/conda-lock/)。

## 4. 一个安全、可恢复的基本工作流

下面使用独立的 `conda-lesson` 环境，不修改你的系统 Python，也不把练习包装进 `base`。

### 创建与激活

```bash
conda create --name conda-lesson python=3.12 pip
conda activate conda-lesson
```

`python=3.12` 是本课为了演示版本约束而选的例子，不是“当前最新 Python”的声明。确认计划中的 channel、版本、build 与新增/删除项后再回答 `y`；看不懂时回答 `n` 不会创建环境。

### 验证当前解释器和环境

```bash
conda info --envs
python -c "import sys; print(sys.executable)"
conda list
```

`conda info --envs` 中的 `*` 标记活动环境。解释器路径应落在 `conda-lesson` 的目录中，而不是系统 Python 或另一个虚拟环境。

### 安装、查看与搜索

```bash
conda install --name conda-lesson numpy
conda list --name conda-lesson
conda list --name conda-lesson numpy
conda search numpy
```

传入 `--name`/`-n` 可以显式锁定目标，避免把包安装到意外的活动环境。安装多个相关包时尽量放在同一次 `conda install` 中，让 solver 同时考虑它们。

### 更新：先看计划，再确认

```bash
conda update --name conda-lesson numpy
conda update --name base conda
```

第一条更新项目包；第二条更新 conda 管理器本身。它们的目标不同。不要在重要项目中习惯性运行 `conda update --all`；它可能为满足新解而同时改动很多间接依赖。更新前先导出规格/锁文件或保留 Git 中的已知可用版本，并审阅 conda 显示的 transaction plan。

### 删除包、退出环境与删除环境

```bash
conda remove --name conda-lesson numpy
conda deactivate
conda env remove --name conda-lesson
conda info --envs
```

`conda remove` 删包，`conda env remove` 删整个环境，二者不可互换。删环境前必须先退出目标环境；确认名称和路径，不要对 `base` 做练习。每个会改动环境的命令都可先查看 `--help` 中本版本是否支持 `--dry-run`。

## 5. 用 `environment.yml` 表达可重建的意图

下面是一个可读的示例：

```yaml
name: conda-lesson
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy
  - pip
  - pip:
      - rich>=13,<15
```

YAML 对缩进敏感：使用空格，不要混用 Tab；`pip:` 是 `dependencies` 中的一个子项，其内列表必须再缩进。`channels` 的顺序有意义，不要为了“多一个备选”随意堆叠来源。

从文件创建环境时，较新的 conda 文档推荐：

```bash
conda create --file environment.yml
```

传统调用仍被保留以兼容现有脚本：

```bash
conda env create --file environment.yml
```

你所用的 conda 若无法识别前一种写法，用 `conda create --help` 和 `conda env create --help` 核对版本能力，不要删掉 YAML 字段去“试出一个能跑的命令”。

将已有环境按文件意图更新，并移除规格中已不需要的包：

```bash
conda env update --name conda-lesson --file environment.yml --prune
```

`--prune` 会删除不再需要的依赖，所以先备份规格、审阅计划，并确认目标环境没有未记录的手工安装。

### 导出：“分享意图”与“复刻现状”不是一份文件

较新 conda 的结构化导出：

```bash
conda export --name conda-lesson --from-history \
  --format=environment-yaml --file=environment.yml
```

`--from-history` 只导出你明确要求安装的顶层包，更适合跨平台分享意图。不带它的完整导出会包含更多间接依赖，但仍不应在不检查平台与来源的情况下当作跨平台锁文件。传统的 YAML 导出也可用：

```bash
conda env export --name conda-lesson --from-history > environment.yml
```

> [!warning] 先检查文件是否已存在
> 导出到同名文件会覆盖旧内容。先用不同文件名导出并对比，或确认旧文件已纳入版本控制；不要对重要的 `environment.yml` 直接盲写。

## 6. `pip` 与 conda 混用规则

Conda 可以管理 Python 之外的二进制依赖，`pip` 主要按 Python/PyPI 的包模型安装。两者对环境状态的视图不完全相同，所以“都能安装”不等于可以随意交替使用。

遵循这个顺序：

1. 为项目新建独立 conda 环境，不在 `base` 中实验。
2. 先用 conda 一次性安装尽可能多的依赖。
3. 确认环境内有自己的 `pip`：`conda install --name conda-lesson pip`。
4. 激活环境，并用 `python -m pip` 将目标解释器写明：

```bash
conda activate conda-lesson
python -m pip --version
python -m pip install --upgrade-strategy only-if-needed rich
```

5. 不在 conda 环境中使用 `pip install --user`；它会把包放到用户级位置，破坏环境边界。
6. 使用 pip 后，如果还需要大量改动 conda 依赖，优先修改 `environment.yml` 并从空环境重建，而不是继续让 conda 和 pip 反复交错修改同一环境。
7. 把 pip 依赖写在 `environment.yml` 的 `pip:` 子列表或受版本控制的 requirements 文件中，不只依赖终端历史。

验证命令：

```bash
python -c "import sys; print(sys.executable)"
python -m pip --version
conda list --name conda-lesson
```

解释器路径、pip 路径和 `conda list` 的目标必须指向同一个环境。

## 7. Channel 策略与安全边界

将 channel 当作“你愿意执行其发布软件的供应者”，而不是搜索引擎结果。

- 优先在项目的 `environment.yml` 中显式记录 channel，不在无人知情时修改全局 `.condarc`。
- 尽量使用一个主 channel；必须混用时明确顺序并考虑 `strict` 优先级。
- 一次性临时使用某个 channel 时，优先显式限定范围，并在执行前审查它会从哪些来源取包：

```bash
conda install --name conda-lesson \
  --channel conda-forge --override-channels numpy
```

`--channel conda-forge --override-channels` 表示本次求解只使用指定 channel。而下面的写法只绑定名为 `numpy` 的包，其依赖仍可从已配置 channel 求解：

```bash
conda install --name conda-lesson conda-forge::numpy
```

这两条命令不等价。若来源之间的编译约定不兼容，定向单包仍可能造成 ABI 冲突。安装前检查 channel 所有者、包名、平台、版本和交易计划；不要从未知 channel 安装与常用包同名的内容。

## 常见坑

| 现象 | 根因 | 更稳妥的做法 |
| --- | --- | --- |
| 把“装了 Anaconda”说成“项目用 Anaconda 管依赖” | 混淆发行物与包/环境管理器 | 说明安装源，再说项目实际使用的 conda 环境和规格 |
| 所有项目都安装到 `base` | 把安装根环境当成通用项目环境 | 为每个项目创建独立命名环境 |
| 激活后还是用错 Python/pip | shell 没初始化、IDE 仍指向旧解释器，或命令来自外部环境 | 同时检查 `conda info --envs`、`sys.executable` 和 `python -m pip --version` |
| 加了更多 channel 反而更难解 | 同名包和二进制约定彼此冲突 | 减少来源；必须混用时审查顺序并使用 strict priority |
| 换 solver 后仍无解 | 版本约束或平台/channel 候选本身不相容 | 阅读冲突链，缩小规格并从空环境重建 |
| pip 安装后再反复 conda install/update | 两个管理器对当前状态的认知不完全一致 | conda 先、pip 后；需大改时从规格重建 |
| 将 `environment.yml` 当成精确锁文件 | 忽略了它创建时仍会重新求解 | 它用于意图；需精确复现时生成并验证锁文件 |
| 直接手改锁文件 | 把已求解产物当作输入规格 | 修改 `environment.yml`，再用对应工具重新生成和测试 |
| 不看条款就把个人安装复制到组织/CI | 把软件安装、仓库访问与商业用途当作同一授权 | 在部署现场核对官方条款和实际 channel |

## 练习：创建、导出、重建并安全删除

> [!warning] 网络与条款
> 练习会从配置的 channel 下载包。先运行 `conda config --show channels` 确认实际来源，并在需要时核对当时有效的官方条款。

1. 运行 `conda --version`、`conda info --base`、`conda config --show channels` 和 `conda config --show solver`，写下“安装根、channel 顺序、solver”三类信息，不记录 token 或带凭据的 URL。
2. 创建 `conda-lesson`：`conda create -n conda-lesson python=3.12 pip numpy`；审阅计划后确认。
3. 激活并验证 `sys.executable`、`python -m pip --version` 和 `conda list numpy`。
4. 创建一份不会覆盖项目文件的 `conda-lesson-history.yml`：

```bash
conda export --name conda-lesson --from-history \
  --format=environment-yaml --file=conda-lesson-history.yml
```

若本机 conda 没有 `conda export`，查阅 `conda env export --help` 后使用传统命令。

5. 打开 YAML，标出环境名、channel 和顶层依赖；说明它为什么不是锁文件。
6. 退出环境，删除它，再从 YAML 创建同名环境；运行一次 NumPy 验证：

```bash
conda deactivate
conda env remove -n conda-lesson
conda create --format=environment-yaml --file conda-lesson-history.yml
conda activate conda-lesson
python -c "import numpy; print(numpy.__version__)"
```

7. 练习结束后退出并删除环境，删除临时 YAML 前先确认它不是项目需要的文件。

## 成功标准

- [ ] 能用一句话分别定义 conda、Anaconda Distribution 和 Miniconda；
- [ ] 能说明 channel 决定候选来源，solver 负责从约束中找出自洽解，二者不是同一层；
- [ ] 能说明 `base` 的用途，并为项目创建独立环境；
- [ ] 能完成 create、activate、install、update、remove、list、export 与整个环境删除，并每次确认目标环境；
- [ ] 能读懂 `environment.yml` 的 `name`、`channels`、`dependencies` 和 `pip` 子列表，不把它当成精确锁文件；
- [ ] 能解释 `conda-lock` 工具与锁文件的关系，并知道锁文件应重新生成而非手改；
- [ ] 能遵循“conda 先、pip 后、大改则重建”，不用 `pip --user` 穿透环境边界；
- [ ] 能在安装前检查包来源和交易计划，并知道许可/商业条款需要在实际部署时重新核对。

## 恢复与删除

- 只想退出当前环境：`conda deactivate`，文件不会被删除。
- 想撤销某次 conda 环境修改：先用 `conda list --revisions` 查看修订历史，再根据本机 `conda install --help` 评估 `--revision` 恢复；修订回滚不会可靠撤销 pip 安装。
- 环境已被 conda/pip 混用改得难以解释：保留已审阅的 `environment.yml`/锁文件，删除项目环境后重建，通常比手工修复每个包更可审计。
- 删除整个项目环境：先用 `conda info --envs` 解析精确名称/路径，退出后运行 `conda env remove --name <env>`，再次列出环境验证。
- 卸载 Miniconda/Anaconda Distribution 不等于删一个项目环境；它会涉及安装目录、shell 初始化、`.condarc` 与缓存。必须按当前操作系统的 [Conda 官方卸载文档](https://docs.conda.io/projects/conda/en/stable/user-guide/install/) 逐项盘点，不要照抄未解析安装路径的递归删除命令。

## 导航

- 上一篇：[[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|venv 与虚拟环境原理]]
- 返回 MOC：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础 MOC]]
- 下一篇：[[计算机知识/10-编程语言/01-Python/11-uv项目依赖与工具管理|uv 项目依赖与工具管理]]

## 一手参考

> [!note] 参考范围
> 本课事实核对只使用 Conda/Anaconda 官方文档与官方法律页面，核对日期为 2026-09-01。

- [Conda：安装 conda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/)
- [Anaconda：如何选择 Anaconda Distribution 与 Miniconda](https://www.anaconda.com/docs/getting-started/concepts/anaconda-or-miniconda)
- [Anaconda：Working with conda](https://www.anaconda.com/docs/getting-started/working-with-conda/main)
- [Conda：管理环境、YAML 导出与锁文件](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html)
- [Conda：管理包与 pip 混用](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-pkgs.html)
- [Conda：管理 channel 与优先级](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-channels.html)
- [Conda：命令索引](https://docs.conda.io/projects/conda/en/stable/commands/commands.html)
- [`conda-lock`：官方文档](https://conda.github.io/conda-lock/)
- [Conda 生态：`conda-lockfiles` 格式支持](https://conda.github.io/conda-lockfiles/)
- [Anaconda：法律与条款入口](https://www.anaconda.com/legal/terms)


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/04-Python-课程地图|Python · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/01-Python/15-对象协议描述符闭包与类型边界|Python 深化：名字、对象、协议与类型边界]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
