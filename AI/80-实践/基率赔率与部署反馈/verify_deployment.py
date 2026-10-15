"""Two-point enumeration oracle; does not import deployment.py.

Checks its JSON stdout for the documented fixed inputs. Risk coefficients are
recovered from exact point evaluations, rather than copied from the formula.
"""
import json
import sys
from fractions import Fraction as F


def outcomes(theta):
    return [theta/2+F(1,4)+theta*u for u in (-1,1)]


def risk_by_enumeration(theta):
    return sum((theta-z)**2 for z in outcomes(theta))/2


if __name__ == '__main__':
    got = json.load(sys.stdin)
    sequence = [F(x) for x in got['trajectory']]
    assert len(sequence) == 11 and sequence[0] == 0
    for n in range(11):
        assert sequence[n] == F(1,2)*(1-F(1,2)**n)
        assert all(0 <= z <= 1 for z in outcomes(sequence[n]))
        if n:
            assert sequence[n] == sum(outcomes(sequence[n-1]))/2
    stable = F(got['stable'])
    assert stable == sum(outcomes(stable))/2 == F(1,2)
    # Recover the quadratic via the two-point loss at theta=0, 1/4, 1/2.
    c = risk_by_enumeration(F(0))
    r_quarter, r_half = risk_by_enumeration(F(1,4)), risk_by_enumeration(F(1,2))
    a = 8*(r_half-2*r_quarter+c)
    b = 4*(r_quarter-c)-a/4
    assert a > 0
    optimum = -b/(2*a)
    assert 0 <= optimum <= F(1,2)
    assert F(got['optimal']) == optimum == F(1,10)
    assert F(got['stable_risk']) == risk_by_enumeration(stable) == F(1,4)
    assert F(got['optimal_risk']) == risk_by_enumeration(optimum) == F(1,20)
    assert F(got['retrain_from_optimal']) == sum(outcomes(optimum))/2 == F(3,10)
    fixed = [F(3,20), F(7,20)]
    fixed_mean = sum(fixed)/2
    assert F(got['fixed_stable']) == F(got['fixed_optimal']) == fixed_mean == F(1,4)
    assert F(got['fixed_risk']) == sum((fixed_mean-z)**2 for z in fixed)/2 == F(1,100)
    print('PASS: 10 steps, exact two-point risks, quadratic optimum, fixed-distribution control')
