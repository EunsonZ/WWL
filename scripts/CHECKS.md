# 本地静态检查入口

这些脚本只读取指定库的文件，报告可定位的问题。导入模块不会启动服务、运行笔记或源码、安装依赖、修复文件、添加基线、提交或推送。

## 来源、范围与原始基线

本批候选目标为提升已有维护算法，补上明确缺失的根检查入口；候选仅涉及 `scripts/links.py`、`scripts/check_mirrors.py`、`scripts/check_vault.py`、`scripts/tests/test_vault_checks.py` 与本说明。2026-09-15 开始时根 `scripts/` 不存在，现场没有 Git，原维护源码保持原字节。

复用依据是 `AI/90-资源/维护/check_vault.py` 的静态检查分层，以及 `Logs/2026-09-08_TBM结构整理/tools/links.py` 的围栏状态、平衡括号目标扫描、精确路径优先思路；镜像检查沿用同目录 `check_mirrors.py` 的正向比较合同。`计算机知识/Kali/90-来源与维护/工具/check_vault.py` 和第二批日志中的解析器也已只读检索。没有执行历史脚本中的默认写入或迁移操作，也没有改动原实现和原测试。

现场复用源码 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `AI/90-资源/维护/check_vault.py` | `ae1ce59f3dc8f0f4a3eaef3348d1a5ed79bd4bbad7ba8020eb4cfd2f1b0f4f06` |
| `Logs/2026-09-08_TBM结构整理/tools/links.py` | `47e5312c464e89e66fb6744b1c1ee10778103fcb578b418180604a6316162632` |
| `Logs/2026-09-08_TBM结构整理/tools/check_mirrors.py` | `675595fe36d003f389f87358b4dbfca3264e58756f1499ef1ef3d03e8af654e5` |

候选验证包括独立成功/失败夹具、只读全库扫描、逐项分析误报和新增回归。原库与其他作者的候选均不是本检查器作者的写入范围；本工具没有批量迁移或回滚功能。

## 使用

2026-09-16 用户授权安装的依赖位于库根 `.venv`；下列 `python3` 在本机可替换为 `.venv/bin/python`，复建步骤及固定版本见 [本地维护与绘图环境](ENVIRONMENT.md)。历史未安装状态仍按原时间保留。

Python 3.10+ 可运行基础标准库层；集成入口调用 `config_checks.py` 检查 C1 项目 TOML 与四个角色的声明，Python 3.11+ 才有标准库 `tomllib`。缺少该标准库时此层明确未运行。从已集成的库根运行：

```bash
python3 -B scripts/check_vault.py --help
python3 -B scripts/check_vault.py --require-yaml
python3 -B scripts/check_mirrors.py --help
python3 -B scripts/check_mirrors.py --root .
python3 -B -m unittest discover -s scripts/tests -v
```

候选可用 `--root /绝对路径/集成树` 指向独立目录。省略 `--root` 时使用脚本所在 `scripts/` 的父目录，不使用历史工程路径。`--json /库外已存在目录/新证据.json` 将完整报告写入新文件；输出文件权限为 `0600`。报告保留路径和解析目标，按私密本机证据保存。必须使用新的文件名，不能覆盖既有证据或把报告写回被检查的库。

命令退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 没有 `critical/error`；仍可能是 `partial`，必须看 `layers` 与 `review`。 |
| `1` | 存在阻断静态诊断，包括启用 `--require-yaml` 时缺少 PyYAML。 |
| `2` | 命令参数、库根或证据输出位置不合法。 |

只有镜像检查的成功/失败例：

```bash
task_tmp="$(mktemp -d)"
printf 'pass\n' > "$task_tmp/example.py"
printf '<!-- code-sync: ./example.py -->\n```python\npass\n```\n' > "$task_tmp/note.md"
python3 -B scripts/check_mirrors.py --root "$task_tmp"
printf 'print(1)\n' > "$task_tmp/example.py"
python3 -B scripts/check_mirrors.py --root "$task_tmp"
```

第一次应退出 `0`，第二次应退出 `1`。`check_vault.py --root "$task_tmp"` 同样会诊断第二次的镜像差异。仅含 `# 首页` 的笔记目录是标准库层的最小成功例；加入实际正文中的 `[[不存在的目标]]` 后应退出 `1`。这些示例只写新临时目录，不运行其中源码。

## 链接解析合同

