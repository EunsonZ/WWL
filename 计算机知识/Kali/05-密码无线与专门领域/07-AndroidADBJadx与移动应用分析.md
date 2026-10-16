---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]"
  - "[[计算机知识/Kali/06-取证逆向与检测/05-GhidraRadare2与静态逆向|GhidraRadare2与静态逆向]]"
sources:
  - "https://frida.re/docs/home/"
  - "https://apktool.org/"
  - "https://github.com/skylot/jadx"
  - "https://developer.android.com/privacy-and-security/security-config"
  - "https://developer.android.com/privacy-and-security/risks/android-exported"
  - "https://developer.android.com/tools/adb"
  - "https://www.kali.org/tools/jadx/"
content_status: "usable"
evidence_status: "partial"
---

# AndroidADBJadx与移动应用分析

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]；[[计算机知识/Kali/06-取证逆向与检测/05-GhidraRadare2与静态逆向|GhidraRadare2与静态逆向]]。

## 设备、应用包和运行时分别回答什么

Android Debug Bridge，简称 ADB，是与 Android 设备/模拟器通信的调试桥。JADX 将 DEX 等字节码转换为便于阅读的近似 Java 表示；Apktool 偏向资源与低层代码表示；二者不等于原始源码完整恢复。动态观察则研究程序实际执行，可能触发网络、文件修改和个人数据访问。先静态、后受控运行，不把下载到的 APK 直接装进日常手机。[^s1][^s2]

本包没有 APK、手机镜像或真实应用资料。示例只适用于你自行编译的演示 App 或明确授权的测试包，不包含第三方应用的登录绕过或数据提取链。

## 四种工具分别看到了应用的哪一种表示

| 工具 | 主要对象与功能 | 应保留的认识边界 |
| --- | --- | --- |
| ADB | 客户端、主机服务和设备端守护进程组成的调试通道 | 主机被设备授权，不表示自动获得每个应用私有数据的任意访问 |
| JADX | 将DEX等输入重建成便于阅读的高级表示 | 不是原始源码恢复保证；某些结构会失败或失真 |
| Apktool | 资源、清单和字节码表示的解码与重建 | 重建产物不是原包身份与签名的原样延续 |
| Frida | 对正在运行的进程进行动态插桩 | 只观察触发的执行路径，插桩本身也会改变环境 |

上游文档支持这些职责划分；本轮未连接设备、重打包应用或注入任何进程。[^v5-adb][^v5-jadx][^v5-apktool][^v5-frida]

工具应按问题搭配：追清单入口与资源配置先看包结构；理解 Java/Kotlin 相关业务逻辑可读反编译表示；遇到 native 库则转向本库 [[计算机知识/Kali/06-取证逆向与检测/05-GhidraRadare2与静态逆向|机器码、数据流与类型推断]]；确认某分支实际发生才需要经授权的运行时证据。不应把每个静态疑点都自动升级为绕过客户端保护的动态操作。

## ADB：确保设备身份和调试授权

```bash
adb version
adb devices -l
# 只有列表中恰好是已授权的测试设备后，才代入其 SERIAL：
# adb -s SERIAL shell getprop ro.build.version.release
```

`unauthorized` 需要在你控制的设备上确认调试授权；不能把它当作应绕过的障碍。多设备时明确 `-s`，避免命令落在私人手机上。即使 `adb devices` 看似只读，ADB 工具也可能启动本机 adb server；所以这些命令并未由本包构建过程执行。设备调试、无线配对和 host server 暴露范围按当前官方说明核对。[^s1]

## JADX 的本地静态工作流

```bash
jadx --version
jadx --help
# own-demo.apk 为你自行提供的演示包；并未随本包分发。
jadx -d "$HOME/kali-lab/output/own-demo-src" own-demo.apk
```

先记录 APK 的 SHA-256、来源和编译版本。阅读 Manifest 的导出组件、权限和网络配置，再看从入口到敏感功能的数据流。某个字符串出现“password”不证明硬编码凭据；可能只是界面标签。反编译失败、混淆和多模块会导致不完整输出，报告不能把缺失代码解释为功能不存在。[^s2]

Apktool 常用于资源解包；应先读本机帮助再对自有 APK 做解码，保留原包，不自动重打包、签名或安装。Frida、Objection 支持运行时观察，但调用脚本可以改变应用行为，必须审阅脚本和限定进程；本课只给选型边界，不附第三方保护绕过脚本。

## 静态反编译结果如何交叉验证

DEX 反编译出的控制流和变量名可能不等于原始源码。对关键分支检查相应低层表示、调用者、异常路径与资源配置；动态运行时只操作专用合成数据，并限定设备序列号、进程、网络范围与日志窗口。

