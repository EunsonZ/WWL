"""Deterministic explanatory SVGs. Import does not write; --output is required.

The output is a candidate/vault root. Illustrations are authored from fictional
lesson cases, not observations, and do not depict every institutional path.
"""
import argparse
from html import escape
from pathlib import Path

PANELS = {
 "社会科学/40-公共政策与社会学/assets/tax-budget.svg": (
  "税额进入预算，预算进入执行", [
  ("原料至制造至零售", "税外售价100、160、200；消费者付220"),
  ("销项减进项", "净缴10＋6＋4＝20；完整抵扣，虚构税率10%"),
  ("税收入库与预算授权", "中央税80＋地方税20＝合并税100"),
  ("转移与融资", "内部转移30抵销；支出110，债务融资10"),
  ("服务执行与决算监督", "拨款、实际支付、服务结果须分别核验")]),
 "社会科学/30-金融市场与风险/assets/household-finance.svg": (
  "先看钱付给谁，再看得到什么权利", [
  ("一级发行", "甲付公司100；公司现金＋100、债务＋100"),
  ("二级交易", "乙付甲102；债券换持有人，公司此次收入0"),
  ("到期履约或违约", "如履约，公司付乙105；承诺不等于保证"),
  ("另一种合同：保险", "交保费12，事故损失100，再核查责任"),
  ("赔款与家庭自留", "免赔20、限额70，赔70、自留30；不含保费")]),
 "社会科学/20-经济流动与宏观/assets/trade-chain.svg": (
  "两国分工与贸易：数量、价值、分配分开", [
  ("甲乙分工和交换", "4布、6酒；消费合计仍4布、6酒"),
  ("甲零件出口100", "甲本环增加值100"),
  ("乙装配返售160", "乙增加值60；甲进口160"),
  ("甲分销，家庭消费200", "甲分销增加值40；世界增加值200"),
  ("另一个市场层：甲成品关税10", "消费者-550、生产者＋250、政府＋200、损失100")]),
 "社会科学/20-经济流动与宏观/assets/fx-payments.svg": (
  "E＝人民币/美元；从货物追到结算资产", [
  ("货物100美元，E＝7", "中国居民进口企业取得货物700人民币"),
  ("支付既有外部存款", "对外国银行存款-100美元；没有另添购汇"),
  ("外国出口商收款", "本国银行存款＋100；银行负债在两客户间转移"),
  ("两国汇总", "中国CA＝FA＝-100；外国CA＝FA＝＋100"),
  ("持有存量与其他变化", "交易、汇率重估、价格重估分别连接期末IIP")])}


def wrap_label(text, limit=22):
    """Keep number/ASCII tokens together, with a bound in CJK-width units."""
    import re
    import unicodedata
    lines, line, width = [], "", 0.0
    for token in re.findall(r"[A-Za-z0-9_/=+.-]+|.", text):
        amount = sum(1.0 if unicodedata.east_asian_width(ch) in "WF" else 0.55 for ch in token)
        if line and width + amount > limit:
            lines.append(line); line, width = "", 0.0
        line += token; width += amount
    if line: lines.append(line)
    if len(lines) > 2: raise ValueError("diagram label exceeds two readable lines")
    return lines


def svg(title, rows):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 770" role="img">',
             '<title>' + escape(title) + '</title>',
             '<desc>五步教学流程，路径箭头表示阅读顺序；数字是正文的同一虚构算例。</desc>',
             '<rect width="480" height="770" fill="#f5f7fb"/>',
             '<g font-family="PingFang SC,Microsoft YaHei,sans-serif">',
             '<text x="20" y="38" font-size="21" fill="#142842">' + escape(title) + '</text>']
    for i, (head, body) in enumerate(rows):
        y = 80 + i * 130
        parts.extend([f'<rect x="16" y="{y}" width="448" height="108" rx="12" fill="#ffffff" stroke="#456e9c" stroke-width="2"/>',
                      f'<text x="30" y="{y+31}" font-size="20" fill="#163f6b">{i+1}. {escape(head)}</text>'])
        for j, line in enumerate(wrap_label(body)):
            parts.append(f'<text x="30" y="{y+62+j*23}" font-size="18" fill="#27394b">{escape(line)}</text>')
        if i < len(rows)-1:
            parts.append(f'<path d="M240 {y+111}v15l-5 -5m5 5l5 -5" fill="none" stroke="#456e9c" stroke-width="2"/>')
    parts.extend(['<text x="20" y="739" font-size="13" fill="#4c5c6c">虚构算例与最小路径；箭头表示阅读顺序。</text>',
                  '<text x="20" y="758" font-size="13" fill="#4c5c6c">条件与边界在正文；不代表完整制度或现实预测。</text>', '</g></svg>'])
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for name, (title, rows) in PANELS.items():
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(svg(title, rows), encoding="utf-8")


if __name__ == "__main__":
    main()
