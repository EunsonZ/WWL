"""Original loan timeline figure; standard library, silent import, explicit output."""
import argparse
from pathlib import Path
from xml.sax.saxutils import escape

def make_svg():
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="360" height="1080" viewBox="0 0 360 1080" role="img" aria-labelledby="title desc">',
           '<title id="title">同一贷款的四个事件</title>',
           '<desc id="desc">竖向箭头表示时间顺序。小陈存款是对银行资产，债务是还款义务，银行准备金用于跨行结算。四事件为放贷20、付款20、返报酬12、还本10并付利息1。</desc>',
           '<rect width="360" height="1080" fill="white"/>',
           '<g font-family="PingFang SC, Heiti SC, sans-serif" fill="#16202a">']
    def text(x,y,label,size=18,bold=False):
        weight=' font-weight="600"' if bold else ''
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}"{weight}>{escape(label)}</text>')
    text(22,35,'同一贷款的四个事件',23,True)
    text(22,65,'箭头只表示时间顺序',18,True)
    text(22,91,'金额为教学单位；无手续费与税',17)
    events=[
        ('1  A放贷20', ['小陈：存款5变25，债务0变20','A：贷款与存款负债各增加20','A准备金仍30；B仍20','借到钱，不等于净财富增加20']),
        ('2  小陈跨行付商户20', ['小陈：存款25变5，债务仍20','商户在B存款10变30','A准备金30变10，B20变40','两行存款合计仍200']),
        ('3  商户返劳动报酬12', ['商户在B存款30变18','小陈在A存款5变17','B准备金40变28，A10变22','这是另笔已发生的劳动报酬']),
        ('4  还本金10、利息1', ['小陈：存款17变6，债务20变10','A贷款90变80，存款102变91','A权益10变11；利息计入收益','A准备金22、B28均不变'])]
    for i,(title,lines) in enumerate(events):
        top=115+i*192
        parts.append(f'<rect x="14" y="{top}" width="332" height="169" rx="9" fill="{["#eaf2fa","#f4f1e8","#eaf3ee","#f0edf7"][i]}" stroke="#334452" stroke-width="1.4"/>')
        text(26,top+29,title,20,True)
        for j,label in enumerate(lines):text(26,top+58+j*28,label,17)
        if i<3:
            y=top+170
            parts.append(f'<path d="M180 {y} V{y+13}" stroke="#334452" stroke-width="2.5"/><path d="M175 {y+10} L180 {y+18} L185 {y+10}" fill="#334452"/>')
    text(22,927,'三种对象分开看',20,True)
    text(22,959,'存款：小陈对银行的金融资产',17)
    text(22,987,'准备金：银行对央行的结算资产',17)
    text(22,1015,'债务：小陈对A的还款义务',17)
    text(22,1052,'银行逐行闭合与反例，见邻接账本',16)
    parts.extend(['</g>','</svg>'])
    return '\n'.join(parts)+'\n'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(make_svg(),encoding='utf-8')
if __name__=='__main__':main()