日志中的 token、Intent extras、剪贴板、备份和本地存储都可能含隐私。先设计只保留类型/字段与必要标记的证据，再采集；不要导出整个手机文件系统。退出后确认调试授权、测试代理与临时应用数据按计划恢复。

## 从看到常量到确认安全问题还缺少使用路径

原创例：包内含一个看似服务器地址的字符串。它可能是当前使用地址、未启用功能、测试残留或错误信息的一部分。需要定位引用、构建变体和实际调用，才能判断用途。找到加密函数也同样不能证明敏感数据一定经过它，必须追踪输入、输出与实际存储或发送位置。

客户端存在权限检查，只支持客户端行为的一部分。若关键资源在服务端，安全结论还需回到服务端身份与对象授权；客户端界面隐藏某按钮不是服务端拒绝该动作的证明。反过来，客户端逻辑容易阅读，也不自动构成漏洞。将可观察性、保护目标和授权结果分开，才能避免把反编译成功本身当成安全发现。

## 从 Manifest 入口追到服务端权限

先列 Activity、Service、Receiver、Provider 等入口及导出/权限条件，再沿 Intent、URI、文件或网络字段追踪到敏感操作。`android:exported` 应按组件类型和目标平台明确声明与审阅，不能只靠历史默认值；导出本身不等于漏洞，但无必要导出会扩大外部可达面。[^v2-androidexported]

假设自有 App 有“打开报告”的导出入口：外部提供报告 ID 后，客户端展示它之前是否经过本地约束，服务端又是否按当前身份检查对象权限？即使客户端检查遗漏，服务端拒绝可能仍保护数据；反过来，客户端按钮隐藏正确也不替代 API 授权。

## 客户端信任配置与测试 CA

Android Network Security Configuration 可以按域配置明文策略和信任锚，并区分调试覆盖；`debug-overrides` 的生效与 debuggable 状态相关。[^v2-androidnetwork] 对自有 App 优先用专门 debug 构建显式信任教学 CA，避免把放宽策略打进发布包或修改日常设备全局信任。

静态看到了证书固定相关函数，不代表所有网络库和路径实际采用它；没看到熟悉函数也可能是原生库或封装实现。TLS 失败先查实际主机名、构建配置、信任来源与所用网络栈，不把绕过第三方保护作为默认排错。

## 如何形成可复核结论

若需要一份自己的源码和可构建合成包，先做 [[计算机知识/64-移动平台开发/01-生命周期状态归属与离线同步#一套能构建的语言、工具与应用结构|Android生命周期工程]]。在专用模拟器上分别观察Activity重建、后台进程终止和数据库恢复，再回来看Manifest/进程/存储表示；该工程只使用合成预约与debug实验入口，不把自身构建、ADB或UI结果冒充JADX/Frida安全验证。

一条“组件暴露”发现至少需要组件名、导出条件、权限校验位置、调用前提、实际可触及的数据及用户交互要求。静态存在导出组件不自动等于有漏洞：它可能是应用有意公开的、受恰当权限保护的接口。网络分析要区分客户端证书信任、平台网络安全配置与应用业务授权，参见 [[计算机知识/Kali/03-Web与API安全/10-TLS证书与服务配置评估|TLS]] 和 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|身份边界]]。

> [!question] 自检
> JADX 显示某函数没有检查权限，可以直接报告越权吗？还不够。检查调用链、组件层限制和服务端权限；也可能在更上游已验证。明确你的观察范围，再设计最小、受控的反例测试。

## 能够迁移的自检

一段反编译代码检查了 `isAdmin`，能否证明管理员权限在服务端执行？不能，需追踪值来源与实际 API 授权。测试包正常连教学代理，能否说明发布包信任策略相同？不能，构建变体就是可能改变结论的条件。

## 来源与核验范围

[^v5-adb]: [Android Developers — Android Debug Bridge](https://developer.android.com/tools/adb)；定位：client/server/daemon 模型与设备授权。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-jadx]: [JADX upstream README](https://github.com/skylot/jadx)；定位：反编译输入、功能和并非全部代码都能正确恢复的限制。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-apktool]: [Apktool official overview](https://apktool.org/)；定位：资源与字节码表示解码、重建职责。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-frida]: [Frida official — Welcome](https://frida.re/docs/home/)；定位：动态插桩与运行时观察定位。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Android 官方：ADB](https://developer.android.com/tools/adb)；定位：devices / shell / authorization / debug bridge。网页读取：2026-09-05。
[^s2]: [Kali 官方：jadx](https://www.kali.org/tools/jadx/)；定位：-d / 输出与反编译限制。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-androidexported]: [Android：android:exported](https://developer.android.com/privacy-and-security/risks/android-exported)；定位：组件导出风险与显式声明。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-androidnetwork]: [Android：Network security configuration](https://developer.android.com/privacy-and-security/security-config)；定位：Trust anchors / domain-config / debug-overrides。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]