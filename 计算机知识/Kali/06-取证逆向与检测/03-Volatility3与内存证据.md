---
domain: "计算机知识"
type: "course"
stage: 5
prerequisites:
  - "[[计算机知识/Kali/06-取证逆向与检测/01-取证流程镜像与时间线|取证流程镜像与时间线]]"
  - "[[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|进程服务日志与本机加固]]"
sources:
  - "https://volatility3.readthedocs.io/en/latest/volatility3.plugins.windows.psscan.html"
  - "https://volatility3.readthedocs.io/en/latest/_modules/volatility3/plugins/windows/pslist.html"
  - "https://volatility3.readthedocs.io/en/latest/volatility3.framework.layers.html"
  - "https://volatility3.readthedocs.io/en/latest/getting-started-linux-tutorial.html"
  - "https://volatility3.readthedocs.io/en/latest/getting-started-windows-tutorial.html"
content_status: "usable"
evidence_status: "partial"
---

# Volatility3与内存证据

**先修关系：** [[计算机知识/Kali/06-取证逆向与检测/01-取证流程镜像与时间线|取证流程镜像与时间线]]；[[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|进程服务日志与本机加固]]。

## 内存快照是结构化但不完整的现场切片

Volatility 3 从内存镜像解析操作系统结构。它需要匹配的层、符号信息和插件支持，不是在文件里搜索几个字符串就得出进程全貌。Volatility 2 的 `--profile` 教程不能直接移植到 Volatility 3；命令入口也依安装方式可能是 `vol`、其他打包命令或源码目录中的 `python3 vol.py`。[^s1][^s2]

本包没有内存镜像，不采集正在使用的主机内存，不下载符号文件。内存数据可能包含口令、令牌、私密文档和第三方信息，不能为了“让结果可复现”直接公开。

## 补强：从字节到进程列表，中间至少有三层假设

第一层是采集文件是否覆盖目标时刻的所需物理内存。第二层是地址转换：如何从内核或进程虚拟地址定位到采集文件中的字节。第三层是结构解释：用匹配的符号和类型信息，把这些字节解释为任务、模块或套接字结构。某个插件显示空表，可能是对象不存在，也可能是在其中一层失败；两者不能合并成“未发现异常”。Volatility 3 的 Linux 教程把内存采集与分析分开，并要求匹配相应内核的符号表。[^v2-vol]

内核版本字符串相似不保证结构布局相同；构建配置和调试信息也重要。看到多个 banner 候选时，先记录其偏移和上下文，不默认第一条就是真实运行内核。插件启动前的 requirement 错误要保留原文以及工具版本、镜像哈希和符号来源，不能只截取空结果区域。

## 地址翻译层与结构解释层不是同一件事

Volatility 的 layer（层）描述地址如何映射到可读取数据；符号与类型描述这些字节应按何种布局解释。一个进程虚拟地址可能先经页表翻译到物理位置，再经转储格式映射到文件位置，最后才能读取字节。API 中的 `mapping`、`translate`、`read` 对应这些不同职责，不应把所有输出偏移都当作镜像文件中的字节位置。[^v5-vol-layers]

原创推演：假设某虚拟页映射到物理页 P，而采集格式没有保存 P。页表关系存在不代表读取能成功；不能把缺失页填零后断言该结构全零。换一种情况，字节能读取但类型版本错误，字段偏移落在别的成员上，输出也许仍是“看起来合理”的整数。这分别是**可用性问题**和**解释问题**，修复符号不会补回未采集的页，补齐数据也不会自动纠正类型解释。

这一层次与 [[计算机知识/Kali/06-取证逆向与检测/05-GhidraRadare2与静态逆向|文件偏移、静态地址和运行地址]] 相通：十六进制外观相同不是地址空间相同。跨工具比较前，至少标注地址种类、架构、映像身份和转换依据。

## 先确认入口、平台与符号

```bash
# 以下以已审阅的官方源码目录为例；vol.py 并未随本包附带。
python3 vol.py -h
python3 vol.py -f own-windows.mem windows.info
python3 vol.py -f own-windows.mem windows.pslist
```

这些是官方 Windows 教程中的基本插件路径；插件全名和帮助随版本变化，应按本机输出核对。`windows.info` 用于检查层和系统信息；如果符号解析失败，先处理匹配条件，而非把空的进程结果解释成“没有进程”。符号获取可能联网，严格离线环境需提前准备经允许的材料。[^s2]

Linux 镜像同样需要恰当符号；发行版名称相同不足以保证内核构建匹配。先阅读该版 Linux 教程，核对插件可用性与符号生成/取得方式。不能拿一个近似版本的符号让工具勉强运行后，就把输出当成真实结构。[^s1]

## 多条观察路径为什么重要

