---
type: practice
domain: artificial-intelligence
stage: 3
aliases: []
sources:
  - https://www.openslr.org/12/
  - https://github.com/espeak-ng/espeak-ng/tree/4870adfa25b1a32b4361592f1be8a40337c58d6c
prerequisites:
  - "[[AI/40-语音与音频模型/10-声学与生成/02-规则TTS真实文本到波形与错误归因]]"
---
# 真实文本到波形：本机复建与评价合同

先读[[AI/40-语音与音频模型/10-声学与生成/02-规则TTS真实文本到波形与错误归因|完整主解释]]，固定模型/许可证/语料版本与归属见[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/SOURCES|来源页]]。本实践实际生成声音但不播放、不采集、不接远程服务，不运行ASR或神经训练。

## 结果和中间对象

- [[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/inputs.json|输入]]固定模型/voice/参数、三语料ID、金额日期原句/应用合同与预先参考、三种前端及速度/pitch/削波干预。
- [[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/data/utterances.json|语料记录]]及同目录三FLAC是实际评价输入；原字节哈希、原转写/speaker/chapter都保留。三条全部evaluation，无训练与调参。摘录README的validation不被认作原库官方split。
- [[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/tts_lab.py|程序真源]]：实际有限规范化、同步C API生成及事件、独立CLI译读trace、参考解码、指标/图。[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/instrument_wavegen.py|观察插入]]只记周期声学分支；[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/prepare_engine.py|准备器]]提供依赖重建和插入前后同句PCM一致检查。
- [[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/results/results.json|总结果]]保存全部原始模型输出属性、语料属性、实际生成音素序列/计数、分派pitch中位数、前端typed对象与数字干预。音频和raw trace就在同目录，非“只有一个分数”。
- 每个实际TTS条件有`.wav`、`.events.json`、`.translation.txt`、`.acoustic.csv`、`.timing.json`。最后timing是每次执行真实墙钟/RSS观察，允许重建变化；其他模型产物按相同构建精确复建。`probe_clipped.wav`明确引用explicit源，没有伪造重新生成的事件。
- 两张同数据SVG和`assets/ai-tts/`对应副本；[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/code-sync/源码与测试镜像|活动镜像]]与四个.py真源同步，[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/test_tts_lab.py|六项检查]]只针对本链行为。

`events.json`记录引擎助记码而非IPA；位置字段原样保留，`reported_text_slice`只作机械切片，不冒精确源字区间。`acoustic.csv`每行包含dispatch/局部样本计数/control、pitch、6×4峰参数、8个整数谐波系数。峰频率/宽度是Hz，高度/谐波是内部整数尺度。`F0_hz`是第0号**谱峰**，不是激励基频；必须读pitch_hz。dispatch index不是整句秒，更不是Mel帧/codec token时间轴。

## 准备、运行与资源边界

作者实际环境：macOS arm64、Python3.14.7、NumPy2.5.2、FFmpeg9.0.1、CMake本机C/C++工具链；pyarrow26.0.0只在提取固定parquet时使用，最终运行直接用已交三FLAC，不依赖pyarrow。新隔离venv复用既有数值库，未升级系统。CMake最多4编译作业，数值库由run_local置单线程；无远程/GPU。

编译/安装属于准备，另列；不计TTS运行时间。准备器需要新的空目录以保全已有工作：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- /private/tmp/wwl-next-165-tts/build/python-env/bin/python -B AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/prepare_engine.py --work /private/tmp/wwl-tts-prepare-new
```

`python-env`是作者临时隔离环境路径；另一台可用具备NumPy的Python执行。准备器原归档下载/哈希、Sonic编译、eSpeak原模型编译/隔离安装、固定句先生成、加观测插入再生成，要求前后WAV逐字相同；不写全局库或项目Git。

实际完整实验（WWL根目录）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- /private/tmp/wwl-next-165-tts/build/python-env/bin/python -B AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/tts_lab.py --engine /private/tmp/wwl-next-165-tts/build/espeak-install --ffmpeg /opt/homebrew/bin/ffmpeg --output /private/tmp/wwl-tts-rebuild
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- /private/tmp/wwl-next-165-tts/build/python-env/bin/python -B -m unittest discover -s AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形 -p test_tts_lab.py
```

