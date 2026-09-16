import tempfile, unittest
from pathlib import Path
from check_mirrors import check

class MirrorTests(unittest.TestCase):
    def test_teaching_marker_is_not_a_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'manual.md').write_text('````markdown\n<!-- code-sync: ./missing.py -->\n```python\npass\n```\n````\n')
            self.assertEqual(check(root),{'checked':0,'missing':[],'mismatched':[],'unparsed':[]})
    def test_active_mismatch_and_missing_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'example.py').write_text('print(1)\n')
            (root/'note.md').write_text('<!-- code-sync: ./example.py -->\n```python\nprint(2)\n```\n<!-- code-sync: ./absent.py -->\n```python\npass\n```\n')
            r=check(root);self.assertEqual(r['checked'],1);self.assertEqual(len(r['mismatched']),1);self.assertEqual(len(r['missing']),1)
    def test_matching_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'a.py').write_text('pass\n')
            (root/'n.md').write_text('<!-- code-sync: ./a.py -->\n```python\npass\n```\n')
            r=check(root);self.assertEqual(r['checked'],1);self.assertFalse(r['mismatched'])
if __name__=='__main__':unittest.main()
