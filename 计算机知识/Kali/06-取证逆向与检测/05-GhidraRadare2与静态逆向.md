---
domain: "计算机知识"
type: "course"
stage: 5
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/04-Shell文件权限与文本处理|Shell文件权限与文本处理]]"
  - "[[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|进程服务日志与本机加固]]"
sources:
  - "https://ghidra.re/ghidra_docs/languages/html/pcodedescription.html"
  - "https://ghidra.re/ghidra_docs/languages/html/additionalpcode.html"
  - "https://ghidra.re/ghidra_docs/languages/html/pcoderef.html"
  - "https://sourceware.org/binutils/docs/binutils/readelf.html"
  - "https://www.kali.org/tools/ghidra/"
  - "https://book.rada.re/first_steps/intro.html"
content_status: "usable"
evidence_status: "partial"
---

# GhidraRadare2与静态逆向

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/04-Shell文件权限与文本处理|Shell文件权限与文本处理]]；[[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|进程服务日志与本机加固]]。

## 从编译后的程序恢复可检验的解释

源代码经过编译、链接和优化后，变量名、注释和某些结构可能丢失。反汇编将机器指令表示为汇编文本；反编译试图构造高层近似程序。它们是对同一字节序列的不同解释，不保证还原作者原文。Ghidra 和 Radare2 提供分析能力，但自动命名、类型推断和函数边界仍需检查。[^s1][^s2]

本课使用附带 `hello.c` 编译出的自有程序，而不是恶意样本。ELF 是常见 Linux 可执行/链接格式；架构、位数、字节序和入口点决定解释方法，不能把 x86-64 的寄存器约定套到 ARM。

## 从指令到伪代码：控制流与数据流的两条线

反汇编将字节按指令集解释；控制流图连接可能跳转的基本块；数据流分析追踪值如何产生、传播和被使用；反编译再将这些关系表达为高层结构。**基本块**可先理解为内部没有额外跳入点、以控制转移结尾的一段顺序指令。Ghidra 的 p-code 为不同处理器提供共同的运算表示，而 raw p-code 与后续分析生成的操作并不相同。[^v5-pcode]

控制流回答“可能接着执行哪一块”，数据流回答“这里使用的值可能来自哪里”。一张函数图有边，不保证边的路径条件可满足；相反，没有识别出间接调用目标，也不说明该调用不会发生。错误的函数边界、调用约定或类型推断，会向后影响看起来很整齐的伪代码。因此，美观不是证据等级。

## SSA 的合流不是把两个分支的值相加

SSA（静态单赋值）给每次赋值使用不同名字，便于追踪值的来源。原创例子：某条件为真时产生 $x_1=3$，否则产生 $x_2=7$，在共同后继块使用 $x_3=\phi(x_1,x_2)$。这里的 $\phi$ 是按实际进入路径选择相应来源，不是计算 $3+7$，也不是声明两个输入相等。Ghidra 的 `MULTIEQUAL` 就表达这种合流；`INDIRECT` 则可表达分析中尚不能直接追踪的间接影响，不能望文生义当成一条“间接跳转”机器指令。[^v5-pcode-extra]

继续沿例子推演：若后继判断 $x_3<5$，真分支只有来源为 3 的路径能满足。若你只读到变量在多个地方“赋值”，没有恢复来源与路径的对应关系，就会把不可能的路径当成真实行为。这里用的是教学控制流，不对应包内某个待执行二进制。

## 位模式的数值解释会改变比较结果

同一个 8 位模式 `0xff`，按无符号数解释是 255，按二进制补码有符号数解释是 -1。因此它与 1 比较时，`255 < 1` 为假，而 `-1 < 1` 为真。Ghidra 的 `INT_LESS` 与 `INT_SLESS` 区分无符号和有符号比较；不能看见伪代码中的 `char` 就跳过实际位宽、扩展方式和比较指令。[^v5-pcode-ops]

排除歧义的顺序是：确认机器指令语义和操作数宽度，检查零扩展/符号扩展，再检查控制流如何使用标志或比较结果，最后才给高层变量命名。修改反编译器类型标注会改变显示，未必改变字节；若两种解释都能解释少数样本，需要能够区分它们的边界输入，而不是重复运行相同样本。动态证据如何使用，见 [[计算机知识/Kali/06-取证逆向与检测/06-GDBGefStrace与动态观察|GDB 与系统调用观察]]；移动端的同类问题见 [[计算机知识/Kali/05-密码无线与专门领域/07-AndroidADBJadx与移动应用分析|JADX 的表示边界]]。

