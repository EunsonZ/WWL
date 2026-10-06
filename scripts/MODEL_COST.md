# 离线费用、预算与重试检查

本工具回答三个问题：给定的请求记录按其绑定的价格能算出多少美元、拟新增任务是否占用了同一份余额、重试配置是否具有明确边界。它只读取本地 JSON，用 Python 标准库 `Decimal` 运算；不创建 API 请求、读取密钥、查询账户或执行预算拨款。

**本批真实模型费用仍为 unknown。** 示例都是教学数据，不能作为本批实际用量。API 美元参考估算与 Codex 订阅额度没有本工具可确认的换算关系。`known` 仅表示给定记录及价格下的算术完整，不能认证真实账单。

## 1. 入口与最小成功／失败例

在 Vault 根运行，或在完整候选根运行。Python 3.10 及以上，无第三方依赖。实际测试环境见本批验收记录。

```bash
python3 -B scripts/model_cost.py --help
python3 -B scripts/model_cost.py estimate --help
python3 -B scripts/model_cost.py budget --help
python3 -B scripts/model_cost.py retry --help
```

| 子命令 | 输入 | 正常输出与退出码 |
| --- | --- | --- |
| `estimate` | `--usage 文件 --prices 文件`；`--prices` 可重复，加载不同历史快照 | JSON，退出 `0`；事实缺失仍退出 `0`，需读 `status` 与 `unknown_reasons` |
| `budget` | `--ledger 文件` | 全部拟任务可容纳且控制权声明有效时 `0`；拒绝任一项、控制权未确认或已有费用未知时 `3` |
| `retry` | `--config 文件` | 有效离线配置 JSON，退出 `0` |

输入合同违规时三者均向 stderr 写结构化错误，退出 `2`。命令行参数本身错误由 `argparse` 解释。错误消息不回显输入正文。

### estimate

```bash
python3 -B scripts/model_cost.py estimate --usage scripts/examples/usage-hypothetical.json --prices scripts/model-prices.json
python3 -B scripts/model_cost.py estimate --usage scripts/examples/usage-invalid.json --prices scripts/model-prices.json
python3 -B scripts/model_cost.py estimate --usage scripts/examples/usage-unknown.json --prices scripts/model-prices.json
```

第一例退出 `0`：三个记录中一个是完整重复，两条不同请求均计入 hypothetical，合计 `0.000782` USD，actual 为 `not_supplied`、总额为 `null`。第二例有重复 JSON 键，退出 `2`。第三例退出 `0`，actual 为 `unknown`；它只演示缺事实的输入形状，没有包含本批真实调用。

### budget

```bash
python3 -B scripts/model_cost.py budget --ledger scripts/examples/usage-budget-ok.json
python3 -B scripts/model_cost.py budget --ledger scripts/examples/usage-budget-denied.json
```

第一例退出 `0`：授权 `10`、已花 `3`、取消尚未核对的预留 `2`，新增工作 `3`、审阅 `1`、收尾 `1` 正好用完。第二例多请求 `0.01`，第二项被拒绝，退出 `3`。前项 `allow` 只是模拟检查结果；运行此命令不会创建真实预留，也不能单独作为派发凭证。

### retry

```bash
python3 -B scripts/model_cost.py retry --config scripts/examples/usage-retry-ok.json
python3 -B scripts/model_cost.py retry --config scripts/examples/usage-retry-invalid.json
```

第一例退出 `0`：由 outer 一层负责，最多三次尝试包含第一次请求，32 并发要求 full jitter。第二例同时配置 outer 与 SDK 重试，退出 `2`。

## 2. 通用 JSON 合同

所有顶层文档要求整数 `schema_version: 1`。未知字段、未知版本和任意深度的重复 JSON 键都拒绝，避免拼错字段后悄悄采用默认值。

