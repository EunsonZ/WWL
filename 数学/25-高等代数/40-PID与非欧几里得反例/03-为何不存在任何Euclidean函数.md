---
type: lesson
aliases:
  - 负十九环非Euclidean证明
  - 任意欧几里得函数排除
sources:
  - https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html
prerequisites:
  - "[[数学/25-高等代数/40-PID与非欧几里得反例/01-负十九二次整数环与理想类]]"
  - "[[数学/25-高等代数/40-PID与非欧几里得反例/02-Minkowski界如何推出PID]]"
---
# 为何不存在任何 Euclidean 函数

说域范数 $N(a+b\omega)=a^2+ab+5b^2$ 不能完成带余除法，只能证明“这个特定函数不行”。我们要证明更强的结论：不存在任何函数
$$
\delta:R\setminus\{0\}\longrightarrow\mathbb N
$$
使每个 $a,b\in R$、$b\ne0$ 都能写成
$$
\begin{gathered}
a=qb+r,\\
r=0\quad\text{或}\quad\delta(r)<\delta(b).
\end{gathered}
$$
这里不要求 $\delta$ 乘法、不要求它等于域范数，也不要求 $\delta(a)\le\delta(ab)$。

## 最小非单位会迫使商环极小

反设存在这样的 $\delta$。非零非单位集合不空，例如 $2$ 在其中；$\mathbb N$ 良序，所以可选非零非单位 $b$，使 $\delta(b)$ 在所有非零非单位中最小。

对任意 $a\in R$，带余除法给 $a=qb+r$。若 $r\ne0$，则 $\delta(r)<\delta(b)$；按 $b$ 的选择，$r$ 不可能是非单位，只能是单位。第 01 课已经由正定范数证明
$$
R^\times=\{1,-1\}.
$$
因此 $R/(b)$ 的每个剩余类都有代表 $0,1$ 或 $-1$，从而
$$
|R/(b)|\le3.
$$
$b$ 不是单位，所以 $(b)\ne R$，商环不止一个元素。主理想范数公式又给
$$
|R/(b)|=N((b))=|N_{K/\mathbb Q}(b)|.
$$
所以商环大小只能是 $2$ 或 $3$。

这就是 Sharifi Lemma 5.4.22 所说的 universal side divisor：欧几里得函数最小的非单位必须让每个剩余类由 $0$ 或单位代表。

## 但本环没有大小 $2$ 或 $3$ 的商

若 $|R/(b)|=p$，其中 $p=2$ 或 $3$，这个含幺交换环必为 $\mathbb F_p$。$\omega$ 的像 $x$ 必须是
$$
f(X)=X^2-X+5
$$
在 $\mathbb F_p$ 中的根。

- 模 $2$：$f(X)=X^2+X+1$，$f(0)=f(1)=1$。
- 模 $3$：$f(X)=X^2-X+2$，对 $x=0,1,2$ 的值依次为 $2,2,1$。

两者都无根，矛盾。因此假设的 $\delta$ 不存在：
$$
\boxed{R\text{ 不是 Euclidean 整环}.}
$$

这里排除的是任意 Euclidean 函数，而不仅是当前的域范数。

## 与域范数的角色分工

域范数在这份反证中做了两件可靠的事：确认单位只有 $\pm1$，以及把主理想商的大小写成 $|N(b)|$。真正反驳任意 $\delta$ 的是“最小 $\delta$ 非单位”引理。没有把 $N$ 偷换成未知的 $\delta$。

既有 [[数学/25-高等代数/16-整环Euclid域PID与唯一分解#逆箭头和一般整环的反例|整环分解链]] 还给出另一种同源算法：先用最小非单位除 $2$，把候选压到 $\pm2,\pm3$，再除 $\omega$ 得矛盾。本页的商环版本把“所有余数只能是 $0,\pm1$”一次性编码为 $|R/(b)|\le3$；两者都排除任意 $\delta$。

把第 02 课与本课合并，得到严格反例
$$
\text{PID}\centernot\Longrightarrow\text{Euclidean}.
$$
PID 保证每个理想有生成元；Euclidean 还要求一个单一的良序量在每次除法中下降。前一性质并不自动制造后一函数。
