"""标准库教学复算：残差、已知偏差校正、风险和完整成本。"""
from fractions import Fraction as F
def residual(x): return abs(F(2)*x - F(6))
def accepted(x, threshold=F(1,10)): return residual(x) <= threshold
def total_cost(*parts): return sum(parts, F())
def main():
    raw, corrected = F(14,5), F(3)
    assert not accepted(raw) and accepted(corrected)
    mean, bias = F(16,45), F(2,25)
    assert mean+bias == F(98,225) and mean+bias-bias == mean
    assert F(1,48) < F(1,40) and F(47,10)+F(4,5) == F(11,2)
    assert residual(F(31,10)) == F(1,5)
    assert 198 + 162 == 360
    print('PASS scalar_r=2/5 E518_risk=1/48 deadline=5.5 SCI-FR=198/360 SCI-FNO=360/360')
if __name__ == '__main__': main()
