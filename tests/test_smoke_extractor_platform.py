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


def linux_only_hard_failure(text):
    """Reject Linux-only checks unless the same preflight rebuilds first."""
    lines = [line.split('#', 1)[0].strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if 'tools/linux64/extractor' not in line or 'tools/osx64/extractor' in line:
            continue
        block = [line]
        if line.startswith('if ') and 'fi' not in line.split():
            for following in lines[index + 1:]:
                if following == 'fi':
                    break
                block.append(following)
        joined = '\n'.join(block)
        rebuild = joined.find('bash scripts/create-extractor-pack.sh')
        fail = joined.find('exit ')
        if rebuild < 0 or (fail >= 0 and fail < rebuild):
            return True
    return False


class AggregatePreflightContract(unittest.TestCase):
    def test_no_linux_only_hard_failure(self):
        scripts = [ROOT / 'scripts/m3-smoke.sh', ROOT / 'scripts/m4-smoke.sh',
                   *sorted((ROOT / 'scripts').glob('m4-*-smoke.sh'))]
        for script in scripts:
            with self.subTest(script=script.name):
                self.assertFalse(linux_only_hard_failure(script.read_text()), script.name)
        for name in ('models-fs-popen-smoke.py', 'models-local-helper-smoke.py',
                     'staged-routing-controls.py'):
            with self.subTest(script=name):
                self.assertNotIn('tools/linux64/extractor', (ROOT / 'scripts' / name).read_text())

    def test_rejects_linux_only_failure_control(self):
        mutant = '''if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
  echo "missing" >&2
  exit 1
fi'''
        self.assertTrue(linux_only_hard_failure(mutant))
        self.assertTrue(linux_only_hard_failure(mutant + '\nbash scripts/create-extractor-pack.sh'))
        self.assertTrue(linux_only_hard_failure(mutant.replace('  exit 1',
                        '  # bash scripts/create-extractor-pack.sh\n  exit 1')))
        self.assertTrue(linux_only_hard_failure(mutant.replace('  exit 1',
                        '  exit 1\n  bash scripts/create-extractor-pack.sh')))
        self.assertFalse(linux_only_hard_failure(mutant.replace('  exit 1', '  bash scripts/create-extractor-pack.sh')))


if __name__ == '__main__':
    unittest.main()
