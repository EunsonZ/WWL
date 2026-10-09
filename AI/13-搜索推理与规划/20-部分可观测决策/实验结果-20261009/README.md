# 部分可观测决策：2026-10-09 实际执行

本次执行已固定作者 `pomdp_lab.py` 版本SHA256 `39e0859b97db068df94370c8be33753da0eacb91eff744393946716322db9c29`，测试版本及来源见[source_snapshot.json](source_snapshot.json)。Python3.14.7/macOS27.0.1 arm64，标准库Fraction，无安装、随机采样或训练。作者代码和执行槽B的独立枚举各使用单进程，所有命令退出码0且不到1秒。

在课程实验目录先运行 `python3 -B -m unittest -v test_pomdp_lab.py`，10项测试通过，见[原始日志](unittest.log)；覆盖零概率观测、非单位转移联合表、输入拒绝、时域边界、信息价值和同均值反例。随后运行的完整命令与固定参数在[commands.json](commands.json)，主例为：

```bash
python3 -B pomdp_lab.py --horizon 3 --cost 1 --output h3c1.json
```

先验1/10，危险损失100，预防损失20，灵敏度4/5，误报率1/10，隐藏Y在任务中固定、给定Y的测量条件独立。实际结果：

| 条件 | 最小风险 | 最优根动作 | 原始输出 |
|---|---:|---|---|
| h3,c1 | 623/100=6.23 | 测量 | [h3c1.json](h3c1.json) |
| h2,c3 | 42/5=8.4 | 测量 | [h2c3.json](h2c3.json) |
| h2,c6 | 10 | 不预防 | [h2c6.json](h2c6.json) |
| h2,c0,K60 | 10 | 不预防与测量并列 | [h2c0K60.json](h2c0K60.json) |
| h2,免费完美信号 | 2 | 测量 | [perfect.json](perfect.json) |
| h3,c1,灵敏度=误报率=1/3 | 10 | 不预防 | [uninformative.json](uninformative.json) |

h3主例枚举38棵策略树，最优策略是先测量，阳性后再测量（再阳性预防、阴性不预防），初次阴性则不预防。单免费信号给出的风险R0=10、RS=27/5、EVSI=23/5、EVPI=8；后验8/17和2/83。K60时该信号EVSI=0，但完全信息EVPI=4。原题三状态δ0和±1等概率都均值0，风险动作收益X²−1/2的期望分别为−1/2与1/2，最优动作分别为安全与风险；程序实际输出与独立计算吻合。

执行槽B的[独立oracle](independent_tree_oracle.py) 不导入作者代码，也不使用belief更新或动态规划。它展开每棵树的所有终止路径，将真状态先验乘每次信号似然，再累计路径测量费用与终止损失；上述六组完整策略集合的风险、全部最优树、数量及同均值原题结果均通过，[日志](independent_verification.log)、[独立期望](independent_tree_expected.json)保留。到本结果目录运行 `python3 -B independent_tree_oracle.py` 可复核已有输出。

完整环境见[environment.json](environment.json)。这是声明有限模型的精确运行，尚无真实传感器、未知模型学习、多状态机器人运行、客户端显示或学习效果证据。运行核验与另行独立语义审阅各自成立，不互相替代。
