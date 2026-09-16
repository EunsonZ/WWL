---
domain: "计算机知识"
type: "course"
stage: 1
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/01-Kali定位与安装校验|Kali定位与安装校验]]"
sources:
  - "https://jqlang.org/manual/"
  - "https://manpages.debian.org/testing/acl/acl.5.en.html"
  - "https://manpages.debian.org/testing/bash/bash.1.en.html"
  - "https://manpages.debian.org/testing/coreutils/chmod.1.en.html"
content_status: "usable"
evidence_status: "partial"
---

# Shell文件权限与文本处理

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/01-Kali定位与安装校验|Kali定位与安装校验]]。

## 命令不是一整块字符串

Shell 先解析引号、变量、通配符与重定向，再启动程序。很多“工具失效”实际上发生在程序收到参数之前。Kali 的交互 Shell 配置可能与 Bash 不同；本课程标记为 `bash` 的代码按 Bash 语义说明，不假定你当前会话就是 Bash。[^s1]

例如文件名包含空格时：

```bash
file='report draft.txt'
printf '%s\n' "$file"
# 引号使变量成为一个参数；不加引号可能发生拆词和通配符展开
```

单引号通常保留字符原样；双引号允许变量展开但保护空格；反引号是旧式命令替换，不是文本引用符。Markdown 的反引号只负责排版，复制进终端后并不会成为“安全边界”。

## 从文件到权限模型

普通文件的 `r/w/x` 分别表示读取、写入与执行；目录的 `r` 用于列出目录项，`x` 用于遍历/查找，`w` 涉及新增或删除目录项。删除一个文件主要受其父目录权限等条件约束，不只看文件自身是否可写。所有者、所属组和其他用户的权限位按适用身份判断，不能简单相加。[^s2]

```bash
id
ls -ld .
stat report.txt
umask
# 仅对你创建的实验文件调整权限
chmod 600 report.txt
chmod 700 private-output
```

`600` 给予所有者读写，组和其他用户无权限；`700` 对目录允许所有者完整访问。`chmod -R 777` 不是通用修复：它同时扩大攻击面、改变证据条件，并掩盖真实的身份/目录问题。ACL、挂载选项、SELinux/AppArmor 和 capabilities 可能进一步影响权限，见 [[计算机知识/Kali/04-服务身份与主机评估/07-Linux权限边界与配置审计|权限边界审计]]。

## 管道、重定向与返回值

标准输入、标准输出和标准错误通常对应文件描述符 0、1、2。`>` 会截断目标文件；`>>` 追加。Shell 在启动命令前完成重定向，因此 `sudo command > protected-file` 中的重定向未必以管理员身份执行。

```bash
mkdir -p "$HOME/kali-lab/output"
printf '%s\n' 'open' 'closed' 'open' > "$HOME/kali-lab/output/states.txt"
sort "$HOME/kali-lab/output/states.txt" | uniq -c
```

这里先排序让相同值相邻，再计数。直接 `uniq -c` 不会自动把分散在文件各处的相同记录合并。分析结构化数据时应保留字段，不把逗号、引号和嵌套结构交给一串脆弱正则。

```bash
# 按 Bash 语义观察管道总退出码；下一条命令必须立即读取 $?
set -o pipefail
printf '%s\n' 'alpha' | grep 'beta'
printf 'exit=%s\n' "$?"
```

`grep` 没匹配到时的非零返回值并不一定表示程序故障。`set -e` 也不是异常处理系统，其行为受条件语句和命令上下文影响。重要失败应显式判断，不靠一个“严格模式”口号。

## 常用文本工具如何分工

`less` 用于分页阅读，`head/tail` 用于局部预览，`grep/rg` 用于检索，`cut` 适合简单分隔字段，`awk` 适合记录与字段计算，`sed` 适合受控文本变换，`jq` 解析 JSON。处理文件名时尽量使用空字符分隔，避免空格和换行造成歧义：

