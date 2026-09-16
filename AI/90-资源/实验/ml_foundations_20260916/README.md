# 机器学习基础集中复算包

本目录只复算 `AI/10-机器学习与深度学习基础` 深化候选中的微型合成例。它不下载数据、不训练真实模型、不声称验证现实分布。NumPy 是现场已有依赖；没有 NumPy 时测试应记为 `not_run`，不得自动安装。

```bash
python3 -B -m unittest test_mechanisms.py -v
```

| 函数 | 对应课程 | 检查什么 | 不证明什么 |
| --- | --- | --- | --- |
| `ridge_solution`、`logistic_gradient` | 07、14 | reduction、L2 收缩、二分类梯度 | 真实数据线性、概率已校准 |
| `finite_class_gap` | 12 | 有限假设类 Hoeffding + union bound 的数值代入 | 界紧、现代深网已解释 |
| `kmeans_step`、`gmm_responsibilities` | 16、20 | 硬分配、软责任和归一化 | 簇具有真实语义 |
| `value_iteration`、`td_targets` | 19 | Bellman backup、TD/SARSA/Q-learning target | 函数逼近或离线 RL 稳定 |
| `beta_bernoulli_update` | 20 | 共轭后验与后验预测 | 先验正确或部署校准 |
| `grouped_and_pooled_rates` | 21 | 分层率与总体率可反向 | 已识别现实因果效应 |
| `autoregressive_joint`、`affine_flow_log_density` | 22 | 联合分布归一化、变量变换项 | 生成质量或训练收敛 |

所有输入均在测试中显式给出。浮点断言使用容差；概率函数同时检查非负和归一化。源码是唯一实现真源，正文只链接本目录，不复制另一份实现。
