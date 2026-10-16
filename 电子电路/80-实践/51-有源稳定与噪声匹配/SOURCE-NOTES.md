# 承重来源与本包自行推导的界线

本页是复核入口，不把课程目录当证明。2026-10-17通过原站实际读取下列承重段；外部页面以后可能更新，公式约定以正文明确对象为准。

- [MIT 6.776 Lecture11，2005](https://ocw.mit.edu/courses/6-776-high-speed-communication-circuits-spring-2005/38ea1be09825024cd20eb09a0d5703d0_lec11.pdf)：PDF第8页给输入电压/电流噪声相关，第10–12页讨论最小噪声源导纳、噪声圆与功率传输最优不同。这里借用问题和前提；本包outgoing噪声波N、具体相位及全部数字是教学构造并自行展开，不把MIT输入等效坐标的相关项直接当C12。
- [Qucs Technical Papers，node9，Noise parameters](https://qucs.sourceforge.net/tech/node9.html)：2.12–2.15给噪声相关矩阵与噪声参数的关系，2.21–2.24为源反射域F和噪声圆。核对Rn归一、复共轭和因子4；正文重新定义Cij方向并从四波推导，避免跨坐标套同名项。
- [Keysight Noise Figure帮助](https://helpfiles.keysight.com/csg/pxivna/Applications/Noise_Figure.htm)：实际说明Fmin、Gammaopt、Rn和噪声相关矩阵，Rn的Ω/归一以及290K参考。厂商帮助中采用的噪声端口记号须与本包显式坐标分别辨认，不据其仪器功能声称本次运行仪器。
- [Keysight Basic RF Amplifier Test with the E5072A，5990-9974](https://www.keysight.com/zz/en/assets/7018-03364/application-notes/5990-9974.pdf)：原站资产说明页实际列稳定因子的K/Δ无条件稳定用途。本包一般像圆/原像圆和反例自行推导，未把该单频工程判据升级成全频内部稳定定理；此链接在当前web读取呈资产说明HTML，不冒称已逐页读PDF。
- [MIT 6.776 Lecture12](https://ocw.mit.edu/courses/6-776-high-speed-communication-circuits-spring-2005/2c7a97621d644036cfed2edbcfb833ad_lec12.pdf)：实际目录/第2–3页把LNA的噪声、功率匹配、线性、功耗、带宽与PVT并列。用来界定原#186后续器件范围，本包不据此称已交付那些节点设计。

本包原创解析部分：D/Γin/out/GT与Thevenin关系、圆盘像和稳定侧、S0全局增益极值、由N推噪声参数、声明H扩展的加权H∞小增益与Sc RHP根、无损L节综合。一般结论由非作者独立推导核准；有限实现另由四波高斯消元、Y节点、逐噪声端响应和LC支路核对。不引用商业器件数据，也不把本频点PSD相容性当整个频带的因果噪声或器件存在证据。
