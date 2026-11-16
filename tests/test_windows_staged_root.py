"""Static guard for Windows root transport; this does not execute cmd.exe."""
from pathlib import Path
import unittest


WRAPPER = Path(__file__).resolve().parents[1] / 'tools/index-files.cmd'


class WindowsStagedRoot(unittest.TestCase):
    def test_wrapper_uses_static_opt_in_flag_without_expanding_root_value(self):
        wrapper = WRAPPER.read_text()
        before, staged = wrapper.split(':staged', 1)
        self.assertIn('if defined CODEQL_UCODE_STAGED_ROOT goto staged', before)
        self.assertNotIn('--staged-root', before)
        self.assertEqual(staged.count('--staged-root-from-env'), 1)
        self.assertIn('"%CODEQL_EXTRACTOR_UCODE_ROOT%\\tools\\win64\\extractor.exe" extract', staged)
        self.assertIn('exit /b %ERRORLEVEL%', staged)

    def test_wrapper_never_interpolates_staged_root(self):
        wrapper = WRAPPER.read_text()
        # cmd variable names are case-insensitive; substitution/substring
        # modifiers also interpolate the value.  A bare "if defined" is safe.
        for delimiter in ('%', '!'):
            with self.subTest(delimiter=delimiter):
                self.assertNotRegex(
                    wrapper,
                    rf'(?i){delimiter}CODEQL_UCODE_STAGED_ROOT(?::[^{delimiter}\r\n]*)?{delimiter}',
                    'the staged root must only be passed through the environment',
                )


if __name__ == '__main__':
    unittest.main()
