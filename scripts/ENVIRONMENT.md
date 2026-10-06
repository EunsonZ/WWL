# 本地维护与绘图环境

知识正文可直接在 Obsidian 阅读。下面的 Python 环境用于检查属性和链接、复算课程例题、生成数值图；打开普通笔记不需要先运行脚本。

## 已安装环境

2026-09-16，按用户明确授权，在库根创建了独立 `.venv`，使用 Python 3.14.7（macOS arm64）。PyYAML 6.0.3 用于 YAML 属性与 Bases 语法检查；Matplotlib 3.11.2、NumPy 2.5.3 和 Pillow 12.3.0 用于数值计算、绘图和图像读取。CairoSVG 2.9.1 配合本机已有 Cairo 库用于按原始尺寸渲染 SVG；中文渲染还需让 Fontconfig 找到支持中文的本机字体。完整的固定版本在 [requirements-knowledge.txt](../requirements-knowledge.txt)。`pip check` 已通过。

本机 Python 直接连接 PyPI 曾超时；本批改用 curl 从官方 PyPI 取得与解释器匹配的 wheel，逐个核对官方 SHA-256 后离线安装。没有关闭 TLS 校验或使用第三方镜像。这个网络现象不能解释为软件包不存在。

## 日常检查

从库根运行，无须修改系统 Python 或全局 PATH：

```bash
.venv/bin/python -B scripts/check_vault.py --require-yaml
.venv/bin/python -B -m unittest discover -s scripts/tests -v
.venv/bin/python -m pip check
```

维护入口的诊断等级、检查范围与证据限制见 [CHECKS.md](CHECKS.md)。本批安装依赖后，103 项维护测试全部通过；全库检查还会报告历史链接问题、教学示例及旧属性类型冲突，不能把“检查能够完整运行”理解为“全库没有问题”。按本批 [实际记录](../CHANGES.md) 判断具体版本。

运行课程实验时使用实验页指定的入口。这套轻量环境没有安装 PyTorch、GPU 工具链或大模型；某些已有实验有自己的依赖，不能从 NumPy 已安装推断所有实验都能运行。

## 换机复建

在确认 Python 版本与平台符合所用依赖要求后，可以在新的库副本中执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-knowledge.txt
.venv/bin/python -m pip check
```

`.venv` 不能当作跨机器可移植文件复制。不要把已有环境覆盖成另一个 Python 版本；需要切换时另建环境并复验。固定版本记录本机实际安装组合，不承诺未测试平台兼容。

生成科学图时选用无界面的 `Agg` 后端，并把 `MPLCONFIGDIR` 指向本地临时目录或 `.venv` 内的缓存目录。图中保留坐标单位、模型条件和合成数据标签；图片的渲染正确与公式的数值正确分别核验。

## 本地 Git

仓库已按用户授权初始化，初始分支为 `main`，仓库级身份为 `z <z@z.com>`。没有设置全局 Git 身份，也没有配置远程仓库。

`.gitignore` 默认排除隐藏应用状态目录、虚拟环境、TaskNotes、Tags、个人规划、常见凭据文件及缓存。规则只是第一层保护，不能证明所有正文都没有私人内容；暂存前仍应按本次具体文件范围检查差异。初始化不会自动产生提交。2026-09-17按用户进一步授权创建本地知识基线提交 `0ef0ce6`，精确纳入2207个知识与维护文件；私人记录、剪藏、保留资料及应用状态仍不在版本范围内。后续审计与规划另批提交；这不是整库所有文件均已备份的承诺。

```bash
git status --short
git diff --cached --stat
git config --local --get user.name
git config --local --get user.email
```

这些是只读检查。不要使用 `git add .`、覆盖式恢复或强制重置来省略文件选择和保全。
