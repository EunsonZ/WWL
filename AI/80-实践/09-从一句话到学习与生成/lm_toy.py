"""A pure-stdlib, deliberately limited position-conditional next-token model."""
import math
import unittest

IGNORE_INDEX = -100
VOCAB = ("BOS", "我", "爱", "蓝", "猫", "EOS", "PAD")

def require_finite(value, name):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")

def shift_targets(tokens):
    if len(tokens) < 2: raise ValueError("need BOS plus one target")
    return tokens[:-1], tokens[1:]

def softmax(logits):
    for value in logits: require_finite(value, "logit")
    peak = max(logits); weights = [math.exp(x - peak) for x in logits]
    return [x / sum(weights) for x in weights]

class PositionSoftmax:
    """Positions and one shared vocabulary bias; intentionally no attention or token lookup."""
    def __init__(self, max_positions, vocab_size=len(VOCAB)):
        self.max_positions, self.vocab_size = max_positions, vocab_size
        self.position_logits = [[0.0] * vocab_size for _ in range(max_positions)]
        self.shared_bias = [0.0] * vocab_size
    def probabilities(self, position):
        if not 0 <= position < self.max_positions: raise ValueError("position out of range")
        return softmax([a + b for a, b in zip(self.position_logits[position], self.shared_bias)])
    def loss_and_gradient(self, labels):
        if len(labels) > self.max_positions: raise ValueError("label length exceeds positions")
        grad_pos = [[0.0] * self.vocab_size for _ in range(self.max_positions)]
        grad_bias = [0.0] * self.vocab_size; total = 0.0; count = 0
        for position, label in enumerate(labels):
            if label == IGNORE_INDEX: continue
            if isinstance(label, bool) or not isinstance(label, int) or not 0 <= label < self.vocab_size:
                raise ValueError("label must be vocab index or ignore_index")
            probs = self.probabilities(position); total -= math.log(probs[label]); count += 1
            for token, probability in enumerate(probs):
                delta = probability - (token == label)
                grad_pos[position][token] += delta; grad_bias[token] += delta
        if count == 0: raise ValueError("zero valid targets: do not divide by zero")
        return total / count, [[x / count for x in row] for row in grad_pos], [x / count for x in grad_bias], count
    def sgd_step(self, labels, learning_rate):
        require_finite(learning_rate, "learning_rate")
        if learning_rate <= 0: raise ValueError("learning_rate must be positive")
        loss, grad_pos, grad_bias, count = self.loss_and_gradient(labels)
        for p in range(self.max_positions):
            for v in range(self.vocab_size): self.position_logits[p][v] -= learning_rate * grad_pos[p][v]
        for v in range(self.vocab_size): self.shared_bias[v] -= learning_rate * grad_bias[v]
        return loss, count, grad_pos, grad_bias
    def generate_greedy(self, prefix, eos_id, max_new_tokens):
        if not prefix: raise ValueError("prefix must be nonempty")
        result = list(prefix)
        for _ in range(max_new_tokens):
            position = len(result) - 1
            if position >= self.max_positions: raise ValueError("generation exceeds positions")
            next_id = max(range(self.vocab_size), key=lambda v: self.probabilities(position)[v])
            result.append(next_id)
            if next_id == eos_id: return result
        return result

def causal_allows(query, key): return key <= query
def padding_allows(is_padding_key): return not is_padding_key
def document_allows(query_document, key_document): return query_document == key_document

class LmToyTests(unittest.TestCase):
    def test_shift_firstanswer_and_eos(self):
        inputs, labels = shift_targets([0, 1, 2, 3, 4, 5])
        self.assertEqual(inputs, [0, 1, 2, 3, 4]); self.assertEqual(labels[0], 1); self.assertEqual(labels[-1], 5)
    def test_ignore_is_accepted_and_invalid_interfaces_rejected(self):
        model = PositionSoftmax(2); loss, _, _, count = model.loss_and_gradient([1, IGNORE_INDEX])
        self.assertEqual(count, 1); self.assertTrue(math.isfinite(loss))
        with self.assertRaisesRegex(ValueError, "zero valid"): model.loss_and_gradient([IGNORE_INDEX])
        with self.assertRaisesRegex(ValueError, "vocab"): model.loss_and_gradient([99])
        with self.assertRaisesRegex(ValueError, "vocab"): model.loss_and_gradient([True])
        with self.assertRaisesRegex(ValueError, "length"): model.loss_and_gradient([1, 2, 3])
        with self.assertRaisesRegex(ValueError, "finite"): model.sgd_step([1], float("nan"))
    def test_probability_loss_gradient_shared_bias_and_update(self):
        model = PositionSoftmax(5); labels = [1, 2, 3, 4, 5]
        before = model.probabilities(0)[1]; loss0, _, _, _ = model.loss_and_gradient(labels)
        _, _, grad_pos, grad_bias = model.sgd_step(labels, 1.0)
        self.assertAlmostEqual(grad_bias[1], sum(row[1] for row in grad_pos))
        self.assertGreater(model.probabilities(0)[1], before)
        loss1, _, _, _ = model.loss_and_gradient(labels); self.assertLess(loss1, loss0)
    def test_greedy_generation_uses_own_prefix_and_stops_at_eos(self):
        model = PositionSoftmax(5); loss0, _, _, _ = model.loss_and_gradient([1, 2, 3, 4, 5])
        model.sgd_step([1, 2, 3, 4, 5], 8.0)
        loss1, _, _, _ = model.loss_and_gradient([1, 2, 3, 4, 5]); self.assertLess(loss1, loss0)
        self.assertEqual(model.generate_greedy([0], 5, 8), [0, 1, 2, 3, 4, 5])
    def test_position_changes_prediction_for_same_input_token(self):
        model = PositionSoftmax(2); model.position_logits[0][1] = 4; model.position_logits[1][4] = 4
        self.assertEqual(max(range(7), key=lambda v: model.probabilities(0)[v]), 1)
        self.assertEqual(max(range(7), key=lambda v: model.probabilities(1)[v]), 4)
    def test_mask_predicates_are_only_responsibility_examples(self):
        self.assertFalse(causal_allows(2, 3)); self.assertFalse(padding_allows(True)); self.assertFalse(document_allows("A", "B"))

if __name__ == "__main__": unittest.main()
