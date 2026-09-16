---
课程: "数据库"
层级: "核心"
修订: "2026-09-06"
类型: "机制讲解与推演"
---

# SQL 的逻辑语义：NULL、外连接、聚合和窗口

> **学习位置**：[[计算机知识/00-开始/课程地图/10-数据库-课程地图|数据库课程地图]] · **适用边界**：关系理论；SQL 案例以 PostgreSQL 17 解释，SQLite 实验明确标识。

![SQL 的逻辑语义：NULL、外连接、聚合和窗口：结构示意](../../_assets/diagrams/round3/sql-order.svg)

[PNG 备用图](../../_assets/diagrams/round3/sql-order.png) · [可编辑图源](../../_assets/diagrams/round3/sql-order.dot)

## 查询先问“哪些行”，再问“怎样运行”

概念上可按 FROM/JOIN、WHERE、GROUP BY、HAVING、窗口计算、SELECT、DISTINCT、ORDER BY、LIMIT 等阶段理解查询，但这是语义辅助，不是数据库必须执行的物理顺序。优化器可以交换许多操作，只要维持该方言规定的结果。

SQL 通常保留重复行；没有 ORDER BY 就没有可依赖的输出顺序。分页需要稳定排序，通常加入唯一键打破并列；仅按非唯一时间排序，即使没有明显业务变更，两页也可能缺行或重复。大偏移分页可考虑基于最后键值的游标式方案，同时定义并发更新时的一致性需求。

## NULL 的三值逻辑要用反例记住

`NULL = NULL` 不是 TRUE；`IS NULL` 才用于空值判断。WHERE 只保留条件为 TRUE 的行，FALSE 与 UNKNOWN 都被过滤。若集合含 NULL，`x NOT IN (...)` 可能成为 UNKNOWN，导致意外没有结果。表达反连接时常用相关 NOT EXISTS，并明确 NULL 是否应视为匹配。

COUNT(*) 计行，COUNT(col) 忽略该列 NULL；SUM 在没有输入行时通常返回 NULL，而不是自动返回 0。业务要求 0 时显式 COALESCE，但不要把“未知金额”随意等同于 0。

## 外连接过滤的位置决定是否保留空匹配

```sql
SELECT s.id, COUNT(e.course_id) AS n
FROM student AS s
LEFT JOIN enrollment AS e
  ON e.student_id = s.id AND e.term = '2026A'
GROUP BY s.id;
```

此查询保留没有该学期选课记录的学生，计数为 0。若把 `e.term='2026A'` 移到 WHERE，NULL 扩展行被过滤，没有匹配的学生会消失。COUNT(*) 在 LEFT JOIN 后还会数到那一条扩展行，因此此处用非空匹配列计数。不能机械地把所有过滤条件“下推”而不检查外连接语义。

## 窗口保留行身份，聚合通常压缩行

设同一账户按 id 排列金额为 10、20、20。求逐笔累计：

```sql
SELECT id, amount,
       SUM(amount) OVER (
         PARTITION BY account_id ORDER BY id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_total
FROM payment
ORDER BY account_id, id;
```

若 id 唯一，结果为 10、30、50。窗口 ORDER BY 不保证最终输出顺序，所以外层仍给 ORDER BY。按 amount 排序并使用包含同值 peer 的默认框架时，两行 20 可能都看到累计 50；ROWS 与 RANGE 不是两个等价写法。

ROW_NUMBER 给每行编号；RANK 对并列共享名次并跳号；DENSE_RANK 不跳号。取“部门前两名”应明确是两个人还是两档成绩，分别对应不同策略。窗口结果需要在子查询或适用方言的后续过滤结构中筛选，不能假定能直接放进同层 WHERE。

## 子查询、递归和修改语句

相关子查询按外层变量表达依赖，不代表引擎必然逐行重新运行。CTE 可以改善可读性，其物化与内联策略依方言和版本而变；递归 CTE 必须考虑终止条件与环。UPDATE/DELETE 需要约束目标集合并在事务中验证影响行数，MERGE/UPSERT 的冲突语义也有引擎差异。

**练习**：金额为 10、NULL、20 时 COUNT(*)、COUNT(amount)、SUM(amount) 分别是什么？分别为 3、2、30。接着让输入为空，比较 COUNT 与 SUM；这样才能看清“忽略 NULL”和“空输入的结果”是两个问题。

## 关联阅读

- [[计算机知识/55-数据库/10-系统课程/01-关系模型ER与约束设计|关系模型与 ER：先约束合法世界，再编写查询]]
- [[计算机知识/55-数据库/10-系统课程/06-查询优化器连接与执行模型|查询优化：从关系表达式到有证据的执行计划]]
- [[计算机知识/10-编程语言/01-Python/10-系统课程/07-类型协议数据边界与安全|类型、协议与数据边界：静态说明不能代替运行时验证]]

## 依据与继续查证

- [PostgreSQL 17 文档（案例方言，不代表所有数据库）](https://www.postgresql.org/docs/17/)
- [SQLite 文档（本地实验引擎）](https://www.sqlite.org/docs.html)
- [CMU 15-445/645（数据库系统原课程）](https://15445.courses.cs.cmu.edu/fall2024/)

本页的例子、推演与练习为教学构造；语言契约、系统接口和版本相关结论应结合以上原始文档核对。

<!-- COURSE SEQUENCE -->
## 顺序导航与验证

[[计算机知识/55-数据库/10-系统课程/00-数据库系统课程索引|本课程总索引]] · [[计算机知识/_labs/round3/DB/数据库-实验说明|本课程实验]]

上一讲：[[计算机知识/55-数据库/10-系统课程/02-函数依赖规范化与设计权衡|函数依赖与规范化：为什么拆表，以及怎样证明没拆坏]]

下一讲：[[计算机知识/55-数据库/10-系统课程/04-可串行化锁与MVCC|事务隔离：用并发历史判断，而不是只背 ACID]]
<!-- END COURSE SEQUENCE -->

<!-- ORIGINAL DEEP LINKS -->
## 与原有长篇专题衔接

- [[计算机知识/55-数据库/02-SQL连接聚合子查询窗口与NULL|02-SQL连接聚合子查询窗口与NULL]]

新旧讲解采用的版本与模型可能不同，比较时先核对各自前提，不把教学简化当成实现细节。
<!-- END ORIGINAL DEEP LINKS -->
