# 正式有限读者证据包

这是唯一正式白名单reader-evidence/；外部pilot/full raw历史不随包进入读者正文。精确11case范围/原始full.raw的SHA/列映射/选取与输出SHA见interface.json。

8个关键整窗（wanted/image/weak_LO/wanted_with_blocker/blocker_only及5ps三组）保留500ns..1us全非均匀点和紧邻左边界的一条原始点，用于原算法线性插值端点；没有抽稀或生成均匀点。baseline及large_signal两组仅最后一个IF周期900ns..1us，供图与局部观察，不能冒称可重算原500ns整窗表；其原整窗数值仍在results.json，重建需按deck重跑。

列为time_s、vdiff=op−on、common_mode=(op+on)/2，17有效数字回读double精确；每个gzip载入后可按interface校验明文字节。所有case保deck、原始ngspice.log、真实command-result或明确由执行源解释的command-context、可用config。LNA三案保全部小OP/AC/noise文件。固定卡副本与原卡同版。

仅复算交付整窗，无新模拟：`python recompute_compact.py --output NEW.json`或`python summarize.py --output NEW.json`（Python+numpy）。对应source summarize.py保留全波形重建路径；先用generate_mixer.py生成各最终case，再在其目录经项目run_local --timeout300调用ngspice47，产生完整waveform.txt后可运行summarize.py。包内4个处理/生成源仅把fixed-inputs定位改为本包相对路径；未以路径化源码重新模拟。check_timestep.py需ngspice并会重建5ps完整数据。

ngspice47/arm64官方source及binary身份见actual-binary.txt；软件准备环境不进入包。所有.noise仅对平稳LNA；MOS1周期LO噪声/物理工艺/硬件、周期稳态与IM3均未验。弱LO与blocker-only小残余只称有限窗口投影；5ps变化见convergence-step5ps/results.json，不报虚假的精确物理失真。

更细执行合同/旧常量来源/LO条件与原始历史在临时区spice/README.md；不依赖它才能重算本包关键投影。