- 文件上限 8 MiB；usage、预留及拟任务数组各不超过 10,000 条。价格选择器不超过 1,000 条，每个选择器最多 100 个分档。
- token、工具次数和计数必须是 JSON 整数，范围为 `0` 至 `10^18`；`true`、负数、浮点 token、字符串 token 均不接受。
- 金额／费率接受十进制字符串或 JSON 十进制数，拒绝布尔、负数、NaN 与 Infinity。绝对值小于 `10^19`，最小小数位为 `10^-18`，有效数字不超过 40。受此输入边界与数组上限约束，运算采用 100 位 Decimal 精度，汇总不做货币分位四舍五入。
- 时间必须是带时区的 ISO 时间戳，例如 `2026-09-15T08:00:00Z`。价格窗口为 `[valid_from, valid_until)`，含开始、不含结束。
- 输出金额是十进制字符串；未知总额用 JSON `null`，同时提供状态和理由。未提供某类记录时是 `not_supplied`，不会将本批实际费用报成零。

这些数值上限限制离线教学工具的输入规模和计算资源，构成 100 位精度足够的前提；不是模型能力上限、账户额度或生产调度推荐。重试的 10 次／3600 秒同样只是明确可检查的配置边界。

## 3. 请求 schema 与计费口径

usage 顶层只有 `schema_version` 和 `requests`。单请求允许以下字段；除 `kind` 外，计费事实可以缺省或为 `null`，但缺省不会自动补成 standard、零 token 或未使用工具。

| 字段 | 类型与作用 |
| --- | --- |
| `kind` | 必填 `actual` 或 `hypothetical`；分别汇总，不能互相冲抵 |
| `provider`、`billing_scope` | 实际提供方及账目作用域。内置价格只匹配 `openai` + `direct-api`；代理提供方需自己的完整价格 |
| `request_id` | 实际请求 ID。去重键为上述两个字段加请求 ID；不使用提示词猜测 |
| `timestamp` | 实际请求时间，用于检查绑定价格的适用窗口 |
| `price_version`、`price_sha256` | 该请求绑定的价格版本及原始 UTF-8 文件字节 SHA256；需同时匹配传入快照 |
| `model`、`service_tier` | 实际精确模型 ID 和服务档。别名与未核验服务档不自动映射 |
| `input_total` | 该请求总输入，用于选择长上下文档；不先跨请求累计 |
| `noncached_input`、`cache_read`、`cache_write` | 三个互斥输入桶，全部已知时必须之和等于 `input_total`；部分已知时和也不得超过总量 |
| `cache_policy` | `disjoint_v1` 表示上述三个桶已按提供方真实口径转换；原始 API 字段不能未经转换直接填入 |
| `output` | 已含适用 reasoning 的全部计费输出 |
| `reasoning` | 可选诊断子集，若同时给出则不得超过 output；费用不再加一次 |
| `output_policy` | `includes_reasoning` 表示 output 已采用上述口径 |
| `tools` | `null`／缺省为未知；确定未使用写 `{"none":true,"evidence":"依据"}`；发生工具写 `{"charges":[{"name":"工具名","units":2}],"evidence":"依据"}` |
| `problem_id`、`attempt_id`、`prompt_ref` | 可选归因标签；不要放提示词正文或私密查询。变更标签不改变去重身份、不重置总费用 |

同一去重键、相同完整计费事实只算一次并增加 `duplicate_records`。不同 ID 即使 prompt_ref 相同，也分别计费。相同键的 token、模型、服务档、时间、价格绑定、kind、工具等事实不同，整个输入拒绝，不能取便宜值。仅归因标签不参与事实冲突判定。

缺任何身份字段时，保留记录且增加 `deduplication_unconfirmed_records`；总额为 unknown。`known_subtotal_usd` 是所提供记录中可计算部分的算术和；身份未确认时它也可能含重复，因此**不是实际账单的下界**。应先补实际 ID 再结算，而不是删掉疑似重复记录。

正常输入下，每个请求计算：

```text
text = (noncached_input × input_rate
      + cache_read × cache_read_rate
      + cache_write × cache_write_rate
      + output × output_rate) / 1_000_000
request = text + Σ(tool_units × tool_unit_rate)
```