结构遍历、扫描残留对象、命令行、模块和网络连接是不同观察窗口。比如进程列表和某种对象扫描结果不同，解释可能包括对象残留、采集不一致、结构变化或异常隐藏；**差异只是线索，不自动证明隐藏进程。** 若需比较 `pslist` 与其他插件，先读该平台当前插件帮助，确认覆盖对象和状态。

PID 是标识，不是永久身份；进程可退出后被复用。把进程创建时间、父子关系、映像路径和命令行连接起来，再对照 [[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|主机日志]] 与 [[计算机知识/Kali/06-取证逆向与检测/08-SuricataZeek与网络检测|网络连接日志]]。敏感内容在加工报告中应最小化或脱敏，原始证据按访问控制保管。

## pslist 与 psscan 的差集是待解释集合

当前所读 `PsList.list_processes` 实现沿 `PsActiveProcessHead` 及进程链接遍历；`PsScan.scan_processes` 使用池扫描与约束寻找候选。源码中还显式处理终止状态、采集不一致和无效地址等情况。因此，“另一张表里没有”并不是一个含义固定的告警。这里是文档和源码阅读，不是实际内存样本测试。[^v5-vol-pslist][^v5-vol-psscan]

设链表视图为集合 $L$，扫描候选为 $S$。$S\setminus L$ 只意味着“满足扫描条件但未出现在此次链表输出”，不能直接等同于隐藏恶意进程。可竞争的解释包括终止后残留对象、采集期间结构变化、过滤条件不同、某一视图读取失败、候选误识别，以及确有异常摘链。比较时还需防止 PID 重用造成错配，尽量结合对象位置、创建时间、退出状态和其他结构关系，而非仅连接 PID。

一个有帮助的反证是：若候选退出时间早于采集、活动线程为零且相关结构支持已退出，那么“它正在隐藏运行”的解释被削弱；但这并不自动证明该进程历史行为无害。每条新证据只更新它能约束的命题，不能替整个系统洗清或定罪。

## 补强：用交叉视图形成待检验假说

对一个可疑进程，依次核对：进程身份是否可能被 PID 重用混淆；创建和退出时间是否合理；父进程关系是否与采集时刻一致；关联映射、命令行及可用日志是否相符。链表遍历、扫描残留对象和其他来源反映的对象集合不同。某项只在扫描结果中出现，可能是残留，也可能是隐藏，还可能是误识别；必须检查对象有效性，而不是给差集自动贴“隐匿进程”标签。

同理，可执行且可写的匿名内存应提高检查优先级，但 JIT、运行时生成代码或特定合法软件也能产生相关现象。下一步是检验所属进程的正常机制、内存内容与控制流，不能从单个权限标记推出恶意结论。

本包不附真实内存镜像，也未运行内存采集或 Volatility。用这些步骤规划证据与解释边界，不将教材中的进程名当成已观察到的实验结果。对内存插件的失败诊断，先回到 [[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|观察与结论]]，再选择补证工具。

## 将失败也纳入结果

符号缺失、镜像截断、格式不支持和插件运行异常都应记录为未完成或失败，不是阴性证据。即使成功列出进程，也不代表采集瞬间所有物理内存都一致；运行中采集可能跨越多个状态。声称某行为“从未发生”通常超出单个快照的证明力。

> [!question] 自检
> 一张镜像里找不到某进程名，能否排除它昨天运行过？不能。该镜像的时间、驻留状态、名称变化和解析覆盖均限制结论。写成“在本次镜像及所用方法下未观察到”，并说明还需要何种日志支持更强结论。

## 来源与核验范围

[^v5-vol-layers]: [Volatility 3：layers API](https://volatility3.readthedocs.io/en/latest/volatility3.framework.layers.html)；定位：Intel、crash 与 FileLayer 的 mapping/read/translate 接口。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-vol-pslist]: [Volatility 3：PsList 源码](https://volatility3.readthedocs.io/en/latest/_modules/volatility3/plugins/windows/pslist.html)；定位：list_processes、create_active_process_filter；读取源码而未运行。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-vol-psscan]: [Volatility 3：PsScan](https://volatility3.readthedocs.io/en/latest/volatility3.plugins.windows.psscan.html)；定位：scan_processes；virtual_process_from_physical。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Volatility 3 官方：Linux Tutorial](https://volatility3.readthedocs.io/en/latest/getting-started-linux-tutorial.html)；定位：运行方式、符号与插件。网页读取：2026-09-05。
[^s2]: [Volatility 3 官方：Windows Tutorial](https://volatility3.readthedocs.io/en/latest/getting-started-windows-tutorial.html)；定位：windows.info / symbols / pslist。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-vol]: [Volatility 3 Linux 教程](https://volatility3.readthedocs.io/en/latest/getting-started-linux-tutorial.html)；定位：符号表、banners、pslist、pstree；采集与分析职责。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]