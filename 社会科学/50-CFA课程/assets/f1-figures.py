"""Redraw the four original F1 scalar diagrams beside this file; stdlib only."""
from pathlib import Path
from html import escape
P=Path(__file__).resolve().parent
def diagram(name,title,subtitle,boxes,footer):
 w=1080;h=370;n=len(boxes);gap=18;bw=(w-60-gap*(n-1))/n
 s=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="1080" height="370" fill="#f6f8fc"/><g font-family="PingFang SC, Noto Sans CJK SC, sans-serif"><text x="30" y="43" font-size="26" fill="#12243b">{escape(title)}</text><text x="30" y="78" font-size="16" fill="#42536a">{escape(subtitle)}</text>'
 for i,(head,a,b,color) in enumerate(boxes):
  x=30+i*(bw+gap)
  s+=f'<rect x="{x}" y="113" width="{bw}" height="165" rx="12" fill="{color}"/><text x="{x+14}" y="150" font-size="19" fill="#fff">{escape(head)}</text><text x="{x+14}" y="192" font-size="22" fill="#fff">{escape(a)}</text><text x="{x+14}" y="233" font-size="14" fill="#fff">{escape(b)}</text>'
  if i<n-1:s+=f'<path d="M{x+bw+2},193 h14 l-5,-5 m5,5 l-5,5" fill="none" stroke="#42536a" stroke-width="2"/>'
 s+=f'<text x="30" y="325" font-size="17" fill="#23374e">{escape(footer)}</text></g></svg>'
 (P/name).write_text(s)
diagram('f1-eps-sequence.svg','岚桥：逐工具检验EPS','单位：万元 / 万股 = 元每股；各工具全年在外，无终止经营',[
 ('基本','108 / 207.5','EPS 0.520482','#224a73'),('加期权','108 / 223.5','EPS 0.483221','#22637b'),('加债A','111 / 233.5','EPS 0.475375','#227d78'),('加优先股','123 / 263.5','EPS 0.466793','#29825d')],
 '债B：增量EPS 0.48 > 当前0.466793；假设加入会升至0.467938，因此剔除。')
diagram('f1-pension-bridge.svg','独立DB计划：费用、OCI和缴款分开','单位：万元；IFRS，期初义务100 / 计划资产80；折现率5%',[
 ('期初净负债','20','100 - 80','#224a73'),('损益成本','+ 9','服务8 + 净利息1','#22637b'),('OCI损失','+ 7','义务精算6 + 回报偏差1','#9b6032'),('雇主缴款','- 10','期末净负债26 = 115 - 89','#29825d')],
 '20 + 9 + 7 - 10 = 26；基金付福利4同时减义务和资产，不再减雇主现金。')
diagram('f1-tax-bridge.svg','独立税片段：永久差异改总费，暂时差异改分配','单位：万元；会计利润65已含罚款4及免税收入6；税率25%',[
 ('法定基准','16.25','65 * 25%','#224a73'),('不可扣罚款','+ 1.00','4 * 25%','#9b6032'),('免税收入','- 1.50','6 * 25%','#29825d'),('总税费','15.75','当前10.75 + 递延5','#22637b')],
 '多扣税折旧20：当前税减少5、递延税增加5；现金付12另按税余额滚动核对。')
diagram('f1-forecast-bridge.svg','澄河2027分析底稿：销售增长仍需融资','单位：万元；销售550；未叠加租赁/股酬/养老金；付息列经营为分析口径',[
 ('经营现金','86.5','NI + Dep - NWC - 旧税','#224a73'),('融资前现金','89.5','按经营与分派推算','#22637b'),('年末借款','40.5','最低现金130 - 89.5','#9b6032'),('期末勾稽','530 = 530','负债266.5 + 权益263.5','#29825d')],
 '借款发生在年末，本年利息固定15；下一年利息、年中缺口与债务期限须另建模。')
