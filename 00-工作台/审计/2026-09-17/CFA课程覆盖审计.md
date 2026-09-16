---
type: audit
audit_date: 2026-09-17
input_baseline: 0ef0ce6d23e06f4c49f35408d906e3cdcb37db7b
---

# CFA 课程覆盖审计与下一步规划

本库已经有可读的金融与宏观基础，现金流、债券局部定价、组合协方差、CAPM 边界、市场效率、一期期权复制、银行和系统风险尤其有用。但现有材料不能据此称为 **CFA Level I/II/III 全课程或达到考试深度**。伦理职业标准、完整财务报表分析、公司财务决策、另类投资、投资政策与绩效归因、Level III 三条专门路径存在大块未定位或只有相邻基础。优先补这些缺口，再扩充已有基础的题型和案例，比平行重写金融八讲更有价值。

## 1. 输入、授权与证据层

- 本次安全检索范围：社会科学、数学、AI、编程知识、计算机知识、哲学与文化，共 **984 个 Markdown 文件**。排除路径组件 `Clippings/Reserved/资料/TaskNotes/Tags/.obsidian`；未加载 Logs、历史执行单、私有会话或配置。984 是检索规模，不是语义审阅页数。
- 脚本选定版本清单包含 30 页；语义判断只绑定下面明确的页面与段落，金融八讲为重点，其余为定向抽样。检索用中英同义词，原始正则、命中行、假阳性、文件字节数、mtime 与 SHA-256 均在库外 `sources-and-evidence.json`。没有把首次截断的大输出当成全文审阅。
- 输入与根线程首次知识基线 commit `0ef0ce6d23e06f4c49f35408d906e3cdcb37db7b` 关联：30页选定输入逐一与该commit字节SHA一致；984页检索输入在交付前复查未发现字节漂移。此核对仅证明版本，不证明内容正确。
- 官方来源身份均为 **CFA Institute**，检索/打开日期为 2026-09-17。纲要以文档标题年份及页码为版本；网页未显示可靠更新日期的记为未知。纲要有 LOS，但本次未逐条验收所有 LOS，不计算全 LOS 覆盖率，不以题目数或词命中算完成率。

状态用法：**入口**＝存在导航或相邻解释；**部分**＝已有若干机制/公式/例子，未满足该课程单元；**可用**＝明确限定的基础教学目标已能兑现，仍不等于考试验收；**未定位**＝本次范围和同义搜索未找到合适解释；**未深审**＝发现材料但未充分审内容。未定位不等于不存在，尤其不涵盖被排除的私人资料。

## 2. 官方年度、级别与 PSM 边界

2026 是本矩阵主基线，2027 用来防止年度漂移。Level I 的 2026 纲要为32页，2027为31页；Level II 分别29/30页；三条 Level III 纲要分别2026为17页、2027为18页。文档份数或页数不能当知识覆盖分母。官方入口分别提供每一年的 PDF：[Level I][LI]、[Level II][LII]、[Level III][LIII]。

Level I 官网目前逐年列权重。2026：Ethics 15–20%，Quant 6–9%，Economics 6–9%，FSA 11–14%，Corporate Issuers 6–9%，Equity Investments 11–14%，Fixed Income 11–14%，Derivatives 5–8%，Alternative Investments 7–10%，Portfolio Management 8–12%。2027：Ethics 10–15%，Quant 11–14%，Economics 6–9%，FSA 11–14%，Corporate Finance 6–9%，Equities 11–14%，Fixed Income 11–14%，Derivatives and Risk Management 6–9%，Alternatives 6–9%，Portfolio Construction 8–12%。这些用于年度导航，不能套成知识页的覆盖率。[官方 Level I 年度表][LI]

2027 Level I 官方更新摘要强调 Quant 与 Equities 的实践应用重构；一级数量方法首部从2026的 Rates and Returns 转为2027的 Returns of Financial Assets and Instruments / Types of Financial Returns / Benchmarking Returns。不要仅改标题就认定新 LOS 已兑现。[官方2027更新摘要][UPDATE]；[2026一级 pp.1–3][I26]；[2027一级 pp.1–3][I27]。Level II/III 本次核对到各自2027纲要与选定模块，**未证明两年全文完全一致**。

Level III 采用共同核心，加候选人选择的一条路径：Portfolio Management、Private Markets 或 Private Wealth。官方网页列共同核心 Asset Allocation、Portfolio Construction、Performance Measurement、Derivatives and Risk Management、Ethics；路径部分权重30–35%。不能说所有考生都要考三条路径，也不能把旧版组合管理目录视为三条路径覆盖。[官方三级说明][LIII]；[2026组合路径 pp.1–17][PM26]。

