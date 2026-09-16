"""生成本轮自绘图。需要本机 Graphviz 的 dot；不下载任何网络资源。"""
from pathlib import Path
import subprocess
import html

HERE = Path(__file__).resolve().parent
FONT = 'Noto Sans CJK SC'

def diagram(name: str, title: str, body: str, direction: str = 'LR') -> None:
    source = f'''digraph G {{
    graph [rankdir={direction}, bgcolor="white", pad="0.35", nodesep="0.35", ranksep="0.5", fontname="{FONT}", fontsize=21, labelloc="t", label="{title}"];
    node [shape=box, style="rounded,filled", fillcolor="#edf4fa", color="#456782", fontname="{FONT}", fontsize=14, margin="0.15,0.12"];
    edge [fontname="{FONT}", fontsize=12, color="#4f6474", arrowsize=0.7];
    {body}
    }}'''
    path = HERE / f'{name}.dot'
    path.write_text(source, encoding='utf-8')
    for fmt in ('svg', 'png'):
        subprocess.run(['dot', f'-T{fmt}', '-Gdpi=120', str(path), '-o', str(HERE/f'{name}.{fmt}')], check=True)

def main() -> None:
    diagram('vjp', '反向传播：局部变化如何回到输入', '''
    x [label="输入 x：2 × 1\n例：(2, −1)"];
    w [label="参数 W：2 × 2\n[[1,2],[3,4]]"];
    y [label="y = W x：2 × 1\n例：(0, 2)"];
    l [label="标量目标 L\n上游梯度 g = (1, −2)"];
    dx [label="输入梯度 Wᵀg\n= (−5, −6)", fillcolor="#e6f3e9"];
    dw [label="参数梯度 g xᵀ\n= [[2,−1],[−4,2]]", fillcolor="#e6f3e9"];
    x -> y; w -> y; y -> l;
    l -> dx [label="VJP：不必显式存完整 Jacobian"];
    l -> dw [label="共享参数的路径贡献相加"];
    ''')
    diagram('conformal', '保形预测：拟合、校准、测试必须分开', '''
    train [label="训练集\n拟合预测器 f"];
    cal [label="独立校准集：n = 9\n计算误差分数 s₁,…,s₉"];
    sort [label="排序 s₍₁₎ ≤ … ≤ s₍₉₎\nα = 0.2 → k = ceil(10 × 0.8) = 8"];
    test [label="测试点 x\n集合：误差分数 ≤ s₍₈₎", fillcolor="#e6f3e9"];
    limit [label="交换性下：边际覆盖保证\n不是每个子群、每个 x 都覆盖\nk > n 时采用 +∞", fillcolor="#fff3de"];
    train -> cal [label="模型冻结"];cal -> sort;sort -> test;test -> limit;
    ''', 'TB')
    diagram('evaluation', '嵌套验证：把选模型与评估选择过程分开', '''
    all [label="开发数据\n先规定用户 / 时间等拆分单位"];
    outer [label="外层训练部分"];
    inner [label="内层训练 / 验证\n拟合预处理 + 选超参数"];
    fit [label="用所选设置\n重训外层训练部分"];
    hold [label="外层留出部分\n只评估，不参与选择", fillcolor="#e6f3e9"];
    report [label="汇总各外层折\n评估的是选择过程"];
    final [label="反复看最终测试集再调整\n仍然会造成选择偏差", fillcolor="#fff3de"];
    all -> outer;outer -> inner;inner -> fit;all -> hold;fit -> hold;hold -> report;report -> final [style=dashed];
    ''', 'TB')
    diagram('token_weight', '损失分母决定实际训练目标', '''
    a [label="微批 A\n9 个有效 token\n平均损失 1 → 损失和 9"];
    b [label="微批 B\n1 个有效 token\n平均损失 9 → 损失和 9"];
    good [label="按全窗口 token 归一化\n(9 + 9) / (9 + 1) = 1.8", fillcolor="#e6f3e9"];
    bad [label="直接平均两个微批均值\n(1 + 9) / 2 = 5\n改变了样本权重", fillcolor="#fff3de"];
    ddp [label="DDP 默认平均各 rank 梯度\n本地目标：R × 本地损失和 / 全局计数\n零 token 的 rank 也需参与约定的通信"];
    a -> good;b -> good;a -> bad;b -> bad;good -> ddp;
    ''')
    diagram('conv_adjoint', '转置卷积是伴随映射，不是求逆', '''
    x [label="x = (1, 2, 3)\n长度 3"];
    k [label="K = [[1,−1,0],[0,1,−1]]\n互相关核 w = (1,−1)"];
    y [label="Kx = (−1, −1)\n长度 2"];
    g [label="上游梯度 g = (2, 3)"];
    back [label="Kᵀg = (2, 1, −3)\n返回输入空间", fillcolor="#e6f3e9"];
    proof [label="内积检验：〈Kx,g〉 = 〈x,Kᵀg〉 = −5\n但 K(1,1,1) = 0，信息已丢失", fillcolor="#fff3de"];
    x -> k -> y;g -> back [label="转置算子"];back -> proof;y -> proof;
    ''')
    diagram('aliasing', '下采样为何对一个像素的平移敏感', '''
    input [label="高频输入\n+1, −1, +1, −1, …"];
    even [label="偶数位置抽样\n+1, +1, +1, …"];
    odd [label="先移一格再抽样\n−1, −1, −1, …"];
    smooth [label="两点均值低通\n(1 + (−1)) / 2 = 0"];
    result [label="再下采样\n0, 0, 0, …", fillcolor="#e6f3e9"];
    note [label="低通抑制混叠，但也丢失高频细节\n边界、采样相位、任务仍影响鲁棒性", fillcolor="#fff3de"];
    input -> even;input -> odd;input -> smooth -> result;result -> note;
    ''')
    diagram('attention_backward', '注意力反向传播：Softmax 让同一行位置彼此竞争', '''
    qk [label="S = QKᵀ / √d\nS：Tq × Tk"];
    p [label="P = softmax(S)，逐行\nP：Tq × Tk"];
    o [label="O = PV\n上游 G = ∂L/∂O"];
    dv [label="dV = PᵀG\ndP = GVᵀ", fillcolor="#e6f3e9"];
    ds [label="每行：dS = P ⊙ (dP − Σ P⊙dP)\n行梯度和为 0", fillcolor="#e6f3e9"];
    dq [label="dQ = dS K / √d\ndK = dSᵀ Q / √d", fillcolor="#e6f3e9"];
    note [label="例：P=(0.25,0.75)，dP=(2,0)\ndS=(0.375,−0.375)\n整行屏蔽须单独定义行为", fillcolor="#fff3de"];
    qk -> p -> o;o -> dv -> ds -> dq;ds -> note;
    ''', 'TB')
    diagram('rope_cache', '缓存续写的掩码：比较绝对位置，而不是矩阵左上角', '''
    pos [label="已缓存 5 个 token\n新 query 的绝对位置：5、6\nkey 的绝对位置：0…6"];
    table [shape=plain, label=<
    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="8">
      <TR><TD>q / k</TD><TD>0</TD><TD>1</TD><TD>2</TD><TD>3</TD><TD>4</TD><TD>5</TD><TD>6</TD></TR>
      <TR><TD>5</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD BGCOLOR="#ffe4dc">×</TD></TR>
      <TR><TD>6</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD><TD>✓</TD></TR>
    </TABLE>>];
    rule [label="可见条件：key_position ≤ query_position\n布尔 True 在 SDPA 中表示允许参与\n缓存中的 key 不应重复旋转", fillcolor="#e6f3e9"];
    rope [label="固定内容与频率时：R(m)ᵀR(n)=R(n−m)\n这不是整个网络的任意平移不变性", fillcolor="#fff3de"];
    pos -> table -> rule -> rope;
    ''', 'TB')
    diagram('dpo', 'DPO：从 KL 约束策略到成对偏好损失', '''
    obj [label="最大化：Eπ[r] − β KL(π || πref)\nβ > 0，参考策略覆盖候选支持集"];
    opt [label="最优形式\nπ*(y|x) ∝ πref(y|x) exp(r(x,y)/β)"];
    diff [label="同一提示的奖励差\n归一化常数 log Z(x) 抵消"];
    bt [label="Bradley–Terry 偏好模型\nP(y⁺ ≻ y⁻ | x) = sigmoid(r⁺ − r⁻)"];
    loss [label="DPO：−log sigmoid(β Δ)\nΔ = log(πθ⁺/πref⁺) − log(πθ⁻/πref⁻)", fillcolor="#e6f3e9"];
    note [label="序列概率：token 对数概率求和\n改为均值会改变目标\n偏好标签不等于事实真值", fillcolor="#fff3de"];
    obj -> opt -> diff -> bt -> loss -> note;
    ''', 'TB')
    diagram('rag_evidence', 'RAG：把检索、证据使用与引用拆开评估', '''
    q [label="问题 + 身份权限\n明确所需证据"];
    ret [label="稀疏 / 稠密检索\n按权限过滤 + 合并排序"];
    rank [label="重排与上下文组装\n保留来源、版本、块位置"];
    gen [label="生成答案\n外部文本视为资料，不是授权指令"];
    eval [label="分开测量\n检索召回 / 证据蕴含 / 引用覆盖", fillcolor="#e6f3e9"];
    oracle [label="诊断对照\n无检索 / 真实检索 / 理想证据 / 干扰证据", fillcolor="#fff3de"];
    q -> ret -> rank -> gen -> eval;oracle -> ret [style=dashed];oracle -> gen [style=dashed];
    ''', 'TB')
    diagram('course_graph', '问题驱动学习图：先定位失败，再追溯依赖', '''
    math [label="数学桥梁\n几何 · 梯度 · 概率 · 优化"];
    stats [label="统计学习\n目标 · 泛化 · 不确定性"];
    torch [label="PyTorch\n形状 · 分母 · 状态 · 通信"];
    cnn [label="CNN\n局部性 · 采样 · 视觉任务"];
    att [label="Transformer\n注意力 · 位置 · 记忆"];
    train [label="训练与对齐\n数据 · SFT · DPO · GRPO"];
    infer [label="推理与系统\n缓存 · 量化 · 调度 · 采样"];
    apps [label="应用与模态\nRAG · Agent · 图像 · 音频"];
    evidence [label="所有路径返回同一问题\n目标是什么？证据能排除哪些替代解释？", fillcolor="#e6f3e9"];
    math -> stats;math -> torch;torch -> cnn;torch -> att;stats -> train;att -> train;att -> infer;train -> apps;infer -> apps;cnn -> apps;apps -> evidence;stats -> evidence;
    ''', 'TB')
    diagram('memory_tradeoff', '三种记忆组织：缓存少，不等于信息没有代价', '''
    hist [label="过去 token 序列"];
    kv [label="标准注意力\n逐 token 保存 K/V\n未来 query 可重新读取"];
    mla [label="MLA 简化结构\n逐 token 保存共享潜变量\n线性吸收 + 独立位置分支"];
    state [label="核线性注意力 / 状态空间\n更新固定维状态\n未来只能读取已保留的信息"];
    judge [label="比较时同时控制\n状态大小、有限精度、训练预算\n精确检索、干扰、更新与组合任务", fillcolor="#e6f3e9"];
    hist -> kv;hist -> mla;hist -> state;kv -> judge;mla -> judge;state -> judge;
    ''')

if __name__ == '__main__':
    main()
