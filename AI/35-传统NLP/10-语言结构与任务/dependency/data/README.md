# 固定UD Swedish-Talbanken数据归属与再生

本目录的UPSTREAM-README.md、LICENSE.txt是UniversalDependencies/UD_Swedish-Talbanken `r2.16`、commit `3fd9c4123f155560ebb68c324b346fa9fa33991c` 的原字节，source-record.json保存官方固定URL/原字节SHA/实际取回时间。来源：[固定上游树](https://github.com/UniversalDependencies/UD_Swedish-Talbanken/tree/3fd9c4123f155560ebb68c324b346fa9fa33991c)。不以网页最新分支代替固定输入。

原treebank基于1970年代Lund大学Talbanken Professional Prose，原创建者Einarsson/Teleman等，UD转换与校核Joakim Nivre、Aaron Smith、Victor Norrman等，详见两原文件。上游将整个treebank按 **CC BY-SA4.0** 发布，包括文本；保留[许可全文](LICENSE.txt)及[官方许可链接](https://creativecommons.org/licenses/by-sa/4.0/)。无上游背书或对标注绝对正确性的保证。

`dependency/inputs/` 的六个features/targets文件是原语料的**有修改派生投影**：保留官方split，选sha256(doc ID)mod4=0和2–12整数词句，只保留原整数ID/FORM/UPOS/HEAD/DEPREL，拆成特征与目标；未改词、HEAD、关系子型，未将参照投射化。去掉multiword range/empty节点和DEPS等其他列，不评价增强依存。投影规则及所有选中样本的doc/sent身份、源行与FORM hash可复算；无个人标注补写。

上述数据投影，以及`dependency/assets/`内由其派生的逐句预测/验证预测、计数模型、指标、oracle/诊断和两图，保留此来源与**CC BY-SA4.0**归属，修改内容为本课程的选择、拆列、统计/模型预测和可视化。代码和其他课程文字的原有许可不因这项数据声明整体改变。不得把数据或预测说成真人语义新判断或商业部署认证。

完整三个原CoNLL-U共约8.6MB留作者库外证据，不随正文重复发布。可用`../code-sync/fetch_talbanken.py --output <库外目录>`串行从固定官方URL取回（逐文件校验预定SHA），再用`prepare_talbanken.py --raw-dir <同目录> --output <输入目录>`逐字再生所选输入。下载与CPU训练/评测分别计时，无模型下载或第三方包安装。