PSM 是另外一层实践要求，官方要求每级至少完成一个才能取得考试结果，同一模块不能跨级重复计入。2026公开表：一级 Financial Modeling / Python I；二级 Python I / Python II / Analyst Skills；三级 Portfolio Development and Construction 加与所选路径对应可访问的 Practical Macro、Due Diligence、Managing Private Wealth Clients。2027表：一级仍为前两项；二级列 Python I、Python II、Equity Analyst Skills；三级列 Portfolio Development and Construction、Macro Insights for Investing、Due Diligence、Managing Private Wealth Clients。[官方PSM年度表与FAQ][PSM]

**官方页面本身有待澄清的2027口径**：该页年度表后“Level III Pathway-specific PSM”列表还出现 Analyst Skills/Equity Analyst Skills，并沿用两年名称并列的写法。表格存在不支持“2027三级所有候选可无条件选任一模块”的结论。后续应以报名年度、所选路径和候选人的官方 LES 可访问选项核对，不在本库写成统一资格规则。阅读本库 Python/AI 页，也不等于官方 PSM 已完成。[同页2027表及其后列表][PSM]

## 3. 覆盖矩阵：25 个审计单元

每个“库内位置”都是实际页面。行号绑定本次 SHA；`Qxx` 指库外证据中的精确/同义检索。对未定位主题，给出的链接是**最近的现有基础**，用于显示从哪里继续补，不冒充缺失主题已经有页。官方页码均采用 PDF 显示页数，从1起；引用纲要只支持课程要求，不能证明本库学完。

