# 进阶算法证书与 Oracle

这组小实验回答一个具体问题：**手算能帮助理解，但怎样确认实现与正文里的结构性结论一致？** 这里把快算法和只适合极小输入的穷举 oracle 放在同一规格下比较。oracle 慢得有意：它从定义枚举真值，避免和待测实现共享同一种递推或 DFS 判定。

## 运行

在本目录执行：

```bash
python3 -B -m unittest -v
```

只使用 Python 标准库。`-B` 避免产生 `__pycache__`。这些实现用于复算性质与反例，不是生产性能基准。

## 五个可复算切片

| 切片 | 快算法给什么 | 独立 oracle / 性质 | 对应解释 |
| --- | --- | --- | --- |
| 桥与割点 | 带边编号的 low-link DFS | 逐边/逐点删除，再数连通分量 | [[计算机知识/50-数据结构与算法/20-算法设计系统课程/12-桥割点双连通分量与块割树\|桥、割点与块割树]] |
| 二分图匹配 | Hopcroft–Karp 与交替可达集 | 枚举所有边子集；验证 <code>&#124;matching&#124;=&#124;min cover&#124;</code> | [[计算机知识/50-数据结构与算法/20-算法设计系统课程/14-二分图匹配Hall-Konig与Hopcroft-Karp\|匹配与 Kőnig 证书]] |
| 树上独立集 | 以父子分隔为状态的 DP | 枚举所有顶点子集 | [[计算机知识/50-数据结构与算法/20-算法设计系统课程/15-树形区间与状态压缩DP的分隔结构\|DP 的分隔结构]] |
| 参数化顶点覆盖 | 按未覆盖边两端分支，预算为 `k` | 枚举至多 `k` 个顶点 | [[计算机知识/50-数据结构与算法/20-算法设计系统课程/18-参数化复杂性FPT核化与搜索树\|FPT 搜索树]] |
| 在线分页 | LRU 只看过去；离线 DP 看完整序列 | 枚举每次缺页时的驱逐选择 | [[计算机知识/50-数据结构与算法/20-算法设计系统课程/20-分页缓存竞争分析与随机在线算法\|分页与竞争分析]] |

## 特意保留的边界

- 桥算法按**边编号**跳过父边。两点之间有两条平行边时，两条都不是桥；若只按父顶点跳过，会误判。
- 匹配输入会去重；顶点编号必须落在左右两侧的范围内。最小点覆盖由最大匹配后的交替可达集构造，测试会重新检查它确实覆盖每条边。
- 树 DP 会拒绝环、断开图和边数不为 `n-1` 的输入，因为递推依赖唯一父边。
- 顶点覆盖搜索每层至少消耗一个预算；返回 `None` 只表示“不存在大小至多 k 的覆盖”，不证明一般图上没有更大的覆盖。
- 分页容量为 0 时每次请求都缺页。离线最优值只能作基准，不能冒充在线算法。

## 怎样读测试失败

失败输出会带上完整的小图或请求序列。先手算 oracle 的定义，再检查快算法的不变量。随机样例使用固定种子只为了复现；正确性证据来自每个样例都与穷举真值相等，而不是“跑了很多次所以大概正确”。

## 来源

- [Jeff Erickson：Depth-First Search](https://jeffe.cs.illinois.edu/teaching/algorithms/book/06-dfs.pdf)、[Maximum Flows and Minimum Cuts](https://jeffe.cs.illinois.edu/teaching/algorithms/book/10-maxflow.pdf)：本批下载原章并渲染核对章首页。
- [MIT 6.046J Lecture 14A：Matching](https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2015/resources/lecture-14a-notes/) 与 [Lecture 18：Fixed-Parameter Algorithms](https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2015/resources/lecture-18-notes/)：本批实际打开课程资源页。
- Hopcroft and Karp, *An n^5/2 Algorithm for Maximum Matchings in Bipartite Graphs*, DOI `10.1137/0202019`；本批打开 DOI 重定向，出版商页面拒绝自动读取，因此此处只作精确书目信息。

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践 MOC]]。
