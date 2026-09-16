---
domain: "计算机知识"
type: "course"
stage: 2
prerequisites:
  - "[[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|从观察到结论的安全方法]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/04-Nmap服务识别NSE与结果管理|Nmap服务识别NSE与结果管理]]"
  - "[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]"
sources:
  - "https://www.first.org/epss/"
  - "https://www.first.org/cvss/v4.0/specification-document"
  - "https://docs.projectdiscovery.io/templates/reference/matchers"
  - "https://docs.projectdiscovery.io/templates/protocols/http/basic-http"
  - "https://docs.projectdiscovery.io/opensource/nuclei/running"
  - "https://greenbone.github.io/docs/latest/"
content_status: "usable"
evidence_status: "partial"
---

# 漏洞扫描NucleiGreenbone与复核

**先修关系：** [[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|从观察到结论的安全方法]]；[[计算机知识/Kali/02-信息收集与网络测量/04-Nmap服务识别NSE与结果管理|Nmap服务识别NSE与结果管理]]；[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]。

## 扫描器返回候选发现，不返回最终判决

漏洞扫描通常把已知检查模板、服务指纹与响应模式结合起来。它能加快覆盖，却也会产生误报、漏报和无效检测。区别在于：误报是错误地报告存在问题；漏报是存在问题却未报；超时或未认证是“没有完成有效观察”，不能自动归类为没有漏洞。

先确认 [[计算机知识/Kali/02-信息收集与网络测量/04-Nmap服务识别NSE与结果管理|服务与配置]]，再选择与其相关的少量检查。一次性运行所有模板，会同时增加负载、结果噪声与解释难度。

## 把自动检测拆成五个职责

一条扫描流水线可以拆成：资产选择、请求或数据采集、响应解析、条件匹配、发现归并与报告。Nuclei 模板把请求与判断组织起来；Greenbone 类管理体系还要管理目标、任务、检测内容和结果生命周期。前文已有组件介绍，这里重要的是：某一层成功，不保证后面每一层都得到有效输入。

例如任务显示完成，但身份失效导致全部请求到达登录页，这只说明一项任务结束，不能说明受保护业务被扫描。又如模板根本未被选中，零命中不能当作该漏洞不存在。审阅时同时保留运行完成状态、实际到达范围和匹配条件。

## Nuclei：审阅模板再运行

Nuclei 以模板表达请求和匹配条件；模板可能涉及不同协议、认证、外部交互或其他执行能力。工具版本和模板版本分别影响结果，必须同时记录。[^s1]

```bash
nuclei -version
nuclei -h
# 仅示意：已人工审阅 approved-check.yaml，目标为自建回环服务
# nuclei -u http://127.0.0.1:8000 -t ./approved-check.yaml \
#   -rl 2 -c 1 -jsonl -o ./output/nuclei.jsonl
```

本包不附未经核验的远程模板全集，也不自动下载模板。运行前确认模板实际发出的请求数、重定向行为、匹配依据和数据去向；模板的严重性字段只是作者评价，并不自动成为你组织里的业务风险等级。

`-rl`、并发与超时控制的是不同维度。模板执行数不一定等于请求数；重试、重定向和多阶段检查会改变总请求量。需要严格预算时，选择已知请求路径的小模板并结合日志计数。

## 读懂 matcher 的逻辑，才能读懂告警

Nuclei 的匹配可以作用于状态、词、正则、二进制或表达式等信息；多个 matcher 的组合以及单个 matcher 内部条件是不同层次。文档说明多个 matcher 默认按 OR 组合，需要全部满足时应明确 AND；负匹配表示在其检测对象上取相反条件，不等于工具出错时也获得一个可靠阴性。[^v5-nuclei-match]

原创纸面例子：令 $A$ 表示响应为预期状态，$B$ 表示出现教学产品标记。如果设计意图是“正确页面上出现标记”，需要 $A\land B$；若误用 $A\lor B$，普通成功页或带标记的错误页也能进入候选集合。真值为 $(A,B)=(1,0)$ 时，前者是假、后者是真。这个区别是布尔逻辑，不需要发送任何探测即可检查。

