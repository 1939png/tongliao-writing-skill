"""Exercise length edges, literal anchors and the authored regression cases."""
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_rewrite', ROOT / 'scripts' / 'check_rewrite.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class RewriteChecks(unittest.TestCase):
    def test_exact_lower_and_upper_edges_pass(self):
        self.assertTrue(checker.evaluate('甲' * 100, '乙' * 85)['length_pass'])
        self.assertTrue(checker.evaluate('甲' * 100, '乙' * 115)['length_pass'])

    def test_outside_edges_fail(self):
        self.assertFalse(checker.evaluate('甲' * 100, '乙' * 84)['length_pass'])
        self.assertFalse(checker.evaluate('甲' * 100, '乙' * 116)['length_pass'])

    def test_whitespace_ignored_punctuation_counted(self):
        self.assertEqual(checker.count('甲， 乙\n丙\t。'), 5)

    def test_empty_source_is_invalid(self):
        with self.assertRaises(ValueError):
            checker.evaluate(' \n', '甲')

    def test_missing_anchor_in_rewrite_fails(self):
        result = checker.evaluate('约20人到访', '有20人到访', ['约20人'])
        self.assertFalse(result['literal_anchor_pass'])
        self.assertEqual(result['anchors_missing_from_rewrite'], ['约20人'])

    def test_anchor_not_present_in_source_fails(self):
        result = checker.evaluate('甲乙丙丁', '甲乙丙丁', ['戊'])
        self.assertFalse(result['literal_anchor_pass'])
        self.assertEqual(result['anchors_missing_from_source'], ['戊'])

    def test_authored_cases_fit_length_and_keep_literal_anchors(self):
        for folder in sorted((ROOT / 'tests' / 'cases').iterdir()):
            with self.subTest(case=folder.name):
                source = (folder / 'source.txt').read_text(encoding='utf-8')
                rewrite = (folder / 'rewrite.txt').read_text(encoding='utf-8')
                anchors = json.loads((folder / 'anchors.json').read_text(encoding='utf-8'))
                result = checker.evaluate(source, rewrite, anchors)
                self.assertTrue(result['length_pass'])
                self.assertTrue(result['literal_anchor_pass'])


if __name__ == '__main__':
    unittest.main()