| # | 官方单元与定位 | 本次状态与库内定位 | 支持的断言；不支持/缺口 | 优先级 |
|---|---|---|---|---|
| 01 | I/II/III Ethics、Code and Standards、GIPS：[I26 pp.31–32][I26]；[III核心2026 pp.13–14][PM26]、[2027 pp.13–15][PM27] | **未定位**。最近相邻 [[社会科学/30-金融市场与风险/05-有效市场信息价格与异常]] 第20–28、82–85行讲信息公平/效率边界；Q01为0命中 | 能区分市场效率与信息分布；没有定位CFA六条Code、七条Standards、违规判例和整改程序。普通价值讨论不能替代职业标准案例。GIPS详见19。 | P0 |
| 02 | I Rates/Returns、TVM：[I26 pp.1–2][I26]；[I27 pp.1–2][I27] | **可用（基础）/课程部分**。[[社会科学/30-金融市场与风险/01-现金流复利贴现与实际收益]] 第17–86行 | 期间、现金流符号、复利、NPV、名义实际收益、费用和IRR边界较清楚，有现金流图及数例；MWR/TWR仅第74行概述，未定位完整计算案例、连续复利和指数基准选择题。 | P1 |
| 03 | I 资产收益统计、概率树、组合数学、模拟：[I26 p.2][I26]；[I27 p.2][I27] | **可用（共享数学）/课程部分**。[[数学/30-概率与统计/01-概率分布条件概率与贝叶斯关系]] 第71–141行；[[数学/30-概率与统计/02-期望方差协方差与抽样]] 第29–108行；[[社会科学/30-金融市场与风险/04-组合分散风险因子与CAPM边界]] 第20–52行 | 贝叶斯推导、有限矩前提、组合方差可迁移；例子多为骰子/模型检测与两资产，没有定位金融概率树、Roy safety-first、半偏差/变异系数、偏峰度完整案例。不能用LLM Top-p抽样等同资产价格模拟。 | P1 |
| 04 | I Estimation/Inference、Hypothesis Testing、Regression：[I26 pp.2–3][I26]；[I27 p.3][I27] | **部分**。[[数学/30-概率与统计/05-统计估计置信度与模型评测]] 第34–140、161–167行；[[数学/20-线性代数与几何/14-最小二乘伪逆与正则化]] 第15–46行；Q15 | 有标准误、Wald/CLT/bootstrap边界、配对差和最小二乘推导；未定位完整t/F/卡方、第一二类错误与功效计算、金融ANOVA输出解释。Q15两处是“检验功效”提醒和来源URL，不算教学兑现。 | P0/P1 |
| 05 | I Firm/Market Structures：[I26 p.5][I26]、[I27经济部分][I27] | **入口/未定位考试单元**。[[社会科学/20-经济流动与宏观/01-生产交换分配与制度约束]] 第44–80行；[[社会科学/40-公共政策与社会学/02-税收转移公共服务与归宿]] 第35行；Q09 | 分工、企业边界、议价和税收弹性相邻机制存在；未定位完全竞争/垄断竞争/寡头的最优产出、停产/盈亏平衡、集中度和成本曲线题。提到“市场”不构成微观课程覆盖。 | P1 |
| 06 | I Economics宏观、政策、贸易、FX；II增长/汇率：[I26 pp.5–7][I26]；[II26经济部分][II26] | **可用（宏观核算）/课程部分**。[[社会科学/20-经济流动与宏观/05-国民账户部门余额与开放经济]] 第25–114行；[[社会科学/20-经济流动与宏观/06-货币信用银行与通胀]] 第21–109行；[[社会科学/20-经济流动与宏观/07-增长周期就业与政策传导]] 第24–107行；Q08 | GDP/GNDI/CA/B9手算、货币信用和需求/供给冲击区别有深度；外汇只在衍生品页提醒双币利率，未定位交叉汇率、CIP/PPP、制度与前向点数计算、贸易限制/地缘政治模块。宏观七讲主题有重心，不能替代CFA Economics整科。 | P1 |
| 07 | I/II FSA：[I26 pp.11–14][I26]；[II26/27报表主题][II26] [II27] | **入口/未定位成体系课程**。[[社会科学/30-金融市场与风险/03-股票所有权现金流与估值]] 第18–35、97行；[[社会科学/30-金融市场与风险/07-银行期限转换流动性与挤兑]] 第31–55行；Q02 | 账面权益/利润/现金流与市场价值区分、银行双重记账存在；未定位收入确认、存货与减值、现金流分类、租赁、税、合并、外币折算、比率/盈利质量的多表调整题。FIFO/LIFO大量命中是队列/栈，必须排除。 | P0 |
| 08 | I Corporate Issuers / 2027 Corporate Finance；II公司财务：[I26 pp.9–10][I26]；[II26公司主题][II26] [II27] | **入口/未定位决策课程**。[[社会科学/30-金融市场与风险/03-股票所有权现金流与估值]] 第29–35、67–90行；[[社会科学/20-经济流动与宏观/01-生产交换分配与制度约束]] 第54–80行；Q03 | 股权权利、增发稀释与企业协调约束可用；未定位WACC、现金转换周期、资本预算排序、资本结构/分派、治理冲突到决策的完整案例。银行“资本成本”一句不能代表公司加权资本成本。 | P0 |
| 09 | I Equity Investments / 2027 Equities：[I26股权主题][I26]；[I27 pp.15–17][I27] | **可用（稳定增长基础）/部分**。[[社会科学/30-金融市场与风险/03-股票所有权现金流与估值]] 第49–93行；[[社会科学/30-金融市场与风险/05-有效市场信息价格与异常]] 第20–78行 | DDM递推、r>g、敏感度、稀释和联合检验解释较好；行业/竞争分析、证券市场组织/指数、三表预测和多种估值未兑现。股权桥现金口径还有P0歧义，见第4节。 | P0/P1 |
| 10 | I Fixed Income：[I26固定收益主题][I26]；[I27固定收益主题][I27] | **可用（局部定价）/部分**。[[社会科学/30-金融市场与风险/02-债券价格利率期限结构与信用利差]] 第19–62、76–100行；Q11 | 确定现金流、YTM条件、Macaulay/修正久期和即远期算例清楚；凸性仅说明误差，缺计算、非平移/key-rate、浮息/期权现金流、证券化和信用分析题。第96行明确不宜套固定式。 | P1 |
| 11 | I Derivatives：[I26衍生品主题][I26]；[I27衍生品风险主题][I27] | **可用（一期复制）/部分**。[[社会科学/30-金融市场与风险/06-远期衍生品无套利与期权]] 第19–78、87–98行 | 两种一期定价与平价逐状态核验，有图；远期交割价与存续合约价值、期货盯市差异、带收入/外汇标的、互换定价和多步树尚需完整题解。BSM/Greeks仅边界说明。 | P1 |
| 12 | I Alternatives：[I26 pp.25–26][I26]；[I27另类主题][I27] | **未定位合适课程**。最近 [[社会科学/30-金融市场与风险/04-组合分散风险因子与CAPM边界]] 第84–93行只讲因子/尾部；[[社会科学/20-经济流动与宏观/04-教育住房地域与累积优势]] 第41–54行讲住房社会机制；Q05 | 不能用住房/银行/系统风险覆盖另类结构、费用净回报、私募资本、房地产估值、资源商品、对冲基金和数字资产。Q05仅1处相关词且非另类投资课程。 | P0 |
| 13 | I Portfolio Management / 2027 Portfolio Construction：[I26组合主题][I26]；[I27组合主题][I27] | **可用（方差/CAPM）/部分**。[[社会科学/30-金融市场与风险/04-组合分散风险因子与CAPM边界]] 第20–95行；[[社会科学/30-金融市场与风险/08-杠杆保证金传染与系统性风险]] 第61–95行 | 组合风险、因子、beta、VaR/ES边界可读；缺有效前沿/资本配置线完整优化、投资者目标约束、IPS、行为偏差与投资流程。系统风险页不是个人组合计划。 | P1 |
| 14 | II 多元回归/错设/Time-Series：[II26 pp.1–3][II26]；[II27 pp.1–3][II27] | **部分（回归）/未定位（金融时间序列）**。[[AI/10-机器学习与深度学习基础/14-线性回归逻辑回归与概率建模]] 第17–19、52–97行；[[数学/20-线性代数与几何/14-最小二乘伪逆与正则化]] 第15–39行；Q16为0 | 有最小二乘、GLM、共线性与残差提醒；缺金融回归联合检验、误差修正与输出；未定位平稳性、AR预测、单位根/协整、ARCH教学。LLM自回归和Arch Linux是假阳性。 | P1 |
| 15 | II Machine Learning/Big Data Projects；2027一级数据应用：[II26 p.3][II26] [II27 p.3][II27]；[I27数量方法][I27] | **可用（通用方法）/部分（金融迁移）**。[[AI/10-机器学习与深度学习基础/05-数据集拆分清洗与泄漏]] 第37–111行；[[AI/10-机器学习与深度学习基础/15-核方法树集成与归纳偏置]] 第25–59行；[[AI/10-机器学习与深度学习基础/16-PCA聚类EM与表示学习]] 第17–96行 | 通用泄漏、核/树/森林、PCA/聚类/EM与数例具备；CFA所需金融数据取得时间、收益/EPS目标、滚动样本外、基线、交易成本和经济意义仍需案例。不能把通用ML多页数量当金融数据科学达标。 | P1 |
| 16 | II Equity Valuation、FI/衍生品/另类深层应用：[II26 pp.14–15及相关主题][II26]；[II27对应主题][II27] | **部分/部分主题未定位**。[[社会科学/30-金融市场与风险/03-股票所有权现金流与估值]] 第49–90行；[[社会科学/30-金融市场与风险/02-债券价格利率期限结构与信用利差]] 第33–96行；[[社会科学/30-金融市场与风险/06-远期衍生品无套利与期权]] 第33–85行；Q04/Q05/Q11 | 基础能作先修；未定位FCFF/FCFE/剩余收益/倍数完整估值、期限结构模型复算、OAS/CDS、复杂衍生品与另类估值。不能由一期树或Gordon式推断二级情景题能力。官方FCF条目明确需要模型选择与估值解释。 | P1 |
| 17 | II Portfolio Risk、Active Management：[II26 pp.24–26][II26]；[II27组合主题][II27] | **部分/未定位主动管理指标**。[[社会科学/30-金融市场与风险/04-组合分散风险因子与CAPM边界]] 第54–93行；[[社会科学/30-金融市场与风险/05-有效市场信息价格与异常]] 第43–78行；Q06为0 | 能警惕alpha基准依赖与数据挖掘；未定位Sharpe/IR、主动管理基本法则、breadth/IC/TC、风险预算与经理选择完整应用。提醒“统计显著不等于利润”不等于已经做绩效评估。 | P1 |
| 18 | III核心 Asset Allocation：[PM26 pp.1–3][PM26]；[PM27 pp.1–3][PM27] | **入口/部分**。[[社会科学/30-金融市场与风险/04-组合分散风险因子与CAPM边界]] 第20–52、90–95行；[[社会科学/20-经济流动与宏观/02-收入消费财富与生命周期]] 第33–84行 | 协方差与生命周期预算能作先修；未定位资本市场预期、资产/负债/目标导向配置、稳健性模拟、风险预算、税/流动性约束和再平衡的推荐论证。 | P1 |
| 19 | III核心 Performance Measurement、Manager Selection、GIPS：[PM26 pp.9–10][PM26]；[PM27对应核心][PM27] | **未定位系统课程**。[[社会科学/30-金融市场与风险/01-现金流复利贴现与实际收益]] 第74–86行；[[社会科学/30-金融市场与风险/05-有效市场信息价格与异常]] 第43–78行；Q01/Q06 | 有收益口径及基准误设提醒；未定位Brinson/固定收益归因、benchmark检验、Sortino/回撤、经理选择/费表、GIPS复合组合与展示。特别不能把IRR定义当整科绩效测量。 | P0/P1 |
| 20 | III核心 Portfolio Construction、Institutional/Private Clients、Trading：[PM26 pp.5–7][PM26]；[PM27 pp.5–7][PM27] | **入口/未定位完整执行链**。[[社会科学/20-经济流动与宏观/02-收入消费财富与生命周期]] 第33–84行；[[社会科学/30-金融市场与风险/05-有效市场信息价格与异常]] 第67–78行；Q06/Q14 | 已有家庭约束与交易成本清单；未定位机构负债/利益相关方、私人客户IPS、SWF案例、显隐交易成本、effective spread/VWAP/implementation shortfall。下一步要把目标→约束→组合→执行接成链。 | P1 |
| 21 | III核心 Derivatives and Risk Management、Currency Management：[PM26 pp.11–12][PM26]；[PM27 pp.11–12][PM27] | **入口/部分**。[[社会科学/30-金融市场与风险/06-远期衍生品无套利与期权]] 第66–92行；[[社会科学/30-金融市场与风险/08-杠杆保证金传染与系统性风险]] 第32–72行 | 合约敏感度和融资边界有基础；未定位covered call/straddle/spread组合损益、期货/互换调整股债风险、FX hedge ratio/carry/cross-hedge与对冲成本计算。不能将“对冲仍有风险”一句当策略课。 | P1 |
| 22 | III Portfolio Management路径：[PM26 pp.15–17][PM26]；[PM27 pp.16–18][PM27] | **入口/未定位路径课程**。[[社会科学/30-金融市场与风险/04-组合分散风险因子与CAPM边界]] 第84–93行；[[社会科学/30-金融市场与风险/02-债券价格利率期限结构与信用利差]] 第33–62行；Q06/Q11 | 因子与局部久期提供起点；指数复制/跟踪误差、Active Share、主动股权构建、LDI/曲线/信用策略、交易执行及endowment案例未定位成体系内容。不是“有CAPM即可覆盖组合路径”。 | P2（若选此路径则P1） |
| 23 | III Private Markets路径：[PR26 pp.15–17][PR26]；[PR27 pp.16–18][PR27] | **未定位路径课程**。最近 [[社会科学/30-金融市场与风险/03-股票所有权现金流与估值]] 第29–35、67–85行只是公开股权基础；Q05/Q14 | 未定位GP/LP、DPI/RVPI/TVPI、费/carry、水位线/分配、VC/growth/buyout估值、私债、房地产/基建尽调与退出；不能将公司/住房相邻页当此路径。 | P2（若选此路径则P1） |
| 24 | III Private Wealth路径：[PW26 pp.15–17][PW26]；[PW27 pp.16–18][PW27] | **入口/未定位路径课程**。[[社会科学/20-经济流动与宏观/02-收入消费财富与生命周期]] 第33–105行；[[社会科学/20-经济流动与宏观/03-代际流动机会不平等与测量]] 第22–103行（本次仅定向定位，未深审全部） | 生命周期/净财富基础有用；代际流动测量不是财富传承方案。未定位高净值客户沟通、税/居留/法律约束、goal-based计划、企业主人力资本、赠与/遗产/慈善完整案例。 | P2（若选此路径则P1） |
| 25 | I/II/III PSM，2026/2027年度表与FAQ：[官方PSM][PSM] | **通用工具入口；官方完成状态未知**。[[计算机知识/10-编程语言/01-Python/13-常用Package生态与用法]] 第123–208行（本次仅定位工具节，未执行）；[[AI/10-机器学习与深度学习基础/05-数据集拆分清洗与泄漏]] 第37–111行；Q14为0 | NumPy/pandas/Jupyter及通用数据流程可迁移；未定位三表金融模型、金融Python项目、分析师工作包、机构组合Excel、宏观投资/尽调/私财客户实践交付。未读取官方LES完成记录，不能承诺取得成绩或免PSM。2027选项歧义见第2节。 | P0（分清要求），P1/P2（制作练习） |

