---
stage: 1
aliases: ["UD EWT HMM 复现", "真实语料序列标注实验"]
sources:
  - "https://github.com/UniversalDependencies/UD_English-EWT/tree/r2.16"
  - "https://creativecommons.org/licenses/by-sa/4.0/"
prerequisites:
  - "[[AI/35-传统NLP/10-真实语料序列标注/03-冻结测试与真实失败]]"
---
# UD English EWT r2.16：可复跑的 HMM 实验

这是 01–03 的可执行真源。源码 [nlp_ud_lab.py](nlp_ud_lab.py) 只用 Python 标准库；测试 [test_nlp_ud_lab.py](test_nlp_ud_lab.py) 检查稳定文档选择、整数 token 投影、官方 split 的保留文档不交叉、每词恰返回一个合法 UPOS、平滑转移行归一与完整 `FORM` tuple 的重复键。可读代码镜像在 [CODE-SYNC.md](CODE-SYNC.md)，它受 `code-sync` 检查约束并链接回本实验页。图由 [plot_ud_results.py](plot_ud_results.py) 从结果生成。`results.json` 是本次运行的聚合指标、切片、混淆、重复计数和协议记录；正常运行不写 `FORM`、句 ID、文档 ID 或逐 token 预测，以免重新发布可重构的底层文本。

## 获取并核对固定输入

发布后的课程目录不携带原始 EWT 文本。首次运行须自行从固定公开 URL 获取 r2.16 的 `en_ewt-ud-{train,dev,test}.conllu`，放到一个本机目录，并核对 01 页列出的 SHA-256；作者的原字节证据位于本批库外 `authors/nlp/evidence/ud-treebanks-v2.16/`，这个作者路径不是发布后程序的默认搜索位置。`--data-dir` 必须显式指定含三个固定 CoNLL-U 文件的目录；缺文件或传错目录会报 `ValueError` 并列出缺失文件，不会退回到作者目录或下载任何数据。

从发布后的本实验目录运行（将绝对路径替换为自己已核对的数据目录）：

```bash
DATA_DIR="/absolute/path/to/ud-ewt-r2.16"
python3 -B nlp_ud_lab.py --data-dir "$DATA_DIR" --output results.json
UD_EWT_DATA_DIR="$DATA_DIR" python3 -B -m unittest -v test_nlp_ud_lab.py
python3 -B plot_ud_results.py
shasum -a 256 results.json figures/*.svg
```

本次运行：7 个测试通过，选中 α=0.01；其中一项明确检查缺少任一固定 CoNLL-U 文件时拒绝数据目录。此作者候选的实际输出 hash 记录在本批库外的集成 manifest，发布页不依赖或链接该临时路径。执行不下载模型、不安装依赖、不访问私人或付费语料。保留的公开数据来自 UD English EWT；EWT README 说明 CC BY-SA 4.0 覆盖 annotations/database rights，且单列底层文本的其他权利来源。原 README、LICENSE 和 CoNLL-U 原字节均在本批 `authors/nlp/evidence/ud-treebanks-v2.16/`，不作为候选正文副本发布。这里的说明是归属记录，并非对其网页文本另行授权。

代码和本页的运行入口配套交付；修改任一算法、投影或数据文件后应重跑结果、图和测试，不能沿用旧数。通过的检查只认证这次固定文件、程序和执行环境上的机械性质；独立语义审阅、Obsidian 客户端显示和人的理解仍须另验。
