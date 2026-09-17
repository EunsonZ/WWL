from pathlib import Path
from html import escape
p = Path(__file__).resolve().parent
def figure(name,title,rows,caption):
    height=140+len(rows)*75
    chunks=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="{escape(title)}">', '<rect width="100%" height="100%" fill="#f6f8fb"/>','<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#325b8e"/></marker></defs>', f'<text x="30" y="40" font-family="Hiragino Sans GB" font-size="24" fill="#18314d">{escape(title)}</text>']
    for i,(label,nodes) in enumerate(rows):
        y=65+i*75
        chunks.append(f'<text x="30" y="{y+30}" font-family="Hiragino Sans GB" font-size="18">{escape(label)}</text>')
        w=(820-(len(nodes)-1)*25)/len(nodes)
        for j,node in enumerate(nodes):
            x=150+j*(w+25)
            chunks.extend([f'<rect x="{x}" y="{y}" width="{w}" height="52" rx="8" fill="#e1ebf7" stroke="#8aa7c9"/>', f'<text x="{x+w/2}" y="{y+31}" text-anchor="middle" font-family="Hiragino Sans GB" font-size="17" fill="#18314d">{escape(node)}</text>'])
            if j<len(nodes)-1:
                chunks.append(f'<path d="M{x+w+3},{y+26} H{x+w+22}" fill="none" stroke="#325b8e" stroke-width="2" marker-end="url(#arrow)"/>')
    chunks.append(f'<text x="30" y="{height-22}" font-family="Hiragino Sans GB" font-size="17" fill="#435a70">{escape(caption)}</text></svg>')
    (p/name).write_text('\n'.join(chunks) + '\n')
figure('semantics-strategies.svg','同一个纯Bool调用的两种求值顺序', [('CBV',['(λx:Bool.true) a','a 求为 false','β 替换得 true']),('CBN',['(λx:Bool.true) a','直接 β 替换得 true'])], 'a = (λy:Bool.y) false；两种策略都不在 λ 体内部提前求值。')
figure('semantics-safety.svg','Bool STLC 类型安全的证明依赖', [('保持',['环境不变 / 弱化 / α','替换引理','β 后仍同型']),('进展',['值语法 + 类型规则','标准形态','闭项为值或可步']),('有限链',['初项有类型','每步保持类型','每个可达项排除卡住'])], '最后一行排除有限卡住；不能据此排除无限执行。')
figure('semantics-loop.svg','N=3：头部不变量与体中间状态', [('第1体',['头 (s,x)=(0,3)','加 s 后 (1,3)','减 x 后 (1,2)']),('循环头',['(0,3)  V=3','(1,2)  V=2','(2,1)  V=1','(3,0)  退出'])], 'I: s+x=3 且 x≥0；只要求每个循环头成立，中间 (1,3) 不满足 I。')
