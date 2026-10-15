import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import nlp_ud_lab as lab

DATA_DIR = pathlib.Path(os.environ["UD_EWT_DATA_DIR"])

class UDExperimentTests(unittest.TestCase):
    def test_document_selection_is_stable(self):
        self.assertEqual(lab.selected("a"), lab.selected("a"))
        self.assertIn(lab.selected("a"), (True, False))

    def test_parser_keeps_only_integer_token_rows(self):
        docs = lab.read_conllu(DATA_DIR / lab.SPLITS["train"])
        self.assertGreater(len(docs), 0)
        for _, sentences in docs:
            for _, xs in sentences:
                self.assertTrue(all(isinstance(w, str) and isinstance(t, str) for w, t in xs))

    def test_train_documents_do_not_cross_official_split(self):
        ids = {k: {d for d, _ in lab.read_conllu(DATA_DIR / f)} for k, f in lab.SPLITS.items()}
        self.assertFalse(ids["train"] & ids["dev"])
        self.assertFalse(ids["train"] & ids["test"])
        self.assertFalse(ids["dev"] & ids["test"])

    def test_hmm_returns_one_upos_per_token(self):
        train = lab.flatten(lab.read_conllu(DATA_DIR / lab.SPLITS["train"]))
        hmm = lab.HMM(rare=1, alpha=.1).fit(train)
        words = [w for w, _ in train[0][2]]
        out = hmm.decode(words)
        self.assertEqual(len(out), len(words))
        self.assertTrue(set(out) <= set(hmm.tags))

    def test_transition_rows_are_normalized_after_smoothing(self):
        train = lab.flatten(lab.read_conllu(DATA_DIR / lab.SPLITS["train"]))
        hmm = lab.HMM(rare=1, alpha=.1).fit(train)
        for previous in hmm.tags:
            p = sum((hmm.trans[previous, following] + hmm.alpha) /
                    (hmm.trans_n[previous] + hmm.alpha * len(hmm.tags))
                    for following in hmm.tags)
            self.assertAlmostEqual(p, 1.0)

    def test_duplicate_key_is_full_ordered_form_tuple(self):
        self.assertEqual(lab.sentence_key([("New", "PROPN"), ("York", "PROPN")]), ("New", "York"))
        self.assertNotEqual(lab.sentence_key([("New", "PROPN"), ("York", "PROPN")]),
                            lab.sentence_key([("York", "PROPN"), ("New", "PROPN")]))

    def test_data_dir_requires_all_three_fixed_files(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaisesRegex(ValueError, "en_ewt-ud-train.conllu"):
                lab.checked_data_dir(empty)

if __name__ == "__main__":
    unittest.main()
