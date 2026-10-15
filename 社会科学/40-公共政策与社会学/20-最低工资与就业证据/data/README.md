# 原数据取得与固定版本

本目录不再分发原始餐馆记录。David Card 的伯克利作者页公开了数据包和说明，但页面与压缩包没有给出明确的再分发许可。请从作者官网取得个人复算副本：

```bash
python3 code/minimum_wage_case.py --fetch local-data --out generated
```

脚本只接受以下固定版本：

- URL：`https://eml.berkeley.edu/~card/data_sets/njmin.zip`
- `njmin.zip`：23,017 bytes；SHA-256 `41a29aec6b489658b20030d044a2b20a5f5a04b871cde41df057afd6013ba587`
- 包内 `public.dat`：82,410 bytes、410 行；SHA-256 `04bde0cad5540980f32ce099c6dad369e2f05494698071d8a65b3e1cbe9ca53a`
- 作者 readme：`https://eml.berkeley.edu/~card/readme/njmin-readme.txt`

若官网文件变化或无法访问，脚本会报错而不会用别的数据冒充。`reference_results.json` 是上述固定原数据产生的聚合结果，不含餐馆级记录。要做完整集成测试：

```bash
NJMIN_DATA=local-data/public.dat python3 -B -m unittest discover -s tests -v
```

不设置 `NJMIN_DATA` 时，餐馆级复现测试明确显示为 `skipped`；其余公式、固定汇总与 SVG 合同仍会运行。
