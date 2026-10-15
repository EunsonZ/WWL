---
domain: "计算机知识"
type: "course"
stage: 3
prerequisites:
  - "[[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/07-漏洞扫描NucleiGreenbone与复核|漏洞扫描NucleiGreenbone与复核]]"
sources:
  - "https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html"
  - "https://www.kali.org/tools/whatweb/"
  - "https://www.kali.org/tools/nikto/"
  - "https://www.kali.org/tools/wpscan/"
content_status: "usable"
evidence_status: "partial"
---

# Web服务器CMS与依赖评估

**先修关系：** [[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]；[[计算机知识/Kali/02-信息收集与网络测量/07-漏洞扫描NucleiGreenbone与复核|漏洞扫描NucleiGreenbone与复核]]。

## 指纹、配置与组件漏洞是三层问题

WhatWeb 识别响应特征，Nikto 检查一组常见服务器配置与暴露路径，WPScan 针对 WordPress 相关信息与检查。它们的结果应分别解释为指纹线索、候选配置问题或组件适用性，而不是一律叫“漏洞已利用”。[^s1][^s2][^s3]

## WhatWeb：轻量观察也有请求成本

```bash
# 自建静态服务已经启动；输出只包含教学内容
whatweb -a 1 --log-json="$HOME/kali-lab/output/whatweb.json" \
  http://127.0.0.1:8000/
```

按当前帮助确认 `-a` 的检测级别及插件行为。一次请求的响应首部、HTML 标记与脚本资源只反映看到的那一层；反向代理、缓存、定制主题与隐藏版本信息会影响指纹。识别不到不代表组件不存在，识别到也不保证版本准确。

## Nikto：规则检查不是业务授权检查

Nikto 可以检查常见路径、文件、首部和配置。它可能产生较多请求，使用前审阅检测类别、最大时间与路径范围。先 `nikto -Help`，再为自建服务器选择最小项目，不把默认全量扫描用于脆弱设备或生产系统。

```bash
nikto -Version
nikto -Help
# 扩展形态：仅在可恢复的自建服务上，明确预算后执行
# nikto -h http://127.0.0.1:8000 -maxtime 30s \
#   -output ./output/nikto.txt
```

本包静态服务器不是供任意漏洞检查的完整靶场，正常响应可用于理解工具请求，但不能代表真实服务器安全水平。Nikto 发现目录索引时，也要确认该目录本来是否设计为公开下载。

## WPScan：专用工具必须匹配应用

先确认目标确实是你拥有的 WordPress 测试站点，再核对 WPScan 当前帮助中的检测模式和 API 数据使用方式。漏洞数据查询可能需要令牌，具体许可、限额和商业使用条件应查官方当前规定，本包不替你作许可判断。

```bash
wpscan --help
# 可选模板：另行建立的本机 WordPress，不是本包静态服务
# wpscan --url http://127.0.0.1:8082 --detection-mode passive \
#   --format json --output ./output/wpscan.json
```

这里的“passive”不表示完全不访问目标，而是相关检测方式的限制。禁用用户名/口令测试等不必要功能，避免把一个插件版本核查扩大成账户审计。

## 依赖与补丁的第二条证据链

从服务器软件物料清单、锁文件、包管理器和厂商公告核对版本，比只根据 HTML 中一个字符串更可靠。版本号可能被隐藏或回移补丁不改变主版本字符串，因此需要记录具体发行版包版本、补丁来源与组件是否启用。

对前端依赖，source map、资源路径与版本标记可以提供线索，但只有实际加载和可达代码路径才与某些问题相关。修复后重跑同一最小请求，并验证正常功能未回归。

## 自检

WhatWeb 识别出 WordPress，WPScan 没有发现已知问题，能否保证插件业务逻辑没有越权？不能，指纹与已知漏洞数据库并不覆盖所有自定义逻辑。应回到 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|授权矩阵]] 与应用自己的安全合同。

## 建立从指纹到适用性的五步链

先记录观察到的产品线索，再从软件清单/锁文件/包版本确认实际组件；随后核对漏洞公告受影响范围，检查有问题的功能和配置是否启用，最后确认部署中能否到达相应代码路径。未知环节保留未知，不能把候选版本直接升级为已确认可利用。[^v2-vulndeps]

举例：静态资源名包含旧版本字符串，但构建实际采用回移修补包，这是两种证据的冲突，应该查包来源与补丁记录；另一个例子是构建依赖有问题但运行时未打包，风险路径与直接暴露的服务器组件不同。反过来，隐藏版本头并不会删除实际易受影响代码。

## SBOM、SCA 与配置扫描的职责

软件物料清单（SBOM）描述组件与关系；软件组成分析（SCA）将组件与已知问题及许可信息关联；服务器配置扫描观察部署行为。SBOM 不是漏洞判定器，SCA 的零结果取决于清单完整性、匹配规则和数据库版本，配置扫描也不能穷尽业务逻辑。

保留包生态、完整版本、来源仓库/镜像摘要、直接或传递依赖、构建/运行用途与数据库更新状态。不要只手填一个短产品名称后期待跨生态版本比较正确。

## 修复不等于把告警设成忽略

升级、回移补丁、关闭受影响功能和额外隔离解决不同层次的问题。暂时缓解应有适用范围、验证结果、负责人和复查条件；“不适用”的结论应能回到配置或可达性证据，而不是因为升级不方便。

相同组件的详细镜像与配置审计放在 [[计算机知识/Kali/05-密码无线与专门领域/06-容器Kubernetes与IaC审计|容器与基础设施审计]]；这里保留 Web 入口的证据链，避免复制两套互相漂移的操作说明。

## 来源与核验范围

[^s1]: [Kali 官方：whatweb](https://www.kali.org/tools/whatweb/)；定位：-a / --log-json / 插件指纹。网页读取：2026-09-05。
[^s2]: [Kali 官方：nikto](https://www.kali.org/tools/nikto/)；定位：-h / -Tuning / -maxtime / -output。网页读取：2026-09-05。
[^s3]: [Kali 官方：wpscan](https://www.kali.org/tools/wpscan/)；定位：--url / detection mode / API token。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-vulndeps]: [OWASP：Vulnerable Dependency Management](https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html)；定位：Identification / Risk Assessment / Remediation。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]