## 4. 高影响风险与现有优点

**P0：股权桥可能双计现金，先明确集合。** [[社会科学/30-金融市场与风险/03-股票所有权现金流与估值]] 第33–35行写“经营资产价值＋非经营资产－净债务－其他优先索取权”，随后又要求逐项检查现金。若非经营资产包含现金C，同时净债务定义为D−C，同一C被加两次。合成反例：经营EV1000、现金100、债务300、无其他索取权；按EV＋C−D为800，按EV＋C−(D−C)为900。官方2026倍数课程公开总结将EV与cash/investments扣除联结，应明确选哪套一致桥接。[官方2026 EV定义，Summary][EV]

该反例支持**现有口径不明确且常见读法会出错**；不支持“所有可能定义下恒等式都错”。若非经营资产排除净债务已处理的现金，则可以一致。验收要求：分别定义经营EV、现金/投资、非经营资产、债务与优先权，展示两种一致等价桥，不重复现金，并用上述数例及有少数股权/租赁的另例交叉复算。现有“估值桥”Mermaid与正文一起检查。

**P0：不能承诺全课程/全考试深度。** 金融MOC第18–25行的八讲主路线兑现的是现金流到系统风险；第29–33行停点也围绕这个机制链。它没有宣称CFA课程，后续审计/导航不能替它增加未经证实的考试承诺。报表与伦理是官方独立大主题；Q01/06无命中、Q02/03有少量相邻行及大量计算机缩写，证据不足以把它们标已覆盖。[一级官方纲要][I26] [2027纲要][I27]

