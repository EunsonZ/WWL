---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 入门
estimated_minutes: 12
topics:
  - Python
  - 实验
  - 可重复环境
tags:
  - computer-science/python
  - computer-science/lab
---

# Python 实验室

这里是 Python 课程的可修改区域。课程正文保持稳定；你可以在本目录建立临时脚本和 `.venv`，完成后按每页的重置步骤清理。

> [!warning] 实验边界
> - 只使用合成数据，不放入密码、token、真实账号或个人文件；
> - 不使用 `sudo pip`，不覆盖系统 Python；
> - 虚拟环境可以删除重建，不提交 `.venv/`；
> - 安装第三方包会访问网络和软件源，先确认环境、索引与项目要求；
> - 所有删除命令必须在当前实验目录核对后逐项执行。

## 推荐顺序

1. [[计算机知识/80-实践/01-Python/01-语法与文件练习|语法与文件练习]]：只使用标准库，完成一个小型数据汇总脚本；
2. [[计算机知识/80-实践/01-Python/02-环境与依赖实验|环境与依赖实验]]：观察解释器、虚拟环境与 site-packages；
3. [[计算机知识/80-实践/01-Python/03-练习答案与解释|练习答案与解释]]：完成后再对照。

## 每次实验的固定记录

```text
目标：
Python 解释器：
工作目录：
运行命令：
预期输出：
实际输出：
错误与完整 traceback：
我改变了什么：
如何恢复：
```

## 开始前检查

在终端进入你准备使用的实验目录，然后运行：

```bash
pwd
python --version
python -c "import os, sys; print(sys.executable); print(os.getcwd())"
```

Windows PowerShell 中用 `Get-Location` 代替 `pwd` 也可以。只有当输出路径和解释器符合预期时才继续。

## 完成标准

- [ ] 我能说明脚本、解释器、工作目录和虚拟环境分别在哪里；
- [ ] 我保留了预期输出和实际输出；
- [ ] 失败时保存了完整 traceback；
- [ ] 我能从空目录重做实验；
- [ ] 实验没有污染系统 Python、真实数据或其他知识域。

---

**返回**：[[计算机知识/10-编程语言/01-Python/00-Python基础-MOC|Python 基础]] · **第一项实验**：[[计算机知识/80-实践/01-Python/01-语法与文件练习|语法与文件练习]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/04-Python-课程地图|Python · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/01-Python/15-对象协议描述符闭包与类型边界|Python 深化：名字、对象、协议与类型边界]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
