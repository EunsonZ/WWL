---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/04-服务身份与主机评估/07-Linux权限边界与配置审计|Linux权限边界与配置审计]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/07-漏洞扫描NucleiGreenbone与复核|漏洞扫描NucleiGreenbone与复核]]"
sources:
  - "https://docs.sigstore.dev/cosign/verifying/verify/"
  - "https://trivy.dev/docs/latest/scanner/vulnerability/"
  - "https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/"
  - "https://github.com/anchore/grype"
  - "https://github.com/anchore/syft"
  - "https://kubernetes.io/docs/concepts/configuration/secret/"
  - "https://kubernetes.io/docs/concepts/services-networking/network-policies/"
  - "https://kubernetes.io/docs/tasks/configure-pod-container/security-context/"
  - "https://trivy.dev/docs/latest/target/filesystem/"
  - "https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html"
  - "https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/"
content_status: "usable"
evidence_status: "partial"
---

# 容器Kubernetes与IaC审计

**先修关系：** [[计算机知识/Kali/04-服务身份与主机评估/07-Linux权限边界与配置审计|Linux权限边界与配置审计]]；[[计算机知识/Kali/02-信息收集与网络测量/07-漏洞扫描NucleiGreenbone与复核|漏洞扫描NucleiGreenbone与复核]]。

## 扫描器究竟看到了哪一层

容器镜像是文件系统与运行配置的打包，不等于正在运行的容器；容器也不是完整虚拟机。Kubernetes 对工作负载进行编排，RBAC 描述主体被允许对哪些资源执行哪些动作。基础设施即代码 IaC 是描述资源配置的文本，不代表已经部署出的真实状态。把这几层混为一谈，会产生“文件没问题，所以集群安全”的错误结论。

Trivy 可分析软件清单、漏洞和配置等不同对象；文件系统模式与镜像模式并非同一输入。Checkov 主要对 IaC 按策略检查，发现的是规则所表达的配置条件，不是一次漏洞利用成功。[^s1][^s2]

## 控制面检查与运行时限制不在同一层

把一次资源创建分成：请求主体认证、API 动作授权、适用的准入变更与验证、持久化及控制器协调，最后才是实际运行。准入位于认证和授权之后，且不是所有只读请求的过滤层。一个主体被允许创建对象，不表示它提交的任何配置都可通过准入。[^v5-k8s-admission]

| 层次 | 主要约束 | 单独通过不能说明什么 |
| --- | --- | --- |
| API身份与RBAC | 谁可对何类API资源执行何动作 | 提交内容一定安全、容器运行时一定受限 |
| 准入与配置政策 | 哪些资源字段或条件允许持久化 | 运行环境永远与静态声明一致 |
| 进程与文件系统 | 身份、能力、挂载和安全限制 | API凭证权限或网络策略完整性 |
| 网络策略与实际数据路径 | 哪些通信被允许 | 应用对象授权、所有插件实现都已正确生效 |

这是职责图，不是所有机制简单串联的内核调用图。命名空间与 capabilities 的精确定义见 [[计算机知识/Kali/04-服务身份与主机评估/07-Linux权限边界与配置审计|Linux权限与命名空间]]；不在这里再维护一份简化到失真的副本。

## 从静态 YAML 到实际进程的四次核对

先审阅提交的配置，再看准入控制处理后的对象，随后确认运行时有效身份与挂载，最后验证业务和网络行为。`runAsNonRoot` 约束运行身份，`allowPrivilegeEscalation: false`、能力丢弃、seccomp 与只读根文件系统控制不同条件，不能互相替代。[^v2-kubeseccontext]

只读根文件系统也不代表所有卷都只读；容器 UID 不是宿主机隔离的全部保证。宿主机路径、daemon socket 和特权配置可能显著改变边界，因此权限判断必须结合实际运行参数，而非仅凭“用了容器”。

## RBAC、NetworkPolicy 和 Secret 的三个误区

RBAC 管 API 操作授权，NetworkPolicy 管受支持实现下的网络流量选择与隔离。策略可按方向隔离，多个允许策略可能组合；只有 API 接受了 YAML，而网络插件不支持所需语义，不能证明流量已经被阻断。[^v2-kubenetpolicy]

Secret 对象中常见 Base64 是编码，不是保密加密；存储加密、API 访问权限、挂载/环境注入与日志泄露另需处理。不要运行 `kubectl get secrets -o yaml` 把凭据材料带入课程证据。[^v2-kubesecrets]

## 一处 YAML 层级变化如何扩大网络允许集合

