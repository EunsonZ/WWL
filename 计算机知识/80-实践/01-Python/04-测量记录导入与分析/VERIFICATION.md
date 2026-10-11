# 本机运行记录与证据边界

本页保留同步首段当时的环境和验证范围。后续科学/性能/取消实验另见 [NEXT_VERIFICATION.md](NEXT_VERIFICATION.md)。

2026-10-11，在 macOS 27.0.1 arm64 上实际运行。解释器为已有的 **CPython 3.12.11**（Clang 20.1.4），SQLite **3.49.1**；主线声明 Python 3.11+，本机没有实际跑 Python 3.11。运行时无第三方依赖。隔离 wheel 构建后端由 pip 取得，wheel 的 WHEEL 元数据记录 **setuptools 84.0.0**；绘图生成只用标准库，视觉检查使用主库已有 CairoSVG 将 SVG 转 PNG。

候选项目实际路径为 `/private/tmp/wwl-python-course-candidate-20261010/计算机知识/80-实践/01-Python/04-测量记录导入与分析`。下列变量为此次实际路径，复制重做时需核对并改成自己的实验目录。

```bash
PROJECT='/private/tmp/wwl-python-course-candidate-20261010/计算机知识/80-实践/01-Python/04-测量记录导入与分析'
LAB='/private/tmp/wwl-python-course-candidate-20261010'
/Users/ysz/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12 -m venv "$LAB/verify-env"
"$LAB/verify-env/bin/python" -m pip wheel --no-deps --wheel-dir "$LAB/wheelhouse" "$PROJECT"
"$LAB/verify-env/bin/python" -m pip install --no-deps "$LAB/wheelhouse/wwl_measurement_import-0.1.0-py3-none-any.whl"
cd "$LAB/verify-run"
"$LAB/verify-env/bin/wwl-measurements" import "$PROJECT/data/measurements.csv" "$LAB/verify-run/console.sqlite"
"$LAB/verify-env/bin/wwl-measurements" import "$PROJECT/data/measurements.csv" "$LAB/verify-run/console.sqlite"
"$LAB/verify-env/bin/wwl-measurements" summary "$LAB/verify-run/console.sqlite"
"$LAB/verify-env/bin/python" -I -B -m unittest discover -s "$PROJECT/tests" -v
"$LAB/verify-env/bin/python" -I -B -c 'import measurement_import; print(measurement_import.__file__)'
"$LAB/verify-env/bin/python" -I -B "$PROJECT/examples/first_record.py"
"$LAB/verify-env/bin/python" -I -B "$PROJECT/examples/recovery.py"
"$LAB/verify-env/bin/python" -I -B "$PROJECT/examples/plot_committed.py" "$LAB/verify-run/plot.sqlite" "$PROJECT/reference/measurements.svg"
```

`verify-run` 是预先建立的库外实验工作目录；绘图用的 `plot.sqlite` 由同一已安装 CLI 首次导入固定 CSV 建立。此页命令是复现接口，原始捕获的命令、退出码、stdout/stderr 位于本次候选根的 `verify-run/commands.json`。原始证据和虚拟环境是本机过程材料，整合课程时不需要复制到读者目录。

此次构建并安装的 wheel 为 `wwl_measurement_import-0.1.0-py3-none-any.whl`，SHA-256：`6665ea22d7bf341ca498a0045ff03d16d8ca3fbbdc0586c163fe6901451c8072`。已安装包位置实际输出为 `verify-env/lib/python3.12/site-packages/measurement_import/__init__.py`；没有用 `PYTHONPATH=src`。

| 实际观察 | 结果与含义 |
| --- | --- |
| 异目录已安装 CLI 首次、重放、summary | 退出码均0；首次新增4，重放新增0/重复4；SQL行集恰a–d。 |
| 固定输入独立 SQL 与有限程序 | n4、sum20、mean5、描述性方差5、N−1方差20/3、RMS²30；单位见正文。 |
| 插入c后故障、关闭重开、恢复 | 故障只留a/b；重开仍为a/b；重跑新增2/重复2，最终a–d。 |
| 同批新x后遇a冲突 | 当前批x回滚，早先a/b保留；错误给非零。 |
| 缺失、NaN、Infinity、布尔、超范围/超长/非规范整数、列数 | 拒绝或按输入框架政策失败；合法0可构造；拒绝不补零。 |
| 干跑不存在原库、已有a/b原库 | 不创建缺库；已有库字节哈希及行集不变；预测新增2并明确是假设行集。 |
| 坏UTF-8、坏表头、未闭CSV引号 | CLI非零；不把输入损坏吞成成功。 |
| 缺输入、缺数据库父目录、已有拒绝文件、同路径别名 | 非零；已有输入/拒绝文件保持；summary缺库不创建库。 |
| stdout故障与关闭责任 | 注入输出OSError后退出1；四行仍提交；文件与连接全部关闭；summary可重建。 |
| import无意外I/O | 在连接和Path.open均禁止的情况下导入成功，空目录无新增文件。 |
| 已安装包测试 | 16项unittest，全部通过；包含8项core与8项CLI测试。 |
| 图源与SVG | 从只读已提交四行生成；源CSV行身份/时间/电压一致，SVG可解析；已转PNG目视检查轴、单位、点标签、均值虚线和注释。 |

测试作者自查支持上述有限行为，独立审阅另外进行。未执行真实 Obsidian 客户端显示、Python 3.11解释器、Linux/Windows运行、性能/RSS实验、并发取消实验、NumPy/pandas数组对照，也没有验证真实仪器、抽样或读者掌握。源码/API采用3.11可用形式，不据此冒称这些未跑环境已通过。完整#245的跨域回链和后续科学/并发阶段仍须单独验收。
