from pathlib import Path
import subprocess,json,html,os
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent;root.mkdir(exist_ok=True)
font='Noto Sans CJK SC'
def graph(name,title,nodes,edges,rank='LR'):
 def q(s):return json.dumps(s,ensure_ascii=False)
 txt='digraph G {\n graph [rankdir='+rank+', bgcolor="white", pad="0.3", nodesep="0.4", ranksep="0.45", label='+q(title)+', labelloc="t", fontsize=22, fontname='+q(font)+'];\n node [shape=box, style="rounded", margin="0.16,0.12", fontsize=16, fontname='+q(font)+'];\n edge [fontsize=13, fontname='+q(font)+'];\n'
 for key,label in nodes:txt+=f'{key} [label={q(label)}];\n'
 for edge in edges:
  a,b,*label=edge;txt+=f'{a} -> {b}'+(' [label='+q(label[0])+']' if label else '')+';\n'
 txt+='}\n';(root/f'{name}.dot').write_text(txt)
 for ext in ['svg','png']:
  subprocess.run(['dot',f'-T{ext}','-Gdpi=145',str(root/f'{name}.dot'),'-o',str(root/f'{name}.{ext}')],check=True)
graph('autograd','前向计算数值；反向累加梯度',[('x','x=2'),('w','w=3'),('b','b=1'),('mul','wx=6'),('z','z=wx+b=7'),('loss','L=(z−5)²/2=2'),('grad','dL/dz=2\ndL/dw=4\ndL/db=2\ndL/dx=6')],[('x','mul'),('w','mul'),('mul','z'),('b','z'),('z','loss'),('loss','grad')])
graph('distributed','不等 token 数：先汇总分母，再匹配梯度平均约定',[('r0','rank 0\n8 token；损失和 8'),('r1','rank 1\n2 token；损失和 6'),('n','全局 N=8+2=10\nrank 数 R=2'),('b','每个 rank 反传 R·Sᵣ/N\nDDP 再平均梯度'),('out','目标：(8+6)/10=1.4\n错误：(1+3)/2=2')],[('r0','n'),('r1','n'),('n','b'),('b','out')])
graph('receptive_field','理论感受野 r 与原图采样间距 j',[('a','输入\nr=1, j=1'),('b','3×3；stride=2\nr=3, j=2'),('c','3×3；stride=2\nr=7, j=4'),('d','3×3；stride=1\nr=15, j=4'),('e','r_new = r_old + (k−1)·d·j_old\nj_new = j_old·stride')],[('a','b'),('b','c'),('c','d'),('d','e')])
graph('residual','恒等路径与可学习修正',[('x','输入 x'),('f','可学习支路 F(x)\n卷积 / Attention / FFN'),('sum','逐元素相加\ny=x+F(x)'),('j','雅可比：I + J_F\n不保证任意深度都稳定')],[('x','f'),('f','sum'),('x','sum','恒等路径'),('sum','j')])
graph('vit','ViT：patch 投影后，使用注意力混合位置',[('a','图像 224×224×3'),('b','16×16 patch\n14×14=196 块'),('c','每块展平 768 维\n线性投影到 D'),('d','位置表示\n可选 CLS token'),('e','Transformer\n全局 token 混合'),('f','分类 / 检索 / 视觉特征')],[('a','b'),('b','c'),('c','d'),('d','e'),('e','f')])
graph('mla','MLA：缓存潜表示，并保留必要的位置分支',[('h','隐藏状态 h'),('c','低秩 c=W_DKV h\n缓存内容潜表示'),('k','内容 key = W_UK c'),('v','value = W_UV c'),('q','当前 query\n可吸收内容上投影'),('r','解耦 RoPE key\n缓存必要位置状态'),('o','内容分数 + 位置分数\n混合潜表示后输出')],[('h','c'),('c','k'),('c','v'),('q','o'),('k','o'),('v','o'),('h','r'),('r','o')])
graph('ssm','状态递推：固定宽度摘要，不是无损保存整个历史',[('h0','状态 h₀'),('x1','输入 x₁'),('h1','状态 h₁\n保留 + 写入'),('x2','输入 x₂'),('h2','状态 h₂\n保留 + 写入'),('y','读取 y₂\n表示能力受状态约束')],[('h0','h1'),('x1','h1'),('h1','h2'),('x2','h2'),('h2','y')])
graph('rl','LLM 强化学习：采样、验证与受约束更新',[('p','prompt / 任务'),('g','旧策略采样\nG 个回答'),('r','验证器 / 奖励\n正确性 + 其他约束'),('a','组内基线 / 优势\n处理零方差与长度'),('o','clipped 目标\n可选 KL 约束'),('u','更新当前策略\n独立留出评测')],[('p','g'),('g','r'),('r','a'),('a','o'),('o','u')])
graph('flash','在线 softmax：合并统计量，不是平均分块输出',[('a','已处理块\nm_A, ℓ_A, u_A'),('b','新块\nm_B, ℓ_B, u_B'),('m','m′ = max(m_A,m_B)\n各块按新最大值重标定'),('s','合并权重和 ℓ′\n合并加权向量和 u′'),('o','最终输出 u′/ℓ′\n避免保存完整 T×T 矩阵')],[('a','m'),('b','m'),('m','s'),('s','o')])
graph('reasoning','测试时计算：候选是否更好，取决于验证与预算',[('p','问题与总预算'),('g','候选生成\n并行采样 / 逐步搜索'),('v','结果 / 过程验证\n测试、证据、工具'),('s','选择或修订\n记录实际成本'),('e','预算或成功条件\n提交 / 停止 / 人工复核')],[('p','g'),('g','v'),('v','s'),('s','e')])
graph('clip','CLIP：N 对图文，形成 N×N 匹配任务',[('i','N 张图像'),('t','N 段文本'),('ie','图像编码器\nL2 归一化'),('te','文本编码器\nL2 归一化'),('s','相似度矩阵 S\nsᵢⱼ = uᵢᵀvⱼ / τ'),('l','行与列交叉熵\n对角配对为正样本')],[('i','ie'),('t','te'),('ie','s'),('te','s'),('s','l')])
graph('vlm','生成式 VLM：让视觉证据进入语言上下文',[('i','图像 / 裁剪'),('e','视觉编码器\n[B,N,D_v]'),('p','投影 / 压缩连接器\n[B,N,D_l]'),('t','问题文本 token'),('l','语言模型\n融合视觉和文本'),('o','答案 + 可核验来源\n检验是否真的依赖图像')],[('i','e'),('e','p'),('p','l'),('t','l'),('l','o')])
graph('audio','语音：连续采样到未知对齐的文本',[('w','波形\n采样率 / 时长 / 声道'),('f','分帧 / STFT\nlog-Mel 等特征'),('e','音频编码器'),('c','CTC\n路径求和 / blank'),('d','自回归 decoder\n文本条件生成'),('o','文本与评测\nCER / WER / 关键错误')],[('w','f'),('f','e'),('e','c'),('e','d'),('c','o'),('d','o')])
graph('diffusion','扩散：训练已知加噪，生成学习反向过程',[('x','真实样本 x₀'),('n','采样 t 与 ε\nx_t=√ᾱ_t x₀+√(1−ᾱ_t) ε'),('p','网络预测 ε_θ(x_t,t)'),('l','与真实 ε 比较\nMSE 训练'),('s','生成：从噪声 x_T 出发\n逐步反向采样')],[('x','n'),('n','p'),('p','l'),('p','s')])
graph('flow','Flow Matching：本图时间方向为噪声到数据',[('n','噪声 x₀'),('d','数据 x₁'),('p','条件路径\nx_t=(1−t)x₀+t x₁'),('v','目标速度 x₁−x₀\n拟合 v_θ(x_t,t)'),('o','生成时解 ODE\ndx/dt=v_θ(x,t)')],[('n','p'),('d','p'),('p','v'),('v','o')])
graph('transformer','Decoder-only Transformer：训练并行，生成逐步',[('t','token IDs\n[B,T]'),('e','Embedding\n[B,T,D]'),('a','Norm → causal attention\n+ 残差'),('f','Norm → FFN\n+ 残差'),('o','最后归一化 → 词表投影\n[B,T,V]'),('l','训练：错位目标交叉熵\n推理：末位分布采样')],[('t','e'),('e','a'),('a','f'),('f','o'),('o','l')])
graph('course_map','学习地图：统计与张量 → 框架与结构 → 训练推理与验证',[('m','机器学习与统计\n目标 / 拆分 / 泛化'),('p','PyTorch\n张量 / 梯度 / 训练'),('c','CNN / ViT\n局部与空间表示'),('l','Transformer / LLM\n表示 / 架构 / 训练'),('v','VLM / 语音 / 扩散\n多模态核心课程'),('e','RAG / Agent / 部署\n验证 / 资源 / 权限'),('x','CPU 实验与数值断言\n原有六组进阶实践')],[('m','p'),('p','c'),('p','l'),('c','v'),('l','v'),('l','e'),('p','x'),('l','x')])
# Matrix diagrams: high-resolution raster plus matching SVG wrapper, no external resources.
fpath=os.environ.get('AI_DIAGRAM_FONT', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
F=lambda s:ImageFont.truetype(fpath,s)
def matrix(name,title,matrices,footer):
 im=Image.new('RGB',(1560,640),'white');d=ImageDraw.Draw(im);d.text((35,20),title,font=F(36),fill='black')
 for x,y,label,rows in matrices:
  d.text((x,y),label,font=F(25),fill='black');sz=67
  for r,row in enumerate(rows):
   for c,val in enumerate(row):
    xx=x+c*sz;yy=y+52+r*sz;d.rectangle((xx,yy,xx+sz,yy+sz),outline='black',width=2)
    box=d.textbbox((0,0),str(val),font=F(25));d.text((xx+(sz-box[2])/2,yy+15),str(val),font=F(25),fill='black')
 d.text((35,485),footer,font=F(25),fill='black',spacing=12);im.save(root/f'{name}.png')
 # SVG is rebuilt as native text and grid, not linked to the PNG.
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="640" viewBox="0 0 1560 640">','<rect width="100%" height="100%" fill="white"/>',f'<g font-family="Noto Sans CJK SC, sans-serif" fill="black"><text x="35" y="58" font-size="36">{html.escape(title)}</text>']
 for x,y,label,rows in matrices:
  svg.append(f'<text x="{x}" y="{y+30}" font-size="25">{html.escape(label)}</text>')
  for r,row in enumerate(rows):
   for c,val in enumerate(row):
    xx=x+c*67;yy=y+52+r*67;svg += [f'<rect x="{xx}" y="{yy}" width="67" height="67" fill="none" stroke="black" stroke-width="2"/>',f'<text x="{xx+33}" y="{yy+44}" text-anchor="middle" font-size="25">{html.escape(str(val))}</text>']
 for i,line in enumerate(footer.splitlines()):svg.append(f'<text x="35" y="{515+i*42}" font-size="25">{html.escape(line)}</text>')
 svg.append('</g></svg>');(root/f'{name}.svg').write_text('\n'.join(svg))
matrix('convolution','互相关：同一个核，在各个位置重复使用',[(50,120,'输入 X：3×3',[[1,2,3],[4,5,6],[7,8,9]]),(480,120,'核 K：2×2',[[1,0],[0,-1]]),(890,120,'输出 Y：2×2',[[-4,-4],[-4,-4]])],'左上输出：1×1 + 2×0 + 4×0 + 5×(−1) = −4\nstride=1，padding=0。可学习卷积核通常不预先固定为差分核。')
matrix('cache_mask','缓存解码：可见性由绝对位置决定',[(80,125,'列： key 位置 0、1、2、3、4、5、6；行：query 位置 5、6',[['✓','✓','✓','✓','✓','✓','×'],['✓','✓','✓','✓','✓','✓','✓']])],'已有 5 个 token，一次提交 2 个新 query：允许 key_pos ≤ query_pos。\n这是 2×7 的偏移因果掩码，不是从左上角起的普通下三角。')
