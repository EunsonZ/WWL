# 检查工具与结果的含义

本目录保存从旧 `com/` 输入包迁入的历史维护工具与交付记录。当前 Vault 的课程源位于 `计算机知识/`；结构、源码与公式检查的每次默认输出位于 `Logs/运行/<批次>/<运行时间戳>/计算机知识/`，不会改写本目录中的历史 JSON 或先前运行。不要把历史 JSON 的数字当当前规模。


返回 [[计算机知识/90-资源/维护/导入-com/_meta/06-深度修订交付报告|历史输入包交付报告]]。先在库外、未编辑的原始 `com/` 快照上核对文件清单，再运行当前 Vault 的检查。

## 验证解压文件是否完整

仅在库外、未编辑的原始 `com/` 快照内运行：

```bash
python _meta/tools/verify_delivery.py .
```

该旧包校验器只读文件，以 `_meta/file_manifest.json` 的字节长度与 SHA-256 检查原始交付包。清单本身不包含自己的哈希，避免自引用。ZIP 的完整 SHA-256 位于包外校验文件。它不适用于当前 Vault，也不应用于已迁入本目录的历史 `_meta`；迁移后路径和内容变化不表示原包损坏。多出的 `.obsidian/` 配置单独列出，不当作丢失文件。

## 结构、源码与公式

从 Vault 根目录运行：

```bash
python 计算机知识/90-资源/维护/导入-com/_meta/tools/audit_vault.py .
python 计算机知识/90-资源/维护/导入-com/_meta/tools/check_sources.py .
python 计算机知识/90-资源/维护/导入-com/_meta/tools/extract_math.py .
```

三个工具均向上查找 Vault 根的 `AGENTS.md`，并默认在 `Logs/运行/static-audit/<运行时间戳>/计算机知识/`、`Logs/运行/source-syntax/<运行时间戳>/计算机知识/` 与 `Logs/运行/math-extract/<运行时间戳>/计算机知识/` 写入新结果。可用 `--output`（审计和公式提取）或 `--output-dir`（三个工具）改到明确的临时目录；显式路径优先于默认值，不会默认覆盖历史 `_meta` 产物。

要与输入包比较，将原包另行解压到独立目录，再为第一个命令传入 `--original /路径/原始com`。不要让原包与修订包指向同一目录。`--repair-table-aliases` 是可选写操作，仅处理 Markdown 表格内的 wiki 别名分隔符。

`audit_vault.py` 检查 wiki 目标、常见标题/块锚点、相对图片链接、未闭合代码围栏、SVG XML 与远程资源引用，并对保留的原链接按来源、目标、锚点逐项计数。它是面向本包格式的静态检查器，不是 Obsidian 内核的完整替代：复杂插件语法和带嵌套括号的 Markdown 目标仍需人工复核。包外的已知链接不应自动删除。

`check_sources.py` 只做 Python 语法编译、`bash -n`、YAML frontmatter 和表格列数检查，不会自动执行旧笔记。Python 只需标准库；YAML 检查需要 PyYAML，缺失时标为 SKIP。系统须有 Bash 才能执行 shell 语法检查。

公式转换还需要 Node.js 与可解析的 `mathjax-full` 包；本次使用 3.2.1，不把依赖打包进知识库。配置好 Node 模块查找路径后执行：

```bash
node 计算机知识/90-资源/维护/导入-com/_meta/tools/check_math.cjs /tmp/local_math_expressions.json /tmp/local_math_audit.json
```

若已全局安装该依赖，可通过 `NODE_PATH="$(npm root -g)"` 显式提供查找路径。转换成功说明公式语法可被该版本解析，不等于定理成立、数值推导正确或每种 Obsidian 主题的视觉效果一致。

## 运行已审查的实验

从 Vault 根目录运行：

```bash
python 计算机知识/_labs/round3/run_all.py
```

仅运行本次列出的、限定范围的本地实验，不遍历执行原库代码。参见 [[计算机知识/00-开始/全局导航/09-本地实验与验证入口|实验入口与环境边界]]。Rust 未安装时会明确跳过；预期编译失败的借用样例不是待修复的错误文件。请使用普通 Python 运行，不启用会移除断言的 `-O` 选项。

本次新运行默认写入 `Logs/运行/round3-labs/<运行时间戳>/计算机知识/round3_lab_results.json`；输入包中上一轮报告的原始快照仍保存在 `计算机知识/90-资源/维护/导入-com/_meta/历史记录/输入包报告快照/`。重新运行当前工具不会改写该快照。
