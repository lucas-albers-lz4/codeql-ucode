import unittest
from unittest.mock import patch
from census import candidates, main


class LexicalCensusTest(unittest.TestCase):
    def test_multiline_copy_and_direct_read_are_both_candidates(self):
        text = 'let fd =\n popen("x");\nlet alias =\n fd;\nlet value = fd.read("all");'
        found = list(candidates(text))
        self.assertEqual([(x[0], x[1]) for x in found], [('fd', 1)])
        self.assertEqual([text[m.start():m.end()] for m in found[0][2]], ['=\n fd', '= fd'])

    def test_namespace_does_not_look_like_direct_popen(self):
        self.assertEqual(list(candidates('let fd = fs.popen("x");')), [])

    def test_nested_path_is_normalized_before_grep(self):
        with patch('census.git', side_effect=['/repo\n', '']) as git:
            main('/repo/nested')
        self.assertEqual(git.call_args_list[0].args, ('/repo/nested', 'rev-parse', '--show-toplevel'))
        self.assertEqual(git.call_args_list[1].args[0], '/repo')

    def test_comment_is_a_false_positive(self):
        self.assertEqual(len(list(candidates('// fd = popen("x")'))), 1)


if __name__ == '__main__':
    unittest.main()
