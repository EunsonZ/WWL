"""Scalar identities; imports no candidate or author's expected output."""
import json
from pathlib import Path

got = json.loads(Path('output.json').read_text())
expected=[]
for x in (-2,0,1):
    p,n=max(x,0),max(-x,0)
    expected.append(dict(x=x, hidden_original=[p,n], hidden_permuted=[n,p],
        original=p-n,permuted=p-n,parameter_mean=0,output_mean=x,
        aligned_parameter_mean=x,only_first_swapped=-x,
        only_first_parameter_mean=0,only_first_output_mean=0,
        scalar_relu=p,scalar_post_activation_recode=p,
        scalar_wrong_pre_activation_change=-n))
assert got=={'rows':expected}
Path('independent_expected.json').write_text(json.dumps({'rows':expected},indent=2)+'\n')
print('PASS: every output field agrees with independent scalar identities for x=-2,0,1')
