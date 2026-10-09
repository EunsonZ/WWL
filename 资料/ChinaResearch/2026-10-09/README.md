# ChinaResearch 交接包接收位置

**当前状态：原始 ZIP 尚未上传。本目录目前只有接收说明，不能作为原件已经到位的证明。**

研究实施入口：[issue #119](https://github.com/EunsonZ/WWL/issues/119)。讨论与来源档案：[issue #118](https://github.com/EunsonZ/WWL/issues/118)。两条 issue 已有内容级交接，但不替代原始 PDF、TXT 和 ZIP。

## 接收位置

仓库：`EunsonZ/WWL`，保持私有。

分支：`handoff/chinaresearch-2026-10-09`。

待接收文件的完整仓库路径：

```text
资料/ChinaResearch/2026-10-09/WWL_ChinaResearch_Handoff_2026-10-09.zip
```

这是待接收路径，不是已有文件的下载链接。上传时保留原文件名和字节，不重新打包、不改写原 PDF。

## 原件身份与校验

| 项目 | 已在聊天工作环境核验的值 |
| --- | --- |
| 文件名 | `WWL_ChinaResearch_Handoff_2026-10-09.zip` |
| 文件大小 | 1,553,463 字节 |
| SHA-256 | `cc1c0d31c8d806cf9777a84e2af2d11a58cab0e937af32043fa7bfdf5aacc48b` |
| ZIP 内文件数 | 11 |
| ZIP CRC 检查 | 通过，仅证明本地原件 |

包内含原始调查 TXT、72 页原始 PDF、逐页文字提取、清理版正文、PDF 外链表、新反思概览、来源表、复算脚本、示例结果和原始 manifest。原报告资料截止 2026-08-10；2026-10-09 是交接包日期，不能混作统计截止日。

## 如何完成接收

在 GitHub 打开本分支的本目录，使用 **Add file → Upload files**，上传聊天中提供的原始 ZIP，并提交到本分支。不要用同名空文件、Git LFS 指针或一份摘要冒充原件。

已有仓库本地副本并完成正常认证的执行者，也可在独立工作区把原始 ZIP 放到上述路径，校验后按仓库正常 Git 工作流提交。原件仍未到位时，不应运行任何声称可从聊天 sandbox 自动下载的脚本。

## Codex 在原件上传后如何取得

不要求先合并 main。已有 WWL clone 的环境，可以只取这一文件，避免切换分支和覆盖现有工作：

```bash
set -euo pipefail
git fetch origin handoff/chinaresearch-2026-10-09
src='资料/ChinaResearch/2026-10-09/WWL_ChinaResearch_Handoff_2026-10-09.zip'
git cat-file -e "FETCH_HEAD:$src"
workdir="$(mktemp -d)"
git show "FETCH_HEAD:$src" > "$workdir/WWL_ChinaResearch_Handoff_2026-10-09.zip"
(
  cd "$workdir"
  printf '%s  %s\n' \
    'cc1c0d31c8d806cf9777a84e2af2d11a58cab0e937af32043fa7bfdf5aacc48b' \
    'WWL_ChinaResearch_Handoff_2026-10-09.zip' | sha256sum -c -
  python3 -m zipfile -t WWL_ChinaResearch_Handoff_2026-10-09.zip
)
printf 'Verified package location: %s\n' "$workdir"
```

**当前原件未上传，所以 `git cat-file -e` 应失败并停止；不能把这些命令记作已经执行成功。** 上传完成后还需独立核对 GitHub 文件大小与哈希，记录实际 commit，再在 #118/#119 回填可访问链接。

取得原件后先读包内 README，再按 #119 的证据纠偏要求处理。保存原稿历史身份，不以新结论覆盖原文件。材料获取、事实核查、知识正文实施、PR 合并与 Obsidian 同步是不同完成状态。

## 本轮自动传输尝试的实际结果

一次临时 GitHub Actions 下载尝试收到 HTTP 403；随后中转配置写入被平台安全校验拦截，已停止该路径。没有创建成功的原件上传 commit，没有解压成员落库。

临时工作流已从该分支当前版本删除，清理提交为 `d490d90a8211690e9e30e1b2776b8bbbc7b3f7ec`。删除属于正常 Git 历史记录，不宣称历史提交和日志已被擦除。没有改动 main 或现有知识库正文。不要重新启用历史中转工作流。