**P0：官方课程学习与PSM完成必须分开。** 三级路径选择和2027 PSM表/列表歧义都影响学习规划。不能用本库Python/AI或宏观课程替代候选人官方完成状态；官方在线errata还提醒PDF/eBook不会年内自动更新。本次打开了errata入口，**未逐条把所有勘误合入矩阵**。[PSM政策说明][PSM] [官方勘误入口][ERRATA]

现有优点值得保留。金融01的现金流时点/有效期间/名义实际量（第17–68行）、金融02的久期近似与重估差（第33–62行）、金融04的协方差数例与CAPM假设（第20–72行）、金融06的复制与风险中性两路定价（第33–74行）、宏观05的GDP/GNDI/CA/B9区别（第39–67行）都能服务多条CFA路线，宜加金融题和指向共享数学的用途链接。

脚本本次复算得到：金融01 NPV≈40.8487；金融02收益率6%债价≈98.1666；金融04两资产标准差≈12.0416%；金融06看涨价≈11.9048，与正文显示精度一致。这只核对四个选定教学算例，未重算所有公式、代码和历史事实。原文中的“独立复算/审阅签收”属性是旧材料声明，本次没有继承为当前审阅证明。

## 5. 例题、图例、链接验收

金融MOC及八正文共 **39个 wikilink 出现位置**，脚本逐一按精确路径检查目标存在；未发现缺失的路径目标。4幅引用SVG均存在：cashflow-timeline、binomial-replication、bank-balance-sheet、margin-spiral；金融部分另有机制Mermaid。证据摘要记录引用页、目标路径和图字节SHA。这里检查的是文件存在与路径，不检查客户端渲染、图中标注是否完整、所有锚点、来源网址活性或全库反链。