```bash
find ./evidence -type f -name '*.txt' -print0 | xargs -0 -r sha256sum
```

上例只读文件并计算摘要；路径必须是你自己的证据副本。不要用 `for f in $(ls)` 处理任意文件名。对 JSON 统计可用 `jq -r '.status' access.jsonl | sort | uniq -c`，前提是每行都是独立 JSON 对象；附带 [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|教学夹具]] 正是这种结构。

`tar`、`zip` 和 `7z` 用于归档；压缩不等于加密。`file` 按文件特征判断类型，不按扩展名保证安全。`sha256sum` 用于内容标识，不证明来源可信。

## 迁移检验

有人把“Permission denied”解决为所有文件 `chmod 777`。你应先问：失败的是目录遍历、文件读写、程序执行还是绑定端口？进程以谁的身份运行？是否在只读挂载中？这组问题比记住一个万能命令更有迁移价值。

自检：`2>&1 >out.txt` 与 `>out.txt 2>&1` 是否相同？不相同，重定向按从左到右处理；前者先让标准错误跟随当时的标准输出，后者先改标准输出再让错误跟随它。参见 Bash 的 REDIRECTION 章节。[^s1]

## 把八进制权限推出来，而不是背结果

每组三位分别对应读 4、写 2、执行或遍历 1。因此普通文件 `640` 表示所有者读写、组只读、其他无权限；目录 `640` 则通常不能被正常遍历，不能把文件的合理值原样套到目录。

在**没有默认 ACL、且程序请求通常创建权限**的简化情形下，实际权限等于请求权限按位去掉 umask 屏蔽的位。普通文件常从 `666` 请求开始，目录常从 `777` 开始。umask 为 `027` 时，两者分别得到 `640` 和 `750`。这是按位运算，不是十进制减法；程序显式请求更少权限时，umask 不会为它补上权限。默认 ACL 存在时还要遵守其继承规则。[^v2-acl]

传统权限检查先看是否为文件所有者，否则检查匹配组，否则看其他位；不能因为所有者权限不够，再退到“其他用户更宽”的权限。ACL 则增加指定用户、指定组和 mask 的约束。`getfacl` 中某用户写着 `rw-`、旁边有效权限却只有 `r--`，应看 mask，而不是认定工具矛盾。

## 三类特殊位应放在具体对象上理解

目录的 setgid 常用于让新建项目文件继承目录所属组；sticky bit 常用于限制共享可写目录中的删除与重命名；普通可执行文件的 setuid 涉及执行时有效身份变化。它们都不是“额外的读写位”。这些机制受挂载、内核和执行格式等条件限制，不应仅凭 `ls -l` 的一个 `s` 就断言可提升权限。进一步的审计放在 [[计算机知识/Kali/04-服务身份与主机评估/07-Linux权限边界与配置审计|Linux 权限边界]]。

## 保留管道中每个程序的状态

考虑“解析日志 → 过滤 → 计数”。计数程序正常退出，不能证明上游成功读取了日志。Bash 的 `PIPESTATUS` 数组能保存最近前台管道各命令的退出码，但下一条命令就会更新它，所以先复制再输出。[^v2-bash]

```bash
# 独立子 shell 避免改变交互会话；set +e 允许观察预期的非零结果。
(
  set +e
  printf '%s\n' alpha | grep beta
  codes=("${PIPESTATUS[@]}")
  printf 'producer=%s filter=%s\n' "${codes[0]}" "${codes[1]}"
)
```

这个例子应观察到生产者 0、过滤器 1；1 在这里表示未匹配。`grep` 的读取错误是另一类状态。生产者提前遭遇关闭的管道又可能收到 SIGPIPE，因此“非零”必须结合程序与上下文解释。

## 结构化处理的一次小闭环