以下两段都是 **ingress 下 from 字段的教学片段**，不是完整 NetworkPolicy，不可直接部署。第一个 from 项中同时存在 namespaceSelector 和 podSelector，要求来源同时满足两者：处在标签 `team: red` 的命名空间中，并且 Pod 标签为 `role: client`。[^v3-netpolicy]

```yaml
from:
  - namespaceSelector:
      matchLabels:
        team: red
    podSelector:
      matchLabels:
        role: client
```

把 podSelector 前再加一个列表项分隔，得到两个独立来源条件：

```yaml
from:
  - namespaceSelector:
      matchLabels:
        team: red
  - podSelector:
      matchLabels:
        role: client
```

第二段允许红团队命名空间里的全部 Pod，**或者**策略所在命名空间中 role=client 的 Pod。它不是“所有命名空间的 client”，也不是原来的交集。两份 YAML 都可能解析成功，但代表不同允许集合。用集合语言，第一段是 `红命名空间内 ∩ client`；第二段是 `红命名空间内 ∪ 本命名空间client`，范围通常更大。

为此设计四个纸面对照：红命名空间/client、红命名空间/非client、其他命名空间/client、策略本命名空间/client。先说明命名空间是否重合，再逐项预测，避免用重复身份伪装四个独立反例。实际网络行为还取决于双方方向隔离、其他策略允许、端口、插件实现和部署生效时刻。[^v3-netpolicy]

### 为什么不能用 ping 替代全部网络策略验收

常规 NetworkPolicy 的可移植定义主要面向 TCP/UDP/SCTP；ICMP 等协议的行为可能由网络插件决定。ping 成功或失败不能独立证明应用 TCP 端口的允许集合符合要求。保持协议与端口一致，核对实际 Pod、namespace 标签与生效策略，再做获准的最小应用请求。[^v3-netpolicy]

本轮没有集群，以上是基于官方语义的配置推演，不是 Kubernetes 或 CNI 的实测。静态扫描可帮助找到疑点，不能替代实际允许/拒绝矩阵；将结果接入 [[计算机知识/Kali/01-系统与网络基础/09-状态防火墙与网络命名空间|网络过滤的观察点]] 与 [[计算机知识/Kali/04-服务身份与主机评估/07-Linux权限边界与配置审计|权限条件组合]]。

## 在本地文本上先建立最小闭环

本包的 `fixtures/iac/pod.yaml` 是**不可用于生产的教学配置**，有意缺少部分安全字段。不需要启动容器，也不需要连接集群。准备好工具后，在复制出的实验目录中检查：

```bash
trivy --version
trivy fs --scanners misconfig "$HOME/kali-lab/fixtures/iac"
checkov --version
checkov -f "$HOME/kali-lab/fixtures/iac/pod.yaml" \
  --framework kubernetes
```

这两条命令未在本包构建中执行。扫描器可能读取缓存或下载策略/数据库；“扫描本地文件”不自动表示完全离线。严格离线时先在允许联网的准备环境固定版本与依赖，再按该版官方选项禁用更新、远程模块和平台功能；缺少数据库应记录未完成，不能临时开放外网来掩盖。

对每个发现定位具体 YAML 字段，解释缺省行为与威胁前提。例如缺少明确的 `runAsNonRoot` 是需复核的配置点；实际运行身份还取决于镜像默认用户和准入策略，不能只凭一个缺失键断言容器已经以 root 运行。单独的 `capabilities.drop`、只读根文件系统和 seccomp 各控制不同边界。

## 一份便于讨论的配置改进片段

下面只是合成示意片段，不是完整可部署 Pod，也不宣称让任意镜像可运行。实际应用可能需要专用可写临时卷、不同 UID 和资源配置，先验证兼容性。

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

本段位于容器级 securityContext 的示意位置；不能把同名字段随意放到 Pod 顶层。扫描器告警减少只说明命中规则改变，不代表镜像已改为非 root，也不代表应用还正常工作。

## 扫描物料清单，而不是只比告警总数

Syft 生成镜像/文件系统的软件物料清单，Grype 对相应组件或 SBOM 做已知漏洞匹配；它们与 Trivy 的配置扫描是可互补的路径。[^v2-syft][^v2-grype] 先固定输入摘要、平台/架构、分析层范围、目录排除、工具版本和数据库时间，再比较匹配项。

镜像 tag 可以指向不同内容，摘要更适合定位本次输入；但摘要相同也不证明运行时外部挂载和环境相同。缺少数据库、组件识别失败和扫描器正常完成但未命中是三种状态，必须分开记录。此包未安装或运行上述扫描器，也未连接任何集群。