目前可复算数例突出，练习多为改变参数和机制解释；基础页没有形成按年度/LOS/难度组织的CFA题组，也没有定位足够的二级vignette和三级短答题。官方二级强调以vignette信息分析，三级强调整合应用与mixed format；现有孤立公式练习不能证明这层能力。[官方二级题型][LII] [官方三级题型][LIII]

下一步图例要表达可检查关系：现金流到TWR/MWR时间线，债券P–y曲线及久期/凸性误差，三表勾稽桥，DDM/FCF终值敏感度，有效前沿与约束，option payoff与profit分开，绩效归因桥与客户IPS流程。每张图注明单位、时点、变量与假设，给数表或脚本复现输入。Mermaid因果/机制箭头与数据识别必须继续分开。

链接规划须兑现承诺：回归课→共享最小二乘的正规方程/QR/SVD；组合课→协方差矩阵与约束优化；固定收益课→Taylor/数值误差只用于近似解释；数据科学课→时间/实体拆分和评测边界。跨域页加必要回顾及金融数例，主证明仍留原页。相邻住房/文化/制度页只作背景，不标成CFA另类、伦理或法律先修替代。

## 6. 后续 P0/P1/P2 工作规划与具体验收

以下是提议工作束，不是已执行任务，不自动授权正文发布、安装依赖、收费来源访问或新增代理。每束先确定考试年度、目标level和路径；未确定时先建设共享基础与明确2026/2027入口。本次没有要求人维护机器任务或哈希。

