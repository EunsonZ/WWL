"""Direct stationarity and coordinate-step oracle, no implementation import."""
import json
import sys
from fractions import Fraction as F


def matrix(raw):return [[F(x) for x in row] for row in raw]


if __name__ == '__main__':
    got=json.load(sys.stdin)
    assert len(got['scalar'])==2
    for row,expected_scale in zip(got['scalar'],(F(100),F(10))):
        scale=F(row['scale']);assert scale==expected_scale
        raw=F(row['untransformed_coefficient'])
        proper=F(row['preserved_coefficient'])
        penalty=F(row['transformed_penalty'])
        assert penalty==scale*scale
        # Differentiate each original scalar objective directly; both curvatures positive.
        assert scale*(scale*raw-1)+raw == 0
        assert scale*(scale*proper-1)+penalty*proper == 0
        assert F(row['untransformed_prediction'])==scale*raw!=F(1,2)
        assert F(row['preserved_prediction'])==scale*proper==F(1,2)
        # Independently compare objectives at corresponding nonoptimal coordinates.
        for v in (F(-1),F(0),F(1,3)):
            w=scale*v
            assert (w-1)**2+w*w==(scale*v-1)**2+penalty*v*v
    assert matrix(got['hessian_v'])==[[F(1),F(0)],[F(0),F(1)]]
    assert matrix(got['dd_transpose'])==[[F(1),F(0)],[F(0),F(1,100)]]
    # Update in v directly from L(Dv)=1/2(v1^2+v2^2), then map to w.
    v_initial=[F(1),F(10)];eta=F(1,100)
    v_next=[x-eta*x for x in v_initial]
    mapped=[v_next[0],v_next[1]/10]
    assert [F(x) for x in got['mapped_v_step']]==mapped==[F(99,100),F(99,100)]
    assert [F(x) for x in got['ordinary_w_step']]==[F(99,100),F(0)]
    print('PASS: changed/preserved objectives, exact scale square, Hessian, and distinct trajectories')
