---
domain: "计算机知识"
type: "lab"
stage: 5
prerequisites:
  - "[[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]"
  - "[[计算机知识/Kali/06-取证逆向与检测/07-YARA日志与检测规则|YARA日志与检测规则]]"
  - "[[计算机知识/Kali/06-取证逆向与检测/04-文件元数据Binwalk与ExifTool|文件元数据Binwalk与ExifTool]]"
sources:
  - "https://yara.readthedocs.io/en/stable/writingrules.html"
content_status: "usable"
evidence_status: "partial"
---

# 实验E文件分析与YARA

**先修关系：** [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]；[[计算机知识/Kali/06-取证逆向与检测/07-YARA日志与检测规则|YARA日志与检测规则]]；[[计算机知识/Kali/06-取证逆向与检测/04-文件元数据Binwalk与ExifTool|文件元数据Binwalk与ExifTool]]。

## 最小检测实验也需要阴性对照

输入只有两个无害文本，正例有两个指定标记，负例缺第二个。它们不是恶意样本；测试标签“正/负”只表示是否满足这条教学规则。先按 [[计算机知识/Kali/06-取证逆向与检测/04-文件元数据Binwalk与ExifTool|文件基线]] 记录摘要、类型和字节内容，再读规则源文件，不要直接依赖名称。

```bash
cd "$HOME/kali-lab"
file fixtures/files/positive.txt fixtures/files/negative.txt
xxd -g 1 -l 128 fixtures/files/positive.txt
yara code/toy_markers.yar fixtures/files/positive.txt
yara code/toy_markers.yar fixtures/files/negative.txt
```

只有已安装且版本已确认的 YARA 才能执行最后两行；本次构建未安装或运行该引擎。没有输出先核对命令状态、规则是否加载和文件是否被读取，再解释为“不匹配”。[^s1]

## 三个有区分力的变体

在 output 中分别创建：保留两个标记的正常小文本；删除第二标记的小文本；保留两个标记但填充到4096字节或更大的文本。预期只有第一种命中。第三种检验 `<4096` 的严格边界，尤其**恰好4096也不命中**。它比再复制十份同样的正例更能检验实现。

```bash
python3 - <<'PYCODE'
from pathlib import Path
base = Path.home() / 'kali-lab'
original = (base/'fixtures/files/positive.txt').read_bytes()
path = base/'output/markers-4096.txt'
with path.open('xb') as output:
    output.write(original + b'X' * (4096-len(original)))
PYCODE
```

新文件已经存在时应报错，避免覆盖上次证据。重新运行规则前记下新摘要和变化意图；不要修改原始样本来迎合结果。更换规则后用原有正负例回归，防止为了捕获一种新模式丢失旧的成立条件。

## 与日志检测连接

同一文件含标记，不等于正在执行；文件读取、进程启动和网络连接属于不同证据。把 YARA 匹配与 [[计算机知识/Kali/06-取证逆向与检测/06-GDBGefStrace与动态观察|进程行为]]、[[计算机知识/Kali/06-取证逆向与检测/08-SuricataZeek与网络检测|网络日志]] 关联时，记录路径、摘要、主机、时间和上下文，不用单个字符串来推断意图。

本包六条 JSONL 日志可用 `offline_lab.py` 汇总；其中500是一次合成HTTP状态，不是解析错误。再给日志副本插入不合法JSON，应出现带行号的错误，不能悄悄减少统计分母。检查“数据失败”和“检测阴性”的区别，是这个实验的另一半。

> [!question] 自检
> 两份样本都判断正确，能否公布精确率100%、召回率100%作为产品性能？不能。最多描述这两项夹具的结果；样本设计、真实基率和分布均不足以支持部署性能外推。

## v2 深化路径

继续用 [[计算机知识/Kali/06-取证逆向与检测/09-模糊测试Sanitizer与崩溃归因|有界解析专题]] 检查文件输入合同，再用 [[计算机知识/Kali/07-综合实验/13-实验J时间线与检测基率|实验 J]] 验证熵与检测基率。C 编译检查、Python数学测试和实际 YARA 引擎测试是不同验收项。

## 来源与核验范围

[^s1]: [YARA 官方：Writing rules](https://yara.readthedocs.io/en/stable/writingrules.html)；定位：strings / condition / filesize。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]