## 先做不执行样本的基线

按 [[计算机知识/Kali/07-综合实验/09-实验代码合同与复现|代码合同]] 复制代码后，可选择在自己的实验机编译。以下会生成本机二进制，但不会关闭系统保护：

```bash
mkdir -p "$HOME/kali-lab/output"
cc -std=c11 -Wall -Wextra -O0 -g \
  "$HOME/kali-lab/code/hello.c" -o "$HOME/kali-lab/output/hello"
file "$HOME/kali-lab/output/hello"
readelf -h "$HOME/kali-lab/output/hello"
readelf -l "$HOME/kali-lab/output/hello"
nm "$HOME/kali-lab/output/hello"
objdump -d "$HOME/kali-lab/output/hello"
```

`-O0 -g` 便于教学观察，不是生产构建建议。`readelf -h` 看 ELF 头，`-l` 看程序段及映射相关信息，`nm` 查看可用符号，`objdump -d` 给反汇编。未剥离的调试构建比真实发布程序容易理解，因此本练习不能代表处理混淆代码的难度。

## 补强：ELF 的三种位置不能混成一个地址

**文件偏移**表示字节位于磁盘文件的第几个位置；**链接视角的虚拟地址**是 ELF 描述的地址；**运行时地址**还受到加载映射等因素影响。节区表（sections）主要描述链接和分析所需的组织，程序头表（segments）描述装载视角。一段可装载映射可以覆盖多个节区；不能把 `.text` 名称当成运行时页权限的完整证据。`readelf` 分别提供文件头、程序头、节区头和动态段检查。[^v2-binutils-readelf]

```bash
# 仅针对本包 hello.c 编译的自有 hello，不执行未知样本。
readelf -h ./hello
readelf -l ./hello
readelf -S ./hello
readelf -d ./hello
objdump -d --disassemble=main ./hello
```

对一个落在文件实际内容覆盖范围内的装载段，若其文件偏移起点为 $o$、虚拟地址起点为 $v$，段内某地址 $x$ 的对应文件偏移可写成 $o+(x-v)$。先验证 $x$ 确实位于该段的文件内容部分，再使用等式。内存中的零初始化区域可能没有相应的文件字节，不能把内存大小与文件大小混为一谈。对于位置无关程序，运行时还要结合加载基址；不要用一次运行的绝对地址给另一轮下结论。

## 在一个装载段里完成地址换算，再故意越界一次

沿用前文文件偏移与虚拟地址的区别，给一个原创合成 PT_LOAD 段：`p_offset=0x1000`、`p_vaddr=0x4000`、`p_filesz=0x600`、`p_memsz=0x900`。这些不是本包 hello 的实测数值。文件覆盖的段内虚拟区间是 `[0x4000,0x4600)`，内存区间是 `[0x4000,0x4900)`。[^v3-readelf]

虚拟地址 `0x4210` 距起点 `0x210`，对应文件偏移为 `0x1000+0x210=0x1210`。它落在文件覆盖范围内，所以前文公式适用。若改成 `0x4700`，它仍在内存段里，却超出文件内容；机械计算出 `0x1700` 并从那里读取文件是错误操作，因为该位置并不是这个地址的文件来源。

对 PIE/共享对象还要从运行映射确定 load bias，并把运行时地址转换回同一坐标系后再算。对齐、多个段和同一页中的权限不能凭一个基址猜测。先确定地址属于哪个映射、哪种坐标，再进行减法，不把不同运行的 ASLR 地址直接做差得到代码修改结论。

### 给反编译变量名降一级证据权重

反编译器的变量名、类型和函数边界通常是恢复出的解释。它们便于阅读，但不能让一个名叫 `is_admin` 的局部变量自动成为真实授权检查。沿数据来源和分支结果核对：输入从哪来、比较哪个值、错误路径是否退出、敏感操作是否确被这条分支支配。

对本包有源码的 hello，先用三条已知输入输出合同定位分支，再观察 `readelf`、反汇编和反编译的映射。优化构建缺少变量名属于调试信息与优化边界，不应自动解释为恶意混淆。对未知样本，静态导入与解析也需隔离和资源限制，不因“没有执行”就忽略解析器风险。

