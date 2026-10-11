# 同一曲线族图示的生成与复算

对应主解释：[[数学/25-高等代数/60-交换代数与代数几何/05-局部环切空间与曲线奇点#同一曲线族：先预测，再区分所见对象|同一曲线族：先预测，再区分所见对象]]。

规范源码为本目录 `generate.py`；自查入口 `check.py` 用原方程残差、另一个有理参数公式及 SVG XML 解析核对产物，不是独立数学审阅。没有正文代码镜像；源码更改后须重新生成三幅 SVG 并重新运行复算。

需 Python 3.10+ 与 matplotlib；使用已有依赖，不自动安装。下列 NEW_OUTPUT_DIR 必须不存在，避免覆盖旧输入；路径按实际库根替换。

```sh
MPLCONFIGDIR=/private/tmp/wwl-curve-mpl python -B 数学/90-资源/图示/issue228/generate.py NEW_OUTPUT_DIR
python -B 数学/90-资源/图示/issue228/check.py NEW_OUTPUT_DIR
```

输出三幅 SVG、对应 PNG 和 `samples.json`。SVG 是正式正文附件，PNG 用于预览，samples用于数值残差检查；PNG 和 samples 不必加入正文。图卡尺寸4.7×7.2英寸，坐标同窗口 [-0.5,0.5]²、等比例，x/y/a 无量纲，线型与域解释见主解释。SVG 字体转换为路径，不依赖接收端字体；窄列下仍需真实 Obsidian 的显示检查，静态 XML 有效不能代替该检查。
