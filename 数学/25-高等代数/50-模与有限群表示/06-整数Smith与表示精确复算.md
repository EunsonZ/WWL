---
type: lab
domain: mathematics
stage: 3
aliases:
  - 整数Smith完整变换复算
prerequisites:
  - 数学/25-高等代数/50-模与有限群表示/02-整数Smith核像商与同调接口
  - 数学/25-高等代数/50-模与有限群表示/04-特征标正交与S3分解
sources:
  - https://kconrad.math.uconn.edu/blurbs/linmultialg/modulesoverPID.pdf
---

# 整数 Smith 与表示精确复算

这里把整数基变换落到可检查的源码，并让同一组 S3 矩阵与特征标接受精确复算。程序服务于固定教学例，不承担一般定理的证明。

## 输入、返回和停止边界

[integer_smith.py](code/integer_smith.py) 是真源，末尾完整镜像与它同步；[examples.py](code/examples.py) 提供固定输入和独立预期答案。两者只需要 Python 3.10+ 标准库，不依赖浮点数、NumPy 或仅返回 D 的 Smith API。

`Matrix.rows` 是整数元组的元组，另存 `ncols`，所以 0×3 与 0×0 能区分。布尔数与浮点数被拒绝；定义域、值域和回原坐标方向见 [[数学/25-高等代数/50-模与有限群表示/02-整数Smith核像商与同调接口#输入与返回：始终保存两侧变换|唯一文字合同]]。

`smith(B)` 返回 U、D、V、rank，满足 UBV=D，并用精确运算核对 shape、幺模性、对角正性、整除链。`kernel_image` 返回整数核基和像基；`homology(A,B)` 在 AB=0 时返回 K、C、两次 Smith、挠不变量、自由秩及原链代表。代表矩阵含 d=1 的零类代表，读取时删去这些平凡项，不能把每列都当非零同调类。

`smith` 的每次输入限于 Z 上至多 8×8、元素绝对值至多 10⁶ 的矩阵；每次默认最多 20,000 次初等操作、中间 U/D/V 整数至多 4096 bit。范围内仍可能因资源界限停止；触发时抛出异常，**不返回认证的部分结果**。`homology` 分别对 A 和核坐标 C 调用 Smith 并检查上述条件，同调入口不另给原 B 的元素大小界限；核坐标计算使用精确整数，未承诺这一步的整体中间位数上限。这里没有给出工业规模性能、多项式环消元或一般 PID 的有效算法保证。

## 消元为什么要检查剩余子块

每轮选非零枢轴，用整数商与余数消去同列、同行非零项；出现非零余数就交换成更小绝对值的枢轴。每个行操作同做于 U，每个列操作同做于 V，因此始终保持当前 D=UBV。

若首行首列已经清零，却有余下元素不被枢轴整除，把它所在行加到枢轴行，再进行 Euclid 消元；新余数严格减小枢轴绝对值。这就是对 diag(6,10) 还须修成 diag(2,30) 的原因。枢轴整除整个余块后再递归，后续整数组合保持该整除性。前课的一般 PID 证明使用主理想升链；这里借 Z 的 Euclid 余数给具体计算步骤。

## 固定输入与独立答案

| 输入 | 预期非零 Smith 不变量 | 预期商／同调 |
|---|---|---|
| B=((4,6),(2,6)) | (2,6)；一阶子式 gcd=2，行列式绝对值12 | coker=Z/2⊕Z/6，核为0 |
| B=diag(6,10) | (2,30)；gcd=2，乘积60 | coker=Z/2⊕Z/30 |
| B=((2,4,0),(0,0,0))，2×3 | (2) | 核秩2，coker=Z/2⊕Z |
| B=((-4,6),(2,-6)) | (2,6) | coker=Z/2⊕Z/6 |
| 零2×2、0×3、2×0 | 空 | coker分别为Z²、0、Z²；核分别为Z²、Z³、0 |
| A=(1,1)，B=(2,-2)ᵀ | 核基(1,-1)ᵀ中边界坐标(2) | H=Z/2 |
| A=(1,1,0)，B=(2,-2,0)ᵀ | 两维核中边界秩1、有因子2 | H=Z/2⊕Z |

第一行另核 [[数学/25-高等代数/50-模与有限群表示/02-整数Smith核像商与同调接口#一个包含非平凡左右变换的精确例|手写 U/V]] 的独立等式，不要求程序选到相同 U/V。不同合法基产生不同矩阵，正不变量应相同。

表示实验穷举 S3 六个排列的36组乘法，核 P_gP_h=P_(gh)，用 P_rT=T(1⊕R) 和 P_sT=T(1⊕S) 检查同一基分块。特征标加权 Gram 矩阵应为 I₃，三维置换重数为(1,0,1)，W⊗W重数为(1,1,1)，维数平方和为6。n=3 Fourier 向量采用 Q(ω) 的精确二元坐标，关系为 ω²=-1-ω，不以浮点容差代替三个特征向量等式。

## 独立执行接口

从本课目录的 `code` 中执行 `python3 -B examples.py`；可把 JSON 标准输出和退出码保存到执行者新建的库外证据位置。固定答案先读本页，执行后核每个输入和输出 shape、完整 U/D/V、K/C 与表示乘法；只出现 JSON 文件不能自动表明全部断言通过。

作者阶段只作 AST、链接、属性和镜像静态检查，课程程序未由作者执行。独立执行者记录实际环境、源码身份、命令、退出码与输出；没有这些新证据时不能把理论预期写成已运行成功。实际 Obsidian 显示、真人阅读与迁移解题也分别需要观察。

## 真源镜像

<!-- code-sync: ./code/integer_smith.py -->
```python
"""Exact, bounded teaching Smith form over Z. No third-party dependencies."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Matrix:
    rows: tuple
    ncols: int

    def __post_init__(self):
        if type(self.ncols) is not int or self.ncols < 0:
            raise ValueError("ncols must be a nonnegative integer")
        if not isinstance(self.rows, tuple):
            raise TypeError("rows must be a tuple of tuples")
        if any(not isinstance(r, tuple) or len(r) != self.ncols for r in self.rows):
            raise ValueError("ragged rows or wrong ncols")
        if any(type(x) is not int for r in self.rows for x in r):
            raise TypeError("entries must be Python integers, not floats or bools")

    @property
    def nrows(self):
        return len(self.rows)

    @property
    def shape(self):
        return self.nrows, self.ncols


def matrix(rows, ncols=None):
    rows = tuple(tuple(r) for r in rows)
    return Matrix(rows, (len(rows[0]) if rows else 0) if ncols is None else ncols)


def identity(n):
    return matrix([[int(i == j) for j in range(n)] for i in range(n)], n)


def multiply(a, b):
    if a.ncols != b.nrows:
        raise ValueError("incompatible multiplication shapes")
    return matrix([[sum(a.rows[i][k] * b.rows[k][j] for k in range(a.ncols))
                    for j in range(b.ncols)] for i in range(a.nrows)], b.ncols)


def determinant(a):
    if a.nrows != a.ncols:
        raise ValueError("determinant requires a square matrix")
    t = [[Fraction(x) for x in row] for row in a.rows]
    result = Fraction(1)
    for k in range(a.nrows):
        pivot = next((i for i in range(k, a.nrows) if t[i][k]), None)
        if pivot is None:
            return 0
        if pivot != k:
            t[pivot], t[k] = t[k], t[pivot]
            result = -result
        value = t[k][k]
        result *= value
        for i in range(k + 1, a.nrows):
            q = t[i][k] / value
            for j in range(k, a.ncols):
                t[i][j] -= q * t[k][j]
    if result.denominator != 1:
        raise ArithmeticError("integer determinant became noninteger")
    return int(result)


def inverse_unimodular(a):
    if a.nrows != a.ncols or abs(determinant(a)) != 1:
        raise ValueError("matrix must be square and unimodular")
    n = a.nrows
    t = [[Fraction(x) for x in a.rows[i]] +
         [Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    for k in range(n):
        pivot = next(i for i in range(k, n) if t[i][k])
        t[k], t[pivot] = t[pivot], t[k]
        q = t[k][k]
        t[k] = [x / q for x in t[k]]
        for i in range(n):
            if i != k:
                q = t[i][k]
                t[i] = [x - q * y for x, y in zip(t[i], t[k])]
    if any(x.denominator != 1 for row in t for x in row[n:]):
        raise ArithmeticError("unimodular inverse became noninteger")
    return matrix([[int(x) for x in row[n:]] for row in t], n)


@dataclass(frozen=True)
class Smith:
    U: Matrix
    D: Matrix
    V: Matrix
    rank: int

    @property
    def invariants(self):
        return tuple(self.D.rows[i][i] for i in range(self.rank))


def verify_smith(b, result):
    u, d, v, r = result.U, result.D, result.V, result.rank
    m, n = b.shape
    if u.shape != (m, m) or v.shape != (n, n) or d.shape != (m, n):
        raise ArithmeticError("wrong returned shapes")
    if type(r) is not int or not 0 <= r <= min(m, n):
        raise ArithmeticError("wrong rank")
    if abs(determinant(u)) != 1 or abs(determinant(v)) != 1:
        raise ArithmeticError("nonunimodular transform")
    if multiply(multiply(u, b), v) != d:
        raise ArithmeticError("UBV != D")
    for i in range(m):
        for j in range(n):
            if i == j and i < r:
                if d.rows[i][j] <= 0:
                    raise ArithmeticError("diagonal is not positive")
            elif d.rows[i][j] != 0:
                raise ArithmeticError("D is not diagonal")
    values = result.invariants
    if any(y % x for x, y in zip(values, values[1:])):
        raise ArithmeticError("divisibility chain failed")


def smith(b, max_ops=20000, max_bits=4096):
    """Return U,D,V with UBV=D; raise on declared teaching resource limits."""
    m, n = b.shape
    if max(m, n) > 8 or any(abs(x) > 10**6 for row in b.rows for x in row):
        raise ValueError("teaching input limit: at most 8x8, abs(entry) <= 10^6")
    if type(max_ops) is not int or max_ops < 1:
        raise ValueError("max_ops must be a positive integer")
    if type(max_bits) is not int or max_bits < 1:
        raise ValueError("max_bits must be a positive integer")
    d = [list(row) for row in b.rows]
    u = [list(row) for row in identity(m).rows]
    v = [list(row) for row in identity(n).rows]
    operations = 0

    def tick():
        nonlocal operations
        operations += 1
        if operations > max_ops or any(abs(x).bit_length() > max_bits
                                      for t in (d, u, v) for row in t for x in row):
            raise RuntimeError("resource limit; no certified partial form returned")

    def swap_rows(i, j):
        for t in (d, u):
            t[i], t[j] = t[j], t[i]
        tick()

    def swap_cols(i, j):
        for t in (d, v):
            for row in t:
                row[i], row[j] = row[j], row[i]
        tick()

    def add_row(dst, src, q):
        for t in (d, u):
            t[dst] = [x + q * y for x, y in zip(t[dst], t[src])]
        tick()

    def add_col(dst, src, q):
        for t in (d, v):
            for row in t:
                row[dst] += q * row[src]
        tick()

    rank = 0
    for k in range(min(m, n)):
        pos = next(((i, j) for i in range(k, m) for j in range(k, n) if d[i][j]), None)
        if pos is None:
            break
        swap_rows(k, pos[0])
        swap_cols(k, pos[1])
        while True:
            i = next((i for i in range(k + 1, m) if d[i][k]), None)
            if i is not None:
                add_row(i, k, -(d[i][k] // d[k][k]))
                if d[i][k]:
                    swap_rows(i, k)
                continue
            j = next((j for j in range(k + 1, n) if d[k][j]), None)
            if j is not None:
                add_col(j, k, -(d[k][j] // d[k][k]))
                if d[k][j]:
                    swap_cols(j, k)
                continue
            bad = next(((i, j) for i in range(k + 1, m) for j in range(k + 1, n)
                        if d[i][j] % d[k][k]), None)
            if bad is None:
                break
            add_row(k, bad[0], 1)
        if d[k][k] < 0:
            for t in (d, u):
                t[k] = [-x for x in t[k]]
            tick()
        rank += 1
    result = Smith(matrix(u, m), matrix(d, n), matrix(v, n), rank)
    verify_smith(b, result)
    return result


def kernel_image(b, result):
    verify_smith(b, result)
    r = result.rank
    kernel = matrix([row[r:] for row in result.V.rows], b.ncols - r)
    ui = inverse_unimodular(result.U)
    image = matrix([[ui.rows[i][j] * result.invariants[j] for j in range(r)]
                    for i in range(b.nrows)], r)
    return kernel, image


def homology(a, b):
    """A=d_k, B=d_(k+1); return integer kernel and boundary coordinates."""
    if a.ncols != b.nrows:
        raise ValueError("A and B have incompatible chain shapes")
    if any(x for row in multiply(a, b).rows for x in row):
        raise ValueError("AB must be exactly zero")
    sa = smith(a)
    k, _ = kernel_image(a, sa)
    vb = multiply(inverse_unimodular(sa.V), b)
    if any(x for row in vb.rows[:sa.rank] for x in row):
        raise ArithmeticError("boundary has a nonzero noncycle coordinate")
    c = matrix(vb.rows[sa.rank:], b.ncols)
    if multiply(k, c) != b:
        raise ArithmeticError("B != KC")
    sc = smith(c)
    reps = multiply(k, inverse_unimodular(sc.U))
    return {"K": k, "C": c, "smith_A": sa, "smith_C": sc,
            "torsion": tuple(x for x in sc.invariants if x > 1),
            "free_rank": a.ncols - sa.rank - sc.rank, "representatives": reps}
```

## 实际执行与正式证据

2026-10-10，独立执行者在 r1 冻结副本完成固定 CLI、修正后的整数 oracle 和表示补充计算，三项退出码均为0、stderr为空。精确核查包含7固定输入、625个二阶矩阵、30个固定种子的三阶矩阵、5个同调案例及CLI的3个同调、19个拒绝路径；第一次 oracle 的AST适配失败、原driver、修正差异与成功重跑完整保留。命令、Python／平台、原始输入与输出及坐标／代表阶证据见 [[数学/25-高等代数/50-模与有限群表示/运行证据/2026-10-10-fixed-inputs/README|固定输入正式运行证据]]。

实际运行输入是该证据包中的 r1 snapshot；两个课程源码在 r3 保持完全相同，因此复用的是同源码计算证据。r2/r3 的守卫范围文字、Fourier归一化消费者及图级不变归属另受正文独立核查，未宣称整个 r3 重新执行。一般定理的证明、Obsidian显示与真人迁移理解仍分别验收。
