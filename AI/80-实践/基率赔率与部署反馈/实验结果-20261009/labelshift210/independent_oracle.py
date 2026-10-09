"""Direct probability masses and pair enumeration; no odds code imported."""
from fractions import Fraction as F
from pathlib import Path
import json

got=json.loads(Path('output.json').read_text())
rates={1:{1:F(9,10),0:F(1,10)},0:{1:F(1,100),0:F(99,100)}}
expected={}
for label,prior in [('source',F(1,2)),('target',F(1,1000))]:
    for alert,name in [(1,'alert'),(0,'no_alert')]:
        joint_positive=prior*rates[1][alert]
        joint_negative=(1-prior)*rates[0][alert]
        expected.setdefault(name,{})[label]=str(joint_positive/(joint_positive+joint_negative))
auc=F(0)
for positive_score in (0,1):
    for negative_score in (0,1):
        credit=F(positive_score>negative_score)+F(positive_score==negative_score,2)
        auc+=rates[1][positive_score]*rates[0][negative_score]*credit
expected['auc']=str(auc)
expected['changed_fpr_alert']=str(F(9,10000)/(F(9,10000)+F(999,50000)))
assert got==expected
Path('independent_expected.json').write_text(json.dumps(expected,indent=2)+'\n')
print('PASS: both posterior branches, four pairwise rank/tie outcomes, and changed-FPR mass')
