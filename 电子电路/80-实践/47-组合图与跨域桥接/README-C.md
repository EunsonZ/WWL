---
type: lesson
domain: electronics
stage: 3
content_status: usable
evidence_status: partial
aliases: []
sources: []
prerequisites: []
---
# C组组合图：条件跟着箭头走

四个入口分别兑现六个图合同：[[电子电路/80-实践/47-组合图与跨域桥接/01-V32V33V34窗口事务与跨域|V32/33/34：窗口、逐拍事务、CDC]]，[[电子电路/80-实践/47-组合图与跨域桥接/02-V35回流跨层与去耦|V35：PCB返回与局部高di/dt]]，[[电子电路/80-实践/47-组合图与跨域桥接/03-V42光子电荷与机械端口|V42：光电到TIA与MEMS两种读出]]，[[电子电路/80-实践/47-组合图与跨域桥接/04-V43生物边界与阵列求和|V43：合成台架隔离概念与阵列KCL]]。先读图与单位，再按链接回正式主解释核推导/原始依据；组合卡不复制平行证明。

## 输入与复现

真源 `bridge_figures.py`；`bridge-inputs.json`固定正式主库正文/模型/数据SHA；图由正式数值数据加原创组合结构生成。所有命令从WWL根，以已有环境执行，无安装。输出要求库外不存在目录，重复执行另取新名：

```bash
.venv/bin/python -B '电子电路/80-实践/47-组合图与跨域桥接/bridge_figures.py' --vault . --output /private/tmp/C6-figures-fresh
```

输出6个可编辑SVG、每图360/425普通与灰度/暗色检查PNG、V32/V33预期WaveDrom JSON、参数/来源/result JSON。所有标签为英语，正文中文解释对象；ASCII单位保持可读。SVG直接生成，CairoSVG/Pillow只在显式生成时导入；不改全局绘图后端、不使用默认输出。非法源SHA、库内路径、已有输出在写前拒绝。缺依赖记录未运行，不安装。

内容完成与执行层不同：V33当前CPU预期与可运行HDL命令合同齐全，实际VCD/截图仍not_run；V34不伪造模拟亚稳态；V35不假装板已填区/提取/制造；V42与V43的来源正文/数据沿正式main，图是教学组合而非实测。作者不自签；冻结后由非作者普通与承重审阅绑定具体版本。

## WaveDrom生产输入与工具记录

V32源 `assets/V32-wavedrom.json` 是严格JSON，1ns/tick，含锁存透明期/正沿采样与launch/capture/setup/hold/skew分组；V33源 `assets/V33-wavedrom.json` 是复位解除后的六拍CPU预期。复位取消责任仍由正式原TB与reset-chain图给出。生成器同时产出这两份源，头部按WaveDrom的 `{text: ...}`格式。

以下命令仅供**已存在**的 `wavedrom-cli` 使用，先选库外不存在输出文件；不要为本卡安装工具。官方[WaveDrom CLI README](https://github.com/wavedrom/cli#usage)的SVG接口为 `-i input -s output`：

```bash
command -v wavedrom-cli
wavedrom-cli -i '电子电路/80-实践/47-组合图与跨域桥接/assets/V32-wavedrom.json' -s /private/tmp/V32-wave-fresh.svg
wavedrom-cli -i '电子电路/80-实践/47-组合图与跨域桥接/assets/V33-wavedrom.json' -s /private/tmp/V33-wave-fresh.svg
```

本轮PATH探测没有 `wavedrom-cli` 或 `wavedrom`；因此两个render命令未执行，实际渲染输出均 `not_run`。输入文件与命令合同已提供；JSON语法/长度检查不是渲染成功。CLI接口已取回官方README核对，没有安装包或以npx触发下载。真实HDL/VCD仍独立 `not_run`，不由WaveDrom预期替代。