| 阶段/工作束 | 建议产物与连接 | 完成验收 |
|---|---|---|
| P0-1 年度及路径入口 | 一张人可读CFA年度路线，连接现有金融/宏观/数学/AI；明确I/II/III共同核心、三路径与PSM | 所有目标均存在；逐单元保留官方年份/模块/LOS指针；2027改名/要求分别核对，列未覆盖项；不写全LOS百分比或用户掌握度。2027 PSM按官网表/歧义与候选人选项标未知。 |
| P0-2 股权桥口径 | 对金融03提供最小修订候选，先处理第33–35行与估值图 | 两种现金一致桥＋EV1000/C100/D300反例复算；正文/图/算例一致；独立复核后才能发布，不用大改文风。 |
| P0-3 伦理与GIPS最低闭环 | 建议单独职业标准课程，连接信息/利益冲突背景；GIPS与绩效课共用主定义 | 按当年官方Code/Standards逐节定位；至少每条主要标准给违规/不违规/预防措施判例和解释；GIPS给复合组合/收费/展示边界案例；新增标准推断原文复核。不能从常识伦理直接判题。 |
| P0-4 财务报表与公司财务骨架 | 三表勾稽→调整/比率→FCF→资本决策；连接存量流量与股权估值 | 资产=负债+权益、现金期初期末与CFO/CFI/CFF一致；至少一组IFRS/明确GAAP对照及存货/租赁/税调整；WACC/现金转换周期/资本预算有单位和口径；教学三表无真实公司数据时明确合成，题解可复算。 |
| P0-5 另类分类与结构 | 给一级另类入口并拆私募资本、房地产、资源/商品、基金/数字资产的边界；连接组合风险 | 官方当年模块逐项可导航；至少费前费后现金流/回报例、直接/共同/基金结构图、流动性/估值反例；不能把住房社会学例标房地产估值课程。 |
| P1-1 一级数量与经济完整化 | 复用共享概率统计、宏观基础，补CFA金融迁移小课 | TWR/MWR同一现金流两算法；偏峰度/下行风险/模拟与金融概率树；t/F/卡方假设与输出；微观停产/产出/成本曲线、FX交叉/CIP/前向点数有详细数题。每关键公式至少一次推导、一次复算、一次失效例。 |
| P1-2 一级资产估值/组合题组 | 金融01—06保留主解释，加题组和图；补信用/证券化、有效前沿/行为约束 | 债券价格/久期/凸性与非平移对比；DDM/估值桥、指数/市场案例；远期交割价vs存续价值/期货盯市/平价；两资产优化前沿和不可行权重反例；每单元建议至少3道差异化原创题＋完整答案与误选原因，题数仅是起点。 |
| P1-3 二级分析闭环 | 回归/时间序列→报表调整→FCFF/FCFE/剩余收益/倍数→FI/衍生品/另类→主动管理 | 每个目标模块至少一组多问题vignette，给输入时间戳/口径、模型选择理由、计算与诊断；AR预测/平稳性/协整不等同LLM生成；金融ML有滚动样本外、泄漏控制、经济意义、基线及误差报告；相关源码与镜像一并核验，缺依赖列未运行。 |
| P1-4 三级共同核心 | 客户/机构IPS→资本预期→配置→风险/执行→归因与经理选择 | 两组资产/负债/目标导向约束案例；机构和私人客户区别；衍生品风险调整与货币对冲算例；performance/attribution/appraisal分别定义、归因桥和benchmarks；短答要求能推荐并以事实/约束解释，不只套公式。 |
| P2-1 所选三级路径 | 选择一条优先深做，其余保持明确边界入口 | PM：tracking error/Active Share、LDI/曲线信用策略与endowment；Private Markets：GP/LP费用及DPI/RVPI/TVPI、VC/buyout/债/房地产/基建尽调退出；Private Wealth：人力资本/税与居留/退休/赠与遗产与客户沟通。每路径一个贯通案例＋原创短答＋图和反例，法律税务版本原文另核。 |
| P2-2 PSM对应练习 | 金融Python/Jupyter、三表模型、分析师工作包、机构组合Excel或所选路径实践案例 | 数据身份/许可/日期可追，合成则标合成；清洗/预测时刻/评估/图/结论/局限完整；能复现且检查非法输入；本库练习只能标技能演练，官方PSM完成须由候选人官方结果另证。 |