- Markdown 的文件目标按本库既有静态约定相对于来源笔记目录；只对同一明确候选路径尝试补 `.md`，不借助全库同名文件补救错路径。`../README.md` 必须实际解析到库根首页。Obsidian 客户端的导入路径解析与根路径偏好仍须单独实测，本工具不会同时尝试根/局部路径来掩盖错误。
- wiki 含目录路径默认从库根解析；`./`、`../` 明确从来源目录解析。无目录短链优先同目录，再采用唯一全库文件名。只匹配属性别名的短链记录候选文件，同时报告 `review/alias_target_needs_ui_review`；它不认证客户端会自动解析 `[[别名]]`。多个同名文件时报告 `review/link_ambiguous`，不能声称选中了读者原本想去的文件。
- 路径先按精确字节匹配；大小写或 Unicode 规范形式不同会单独诊断。显式错误目录永不回退成 basename。文件名中的点不自动代表真实扩展名，因此 wiki 的 `llama.cpp` 可定位到 `llama.cpp.md`。
- wiki 的显示别名及表格转义竖线不属于目标；附件嵌入、百分号编码、相对路径与平衡括号的 Markdown 目标分别处理。外部 URL 只识别，不访问网络。
- 标题查 ATX、Setext 标题的可见文字，支持常用转义/强调/行内代码。Markdown 也比较常见标题 slug 和重复标题的 `-1` 后缀；wiki 使用可见标题。块 ID 单独按 `#^id` 查找。具体文件及目标段落必须成立。
- 代码围栏（含相同前缀的引用/缩进容器）、同一段落内行内反引号（含跨行）、HTML/Obsidian 注释、HTML `code/pre` 示例和转义 wiki 语法不作为活跃链接。带文字的伪关闭围栏不会关闭代码段；未关闭围栏/注释有诊断。悬空反引号不会跨过空段吞掉下一段真实链接。
- Markdown 引用定义检查一次；脚注定义不误识别成普通引用定义。Canvas 文件节点检查真实文件目标。成功解析映射保存在 `resolved_links`，供 T29 核对具体文件。

缺少 PyYAML 时，别名仅识别明确的普通/引号列表子集；复杂 YAML 别名报告 `alias_syntax_not_checked`。这不宣称 YAML 校验已经完成。

这不是完整 CommonMark/Obsidian 渲染器：复杂嵌套列表/引用中的变形围栏、缩进代码块、任意 HTML、插件语法、重复标题在不同渲染器的定位差异、PDF 页码/媒体时间片段等仍需要针对性核对。多级 `#父标题#子标题` 和含非字母/数字/短横线的块 ID 单独报告 `review`，避免把尚未支持的语法误判成确认断链。附件片段目前是 `review/attachment_anchor_not_checked`。原稿和教学夹具不自动豁免；实际活跃的演示断链应逐项确认职责，不能全域忽略。

## 属性、配置与源码镜像

PyYAML 已安装时检查 frontmatter 解析、重复属性、声明字段类型、枚举、同名属性类型冲突，以及先修/主题字段的链接形式；链接的具体路径与标题继续由同一链接层检查。缺省值保留原意，不填日期、不推算学习成果、不把 `ready` 转换为 `reviewed`。`.obsidian/types.json` 的已知属性类型同时与解析结果核对。未安装时相应层明确 `not_run_missing_PyYAML`，不会自动安装；`--require-yaml` 把缺层变成 `error`。

JSON 检查覆盖 `.obsidian/` 的 `app`、`appearance`、`graph`、`types`、`templates`、`core-plugins`、`community-plugins`，可见 `config/` 下 JSON 以及 Canvas。重复 JSON 键、NaN、Infinity 和溢出的浮点数均拒绝。已启用社区插件检查 `manifest.json`、`main.js` 的存在性；不读取插件 `data.json`、脚本正文或凭据。配置错误不回显属性值或解析异常中的敏感片段。Bases 只检查 YAML 语法/映射形状，不认证 Bases 表达式、显示效果或插件运行。

活动 `code-sync` 标记须独占一行，后面紧接空白和代码围栏；行内说明、注释中的嵌套标记、代码教学示例不是合同。源码明确相对路径或库根路径；无目录源码沿既有约定先查库根，再查同目录。只比较规范文本文件与代码块，不执行代码、不把镜像反写到源码；Markdown 报告模板也是可用的规范文本来源。

比较按 UTF-8 原字节解码，保留 CRLF 与 LF 的区别；唯一有限规范化是允许源码缺少一个最终 LF，以便代码围栏另起一行关闭。额外空行、空格、行尾类型和代码差异保持显著；源码与镜像同为 CRLF 可通过，源码 CRLF/镜像 LF 必须报差异。目录或文件符号链接不作为可读取真源；不会回退到更宽权限路径。本工具是静态检查器，不是对并发路径替换的完整文件系统隔离。

## 报告 schema 与证据边界

`wwl-static-check-v1` 具有 `root`、`status`、`counts`、`scope`、`layers`、`issues`、`resolved_links`。每项诊断有 `rule`、`severity`、`path`、`line`，按需要附 `target`、`resolved`、`source` 或字段名；不附源码差异或私密属性值。镜像独立命令使用 `wwl-mirrors-v1`，保留 `checked`、`markers`、`issues`。

`error` 表示明确结构错误或必需能力缺失；`review` 表示路径歧义、能力边界等尚需确认的问题。本工具不自动批准审阅，也没有全域基线豁免选项。结构扫描、数学/数值、实验运行、来源语义与真实 Obsidian 界面分别报告；本检查器的绿色结果不能代替后面四层。

测试中 T29 覆盖同名 README/术语、移动后相对路径、标题与块；T27/T28 仅验证检查器自身只读幂等、不要求根 `CHANGE.md`，以及能发现指向已删文件的活跃链接。T26 的项目配置/角色声明检查在集成入口运行；实际客户端加载、权限与并发没有由此得到认证。实际迁移幂等、原件保全及删除收尾由本批独立验收证据承接。
