"""Count-table oracle: does not import the odds implementation.

Feed label_shift.py stdout through stdin. Oracle derives both posteriors and
pairwise AUC directly from integer contingency tables, counting ties by half.
"""
import json
import sys
from fractions import Fraction as F


def from_counts(tp, fp, fn, tn):
    positive, negative = tp+fn, fp+tn
    return {'alert': F(tp, tp+fp), 'no_alert': F(fn, fn+tn),
            'auc': F(2*tp*tn+tp*fp+fn*tn, 2*positive*negative)}


if __name__ == '__main__':
    got = json.load(sys.stdin)
    source = from_counts(90, 1, 10, 99)
    target = from_counts(900, 9990, 100, 989010)
    failure = from_counts(900, 19980, 100, 979020)
    for branch in ('alert', 'no_alert'):
        assert F(got[branch]['source']) == source[branch], branch
        assert F(got[branch]['target']) == target[branch], branch
    assert F(got['auc']) == source['auc'] == target['auc'] == F(189,200)
    assert F(got['changed_fpr_alert']) == failure['alert'] == F(5,116)
    assert failure['alert'] != target['alert']
    print('PASS: both posterior branches, pairwise AUC, and changed-FPR counterexample')
