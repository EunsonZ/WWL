---
type: resource
status: ready
---

# 检查脚本与运行记录

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本页保留原交付的历史内容。第二轮修订请先读[[AI/90-资源/08-本轮深化修订与验收报告|本轮深化报告]]，实际复测日志位于 `90-资源/维护/深化研究`；不要把下文历史数字与本轮数字混合。


`check_vault.py` 检查 AI 内部 Wikilink、章节锚点、本地图片、Markdown 文件链接、代码围栏、公式定界符和表格别名。跨目录链接另列为外部知识域引用，不当作本目录缺失。安装 PyYAML 时还检查 frontmatter；未安装时不会验证 YAML 内容。本轮已安装并执行了 YAML 检查。

从本目录运行即可，默认通过脚本位置定位 AI 根目录，不要求原机器路径：

```bash
python check_vault.py --output /tmp/ai-audit.json --formulas /tmp/ai-formulas.json
```

`check_math.cjs` 使用 MathJax 3 的 `mathjax-full` 包渲染提取的公式，检查语法错误。需在独立 Node.js 工作目录安装相应依赖，或将该依赖位置放入 `NODE_PATH`。本轮引擎为 MathJax 3.2.2。示例中的临时路径适用于 Linux/macOS，其他系统可换成本机路径。

```bash
node check_math.cjs /tmp/ai-formulas.json /tmp/ai-math-report.json
```

公式语法可渲染不等于数学命题得到证明，也不等于所有主题都经过专家评审。语义与数值例另由课程推导、20 项新增测试以及原有测试提供有限验证。本轮没有启动桌面版 Obsidian 逐页截图，不能声称验证了每种主题和插件组合。

本目录保存 `static_audit.json`、`math_render.json`、`format_repairs.json`、`preservation.json`、`environment.json`、原有测试日志、新增测试日志和 CNN 指标。`external_vault_links.json` 列出原有跨目录目标及引用位置；这些文件应由完整知识库提供，不在 AI 子包中创建虚假占位页。

`file_manifest_sha256.json` 用于文件完整性校验，覆盖包内 AI 目录的文件，但排除清单自身。它不是软件签名或安全审计证明。对代码、模型与数据的安全边界，继续遵循原课程的实践说明。

返回 [[AI/90-资源/06-修订与验收报告]]。