非机械内容应独立核对关键原文和计算；此审计作者不能把自己参与设计/撰写的后续候选称作独立复核。发布须绑定当前页面版本与签收，发现第三种新内容先局部合并/重审。只发布完整的小工作束，避免让读者沿链接读到等待修复的半条知识链。

## 7. 未覆盖与交付边界

未覆盖：禁止范围内的私人资料；付费/登录LES完整教材和官方题库；所有LOS逐条映射与数值覆盖率；全库历史来源验证；全部数学/AI页深审；客户端真实渲染/阅读体验；所有锚点反链及所有外链活性；所有代码执行/镜像一致性；用户官方PSM/考试完成与掌握状态；官方errata逐条对照；全年纲要自动更新监控。发现未定位主题后，仍应先按同义词定位现有解释，不能为了目录整齐重复造页。

本候选冻结为 **CFA-audit-v1**。30页选定输入以及984页检索输入的SHA可供发布者核对；如当前字节漂移，不能无条件复用旧断言。冻结后变更另出版本。报告未运行全库check_vault/unittest：本次未改正文且未发布，独立静态存在性脚本只针对金融39链接/4图；不把未运行写成通过。

官方来源定位如下；所有来源已通过内置web打开/检索核实，链接标题所标年级/年度为本次输入身份，网页更新日期未知的没有补造日期。

[I26]: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026-l1-topics-combined.pdf "CFA Institute 2026 Level I Topic Outlines，32页"
[I27]: https://www.cfainstitute.org/sites/default/files/2027levelitopicoutline_online.pdf "CFA Institute 2027 Level I Topic Outlines，31页"
[II26]: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026-l2-topics-combined.pdf "CFA Institute 2026 Level II Topic Outlines，29页"
[II27]: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2027-cfa_l2_topic_outline.pdf "CFA Institute 2027 Level II Topic Outlines，30页"
[PM26]: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026leveliii-portfolio-management-pathwaytopicoutline_online.pdf "CFA Institute 2026 III Core＋Portfolio Management，17页"
[PR26]: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026leveliii-private-markets-pathwaytopicoutline_online.pdf "CFA Institute 2026 III Core＋Private Markets，17页"
[PW26]: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026leveliii-private-wealth-pathwaytopicoutline_online.pdf "CFA Institute 2026 III Core＋Private Wealth，17页"
[PM27]: https://www.cfainstitute.org/sites/default/files/2027leveliii-portfolio-management-pathwaytopicoutline_online.pdf "CFA Institute 2027 III Core＋Portfolio Management，18页"
[PR27]: https://www.cfainstitute.org/sites/default/files/2027leveliii-private-markets-pathwaytopicoutline_online.pdf "CFA Institute 2027 III Core＋Private Markets，18页"
[PW27]: https://www.cfainstitute.org/sites/default/files/2027leveliii-private-wealth-pathwaytopicoutline_online.pdf "CFA Institute 2027 III Core＋Private Wealth，18页"
[LI]: https://www.cfainstitute.org/programs/cfa-program/candidate-resources/level-i-exam "CFA Institute Level I年度权重/纲要入口，检索核实；本次open超时"
[LII]: https://www.cfainstitute.org/programs/cfa-program/candidate-resources/level-ii-exam "CFA Institute Level II入口与题型"
[LIII]: https://www.cfainstitute.org/programs/cfa-program/candidate-resources/level-iii-exam "CFA Institute Level III核心/路径/题型"
[PSM]: https://www.cfainstitute.org/programs/cfa-program/candidate-resources/practical-skills-modules "CFA Institute PSM 2026/2027表、FAQ与路径列表"
[UPDATE]: https://www.cfainstitute.org/sites/default/files/curriculum-update-2027.pdf "CFA Institute 2027 Curriculum Update，1页"
[ERRATA]: https://www.cfainstitute.org/programs/candidate-resources/submit-errata "CFA Institute Curriculum errata入口"
[EV]: https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples "CFA Institute 2026 Level II公开Refresher，EV定义/倍数"

返回 [[00-工作台/审计/2026-09-17/README|审计总览]] · 实施顺序见 [[00-工作台/下一步建设规划|下一步建设规划]]。