`input_total` 只用于校验分桶与逐请求选档，不会再次按总输入收一份费用。工具费走自身的单位价，无文本服务倍率。已发生但未核验的工具费、非零 token 的 `null` 费率使总额 unknown；其他已知部分保留。明确为零的桶不需要猜一个尚未核验的单价。

完整批次还需由实际账目提供协调、共享取证、作者、独立审阅、收尾、重试、失败／弃稿和工具费用。脚本不会从线程数推算这些调用，也无法发现未提供的记录；某份输入计算完整不等于整个批次账目完整。共享请求只计一遍，按 problem_id 归因不能再加一遍。

单例手算：假设费率 input/cache_read/cache_write/output 分别为 `2/0.5/3/8` 美元每百万，输入桶 `600/300/100`、output `200`，则费用为 `(1200+150+300+1600)/1e6 = 0.00325`。如果 reasoning 为 `150`，费用仍为 `0.00325`；再发生两次每次 `0.01` 的工具调用，总计 `0.02325`。这些手算常量是测试夹具，并非官方报价。

## 4. 价格 schema、历史与官方参考范围

[model-prices.json](model-prices.json) 顶层包含 `schema_version/version/currency/status/verified_at/source/scope_note/entries`。`status` 为 `verified_reference` 或 `hypothetical`；后者不能用于 actual 记录。字段描述的是该价格资料的来源状态，不是工具自动认证的结果。

每个 entry 是唯一的 `provider/billing_scope/model/service_tier` 组合，含 `valid_from/valid_until/input_tiers/tool_rates_per_unit`，可附 `source/notes`。每档有 `max_input_tokens` 与四个 `rates_per_million`。上界递增且包含边界；最后一档上界为 `null`。费率未知可以显式写 `null`。工具单位价位于独立字典，不依赖文本档倍率。

本文件版本为 `openai-standard-reference-2026-09-15`。本批资料核验者于 2026-09-15 打开各官方模型页面并核对下表；本脚本没有联网。短上下文标准文本报价，单位 USD／百万 token：