再把标记换成登录页面通用文字，即使 AND 写对也仍可能缺乏区分力。检测表达式的**逻辑正确性**与特征的**安全相关性**不是一回事。前者用真值表检查，后者要用带已知条件的正例、反例和边界例确认。结果解释由 [[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|证据方法]] 统一约束。

## 附带一个只识别教学页面的 Nuclei 模板

[[计算机知识/Kali/07-综合实验/代码/public-health.yaml|public-health.yaml]] 仅请求 `/health`，要求 HTTP 200 且正文同时含两个公开教学标记；严重性为 info。命中表示“响应匹配课程夹具特征”，**不表示存在漏洞**。模板没有口令、数据库读取、带外回连或代码执行逻辑。HTTP 模板与匹配器字段按上游文档编写。[^v2-nucleihttp][^v2-nucleimatch]

在另行安装 Nuclei、确认其当前帮助之后，先做本机模板校验，再按实验 A 显式启动回环服务。下面仅为参考；当前交付只检查 YAML 结构与教学匹配条件，未执行 Nuclei 引擎。

```bash
# 本地校验入口；本机没有 Nuclei 时不要把结果写为通过。
# nuclei -validate -t ./public-health.yaml
# 显式启动本机静态服务后才允许该单目标操作。
# nuclei -u http://127.0.0.1:8000 -t ./public-health.yaml \
#   -rl 1 -c 1 -retries 0 -timeout 3 -jsonl -o ./output/health-check.jsonl
```

模板选择本身不构成整个工具绝不联网的保证；全局配置、版本检查和更新行为应在实际版本中检查。需要严格断网时使用操作系统层的网络边界，不把一个模板中的固定 URL 当沙盒。

把两个 matcher 的组合从 AND 改成 OR，会使“状态正常但页面不相关”的响应也可能命中；把 words 的 condition 改成 OR，则可能只有一个教学标记就命中。这是两层独立逻辑，应分别设置正例和反例。

## Greenbone / OpenVAS / GVM

这些名字涉及扫描引擎、管理与界面等不同组件，具体组合以当前官方部署文档为准。[^s2] 不要把旧教程中的单条初始化命令当成跨版本保证。完整平台涉及服务、数据库、漏洞数据 feed、任务与凭据，部署成本高于单个命令行工具。

合理流程是：确认版本与 feed 状态 → 创建精确目标 → 选择扫描配置 → 在维护窗口运行 → 阅读检测细节 → 人工确认 → 复测。具备凭据的检查可能提高本机配置可见性，但凭据权限和保管风险也增加；无凭据扫描没看见本地补丁，不等于补丁不存在。

本包没有替你启动 GVM 服务、同步 feed 或扫描任何目标。菜单名、默认配置和部署参数需要在你安装的版本中再次核对。

## 扫描平台的有效性检查表

GVM 类平台的 feed 更新成功，只说明相关数据更新阶段成功；扫描器可连接、目标可达、凭据可用、检查实际执行、结果完整又是后续五个条件。认证扫描特别要区分“连接成功”和“获得足够的只读系统证据”。凭据被锁、权限不足或服务拒绝，会让发现数量下降，却不代表漏洞减少。

## 从指纹匹配走向漏洞证据

对每条候选发现，分别记录：扫描器原文；它实际观察到的响应；推断依赖的版本/配置条件；独立验证；尚未排除的解释。版本匹配不够时，不通过重复扫描让自己“更有信心”。

例如 HTTP 首部显示旧版本字符串，但管理员提供了厂商安全补丁回移记录。正确结论可能是“banner 暴露旧字符串，漏洞适用性待结合补丁确认”，而不是删除管理员证据或盲目相信扫描器。

## 指标与优先级

查准率为 $TP/(TP+FP)$，召回率为 $TP/(TP+FN)$，其中 TP/FP/FN 必须由独立的真值或审定过程定义。未核查全部目标时通常不知道 FN，因此不能随意宣称扫描召回率。分母为零时指标未定义，不填写 100%。