另一台没有临时runner时直接执行其`--`后的课程命令。当前动态库路径按本次Mac构建的`.dylib`，不声称所有平台可原样运行或逐位相同。非Mac可先适配同一API的库路径，再独立核行为/数值。

先有单词`one`的短worker预跑，再跑3参考+8生成条件（其中probe_explicit是3.170431秒）；父程序为每个条件启动新worker，使生成状态不互相污染。每worker禁用播放/异步，最大输入1000 ASCII字符，固定三条小FLAC，全部实际短音频；未执行长文本/长时服务。Mac在本沙盒拒绝降低RLIMIT_AS，因此实现**固定负载上界+阶段前后测量RSS与8GiB超界拒绝**，不是虚称OS硬内存配额。当前最大worker峰RSS约40.2 MB，远低于8GiB；准备工具的并发/库安装另有日志，不与此数混合。CPU具体型号读取被沙盒拒绝，不能据本时延报告硬件排名。

正式运行记录包括：explicit69908样本/22050、slow86635样本、pitch69604样本；三真实录音时长5.855/4.815/12.485秒，模型对应4.616916/3.118367/8.847528秒。后处理×4饱和3.3358%，波形参考到误差比约−7.405 dB，不能解释成人类质量分。六项本机检查PASS，原始实际数值见JSON。

## 重要性、独立预期与失败判据

| 实验/断言 | 重要性和原因 | 独立预期/容差及失败 | 当前结果/边界 |
| --- | --- | --- | --- |
| 模型与真实数据身份/许可/拆分 | 高；错误身份可使整链无意义 | 实读官方commit/语言与方法、OpenSLR许可；3FLAC哈希精确相等，原元数据mono16k，非训练/单speaker不冒跨人群 | 固定版本/3原字节已交；HF摘录与上游分开，未双源逐字认证 |
| 实际规范化和语义合同 | 高；下游不能默默修正上游目标 | 独立整数USD cents和DD/MM解析→1250cents/4月3日，词串与预注册参考逐字相等；MM/DD应换3月4日；bad路径不同且无typed语义 | normalize_probe确实执行，不是手填“正确”标签；这是前端合同检验，不是音频WER |
| C API译读/事件/声学/实际WAV | 高；只看API框图不足 | 独立读ABI、原事件/字节，22050Hz/mono/PCM16，N/fs精确；事件ms非降且不超过文件末+1ms；原型插入前后PCM字节全等；CSV first pitch94.04492188/peak0=284，单位/定点解释正确 | 全中间材料已生成；API事件不冒录音真值，周期trace不代表所有辅音 |
| 固定音素与速度/pitch替换 | 高；归因不能凭听感猜 | explicit/slow/pitch的非空phoneme序列相同；175→140时长增长但不要求所有时长恰×1.25；pitch knob50→75使实际参数改变，不将75当Hz | 3.170431→3.929025秒；pitch median101.794→131.137Hz；finite事实不推广全部语言 |
| 后处理失败 | 高；这是可复现实际波形损伤 | 独立逐整数算clip(4q)，全部69908样本精确一致；重新求饱和比例/RMS误差，浮点容差1e−12；词/声学事件源仍为explicit | 3.3358%饱和、误差RMS .208375，不代表某个自然度下降幅度 |
| 三句真实参考评价与自动边界 | 高；易拿输入文本当识别成绩 | 单独解码原FLAC，不用错误采样率；时长、峰/RMS/样本数误差≤1e−12；没有ASR/听测就不生成WER/MOS/身份分 | 图只比时长，单speaker/单chapter描述性结果，不做统计泛化 |
| 图/重建/镜像 | 中；图必须消费本次结果 | 同工具链重新生成，WAV/events/translation/acoustic/results及两图逐字同；timing墙钟/RSS允许变化并必须真实保留。两asset与结果SVG相同，坐标容差1e−3px（写4位） | 重绘从真实参数/样本读取，非手画理想音素；实际Cairo只核显示，不代听测 |
| 真人可懂度/自然度 | 高；不能被程序自动替代 | 下一节的盲听原始记录、实际设备/参与者/随机条件齐全后才能出结果；当前状态必须not_performed | 固定材料与空模板已交，无听者、无播放、无质量分 |

