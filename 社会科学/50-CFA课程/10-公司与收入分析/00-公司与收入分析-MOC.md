---
domain: social-science
type: moc
content_status: draft
evidence_status: partial
evidence_note: "2026/2027 CFA一级公开纲要、CFA公开模块与IFRS 15官方资料已定位；合成案例和源码测试通过，非机械内容待独立复核，未验收真实客户端或人的理解。"
aliases:
  - 公司组织商业模式ROIC与收入确认路线
sources:
  - https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026-l1-topics-combined.pdf
  - https://www.cfainstitute.org/sites/default/files/2027levelitopicoutline_online.pdf
  - https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/organizational-forms-corporate-issuer-features-and-ownership
  - https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/business-models
  - https://www.ifrs.org/issued-standards/list-of-standards/ifrs-15-revenue-from-contracts-with-customers/
prerequisites:
  - "[[社会科学/50-CFA课程/10-三张财务报表权责发生与现金勾稽|三张报表与现金勾稽]]"
---

# 公司与收入分析：同一门生意为何需要不同资本，也产生不同收入与现金

读者要解决的是一条连续问题：**组织和所有权怎样限制融资，商业模式与竞争怎样决定资本占用，资本怎样转成经营回报；客户付款、履约和会计收入不同步时，又怎样判断利润质量与估值输入？**

本组以原创合成公司“澄桥设备云”为主线，金额统一为百万元本币，税率和合同条件只为教学设定。它补足[[社会科学/50-CFA课程/04-一级伦理财报公司财务年度核对表|04年度核对表]]明确保留的组织形式、商业模式和ROIC缺口，并扩展[[社会科学/50-CFA课程/11-收入存货长期资产与报表调整|11课]]只有单一预收设备的收入例。它不会复制[[社会科学/50-CFA课程/20-资本预算增量现金流与项目选择|20课]]的项目NPV、[[社会科学/50-CFA课程/21-WACC资本结构分派与治理|21课]]的资本结构，也不会把[[社会科学/50-CFA课程/61-公司估值多信息案例与模型选择|61课]]的完整FCFF估值再做一遍。

## 按问题选择入口

| 读者问题 | 先读哪里 | 能带走的检查动作 |
|---|---|---|
| 独资、合伙、私人公司与公众公司只是名称不同吗？ | [[社会科学/50-CFA课程/10-公司与收入分析/01-组织形式所有权与融资边界\|01组织形式、所有权与融资]] | 按法域、法律人格、责任、控制、税、披露、证券流动性与融资渠道逐项比较，不把通用教材描述当本地法律结论。 |
| 同样收入200，为什么一家公司需要更多资本？ | [[社会科学/50-CFA课程/10-公司与收入分析/02-商业模式竞争与资本需求\|02商业模式、竞争与资本需求]] | 从客户、价值主张、渠道、定价和价值链追到毛利、营运资本、固定资产与风险。 |
| 高ROIC是否自动意味着价值创造和高估值？ | [[社会科学/50-CFA课程/10-公司与收入分析/03-ROIC再投资增长与价值判断\|03 ROIC、再投资与增长]] | 固定NOPAT与投入资本口径，区分综合ROIC和增量回报，用资本成本检查经济利润。 |
| 签了合同、开了发票或收了现金，哪一刻才是收入？ | [[社会科学/50-CFA课程/10-公司与收入分析/04-客户合同履约义务与收入确认\|04客户合同与收入确认]] | 走完合同识别、履约义务、交易价、相对单独售价分配、时点/期间确认和合同余额。 |
| 收入增长、利润增长与现金增长背离，如何分析？ | [[社会科学/50-CFA课程/10-公司与收入分析/05-利润质量现金勾稽与估值限制\|05利润质量、现金与估值限制]] | 用余额变动重建收入—现金桥，查判断、可收性和资本需求，明确哪些数字还不能进入估值。 |
| 如何独立复算而不相信页面舍入？ | [[社会科学/50-CFA课程/10-公司与收入分析/90-公司与收入分析复算\|90复算]] | 运行标准库源码与测试，重绘同数值SVG，检查非法输入和代码镜像。 |

推荐路线是01→02→03，再读04→05→90。公司线回答“赚钱需要占用多少资本”；合同线回答“何时形成会计收入、应收或合同余额”；05把两线合并，防止把高利润率、高ROIC或高经营现金中的任一个指标单独当作估值结论。

![三种组织与所有权状态如何改变融资和可观察信息](assets/org-capital-map.svg)

## 年度范围与准则边界

[2026 Level I公开纲要](https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026-l1-topics-combined.pdf)显示页9–10的Corporate Issuers与[2027纲要](https://www.cfainstitute.org/sites/default/files/2027levelitopicoutline_online.pdf)显示页9–10的Corporate Finance均列组织形式/发行人特征/所有权、资本分配中的ROIC及Business Models；2027 FSA显示页11的Analyzing Income Statements列收入确认一般原则、具体应用和分析影响。本组只兑现这些公开范围中的明确子问题，不复制官方LOS清单，也不据模块映射声称整门课程完成。

收入确认采用IFRS 15的合成案例。[IFRS 15官方入口](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-15-revenue-from-contracts-with-customers/)说明五步模型与控制转移；具体段落定位引用IFRS Foundation公开的2021 issued text。准则的现行修订、当地采用版本、监管解释、合同可执行性、税务与法律责任须按实际报告期和法域另查。本组不是会计处理意见、法律意见、税务意见或投资建议。

## 证据与完成状态

机械层已经由同目录源码和测试核对：交易价120分配为系统96与监测24；两份合同收入126可与现金、应收和合同余额勾稽；ROIC使用平均投入资本；增长桥使用增量NOPAT与净再投资；三张SVG由同一源码生成。公开资料定位、合成案例机制和页面解释仍要经过独立复核；真实财报、真实合同、全部IFRS 15应用、US GAAP Topic 606差异、Obsidian客户端呈现及人的掌握均不在本页已验证范围。

