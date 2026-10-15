---
type: linter-sandbox
status: intentionally-messy
tags: [playground/plugin, playground/linter]
---

# Linter 手动实验：这页故意排版混乱

> [!danger] 只处理当前文件
> 这页故意留下多余空行、混用列表符号、错误编号和不一致的强调空格。请只运行命令面板中的 **Linter: Lint the current file**。不要运行 “Lint all files” 或 “Lint all files in folder”。

> [!note] 如果运行后没有变化
> 当前 vault 可能还没有启用任何 Linter 规则。这是安全的：先在插件设置里阅读规则说明，只挑一两条你理解的规则，再回到本页手动运行。不要为了看到变化而开启全库或保存时自动整理。

---

##下面开始是故意混乱的内容



这一段后面有很多空行。




#### 标题层级从二级突然跳到四级
这个标题下面故意没有空行。

## 列表符号混用

- 第一项使用短横线
* 第二项使用星号
+ 第三项使用加号

1. 第一步
1. 第二步仍然写成 1
7. 第三步突然从 7 开始

## 强调和空格

** 这段粗体两侧故意多了空格 **

一句话    中间故意留下很多空格。

## 你的观察

- [ ] 运行前先截屏或查看 Git diff
- [ ] 只执行 “Lint the current file”
- [ ] 记录哪些改动符合预期
- [ ] 如果结果不喜欢，立刻撤销

