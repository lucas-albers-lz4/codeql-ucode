"""Static guard for Windows root transport; this does not execute cmd.exe."""
from pathlib import Path
import unittest


WRAPPER = Path(__file__).resolve().parents[1] / 'tools/index-files.cmd'


class WindowsStagedRoot(unittest.TestCase):
    def test_wrapper_uses_static_opt_in_flag_without_expanding_root_value(self):
        wrapper = WRAPPER.read_text()
        before, staged = wrapper.split(':staged', 1)
        self.assertIn('if defined CODEQL_UCODE_STAGED_ROOT goto staged', before)
        self.assertNotIn('%CODEQL_UCODE_STAGED_ROOT%', wrapper.upper())
        self.assertNotIn('--staged-root', before)
        self.assertEqual(staged.count('--staged-root-from-env'), 1)
        self.assertIn('"%CODEQL_EXTRACTOR_UCODE_ROOT%\\tools\\win64\\extractor.exe" extract', staged)
        self.assertIn('exit /b %ERRORLEVEL%', staged)


if __name__ == '__main__':
    unittest.main()
