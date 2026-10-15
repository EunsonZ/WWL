"""Generate three original teaching diagrams. Importing writes nothing.

Usage: python3 -B social_figures.py --output /absolute/asset/directory
These figures explain the adjoining lessons; they are not legal process charts.
"""
import argparse
from html import escape
from pathlib import Path

PANELS = {
    'social-organizations.svg': (
        '谁决定，谁受影响，谁承担后果',
        [('目的', '为什么一起行动'), ('成员与受影响者', '谁能表决，谁受后果'),
         ('资源', '钱、人员、场地从哪来'), ('决策', '谁授权，谁执行'),
         ('退出与申诉', '能否离开，怎样异议'), ('责任', '谁说明，谁纠正')],
        '原创分析清单；六项需要结合实体、法域与具体规则检查。'),
    'public-decision.svg': (
        '从公共问题到可检查的决定',
        [('进入议程', '谁提出，谁未被听见'), ('目标与选项', '比较目标和替代方案'),
         ('权限与预算', '谁能决定，有无资源'), ('讨论与决定', '记录依据、范围和程序'),
         ('执行', '人员、支付、服务落实'), ('核对与纠正', '报告、监督、救济')],
        '教学检查点；现实有回退、并行和例外，不是任何国家的法定统一流程。'),
    'payroll-resources.svg': (
        '工资怎样连接到生活资源',
        [('雇主成本 12000', '工资10000＋1800＋200'), ('税前工资 10000', '扣个人款项之前'),
         ('到手现金 8780', '减个人缴费800、税420'), ('家庭现金 13480', '加伴侣、转移和财产现金'),
         ('价格与支出', '现金能买多少，剩多少'), ('服务、时间与风险', '分别检查，不能直接加钱')],
        '金额为元/月；虚构税制与教学账。家庭现金不是完整统计可支配收入。'),
}

def render(title, boxes, footer):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="590" viewBox="0 0 1040 590" role="img">',
         f'<title>{escape(title)}</title>', '<desc>三列两行的六个检查点，依次连线。详见相邻正文解释。</desc>',
         '<rect width="1040" height="590" fill="#f5f7fb"/>',
         '<defs><marker id="a" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8" fill="#55708c"/></marker></defs>',
         '<g font-family="PingFang SC,Microsoft YaHei,sans-serif">',
         f'<text x="40" y="56" font-size="28" fill="#142b46">{escape(title)}</text>']
    for i, (head, body) in enumerate(boxes):
        x = 40 + (i % 3) * 330
        y = 110 + (i // 3) * 205
        s += [f'<rect x="{x}" y="{y}" width="300" height="142" rx="14" fill="#fff" stroke="#a4b7cb"/>',
              f'<text x="{x+20}" y="{y+40}" font-size="23" fill="#16466b">{i+1}. {escape(head)}</text>',
              f'<text x="{x+20}" y="{y+85}" font-size="18" fill="#33465c">{escape(body)}</text>']
        if i in (0, 1, 3, 4):
            s.append(f'<path d="M{x+303},{y+71} L{x+324},{y+71}" stroke="#55708c" fill="none" stroke-width="2" marker-end="url(#a)"/>')
    s += ['<path d="M850,258 L850,285 L190,285 L190,309" stroke="#55708c" fill="none" stroke-width="2" marker-end="url(#a)"/>',
          f'<text x="40" y="530" font-size="17" fill="#33465c">{escape(footer)}</text>',
          '<text x="40" y="565" font-size="15" fill="#52677e">箭头为阅读连接；不能从先后步骤直接推断因果、法律效力或福利。</text>', '</g></svg>']
    return '\n'.join(s) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, parts in PANELS.items():
        (args.output / name).write_text(render(*parts), encoding='utf-8')

if __name__ == '__main__':
    main()
