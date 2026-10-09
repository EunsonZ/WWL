# 2026-10-10 固定输入的独立有限执行

这组记录对应课程目录的 `dynamics_lab.py`（SHA开头 d533cf313ad1）和 `fixed-inputs.json`（296f0bdfb2bb），由未参与源码编写的执行者先冻结快照，再运行并用另一实现复算。实际业务JSON在 [cli-output/report.json](cli-output/report.json)，人读回执在 [report.md](report.md)，总回执在 [report.json](report.json)。[final-source-bindings.json](final-source-bindings.json)给出完整输入身份；[delivery-copy-map.json](delivery-copy-map.json)逐项说明原始59项证据及原SHA清单的交付映射，原命令、输入、输出、失败与边界观察保持原字节。

`*-receipt.json` 和对应 stdout/stderr 保留实际命令、环境、退出码和超时上限；默认预跑60秒以内，完整业务运行上限300秒。实际默认预跑约0.075秒、保存业务输出约0.081秒。程序单进程，环境请求线程4，记录没有建立OS硬线程数或硬内存上限保证。这里的资源观察只描述这次运行环境。

[独立算术与解析结果](independent-results.json)核矩阵幂、累计量、概率多项式卷积与高精度径向解；[完整轨迹检查](trajectory-results.json)另算能量、角度与端点差；[临界精度观察](radial-boundary-results.json)保留接口拒绝和返回的两种情况。域内有限返回也没有临界附近高相对精度的普遍保证：在爆破前约10⁻¹²的请求，返回707144.0446，而声明的Decimal roundtrip输入参考约707133.1429，相对差约1.54×10⁻⁵。32epsilon护栏是保守拒绝规则，本组没有证明它是全域前向误差界。数学上仍有限的临近时点也可能因数值未分辨而拒绝；不能将所有拒绝都解释成物理爆破。

[相图SVG](assets/pendulum-phase.svg)与原输出同字节；[1000×570离线PNG](assets/pendulum-phase.png)由既有CairoSVG2.9.1生成并实际查看，轴、图例与轨迹没有裁切。渲染回执与观察在 [render-results.json](render-results.json)、[visual-observations.json](visual-observations.json)。这是离线图层，未验证Obsidian客户端、跨设备同步或真人学习。

异机复算使用上两级课程目录的源码与固定输入，只需Python3.10+标准库，并选择尚不存在的课程/工作区外部输出目录。`snapshot/README.md.txt` 和 `snapshot/AGENTS.md.txt` 是保留原字节的历史快照，其 `.txt` 后缀防止把当时说明当作当前客户端笔记或嵌套指令。原辅助脚本与原命令用于追溯当时执行，包含当时路径；搬运后不要直接照旧绝对路径执行它们。没有复制环境、缓存或编译文件。

这些有限结果不证明一般LaSalle、Hopf、强大数定理、现实金融危机或真实器件参数。对应一般论证和模型条件在课程正文中，重要内容由独立核查者另行核对。