同版重建的byte目标限定当前工具链；换平台/编译器导致PCM差异须单独定位，不用宽松均值容差掩盖前端或事件路径改变。timing是一次初始化后离线调用，不包含下载/编译/库初始化、trace CLI/文件写入、播放/网络；不作为首响/真实双工指标。

## 固定听测材料与空记录接口

本包确有可听WAV和真实参考FLAC，但没有实际播放或招募。[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/听测记录模板.csv|空模板]]只含字段。分两套任务，不能拿一个数字包办：

1. **内容/可懂度**：预先固定USD/DDMM应用合同，先盲听raw/explicit/bad条件、随机顺序，原样记录转写及能恢复的金额/日期；允许不确定，记录实际错/漏/增与typed槽位。参考转写与评分规则在听者作答前固定，不能让模型代听者填写。raw的表面字串可正确读成“零三斜杠零四”，但业务日期表达仍需另一合同评分，两个目标分列。
2. **自然度**：在同一文本、设备/播放设置下单独预设评分标尺与随机材料顺序，保存每次原始回答/缺失、听者与试次单位，再报告统计；无足够真实记录不推人群结论。不要用与真实录音的时长更近代替自然度。
3. **模块失败**：explicit/clipped或正常/慢速可作独立干预任务，先盲记观察再解释改了哪层；音量、播放器音效与重采样必须记录，任何响度匹配处理要另存材料版本。

不默认采集新人的语音，不推断原参考speaker身份；原公开数据归属继续随材料保留。高重要性的真人证据不可由走读冒充，但缺真人不妨碍当前本机理论/软件链已实际完成。

## 原完整要求定位与真正未验项

| #165原目标 | 当前所在与证据 |
| --- | --- |
| 1 同短声音的时间/频率/帧与基频/共振/token区分 | 已交01和80原实验；本包再落实22050样本率、事件ms、内部dispatch与峰0/激励pitch的区别，不重跑旧课 |
| 2 含数字/歧义的一句直到波形及错误层次 | 本页/新02实际USD/DDMM探针、规范化/译读/日程/参数/PCM，前端/速度/pitch/削波干预 |
| 3 完整所选链目标/对齐/维度/推理 | 新02选定规则TTS，手工规则目标、无训练loss；固定C源码/音素与声学数据/事件类型/谐波分支实际解释，不借神经设计文档冒实现 |
| 4 合法小语料/模型身份/拆分/可核输出及分开指标 | SOURCES、3原FLAC/转写/哈希、固定commit/voice、全部eval/单speaker边界与完整软件输出；没有WER/MOS/身份分或真实流式承诺 |
| 5 可控替换复现真实任务失败/合成边界/实际听测才报 | 数字前端错合同与真实引擎输出、后处理真实样本损伤已做；真人状态not_performed，高重要性固定材料和空记录接口，未代填 |
| 6 codec固定20000bit/PCM3840000bit/比192与质量分开 | 已交01指定算术继续复用，当前明确选择模块式路线，不扩成必须跑第二条codec链 |

本包可自主的软件与论证部分已交；原要求允许真实听测未发生时只报告声学/任务/静态结果，所以范围判断须据完整同版非作者审阅与正式发布，不假装听过。一般神经TTS训练、其他语言/人群、长期服务与真人质量结论未验，不能从有限课闭合外推。本页明确每项边界，不自行把更多研究方向加成无限新门槛。返回[[AI/40-语音与音频模型/10-声学与生成/02-规则TTS真实文本到波形与错误归因#练习与答案：改合同，先改预期|六题与答案]]。