这节的数值例子是推演，不冒充 Ghidra 图形界面实测。后续 [[计算机知识/Kali/06-取证逆向与检测/06-GDBGefStrace与动态观察|动态观察]] 应验证可观察行为，而不是为了迎合反编译图去修改输入标签。

## Ghidra 与 Radare2 两条路线

Ghidra 中建立独立项目，导入自己的 `hello`，确认识别的语言/架构，再运行适用的分析器。从 `main` 观察输入数量判断、分支和输出调用，给函数添加你自己的解释注释。不要把自动命名的 `local_...` 当成原始变量名。引用字符串可帮助找到使用点，但交叉引用也可能因间接调用而不完整。[^s1]

Radare2 的最小只读分析流程：

```bash
r2 "$HOME/kali-lab/output/hello"
```

进入交互界面后分别执行 `aa` 分析、`afl` 列函数、`pdf @ main` 查看对应函数反汇编，最后 `q` 退出。不要使用写模式或启动调试模式来“顺便看看”；它们会改变风险。部分构建里函数符号名称不同，可从 `afl` 实际输出选择，不预设所有程序都有可见 `main`。[^s2]

## 补强：从三个已知输入建立反编译的校验点

本包 `hello.c` 给出一个可查源码的基线：无额外参数使用 `learner`；一个额外参数使用该字符串；两个额外参数走错误分支并返回 2。先写出这三个路径，再在反汇编或反编译中寻找条件判断、字符串引用、输出调用和返回值。这样是在用独立的输入输出合同检查解释，而不是把反编译器生成的伪代码当成原始源码。

编译优化可能合并分支、内联调用或改变变量的可见性。`-g` 提供调试信息，不保证所有源码变量始终有可读位置；`-O0` 便于入门，也不能代表生产构建。只有在语言行为已定义的前提下，才能拿不同优化构建作行为比较。下一步连接 [[计算机知识/Kali/06-取证逆向与检测/06-GDBGefStrace与动态观察|动态观察]]：用同一组输入检查路径，不应仅因为静态图“看起来合理”就跳过验证。

## 保护机制不是二元安全标志

NX/不可执行数据页、PIE、ASLR、栈保护和 RELRO 控制不同环节。Checksec 等汇总工具能提供构建与运行条件的线索，但“全绿”不代表没有内存错误，“某项缺失”也不等于已存在可利用漏洞。要解释实际代码路径、输入约束、平台行为和权限边界。

> [!question] 自检
> 把同一源文件从 `-O0` 改成优化构建后，反编译结构不同，说明功能被篡改了吗？不一定。先用相同输入比较可观察输出，再检查优化是否保持定义良好的程序语义。动态验证在 [[计算机知识/Kali/06-取证逆向与检测/06-GDBGefStrace与动态观察|GDB 与系统调用观察]]。

## 来源与核验范围

[^v5-pcode]: [Ghidra：P-Code Reference](https://ghidra.re/ghidra_docs/languages/html/pcoderef.html)；定位：A Brief Introduction to P-Code。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-pcode-extra]: [Ghidra：Additional P-CODE Operations](https://ghidra.re/ghidra_docs/languages/html/additionalpcode.html)；定位：MULTIEQUAL、INDIRECT、CAST。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-pcode-ops]: [Ghidra：P-Code Operation Reference](https://ghidra.re/ghidra_docs/languages/html/pcodedescription.html)；定位：INT_LESS 与 INT_SLESS；LOAD/STORE。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Kali 官方：Ghidra](https://www.kali.org/tools/ghidra/)；定位：工具定位、分析能力与环境要求。网页读取：2026-09-05。
[^s2]: [Radare2 官方书：First Steps](https://book.rada.re/first_steps/intro.html)；定位：分析、函数、反汇编与只读模式。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-binutils-readelf]: [GNU Binutils readelf 手册](https://sourceware.org/binutils/docs/binutils/readelf.html)；定位：--file-header；--program-headers；--section-headers；--dynamic。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-readelf]: [GNU Binutils：readelf](https://sourceware.org/binutils/docs/binutils/readelf.html)；定位：ELF file/program headers；segments；section mapping。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]