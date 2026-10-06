---
stage: 0
aliases: []
sources: ["https://commons.wikimedia.org"]
prerequisites: ["[[电子电路/00-开始/03-元件实物符号与引脚对照#从端子到节点的完整小例]]"]
---
# 元件实物符号引脚图鉴

七类实物照片、原创可编辑符号和有限型号表的一处真源。读主课再用SOURCES核图权利、用catalog.json核来源字节。未知MPN、公差/额定和不清的照片pin1保持未知；不把参考厂商认证到照片上。

```bash
python -B -m unittest discover -s . -v
python -B generate.py --output /private/tmp/v01-new-run
```

必填--output，目录必须全新且在主库与发布树之外。函数catalog()只在调用时读七照片并核SHA；generate()显式输出才延迟导入CairoSVG。导入不读盘、不解析argv、不写文件；不用随机数或Matplotlib。输出sourceassets保留照片，assets保存七SVG、360/425PNG和哈希记录，共29再生成文件。SVG图片使用../sourceassets相对路径，移动输出整个目录仍能渲染。源码无code-sync镜像，没有双真源。

测试核七族唯一、源哈希、参考型号端口与二极管K横线及目录拒绝；不把自测当独签、真实性/器件测试或学习表现证明。颜色并非身份，文字/端口名字仍在灰度可读；原照片许可见SOURCES，原符号注释按同图许可交付。

CairoSVG对本组自建SVG设置unsafe=True，以允许受控的本地相对图片读取；不接受外来SVG、网络href或任意URL输入。原图像由固定清单与哈希绑定，生成读取只发生在显式调用时。