修复优先级综合可利用条件、暴露范围、资产价值、现有控制与影响。CVSS 等框架可帮助描述技术严重性，但不等于本组织的损失概率或金钱风险；具体版本和向量需记录，评分不应从工具标签机械复制。

## 严重性、利用概率和业务优先级

CVSS v4.0 分开描述基础、威胁、环境等指标组；保存版本和向量，才能解释评分。EPSS 估计公开漏洞在未来 30 天被利用的概率，概率与百分位不是同一个数，也不是特定资产遭入侵的概率。[^v2-cvss4][^v2-epss]

例如候选 A 技术严重性高但功能未部署，候选 B 分值略低却直接暴露关键业务。不能仅按扫描器排序决定修复顺序。先确认适用性和暴露，再结合利用证据、资产价值、可用缓解及修复成本；任何数字缺失都应保留为未知，不代填零。

当前包不收录动态的“今日已利用漏洞清单”，避免把以后会变化的目录冻结成永久结论。需要处理真实 CVE 时，再从发布者公告、版本记录和当时的利用证据逐项核对。

## 严重性、利用可能性与本地处置顺序分开记录

CVSS v4.0 组织 Base、Threat、Environmental 和 Supplemental 指标；它描述漏洞技术特征及有关条件，不是“当前这台机器马上被攻击”的概率。EPSS 则估计已公开 CVE 在未来 30 天发生在野利用的概率，预测对象不是你某一台资产的失陷概率。[^v5-cvss4][^v5-epss]

本地处置还要结合是否真的受影响、可达性、必要权限、资产价值和现有控制。一个高技术严重性但不满足触发条件的条目，和一个分值较低却已暴露关键业务的条目，不能仅按单列数字排序。也不能把 CVSS 数字与 EPSS 小数相乘后就命名为“精确风险”，除非另外给出了经验证的模型与单位。

这些指标可以帮助提出复核优先级，却不能替代漏洞事实判定。将“匹配了公告”“目标满足前提”“影响得到最小证据支持”和“建议处理顺序”分别写入 [[计算机知识/Kali/08-模板与速查/03-发现与复测模板|发现与复测记录]]，保留版本、来源时间和未排除的解释。

## 自检

模板从“匹配服务器响应字符串”更新成“验证具体行为”后，告警减少说明什么？可能是误报减少，也可能是检查前提变严导致漏报，需要对样本做独立复核。完整报告方法见 [[计算机知识/Kali/07-综合实验/07-实验F从发现到报告复测|从发现到报告复测]]。

## 来源与核验范围

[^v5-nuclei-match]: [ProjectDiscovery：Matchers](https://docs.projectdiscovery.io/templates/reference/matchers)；定位：negative matchers / matchers-condition / internal matchers。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-cvss4]: [FIRST：CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)；定位：Base、Threat、Environmental、Supplemental metric groups。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-epss]: [FIRST：EPSS](https://www.first.org/epss/)；定位：模型目标：已公开 CVE 未来 30 天被在野利用的概率。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [ProjectDiscovery：Running Nuclei](https://docs.projectdiscovery.io/opensource/nuclei/running)；定位：单模板执行、速率、输出与模板选择。网页读取：2026-09-05。
[^s2]: [Greenbone 社区官方文档](https://greenbone.github.io/docs/latest/)；定位：产品组件与部署文档入口。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-nucleihttp]: [ProjectDiscovery：Basic HTTP](https://docs.projectdiscovery.io/templates/protocols/http/basic-http)；定位：method / path / redirects / cookies。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-nucleimatch]: [ProjectDiscovery：Matchers](https://docs.projectdiscovery.io/templates/reference/matchers)；定位：status / word / matcher AND and OR。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-cvss4]: [FIRST：CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)；定位：Base / Threat / Environmental / Supplemental metric groups。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-epss]: [FIRST：EPSS](https://www.first.org/epss/)；定位：exploitation probability within next 30 days; probability versus percentile。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]