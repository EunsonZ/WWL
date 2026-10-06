---
type: reference
aliases: []
sources:
  - https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage
---

# WWL 的 GitHub 同步

用户于2026-10-06授权创建私有仓库 `EunsonZ/WWL`，同步正文、代码、图件、书籍及个人学习记录，并选择**每次 Git 提交后自动推送**。编辑、保存文件不会自动暂存或提交。CFA 也属于本次备份范围；先前的 CFA 排除约定针对课程修订。

仓库地址：<https://github.com/EunsonZ/WWL>。

## 日常操作

按本次实际修改范围显式暂存文件，再运行 `git commit`。本机的 `.githooks/post-commit` 会把当前已提交分支推送到 `origin` 的同名分支，并核对远端提交号。它不暂存其他文件，不自动合并，不强制推送。推送失败时保留本地提交并显示重试命令：

```bash
python3 scripts/github_sync.py
```

断网、token失效、GitHub有独立的新提交或LFS配额不足时，失败仍是失败。修复相应条件后重试；不会以覆盖远端解决冲突。最近一次结果在本机 `.git/wwl-github-sync.json`，不上传。

PDF 使用 Git LFS。新机器克隆前需具备 Git LFS；克隆后执行 `git lfs pull` 获得附件。普通 GitHub 页面中的LFS指针与实际PDF内容分别存储。首次上传前保全原始历史，再只将本地 `main` 历史中的PDF转换为LFS；原始提交保留在本地恢复引用，旧分支保留。新仓库首次推送不需要强制推送。

## 凭据和本地状态

凭据通过本机 `git config --local wwl.githubTokenFile` 指定的库外文件读取。token不写入仓库、远程URL、提交或终端日志；读取响应仅交给Git的credential通道。`.githooks/pre-push`核对实际发出的提交，检查新Git对象（含提交及标签消息）中的可识别GitHub token、私钥、每个未推提交的全部树路径、普通Git大文件和新LFS内容哈希，再调用Git LFS上传。

这些检查是有限防护，不证明任意文档没有其他敏感信息。`.obsidian`运行配置与插件状态（已跟踪的`types.json`除外）、虚拟环境、缓存、`.env`和密钥文件保留在本地。个人学习笔记、TaskNotes和个人规划经本次授权纳入私有备份；Tags中的`.space/context.mdb`是插件运行数据库，保留在本地。C1历史证据中的`originals/.obsidian/app.json.txt`只有两字节`{}`，按精确路径与Git对象号保留；该文件内容一旦变化，推送检查要求重新审阅。

## 本机配置与迁移

本次配置只作用于此库：`core.hooksPath=.githooks`、`core.askPass`、`wwl.githubRepository`、`wwl.githubTokenFile`、`wwl.githubAutoPush=true`、`credential.helper`空值和Git LFS过滤器。迁移到其他电脑后，需在该电脑设置token文件、Git LFS及hook路径；Git克隆不会自动启用本机hooks。

临时停止提交后自动推送：

```bash
git config --local wwl.githubAutoPush false
```

恢复：

```bash
git config --local wwl.githubAutoPush true
```

此开关只控制提交后推送，手动推送仍执行pre-push检查。同步采用Git版本与远端提交号验收，不代替知识正确性、客户端或学习效果验收。
