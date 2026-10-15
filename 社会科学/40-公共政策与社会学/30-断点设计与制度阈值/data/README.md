# Lee（2008）固定数据获取与转换

原归档没有给出明确再分发许可，所以知识库不包含ZIP、DTA或逐行派生CSV。读者从MIT官方地址取得固定字节：

```bash
curl -fL 'https://economics.mit.edu/sites/default/files/inline-files/Lee2008%20%281%29.zip' -o Lee2008.zip
shasum -a 256 Lee2008.zip
```

预期ZIP SHA-256：

`ce7a164d659aa5e0706266c852526b7727b126566f4d38e7bbddf49d4720d9bf`

解压后使用 `Lee2008/table_two_final.dta`；其SHA-256应为：

`4114a0c1120e6a5cf1e7a2e1f790f04c8d1678bc4e41bd2a901a088affae9db6`

上游同时包含 `readme.txt` 与 `public_use.do`。前者给变量定义，后者是论文图表的Stata复现程序。不要用来源不明的两列镜像替代，因为那会丢失样本标记、精确零点、聚类标识和协变量。

本组的 `code/prepare_data.R` 用R的 `foreign` 包读取旧版Stata文件，只保留 `use==1` 与列明字段。它不会安装依赖：

```bash
Rscript code/prepare_data.R Lee2008/table_two_final.dta local-data/lee_table2_use.csv
python3 code/rd_case.py --data local-data/lee_table2_use.csv --source-proof local-data/lee_table2_use.csv.provenance --out generated --assets assets
LEE2008_DATA=local-data/lee_table2_use.csv LEE2008_PROOF=local-data/lee_table2_use.csv.provenance python3 -B -m unittest discover -s tests -v
```

转换器会把已验证的DTA哈希、生成CSV的实际SHA-256和6559行计数写入 `.provenance`；Python会重算CSV哈希并拒绝不匹配字节。转换后应有6559行；唯一 `difdemshare==0` 行的 `right` 缺失。分析脚本排除该行并报告6558行。若没有R/foreign，可用Stata按 `public_use.do` 读取DTA，再导出同名十列；不要自动安装依赖或忽略哈希失败。
