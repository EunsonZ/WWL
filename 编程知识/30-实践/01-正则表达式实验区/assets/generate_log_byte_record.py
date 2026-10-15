"""Generate the editable teaching SVG; no writes on import; explicit --output."""
import argparse
from pathlib import Path
from html import escape


def make_svg():
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" viewBox="0 0 480 480" role="img" aria-labelledby="title desc">',
             '<title id="title">同一日志从字节到业务记录</title>',
             '<desc id="desc">v1 的中文消息在码点68到70、字节68到74；LF位于字节74。正文严格解码、完整匹配、日期及单位验证后得到1250微秒；v2的1.250毫秒得到同一业务记录。</desc>',
             '<rect width="480" height="480" fill="white"/>',
             '<style>text{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;fill:#142434} .title{font-size:25px;font-weight:bold} .label{font-size:21px} .small{font-size:19px} .mono{font-family:monospace;font-size:20px}</style>']
    def text(x, y, value, cls='label', anchor='start'):
        y = y-24 if y >= 124 else y
        parts.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(value)}</text>')
    def box(x,y,w,h,color):
        y = y-24 if y >= 124 else y
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{color}" stroke="#475569" stroke-width="1.5"/>')
    text(240,34,'同一日志：字节 → 记录','title','middle')
    text(240,66,'v1 … message=中文 + LF','label','middle')
    text(240,93,'… 是图中省略，真实帧不含它','small','middle')
    vals=['E4','B8','AD','E6','96','87','0A']
    for i,value in enumerate(vals):
        x=19+i*63
        text(x+28,148,str(68+i),'mono','middle')
        box(x,158,56,44,'#e0f2fe' if i<3 else '#dcfce7' if i<6 else '#fef3c7')
        text(x+28,186,value,'mono','middle')
    text(104,228,'中：码点 68','label','middle')
    text(292,228,'文：码点 69','label','middle')
    text(425,228,'LF','label','middle')
    box(20,246,440,74,'#f1f5f9')
    text(36,274,'message：码点 [68,70)','label')
    text(36,303,'原帧字节 [68,74)，LF 在 74','label')
    text(240,345,'正文 70 码点 / 74 字节；帧 75 字节','small','middle')
    text(240,374,'↓ 严格 UTF-8 → 完整匹配','label','middle')
    text(240,402,'↓ 真实日期 + 版本单位 + 范围','label','middle')
    box(20,419,440,72,'#e0f2fe')
    text(240,448,'v1：1250 us = v2：1.250 ms','label','middle')
    text(240,478,'同一业务记录：1250 微秒，中文','label','middle')
    parts.append('</svg>')
    return '\n'.join(parts)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_svg(), encoding='utf-8')


if __name__ == '__main__':
    main()
