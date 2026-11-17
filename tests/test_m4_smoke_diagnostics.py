"""Exercise each standalone M4 smoke against captured recovered semantic rows."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tests/data/m4-diagnostics'
DIGESTS = {
    'ssa/flow.csv': 'a0ab60989c5c497797bcc946626a67fa6b18c1eee382e9dca19cb9fc83fd605a',
    'ssa/ssa.csv': '67ca654ce7fa78446541d964cba553a27ee6f09b2199e4fa82d87b6026179f33',
    'ssa/ssaSys.csv': 'ef1e0c688070717d8334058d7521bc5e72e331e43dfa3259b22b417240dbc76b',
    'ssa/writes.csv': 'c36a8c61d45a7a4fdb5da4f9176c0e6051a239b577d80e59039e7ac62535d0e5',
    'store/store-read-composition.csv': '2643e22d5efe59a51a98714c20bbae6c29800628f1f6dc53f7dc7499ca1fce5e',
    'store/store-read-semantics.csv': 'c4cc4c946d044e0dd0fda52628e4c05d108a90e81f36068c721796ff3b0a8f02',
    'store/store-read.csv.gz': '6882f11f6f186e420c1826e0475b8990dbaf23c4102ad6761c66ba75e2bd9f4e',
    'ssa/baseline-SuccessfullyExtractedFiles.json': '046402d0c8b0306ba704f4ab429edbc83323aa4c5d00f73e619aec033f4df774',
    'ssa/malformed-SuccessfullyExtractedFiles.json': '25cda2c939295a5f809d7f1a5e70fad71dc23a982ff72e37d69c6c5bb0ada52a',
    'store/baseline-SuccessfullyExtractedFiles.json': 'fc0ccca15fce109af982016ee1a759607a127ac1007035e702740ed6a41b7abd',
    'store/malformed-SuccessfullyExtractedFiles.json': '4a92c76887661282bb0a6325ab9ff1327e34e78f0a9cbf9de66a3c3ec8cec6ec',
    'ssa/baseline-ExtractionErrors.json': '2c38be0a7d1935f63300ceccb92fd50f5bb76b829bcd0bac782393521a7665fc',
    'store/baseline-ExtractionErrors.json': '2c38be0a7d1935f63300ceccb92fd50f5bb76b829bcd0bac782393521a7665fc',
    'ssa/malformed-ExtractionErrors.json': '550bcb344c8267aa1fe511530f857ea51908ca145bc7e60e77f320c46e03a0b2',
    'store/malformed-ExtractionErrors.json': '550bcb344c8267aa1fe511530f857ea51908ca145bc7e60e77f320c46e03a0b2',
}


def receipt(path):
    return [{'label': str(path), 'url': {'uri': path.as_uri(), 'startLine': 0,
            'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']


class M4SmokeDiagnostics(unittest.TestCase):
    def test_snapshot_digests(self):
        for name, digest in DIGESTS.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((DATA / name).read_bytes()).hexdigest(), digest)

    def run_smoke(self, name, variant, mutant=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name) / 'checkout'
        shutil.copytree(ROOT / 'scripts', root / 'scripts')
        shutil.copytree(ROOT / 'ql', root / 'ql')
        if mutant in ('errors', 'identity'):
            verifier = root / 'scripts/m4-smoke-diagnostics.py'
            text = verifier.read_text()
            old = 'if errors:' if mutant == 'errors' else 'if Counter(map(encode, success)) != Counter(map(encode, wanted)):'
            self.assertEqual(text.count(old), 1)
            verifier.write_text(text.replace(old, old.replace('if ', 'if False and ', 1)))
        if mutant in ('wrong-query', 'wrong-flags'):
            helper = root / 'scripts/m4-smoke-diagnostics.sh'
            text = helper.read_text()
            old, new = (('ql/src/diagnostics/', 'ql/src/extractor-smoke/') if mutant == 'wrong-query'
                        else ('--entities=url,string', '--entities=string'))
            self.assertEqual(text.count(old), 1)
            helper.write_text(text.replace(old, new))
        if mutant == 'wiring':
            script_name = 'm4-ssa-smoke.sh' if name == 'ssa' else 'm4-store-read-smoke.sh'
            script_path = root / 'scripts' / script_name
            lines = script_path.read_text().splitlines(keepends=True)
            self.assertEqual(sum(line.startswith('check_m4_extraction ') for line in lines), 1)
            script_path.write_text(''.join(line for line in lines if not line.startswith('check_m4_extraction ')))
        extractor = root / 'extractor-pack/tools/linux64/extractor'
        extractor.parent.mkdir(parents=True)
        extractor.touch(mode=0o755)
        binary = Path(directory.name) / 'bin'
        binary.mkdir()
        shutil.copy(ROOT / 'tests/m4_diagnostics_fake_codeql.py', binary / 'codeql')
        (binary / 'codeql').chmod(0o755)
        src = root / 'ql/test/extractor-smoke'
        targets = [src / 'ssa_neg', src / ('ssa_pos' if name == 'ssa' else 'usr/share/rpcd/ucode/luci')]
        if variant == 'recovered':
            targets[0].write_bytes(targets[0].read_bytes() + b'\nlet integrity_probe = ;\n')
        successes = [receipt(p) for p in targets]
        errors = []
        if variant == 'recovered':
            successes.pop(0)
            errors = [[{'label': 'parse error'}, 'parse error', 2]]
        elif variant == 'error_only':
            errors = [[{'label': 'parse error'}, 'parse error', 2]]
        elif variant.startswith('omit'):
            successes.pop(int(variant[-1]))
        elif variant.startswith('duplicate'):
            successes.append(successes[int(variant[-1])])
        elif variant.startswith('substitute'):
            index = int(variant[-1])
            successes[index] = receipt(src / ('ssa_pos' if name == 'store' else 'usr/share/rpcd/ucode/luci'))
        elif variant == 'wrong_root':
            successes[0] = receipt(Path(directory.name) / 'elsewhere/ssa_neg')
        elif variant == 'wrong_span':
            successes[0][0]['url']['startLine'] = 1
        elif variant == 'uri_mismatch':
            successes[0][0]['url']['uri'] = (src / 'ssa_pos').as_uri()
        elif variant == 'reordered':
            successes.reverse()
        success = {'#select': {'columns': [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}],
                              'tuples': successes}}
        error = {'#select': {'columns': [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}],
                             'tuples': errors}}
        if variant == 'bad_success_schema':
            success['#select']['columns'] = []
        if variant == 'bad_error_schema':
            error['#select']['tuples'] = None
        if variant == 'bad_json':
            success = '{'
        if variant in ('valid', 'recovered'):
            leg = 'baseline' if variant == 'valid' else 'malformed'
            success = json.loads((DATA / name / f'{leg}-SuccessfullyExtractedFiles.json').read_text().replace('__SOURCE_ROOT__', str(src)))
            error = json.loads((DATA / name / f'{leg}-ExtractionErrors.json').read_text().replace('__SOURCE_ROOT__', str(src)))
        diagnostics = Path(directory.name) / 'diagnostics.json'
        diagnostics.write_text(json.dumps({'SuccessfullyExtractedFiles': success, 'ExtractionErrors': error}))
        env = os.environ.copy()
        env.update(PATH=str(binary) + os.pathsep + env['PATH'], CODEQL_UCODE_SMOKE_PACKS_READY=str(root),
                   M4_TEST_ROOT=str(root), M4_TEST_DATA=str(DATA / name), M4_TEST_DIAGNOSTICS=str(diagnostics),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE=str(sys.flags.optimize))
        script = root / 'scripts' / ('m4-ssa-smoke.sh' if name == 'ssa' else 'm4-store-read-smoke.sh')
        return subprocess.run(['bash', str(script)], cwd=root, env=env, text=True, capture_output=True)

    def test_recovered_semantics_cannot_hide_parse_error(self):
        for name in ('ssa', 'store'):
            with self.subTest(smoke=name):
                result = self.run_smoke(name, 'recovered')
                self.assertNotIn('fake codeql rejected', result.stderr, result.stderr)
                self.assertNotEqual(result.returncode, 0, result.stdout[-1000:])
                self.assertIn('expected zero extraction errors', result.stderr)
                self.assertIn('expected exact successful-file multiset', result.stderr)

    def test_isolated_guard_and_wiring_mutants_reveal_false_greens(self):
        # Each input satisfies the other guard, so neither can mask the mutation.
        for name in ('ssa', 'store'):
            for mutant, variant in (('errors', 'error_only'), ('identity', 'omit0'),
                                    ('wiring', 'recovered')):
                with self.subTest(smoke=name, mutant=mutant):
                    result = self.run_smoke(name, variant, mutant=mutant)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('smoke passed', result.stdout)

    def test_fake_cli_rejects_bad_diagnostic_wiring(self):
        for name in ('ssa', 'store'):
            for mutant in ('wrong-query', 'wrong-flags'):
                with self.subTest(smoke=name, mutant=mutant):
                    result = self.run_smoke(name, 'valid', mutant=mutant)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('fake codeql rejected', result.stderr)

    def test_independent_guards_and_valid_baseline(self):
        cases = {
            'valid': None, 'reordered': None,
            'error_only': 'expected zero extraction errors',
            'omit0': 'expected exact successful-file multiset', 'omit1': 'expected exact successful-file multiset',
            'duplicate0': 'expected exact successful-file multiset', 'duplicate1': 'expected exact successful-file multiset',
            'substitute0': 'expected exact successful-file multiset', 'substitute1': 'expected exact successful-file multiset',
            'wrong_root': 'expected exact successful-file multiset', 'wrong_span': 'expected exact successful-file multiset',
            'uri_mismatch': 'expected exact successful-file multiset',
            'bad_success_schema': 'unexpected diagnostic schema', 'bad_error_schema': 'invalid diagnostic tuples',
            'bad_json': 'M4 extraction rejected',
        }
        for name in ('ssa', 'store'):
            for variant, reason in cases.items():
                with self.subTest(smoke=name, variant=variant):
                    result = self.run_smoke(name, variant)
                    self.assertNotIn('fake codeql rejected', result.stderr, result.stderr)
                    if reason is None:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn('M4 extraction accepted', result.stdout)
                    else:
                        self.assertNotEqual(result.returncode, 0, result.stdout[-1000:])
                        self.assertIn(reason, result.stderr)
                        if variant == 'error_only':
                            self.assertNotIn('expected exact successful-file multiset', result.stderr)
                        if variant.startswith(('omit', 'duplicate', 'substitute')):
                            self.assertNotIn('expected zero extraction errors', result.stderr)


if __name__ == '__main__':
    unittest.main()
