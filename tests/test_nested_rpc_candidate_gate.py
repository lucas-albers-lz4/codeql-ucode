import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

gate = load('release_gate', 'scripts/direct-rpc-release-gate.py')
verify = load('nested_verify', 'scripts/nested-rpc-shell-command-verify.py')

class CandidateGateTest(unittest.TestCase):
    def test_default_skips_candidate_even_when_files_absent(self):
        oracle, summary = {}, {}
        self.assertIsNone(gate.nested_oracle(False, Path('/missing'), oracle))
        with mock.patch.object(gate, 'run_nested_rpc_regression', side_effect=AssertionError('must not run')):
            gate.add_nested_regression(False, None, Path('/missing'), {}, None, summary)
        self.assertEqual(oracle, {})
        self.assertEqual(summary, {})

    def test_opt_in_validates_and_runs_candidate_and_propagates_failure(self):
        oracle, summary = {}, {}
        expected = gate.nested_oracle(True, ROOT, oracle)
        self.assertEqual(oracle['nested_rpc']['expectations'], expected)
        with mock.patch.object(gate, 'run_nested_rpc_regression', return_value={'tested': True}) as run:
            gate.add_nested_regression(True, None, ROOT, {}, expected, summary)
            run.assert_called_once_with(None, ROOT, {}, expected)
        self.assertEqual(summary['nested_rpc_explicit_regression'], {'tested': True})
        with mock.patch.object(gate, 'run_nested_rpc_regression', side_effect=RuntimeError('candidate failed')):
            with self.assertRaisesRegex(RuntimeError, 'candidate failed'):
                gate.add_nested_regression(True, None, ROOT, {}, expected, {})
        with self.assertRaises(FileNotFoundError):
            gate.nested_oracle(True, Path('/missing'), {})

    def test_workflow_invocations_keep_release_default(self):
        pr = (ROOT / '.github/workflows/direct-rpc-release-gate.yml').read_text()
        publish = (ROOT / '.github/workflows/publish-linux-release.yml').read_text()
        self.assertIn('python3 scripts/direct-rpc-release-gate.py --nested-rpc-candidate', pr)
        self.assertIn('python3 scripts/direct-rpc-release-gate.py\n', publish)
        self.assertNotIn('--nested-rpc-candidate', publish)

    def test_extraction_identity_rejects_same_suffix_wrong_root(self):
        stage = Path('/tmp/nested-identity/stage').resolve()
        wanted = {'usr/share/rpcd/ucode/a.uc': {}}
        row = lambda label: [[{'label': label}]]
        verify.verify_success_identities(row(str(stage / next(iter(wanted)))), stage, wanted)
        with self.assertRaisesRegex(AssertionError, 'successful-file identities differ'):
            verify.verify_success_identities(row('/tmp/other/stage/usr/share/rpcd/ucode/a.uc'), stage, wanted)

if __name__ == '__main__':
    unittest.main()