`jq -e 'type == "object"' access.jsonl` 会为每个 JSON 值分别输出布尔值，**不能凭它的退出码断言全部记录都是对象**：`-e` 依据最后一个输出值确定相应退出状态。前面输出 false、最后输出 true 时，进程仍可返回 0。还需要整体聚合判断和字段检查；本轮已用坏记录在前、好记录在后的输入复现这个问题。[^v3-jq]

> [!question] 自检
> 目录对你有 `wx` 而没有 `r`，已知完整文件名时是否一定打不开文件？不一定。你可能仍能按名字查找；目录列举权限与文件本身读权限是两个检查。再加上 ACL、挂载和强制访问控制，才能解释具体系统上的失败。

## 从坏记录到错误统计：完整走一次输入验收

先不要统计状态码，观察下面这个不创建文件的反例。输入是一个数组和一个对象，两者都是合法 JSON，但前者不符合日志记录的对象合同。

```bash
# Bash；仅处理内存中的合成输入，没有网络或系统配置变更。
(
  set +e
  printf '%s\n' '[]' '{"status":200}' | jq -e 'type == "object"'
  rc=$?
  printf 'jq_exit=%s\n' "$rc"
)
```

会依次出现 false、true、`jq_exit=0`。错误不在 JSON 解析器，而在我们把“最后一个条件成立”当成了“所有条件成立”。加入 `pipefail` 也无济于事，因为这个 jq 本来就返回成功。把输入顺序反过来，退出状态又不同，说明这个验收条件错误地依赖记录排列。

对已经限定为小文件的教学输入，可以先 `-s` 将全部 JSON 值收集成数组，再只输出一个整体条件。这里的明确合同是：至少一项、每项为对象、status 为 100 到 599 之间的整数值。[^v3-jq]

```bash
# 在夹具目录执行；只适合内存预算内的小文件。
jq -e -s -f "$HOME/kali-lab/code/validate_status.jq" access.jsonl
```

完整表达式以 [[计算机知识/Kali/07-综合实验/代码/validate_status.jq|validate_status.jq]] 为唯一真源，先按实验准备页复制本版代码。`all` 对空集合本身为真，因此额外写 `length > 0`；这是一项显式政策，不是所有日志任务都必须拒绝空输入。大文件不应无界 slurp，换用有记录数量/字节预算的流式验证。这里也**没有**校验时间、主体、路径、重复 JSON 键或“一行恰好一条记录”；jq 的输入是 JSON 值流，空白行可被忽略，而原 `summarize_logs` 对空白行另有拒绝政策。不能把这个小检查包装成其等价替代品。

完成验收后，再按 `.status` 统计；统计输出与原始输入摘要、校验程序退出码一起保存。失败的输入不进入正式统计表，诊断输出仍单独保留。这一做法会在 [[计算机知识/Kali/06-取证逆向与检测/08-SuricataZeek与网络检测|检测日志关联]] 中重复出现：解析成功、记录合格、统计有意义是三个条件。

## 来源与核验范围

[^s1]: [GNU Bash 手册（Debian 分发）](https://manpages.debian.org/testing/bash/bash.1.en.html)；定位：QUOTING / EXPANSION / REDIRECTION / EXIT STATUS。网页读取：2026-09-05。
[^s2]: [GNU chmod 手册（Debian 分发）](https://manpages.debian.org/testing/coreutils/chmod.1.en.html)；定位：符号模式与八进制模式。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-bash]: [GNU Bash 手册（Debian 分发）](https://manpages.debian.org/testing/bash/bash.1.en.html)；定位：Pipelines / PIPESTATUS / Redirections / umask。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-acl]: [Linux POSIX ACL 手册（Debian 分发）](https://manpages.debian.org/testing/acl/acl.5.en.html)；定位：Access Check Algorithm / ACL_MASK / Default ACL。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-jq]: [jq 官方手册](https://jqlang.org/manual/)；定位：Invoking jq: --exit-status / --slurp；all；JSON 值流。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]