"""Known-prior binary label shift; exact arithmetic, no network or file writes."""
import json
from fractions import Fraction as F
from pathlib import Path


def calculate(config):
    ps, pt = F(config['source_prior']), F(config['target_prior'])
    t, f = F(config['tpr']), F(config['fpr'])
    if not (0 < ps < 1 and 0 < pt < 1 and 0 < t < 1 and 0 < f < 1):
        raise ValueError('This finite example requires interior priors and rates.')
    ratio = (pt / (1 - pt)) / (ps / (1 - ps))
    result = {}
    for name, positive, negative in [('alert', t, f), ('no_alert', 1-t, 1-f)]:
        source_odds = positive / negative * ps / (1-ps)
        target_odds = source_odds * ratio
        result[name] = {'source': str(source_odds/(1+source_odds)),
                        'target': str(target_odds/(1+target_odds))}
    result['auc'] = str((1+t-f)/2)
    changed_f = F(config['changed_target_fpr'])
    if not 0 < changed_f < 1:
        raise ValueError('Changed FPR must be interior.')
    result['changed_fpr_alert'] = str(t*pt/(t*pt+changed_f*(1-pt)))
    return result


if __name__ == '__main__':
    data = json.loads(Path(__file__).with_name('label_shift_inputs.json').read_text())
    print(json.dumps(calculate(data), ensure_ascii=False, indent=2))
