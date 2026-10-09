"""Algebraic-value and period-table oracle; imports no aliasing implementation."""
import json
import math
import sys


def check(actual, expected):
    assert len(actual) == len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):
        assert math.isfinite(a) and abs(a-b) <= 1e-11, (i,a,b)


if __name__ == '__main__':
    data=json.load(sys.stdin)
    a=math.sqrt(2)/2
    check(data['low_first_eight'],[1,a,0,-a,-1,-a,0,a])
    check(data['high_first_eight'],[1,-a,0,a,-1,a,0,-a])
    check(data['low_downsampled'],[1,0,-1,0]*3)
    check(data['high_downsampled'],[1,0,-1,0]*3)
    check(data['gains'],[math.sqrt(2+math.sqrt(2))/2,math.sqrt(2-math.sqrt(2))/2,0])
    check(data['square_downsampled'],[1,1/4,1/4]*4)
    check(data['filter_square_downsampled'],[1,1/4,1/4]*4)
    check(data['square_filter_downsampled'],[1/2]*12)
    print('PASS: shared samples, gain radicals, and nonlinear/filter ordering')
