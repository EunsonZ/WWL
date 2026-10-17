---
type: reference
stage: 3
aliases: []
sources:
  - https://www.openslr.org/12/
  - https://github.com/espeak-ng/espeak-ng/tree/4870adfa25b1a32b4361592f1be8a40337c58d6c
prerequisites: []
---
# 固定模型、数据与归属

## eSpeak模型与实际方法

- eSpeak NG 1.52.0，官方提交`4870adfa25b1a32b4361592f1be8a40337c58d6c`。上游项目及源码按GPL-3.0-or-later发布，本包不分发编译二进制；编译、观测插入和本机输出已实际执行。[固定项目](https://github.com/espeak-ng/espeak-ng/tree/4870adfa25b1a32b4361592f1be8a40337c58d6c)
- `en-us`由`espeak-ng-data/lang/gmw/en-US`指定：英文美国规则、`en-us`音素表与词典规则3/6、重音长度/幅度等；使用当前提交自带的编译数据，没有神经权重、MBROLA声库或身份输入。[固定语言文件](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/espeak-ng-data/lang/gmw/en-US)
- 读音/数字：`dictsource/en_list`、`docs/numbers.md`及`src/libespeak-ng/numbers.c`，用于词典例外、数字分组、小数点与语言选项。不是调用外部LLM猜前端。
- 分句到声学命令：`synthesize.c`的`SpeakNextClause`实际调用`TranslateClause`、`CalcPitches`、`CalcLengths`、`Generate`。[固定实现](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthesize.c)
- 音素/声学数据方法：`docs/phontab.md`说明FMT、WAV、addWav等不同指令；`docs/intonation.md`说明按标点的tune与nucleus。`docs/phoneme_model.md`自述尚未反映当前实现，不能据它认证本包声学算法。[固定phontab](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/docs/phontab.md)、[固定intonation](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/docs/intonation.md)
- 波形：`wavegen.h`声明`freq/left/right`的Hz<<16与高度尺度；`wavegen.c`的`PeaksToHarmspect`、每64样本参数调整与谐波合成是本次实际周期分支。插入脚本只在该函数返回前记录，不代表覆盖采样辅音/暂停/其他分支。[固定wavegen](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/wavegen.c)
- ABI：`src/include/espeak-ng/speak_lib.h`的事件结构、同步retrieval模式、PHONEME事件开关和rate/pitch/volume参数。`sample`字段为内部用途，本包不拿它充全句时间；时间只保存`audio_position`毫秒并注明语义。[固定头文件](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/include/espeak-ng/speak_lib.h)

以上方法均由作者实际读固定源码/文档并运行；没有用搜索摘要替代实际路径。预热、编译缓存与参数来源分别保留，不能把可用分支/库特性当本次默认声音全部走过。

## 构建来源

准备器只写给定新空目录，下载两个固定归档、验证SHA256，然后本机4作业编译/安装。实际归档为：

| 来源 | SHA256 |
| --- | --- |
| `https://api.github.com/repos/espeak-ng/espeak-ng/tarball/1.52.0`（对应上面固定commit） | `2b56ec2b03a19e63ea5ead7f605a1d6adac33c19859c23a6da7b0c618fb7dddf` |
| Sonic `fbf75c3d6d846bad3bb3d456cbc5d07d9fd8c104`归档，CMake上游固定依赖 | `6e60badda11fc663a771281cd731a8cc51cb8c24ab0fbc5c810aced0d2cd43ce` |

Sonic源码归档保留上游许可证与原文件，项目按Apache-2.0发布；本包不重写/分发其库。构建为libsonic ON、libpcaudio OFF、async OFF、MBROLA OFF、speech-player OFF、shared ON；库支持Klatt但本任务没有选择Klatt声音。编译期准备独立于数值/生成RTF，不将下载编译算成模型运行时间，也不升级系统。

## 真实录音归属、许可与摘录

LibriSpeech：Vassil Panayotov、Guoguo Chen、Daniel Povey、Sanjeev Khudanpur（2015），“LibriSpeech: an ASR corpus based on public domain audio books”，ICASSP。上游说明16kHz朗读有声读物，来自LibriVox，并在资源页列明CC BY4.0。[OpenSLR12原说明与许可](https://www.openslr.org/12/)、[CC BY4.0](https://creativecommons.org/licenses/by/4.0/)

本包音频来源为此语料的HF小测试摘录，`hf-internal-testing/librispeech_asr_dummy`固定revision `5be91486e11a2d616f4ec5db8d3fd248585ac07a`；选择三条ID/同一speaker与chapter。HF README给出73条、`validation`及字段，但未写许可或上游split映射；上游归属/许可与本摘录身份在此分开，不制造HF独立授权或官方背书。实际parquet SHA256=`4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603`。[固定摘录与README](https://huggingface.co/datasets/hf-internal-testing/librispeech_asr_dummy/tree/5be91486e11a2d616f4ec5db8d3fd248585ac07a)

保留三份原FLAC字节和原转写，未编辑录音：

| ID | SHA256 |
| --- | --- |
|1272-128104-0000|`4e25e22555cd16e90edb0a3b49fdcf1fe652b2a1250ab643634db33895c75b41`|
|1272-128104-0001|`46a9d58622b4675b29564da2d9ba73e702241c5fa969f12c387cad4aa984276a`|
|1272-128104-0002|`59bf7bb1129c11734a8dd362ad52b4e10ae31c03f0879fc92f7107ecd513513f`|

这些记录都作描述性评价，没有训练/调参，没有跨speaker拆分。只核固定摘录字节，未下载完整上游库做双源逐字认证；不推断原说话人身份或许可之外的属性。本包新WAV均标合成，未以参考speaker作生成条件；削波WAV明确是对同一合成结果的变换。

返回[[AI/40-语音与音频模型/10-声学与生成/81-真实文本到波形/README|复建与实际证据]]。
