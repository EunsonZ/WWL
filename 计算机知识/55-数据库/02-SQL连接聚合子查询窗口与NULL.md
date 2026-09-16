---
type: lesson
domain: computer-science
status: expanded
revision: 2026-09-06
tags: [computer-science, revision-2]
---

# 数据库：SQL 的结果为什么经常比预期多或少

> 阅读定位：关系理论通用；实现示例区分 SQLite 与 PostgreSQL 17。返回 [[计算机知识/00-开始/课程地图/10-数据库-课程地图|数据库 · 课程地图]]；全域入口 [[计算机知识/00-开始/全局导航/00-总学习地图|计算机知识库 · 总学习地图]]。

## 先按逻辑含义理解查询

可用 FROM/JOIN、WHERE、GROUP BY、HAVING、SELECT、DISTINCT、ORDER BY、LIMIT 的逻辑次序理解许多查询，但实际执行器会优化，不能把逻辑次序当物理指令顺序。SELECT、INSERT、UPDATE、DELETE 之外，DDL 定义结构，权限与事务命令管理使用边界。

SQL 默认常按多重集合处理重复值。连接匹配不唯一时，一条左侧记录可以匹配多条右侧记录，数量相乘。统计客户订单总额前，若又连接了多行联系方式，金额可能被重复累计。先确认连接基数和唯一性，再写聚合。

## 外连接与 NULL 的具体反例

```sql
SELECT c.customer_id, COUNT(o.order_id) AS order_count
FROM customer AS c
LEFT JOIN orders AS o
  ON o.customer_id = c.customer_id AND o.status = 'paid'
GROUP BY c.customer_id;
```

把 `o.status='paid'` 放到 WHERE 会过滤掉没有匹配订单的客户，因为补出来的 o.status 是 NULL，比较不为真。COUNT(*) 会统计外连接补出的行，而 COUNT(o.order_id) 忽略该字段的 NULL，二者不能互换。

NULL 表示缺失或未知语义，`NULL = NULL` 不是 true，应使用 IS NULL 判断缺失。`NOT IN` 的子查询结果含 NULL 时可能让结果出乎意料；在合适业务语义下改用 NOT EXISTS 并明确关联条件。COALESCE 可提供替代值，但把缺失统一填成零可能改变业务含义。

## 子查询、集合操作和窗口

EXISTS 检查存在性，相关子查询引用外层值；CTE 帮助组织表达，不保证所有实现与版本都会将其物化。UNION 通常去重，UNION ALL 保留重复，INTERSECT 与 EXCEPT 表达集合关系。

聚合把多行合为少量组；窗口函数保留每行并计算组内信息，例如 `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at,order_id)`。只有时间戳而没有稳定并列规则时，排序结果可能不确定。窗口默认 frame 在某些函数和重复排序键下容易与直觉不同，应明确 ROWS/RANGE 与边界。

## 安全与可重复性

参数化查询把值与 SQL 结构分开，避免把用户字符串拼进 SQL。表名和排序方向通常不能直接当普通值参数，应从可信白名单选择。更新和删除前先确认条件与预计影响行数，真实数据变更应有事务和恢复方案。

练习：构造两个客户，其中一个无订单，一个有两笔订单，再为后者加两个地址。手算不同 JOIN 的行数，解释错误总额如何产生。然后用窗口函数选每个客户的最新订单，明确时间相同时按哪个唯一字段打破并列。

## 把知识接起来

[[计算机知识/55-数据库/01-关系模型约束与数据建模|数据库：从业务不变量到关系模型]]；[[计算机知识/55-数据库/04-事务隔离锁MVCC与并发异常|数据库：事务、隔离、锁与 MVCC 的时间线]]；[[计算机知识/50-数据结构与算法/23-正确性证明反例与复杂度边界|算法设计深化：证明、反例与复杂度边界]]。

## 规范与进一步核对

参见 [[计算机知识/90-资源/10-本轮权威资料与版本边界#数据库|数据库原始资料]]。正文中的例题是本库的教学构造；一般模型不自动等于某一实现。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/55-数据库/10-系统课程/03-SQL查询语义与窗口函数|SQL 的逻辑语义：NULL、外连接、聚合和窗口]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
