# 查询合同、类型统一与状态join：有限执行与复现

主解释为 [知识表示、规则与查询](../../05-知识表示规则归结与查询.md) 和 [复制一致性与可见性历史](../../../../计算机知识/65-分布式系统/02-复制一致性与可见性历史.md)。规范代码分别为 [query_contract_examples.py](../../query_contract_examples.py) 和 [gcounter_join_examples.py](../../../../计算机知识/65-分布式系统/gcounter_join_examples.py)，有限项统一依赖已有 [symbolic_ai_lab.py](../../symbolic_ai_lab.py)。一般语义、保解集与收敛结论依靠正文的前提和证明，有限执行补具体模型与反例。

[独立执行原报告](execution-report.md)、[固定命令/环境](fixed-runs.json)、[执行者oracle命令](executor-run.json)、[原18份输入身份](source-manifest.json)、[运行后源检查](source-recheck.json) 保存原执行身份；冻结输入从下述固定 Git 提交恢复。三条固定命令与执行者另写的独立oracle均真实exit 0，四份stderr为空；Python 3.14.7、标准库SQLite及macOS平台见原记录，没有安装或连接服务。原快照中的作者“未运行”文字记录的是作者提交时状态，正式读者页随后接实际回执，代码未改，不把后修文字SHA冒充执行输入。

