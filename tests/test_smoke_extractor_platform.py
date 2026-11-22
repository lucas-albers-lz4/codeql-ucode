import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/smoke-extractor-platform.sh'


class SmokeExtractorPlatform(unittest.TestCase):
    def check(self, system, pack):
        return subprocess.run(
            ['bash', '-c', 'source "$1"; platform="$(smoke_extractor_platform "$2")" || exit; '
             '[[ -x "$3/tools/$platform/extractor" ]]', 'bash', str(HELPER), system, str(pack)],
            text=True, capture_output=True)

    def test_native_present_missing_and_unsupported(self):
        with tempfile.TemporaryDirectory() as temp:
            pack = pathlib.Path(temp)
            for system, platform in [('darwin24', 'osx64'), ('linux-gnu', 'linux64')]:
                with self.subTest(system=system):
                    self.assertNotEqual(self.check(system, pack).returncode, 0)
                    binary = pack / 'tools' / platform / 'extractor'
                    binary.parent.mkdir(parents=True)
                    binary.write_text('#!/bin/sh\n')
                    binary.chmod(0o755)
                    self.assertEqual(self.check(system, pack).returncode, 0)
                    binary.unlink()
            result = self.check('unsupported', pack)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unsupported OS: unsupported', result.stderr)


if __name__ == '__main__':
    unittest.main()