## SBOM到漏洞结论之间有四次匹配

软件物料清单先描述识别出的组件，再匹配生态与版本、供应商公告、修复状态以及适用条件。Trivy 对操作系统包与语言依赖采用相应数据源，发行版回移植补丁会使上游版本号比较失效；识别与公告策略也会在漏报、误报之间取舍。[^v5-trivy-vuln]

原创反例：镜像中的组件存在某版本字符串，但供应商已在发行版修订包中回移植修复。直接把上游版本区间套上去可能误报。另一方向，扫描器无法识别组件，不等于镜像没有该组件。于是告警数量变化必须与物料、识别器、数据库时间和过滤政策一起比较。

## 摘要、签名与安全审查是三种证据

镜像摘要用于标识内容，签名把某内容与某签名身份关联；Cosign 验证还需要明确期待的证书身份、签发者或密钥约束。[^v5-cosign] 任意签名存在不是可信发布者的证明，可信发布者签名也不是程序无漏洞的证明。

从供应链角度，应连起“分析的内容是哪一份”“为何相信来源”“该内容有哪些已知与未知问题”。这与 [[计算机知识/Kali/06-取证逆向与检测/01-取证流程镜像与时间线|哈希、来源与采集完整性]] 使用同一个证据分层，而不是把校验摘要当成万能安全认证。

## 连接真实集群之前先验证上下文

```bash
# 以下只用于你另行授权的测试集群，不属于附带离线实验。
kubectl config current-context
kubectl auth can-i get pods --namespace kali-lab
```

第一条读取本机配置中的当前上下文；第二条会联系对应 API 服务器，检查当前身份的特定权限。`yes` 仅说明这项授权判断，不代表实际请求一定成功，也不代表该命名空间所有操作都获准。未知上下文或可能指向生产集群时停止。不要为练习加 `--as` 冒用身份、导出 Secret 或访问全部命名空间。[^s3]

Docker 的 daemon socket、宿主机目录挂载、特权容器和服务账户令牌是重要信任边界；只读观察也要考虑返回内容敏感性。Kube-bench、Docker Bench 等基线工具需要与平台版本和部署方式匹配，不能把默认运行全部检查作为初学者准备步骤。本包仅作选型提示，不将这些工具算作已完成实操。

## 自检与证据边界

把教学 Pod 配置补入安全字段后，静态告警减少，只支持“对应规则不再命中”。要声称运行安全，还须检查部署后的规格、有效身份、网络策略和实际行为。把策略版本、输入摘要和扫描退出状态写入 [[计算机知识/Kali/08-模板与速查/03-发现与复测模板|发现与复测模板]]，避免用 `--soft-fail` 将发现转换为虚假的验收通过。

## 来源与核验范围

[^v5-k8s-admission]: [Kubernetes — Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)；定位：What are they、Admission control phases；仅使用稳定的概念流程，不宣称某个最新版本。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-trivy-vuln]: [Trivy — Vulnerability scanning](https://trivy.dev/docs/latest/scanner/vulnerability/)；定位：Data sources、Detection behavior、Package detection。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-cosign]: [Sigstore Cosign — Verifying Signatures](https://docs.sigstore.dev/cosign/verifying/verify/)；定位：签名验证、证书身份及OIDC签发者约束。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Trivy 官方：Filesystem](https://trivy.dev/docs/latest/target/filesystem/)；定位：--scanners / filesystem / lock files。网页读取：2026-09-05。
[^s2]: [Checkov 官方：CLI Reference](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html)；定位：-f / --framework / --soft-fail / 外部规则。网页读取：2026-09-05。
[^s3]: [Kubernetes 官方：kubectl auth can-i](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/)；定位：verb / resource / namespace / --list。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-kubeseccontext]: [Kubernetes：Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)；定位：runAsNonRoot / readOnlyRootFilesystem / capabilities / seccomp。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-kubenetpolicy]: [Kubernetes：Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)；定位：选择器、隔离方向、实现支持与合并语义。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-kubesecrets]: [Kubernetes：Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)；定位：Secret 数据编码、访问与存储保护。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-syft]: [Anchore：Syft](https://github.com/anchore/syft)；定位：SBOM inputs / output formats。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-grype]: [Anchore：Grype](https://github.com/anchore/grype)；定位：vulnerability scanning / SBOM input / database。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-netpolicy]: [Kubernetes：Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)；定位：Behavior of to/from selectors；directions；Network traffic filtering。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]