- [query原stdout](logs/query.stdout) / [stderr](logs/query.stderr)：M0/M1均满足事实与全部规则实例，`Anc(Cora,Ada)`分别false/true；SQLite实际三行是 `[1,0,0,0]`、`[2,null,1,1]`、`[null,null,1,0]`。Arrow三变量归一到同一自由代表，Bool题为Bool/Bool；间接occurs、自应用及Bool/Int冲突失败。空KB的结构统一成功不能推导语义蕴含。
- [G-Counter原stdout](logs/gcounter.stdout) / [stderr](logs/gcounter.stderr)：三种乱序重复状态都得到(2,3)/5，scalar-max为3、scalar-sum为7；共享身份、状态丢失、末次未传播和溢出各有具体失败条件。重复命令与重复状态不同；预约集合union同值，但两条重叠预约使容量1不成立。
- [作者有限oracle输出](logs/author-batch-oracle.stdout) / [stderr](logs/author-batch-oracle.stderr) 与 [原源码（固定提交）](https://github.com/EunsonZ/WWL/blob/b19b34ce1d11562a9963c0206503988976a65448/AI/13-%E6%90%9C%E7%B4%A2%E6%8E%A8%E7%90%86%E4%B8%8E%E8%A7%84%E5%88%92/%E8%BF%90%E8%A1%8C%E8%AF%81%E6%8D%AE/2026-10-10-query-types-join/snapshot/evidence/independent_batch_oracle.py) 明确归属于作者；[执行者独立oracle](executor_oracle.py) 及 [原输出](logs/executor-oracle.stdout) / [stderr](logs/executor-oracle.stderr) 用另写预期核规则真值、SQL三值、替换/组合/occurs、事件集合、最小上界与容量反例，不调用被测报告函数作为期待真源。

独立有限检查还包括：4个有限ground Bool/Arrow类型的64赋值中恰4组相等解；5例编码/替换交换；16状态的256对最小上界和4096三元ACI、三个消息序列以及完整事件身份集合。这些不是任意输入正确性或所有CRDT历史证明，也没有运行预约Authority。三固定任务约0.044/0.017/0.032s，独立oracle约0.011s只是软件耗时；子进程集合RSS26,132,480byte及oracle自进程26,230,784byte分别是有限观察，不是硬上限或OS线程数认证。

本目录保留原驱动、实际执行报告、stdout/stderr 与身份清单。冻结输入及5项只读资源副本保存在清理前固定提交 `b19b34ce1d11562a9963c0206503988976a65448`，按下述命令恢复到库外临时目录。原artifact清单属于首次包的文件身份，其中`README.md`原件在此存为`execution-report.md`；实际复制映射见 [delivery-copy-map.json](delivery-copy-map.json)。快照80引用的既有prototype HTML及SQL/RAG文档引用的既有图资源另作只读归档副本，不属于18份实跑输入，没有新增图渲染或HTML/UI执行。原绝对目录仅作为命令来源，不是复建依赖。原报告、`source-manifest.json`、`artifact-manifest.json` 和 `delivery-copy-map.json` 中的 `snapshot/` 相对路径描述首次执行/复制时的布局，保留历史原文；它们不表示这些副本仍位于当前工作树。恢复后会重新得到原布局。

复建需要本地 Git 中仍可读取该固定提交，以及 Git、tar 和已有 Python 解释器。从库根执行，创建自己拥有的唯一新空目录；归档先落盘再解包，任一步失败都停止，不在本证据目录覆写 logs 或 JSON：

```bash
query_commit=b19b34ce1d11562a9963c0206503988976a65448 &&
query_evidence='AI/13-搜索推理与规划/运行证据/2026-10-10-query-types-join' &&
git cat-file -e "$query_commit^{commit}" &&
query_run=$(mktemp -d /tmp/wwl-query-types-join.XXXXXX) &&
git archive --format=tar "$query_commit" \
  "$query_evidence/snapshot/AGENTS.md" \
  "$query_evidence/snapshot/HANDOFF.md" \
  "$query_evidence/snapshot/candidate" \
  "$query_evidence/snapshot/evidence" \
  "$query_evidence/run_fixed.py" \
  "$query_evidence/executor_oracle.py" \
  "$query_evidence/source-manifest.json" > "$query_run/frozen-inputs.tar" &&
tar -xf "$query_run/frozen-inputs.tar" -C "$query_run" --strip-components=4 &&
cd "$query_run" &&
python3 -B - <<'PY_VERIFY'
import hashlib, json
from pathlib import Path
rows = json.loads(Path("source-manifest.json").read_text())["files"]
assert len(rows) == 18, f"expected 18 inputs, got {len(rows)}"
for row in rows:
    data = (Path("snapshot") / row["path"]).read_bytes()
    assert len(data) == row["bytes"], row["path"]
    assert hashlib.sha256(data).hexdigest() == row["sha256"], row["path"]
print("18/18 source bytes and SHA256 PASS")
PY_VERIFY
```

上一步退出码为 0 且打印 `18/18 source bytes and SHA256 PASS` 后，在同一 shell 继续运行：

```bash
mkdir home tmp logs &&
python3 -B run_fixed.py &&
python3 -B - <<'PY_RUNS'
import json
from pathlib import Path
runs = json.loads(Path("fixed-runs.json").read_text())["runs"]
assert [r["name"] for r in runs] == ["query", "gcounter", "author-batch-oracle"]
assert all(r.get("exit") == 0 and "error" not in r for r in runs)
assert all((Path("logs") / (r["name"] + ".stderr")).stat().st_size == 0 for r in runs)
print("3/3 fixed tasks exit 0; stderr empty")
PY_RUNS
```

三任务检查退出码为 0 后，继续执行独立 oracle 并检查实际输出：

```bash
python3 -B executor_oracle.py > logs/executor-oracle.stdout 2> logs/executor-oracle.stderr &&
python3 -B - <<'PY_ORACLE'
import json
from pathlib import Path
assert json.loads(Path("logs/executor-oracle.stdout").read_text())["status"] == "PASS"
assert Path("logs/executor-oracle.stderr").stat().st_size == 0
print("executor oracle PASS; stderr empty")
PY_ORACLE
```

成功须三段检查均退出 0，三固定任务全部 exit 0、oracle 的 JSON `status` 为 `PASS`，四份 stderr 为空；新回执只在 `$query_run` 中。原 stdout 可逐项对照本页链接，耗时、PID、绝对路径与平台字段按本次实际记录，不要求与历史值相同。独立执行代理已从上述固定提交恢复旧布局并观察到18/18身份通过、三任务 exit 0、oracle PASS、三固定 stdout 与原回执相同；这是该次恢复实验的观察，不代表任意后续环境已通过，也不把修改本说明当作重跑。

驱动以自身目录解析冻结源码，只有标准库与已有Python解释器前提，不依赖hidden作者目录。三固定子命令各设60秒超时；额外oracle是有限循环，没有线程池。规范示例也可从库根直接只输出stdout：

```bash
python3 -B AI/13-搜索推理与规划/query_contract_examples.py
python3 -B 计算机知识/65-分布式系统/gcounter_join_examples.py
```

这里实际执行SQLite，没有认证PostgreSQL方言或真实RAG服务/访问权限。预约容量例反驳另造的无协调接受规则，不认证实际Authority或生产数据库。#172/#175的更新/删除、事件时间与恢复协议及#209删除/成员变更/恶意节点/文本协作仍由各自任务建设。HTTP/身份认证、网络存储部署、Obsidian显示/同步、真人学习和性能未验，不把最终集合相同当作业务承诺安全。