| 官方精确模型 ID | 非缓存输入 | 缓存读 | 缓存写 | 输出 |
| --- | ---: | ---: | ---: | ---: |
| [gpt-6-astra](https://developers.openai.com/api/docs/models/gpt-6-astra) | 10 | 1 | 12.5 | 50 |
| [gpt-5.6-sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) | 4 | 0.4 | 5 | 20 |
| [gpt-5.6-terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | 2 | 0.2 | 2.5 | 12 |
| [gpt-5.6-luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) | 0.2 | 0.02 | 0.25 | 1.2 |

缓存写按页面 `1.25 × uncached input` 规则计算；Astra 另有明确 `12.5` 值，其他三项为规则派生。单请求输入 **大于 272,000** 时整请求输入价乘 2、输出价乘 1.5；Astra 的长档缓存倍率有明确说明，另外三个模型的长档缓存读写解释尚未确认，均保留 `null`。Sol 页面说明促销至少延续至 2026-11-21，不保证之后仍为同价。[官方定价总页](https://developers.openai.com/api/docs/pricing) 与 [reasoning 输出说明](https://developers.openai.com/api/docs/guides/reasoning) 提供计价口径背景。

默认文件只允许 `2026-09-15T00:00:00Z` 至 `2026-09-16T00:00:00Z` 的显式绑定参考估算。**这是本库对核验日的保守限制，不声称供应商恰在该时刻生效／失效。** 日期之前的请求需要其历史价格资料；日期之后需重新核验并保留新快照。URL 不变不能证明价格没变。

同批历史请求可传多个文件：

```bash
python3 -B scripts/model_cost.py estimate --usage usage.json --prices price-old.json --prices price-new.json
```

每个请求独立匹配版本及文件哈希。重排、改空白也会改变原始文件哈希，不能偷偷改旧快照后刷新旧请求绑定。新报价不是旧账单证据；缺历史快照、服务档、缓存语义等时保留 unknown。本工具不认证供应商附加费、税、地区、私有折扣、模型别名或账单四舍五入。

## 5. 预算 schema 与取消语义

ledger 字段完整示例见 [usage-budget-ok.json](examples/usage-budget-ok.json)。

- `controller` 含 `id/confirmed/active_claimants`，`actor` 必须等于 id；只有 confirmed 为 true 且 active_claimants 恰好包含该一个 id 时通过声明检查。
- `authorized_budget` 是已授权美元上限；`spent.amount` 是已确认支出；`spent.complete` 为 false 则停止新增。授权不是由填入 JSON 数字创建的。
- `reservations` 每条含唯一 `id`、稳定 `problem_id`、`amount`、`state`、`usage_reconciled`。预留未知金额为 `null`，使可用余额未知并拒绝新增。
- `state` 为 `in_flight/cancel_requested/unknown/settled/cancelled_confirmed`。只有后两种终态且 usage_reconciled 为 true 才释放预留；调用方应已将核对后的实际支出加入 spent。取消意图、超时、状态未知或未核对终态都保留预留。
- `proposals` 每条含唯一 `id`、稳定 `problem_id` 和显式 `work/review/closeout` 三项预留。零可以显式填写，但不自动填零；任何一项为零时必须补 `zero_cost_evidence` 非空说明，例如本地审阅无需新增 API 费用。说明不等于质量门槛可以省略，工具也不认证该说明真实。同一读者问题的重试仍保留原 problem_id；共享费用只记一条，不把归因标签作为第二笔支出。

整份输入先校验，再按 proposals 顺序检查 `spent + retained + 已允许提案 + 当前提案 ≤ authorized_budget`。这让同一次模拟的 32 项提案不能反复使用同一余额。禁止将同一份旧 ledger 分别交给 32 个工作者再将各自 allow 结果合并。

**控制权字段只是待核对的事实声明，无法证明跨进程互斥。** 真实唯一预算持有人需要确认现有会话／授权，在派发前持久化预留再使用更新后的账目；本 CLI 不提供拨款、文件锁、跨设备协调或硬熔断。缺实际请求上界和取消保证时，不能承诺硬金额上限。

## 6. 重试 schema 与运行边界

完整字段见 [usage-retry-ok.json](examples/usage-retry-ok.json)：

- `retry_layers` 是空数组、`["sdk"]` 或 `["outer"]`；不允许两层叠加。
- `max_attempts` 为 1–10，包含第一次请求；为 1 时不配置重试层，其余必须指定一层。
- `initial_backoff_seconds/max_backoff_seconds` 满足 `0 < initial ≤ max ≤ 3600`。
- `concurrency` 为 1–10,000；并发超过 1 且允许重试时 `jitter` 必须为 `full`。运行方应采用有界退避并在每次重试前随机化等待，避免同时醒来。此脚本不运行随机调度。
- `respect_retry_after` 必须为 true；服务方要求的最短等待超过本次允许等待时应停止／延期，不能把 Retry-After 截短后立即重试。

成功输出明确 `runtime_enforcement_verified: false`。本地验证记录能检查字段组合，不能证明 SDK 的真实重试参数、远端取消或限流服务行为已经执行。

## 7. 验证与维护

```bash
python3 -B -m unittest discover -s scripts/tests -p test_model_cost.py -v
```

测试采用可手算常量，覆盖 T20 的请求身份／冲突／真实重试、T21 的缓存／reasoning／工具费用、T22 的缺事实／非法数／重复键、T23 的 32 个短请求／长档／多历史快照，以及 T19/T24 的控制者声明／取消未知／审阅收尾预留／单层有界重试。每个 CLI 均通过 subprocess 实际运行 help、成功与失败路径；另有超大 JSON 指数不能回溯崩溃的回归。

这是离线确定性验收；真实 API、订阅额度、付费重试、远端取消、跨进程锁、32 个真实模型并发均未由这些测试验证。更新价格或规则时应新增有出处的快照、同步示例绑定、运行受影响测试，并保留原有历史记录。
