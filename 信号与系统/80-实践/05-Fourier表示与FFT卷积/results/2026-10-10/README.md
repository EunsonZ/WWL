# Fourier／旧IIR实际结果与五图显示

2026-10-10的当前源码独立执行完成Fourier 8测试、规范CLI与独立oracle；独立162项比较最大缩放误差6.365e−15，容差2e−11(1+|目标|)。六点输入全部32分块、四核共128布局核full与EOF。该源与最终正文使用的Fourier源逐字一致；结果不证明无限对象的一般收敛定理。

- [Fourier完整JSON](v1/fourier-cli-output/results.json)、[独立核算](v1/fourier-independent.json)、[6项真实命令回执](v1/execution-receipt-with-independent.json)、[测试日志](v1/fourier-tests.stderr)。
- [当时原始报告逐字快照](v1/report.md.txt)同时保留旧IIR系数与轨迹、未向外舍入估计，以及辅助求重复根失败／精确零点重试成功。它是V1历史状态，后续严格IIR结果转到[最终IIR结果](../../../06-IIR规格与实现/results/2026-10-10/README.md)，不能把旧报告的未认证当成新层结论。
- [WebKit报告逐字快照](webkit/report.md.txt)、[逐图观察](webkit/visual-observations.json)、[成功回执](webkit/render-escalated-receipt.json)、[标准沙箱失败](webkit/render-standard-receipt.json)。[表示](webkit/png-escalated/four-representations.png)、[蝶形](webkit/png-escalated/four-point-butterfly.png)、[OLA](webkit/png-escalated/overlap-add-timeline.png)、[设计链](webkit/png-escalated/design-chain.png)、[内部尺度](webkit/png-escalated/internal-scale.png)均是实际全幅PNG。
- [独立源审逐字快照](review/SOURCE_REVIEW_V1.md.txt)、[输入身份](review/reviewed-inputs-v1.json)。V1新机器证书当时被拒绝的记录保留，后续由另一独立审者接受V2层。

`v1/source-layout/`保留原27输入快照，`webkit/sources/`保留原5 SVG；所有历史Markdown改名为`.md.txt`，内容逐字保全，避免误作为读者正文。原始驱动与绝对路径回执不改写，见目录内源码与输入绑定。Cairo中文缺字、QuickLook限制、WebKit标准沙箱失败也保留；系统WebKit静态全幅查看不等于Obsidian、360px窄列、硬件或真人验收。原数值环境Python3.14.7、NumPy2.5.3、SciPy1.18.1、mpmath1.3.0，五类线程环境变量请求4，完成子进程集合观测RSS258146304bytes；没有取得OS线程计数或硬RSS上限。

复建只在自己拥有的新目录运行；[rebuild.py](rebuild.py)复制必需输入与原oracle，不调用依赖历史author路径的`v1/run.py`。先选已有上述依赖的解释器，不在复建中自动安装。下例创建唯一目录，任何步骤失败即停：

```sh
wwl_work="$(mktemp -d /private/tmp/wwl177178-rebuild.XXXXXX)" && python3 -B rebuild.py --work "$wwl_work" --kind v1
```

新驱动保存`fixed-runs.json`并验证预期7任务集合、每项exit0、无error与无超时；不能只用外层退出码作为成功证明。原始辅助失败不在新成功集合中消失，仍在冻结证据内。复建接口这里只读/AST核过，本次交付没有重跑实验。
