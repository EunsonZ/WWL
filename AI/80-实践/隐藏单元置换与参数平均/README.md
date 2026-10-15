# 隐藏单元置换与参数平均：2026-10-09 实际执行

主解释见[[AI/10-机器学习与深度学习基础/09-神经网络层激活函数与表示学习|神经网络的表示与坐标变换]]，计算源码位于 `AI/10-机器学习与深度学习基础/09_隐藏单元置换与参数平均.py`。固定输入为−2、0、1；W1=(1,−1)、W2=(1,−1)ᵀ，交换矩阵为两隐藏单元互换。没有训练、随机输入或依赖安装。

执行槽B以源码SHA256 `0fe5ad8b4d7c519fa9e8afea420441f0e547edc9661ffb46d084e34b4044b3ce` 的固定副本运行，环境Python3.14.7/macOS27.0.1 arm64。在库根目录执行：

```bash
python3 -B 'AI/10-机器学习与深度学习基础/09_隐藏单元置换与参数平均.py' > output.json
```

命令退出码0、用时不到1秒。[本次原始输出](output.json) 中，同步置换两层后仍输出x；直接参数平均输出0；先对齐再平均输出x；只置换第一层输出−x。ReLU后重编码恢复原函数，负号移到ReLU前时在−2与1处改变函数。

另用[独立标量oracle](independent_oracle.py) 从 `relu(x)-relu(-x)=x` 推出全部字段，未导入计算实现，也未将作者的预期JSON当作答案。在本目录运行：

```bash
python3 -B independent_oracle.py
```

[逐项结果全部通过](independent_verification.log)，独立期望保存在[independent_expected.json](independent_expected.json)，环境和来源版本分别见[environment.json](environment.json)、[source_snapshot.json](source_snapshot.json)。本次实际执行核验该构造例，语义论证由另一代理独立核查；不证明训练模型对齐后平均的普遍有效性，也不宣称部署性能、客户端显示或读者理解已验证。
