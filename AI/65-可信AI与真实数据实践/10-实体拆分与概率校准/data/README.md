---
type: reference
domain: artificial-intelligence
content_status: usable
evidence_status: partial
evidence_scope: "官方URL与2026-09-20下载字节已核；官方页面和内嵌README许可文字冲突未决"
aliases: []
sources:
  - "https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones"
  - "https://creativecommons.org/licenses/by/4.0/"
prerequisites: []
---

# UCI HAR 数据获取合同

课程不再分发 58.2 MB 数据归档。显式下载到你选择的库外路径：

```bash
curl -fL 'https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip' \
  -o '/absolute/path/human_activity_recognition_using_smartphones.zip'
shasum -a 256 '/absolute/path/human_activity_recognition_using_smartphones.zip'
```

2026-09-20 固定值：

```text
outer ZIP file bytes: 61005872
outer SHA-256: c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031
inner UCI HAR Dataset.zip SHA-256: 2045e435c955214b38145fb5fa00776c72814f01b203fec405152dac7d5bfeb0
```

注意：`unzip -l` 外层归档末行的 `61005618` 是两个成员各自**解压后**长度之和；本合同的 `61005872` 才是外层 ZIP 文件本身的字节数。

脚本直接读取这个嵌套 ZIP，不要求解压，也不联网；哈希不符会先失败。数据 DOI 为 `10.24432/C54S4K`，应引用 UCI 数据记录及 Anguita 等 2013 原论文。

## 许可状态不能被静默合并

当前 [UCI 数据页](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones) 标注 CC BY 4.0；外层归档内的 `UCI HAR Dataset.names` 和内层 Version 1.0 `README.txt` 却写有引用要求、AS-IS 免责声明和 “Any commercial use is prohibited”。原论文标题又称数据为 public domain。

本组只记录冲突，不给法律结论，也不把数据复制进候选。若要商业使用或再分发，请先向 UCI、作者或所属机构确认哪个条款适用于这组具体字节。
