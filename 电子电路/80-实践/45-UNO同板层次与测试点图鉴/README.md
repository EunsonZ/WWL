---
stage: 2
aliases: []
sources: ["https://docs.arduino.cc/hardware/uno-rev3"]
prerequisites: ["[[电子电路/50-PCB布局与调试/07-同板照片布局原理图与仪器定位#一个节点穿过原理图、焊盘与空间]]"]
---
# UNO同板层次与测试点图鉴

原始照片、EAGLE源、许可证保留；models.py按实际选定网抽取，generate.py绘五个可编辑图与360/425PNG。源码单一真源，无code-sync镜像。图不是制造包或真实仪器日志，UNO不可冒充RCDAQ-P1实板。

```bash
python -B -m unittest discover -s . -v
python -B generate.py --output /private/tmp/v37-new-run
```

必填output、全新库外目录；导入不读盘、写盘、解析argv或加载CairoSVG。显式generate才读取有限源并延迟绘图依赖。models.coordinate限定有限±1000mm与未镜像正交R旋转，溢出/非有限/其他类型抛ValueError；本板选定pad不需镜像，输出屏幕/照片镜像由图和正文另论。models.load返回实际8端子、导线、过孔、板边及原网名；它验证7项同版SCH与BRD身份，不验证实体铜连续或正确设计。

生成输出五SVG、十PNG、布局JSON和两原照片共18文件；移动整棵输出仍可渲染相对图片路径。再生成assets与照片逐byte比对。布局只显示AD0/+5V/GND导线，面区不填，curve弦近似有标记。tests对旋转闭环、真实pad中心、SCH/BRD网身份、AD0端点及有限拒绝做有意义CPU核，不假称EAGLE工具/硬件/实测/客户端/真人通过。图和原材料CC BY-SA4，来源页记录说明与商标边界。

CairoSVG对本组自建SVG设置unsafe=True，以允许受控的本地相对图片读取；不接受外来SVG、网络href或任意URL输入。原图像由固定清单与哈希绑定，生成读取只发生在显式调用时。
