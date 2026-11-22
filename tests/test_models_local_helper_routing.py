"""Exercise routing-receipt retention through the shipped smoke entrypoint."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('helper_routing_smoke', ROOT / 'scripts/models-local-helper-smoke.py')
assert spec is not None and spec.loader is not None
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class StopAfterFinalize(Exception):
    pass


class RoutingRetentionTests(unittest.TestCase):
    def run_smoke(self, failure):
        with tempfile.TemporaryDirectory(prefix='helper-routing-test-') as tmp:
            tmp = Path(tmp)
            evidence = tmp / 'evidence'
            pack = tmp / 'pack'
            for platform in ('linux64', 'osx64'):
                extractor = pack / 'tools' / platform / 'extractor'
                extractor.parent.mkdir(parents=True)
                extractor.touch()
            captured = {}
            stdout = io.StringIO()

            def command(*args):
                if args[1:3] == ('database', 'init'):
                    Path(args[3]).mkdir(parents=True)
                elif args[1:3] == ('database', 'index-files'):
                    db = Path(args[3])
                    source = Path(next(str(x).split('=', 1)[1] for x in args if str(x).startswith('--working-dir=')))
                    files = sorted(source.glob('*.uc'))
                    self.assertEqual({p.name for p in files}, set(smoke.ORACLE['inputs']))
                    self.assertEqual(set(source.iterdir()), set(files), 'metadata was placed in indexed source')
                    decisions = [{'path': str(p), 'classification': 'plain', 'status': 'plain_route_selected'} for p in files]
                    if failure == 'validation':
                        decisions[0]['status'] = 'bad-status'
                    data = {'decisions': decisions, 'duplicate_input_count': 0, 'excluded_count': 0}
                    raw = (json.dumps(data, indent=3) + '\n \n').encode()
                    captured['raw'] = raw
                    receipt = db / 'trap/ucode/routing.json'
                    receipt.parent.mkdir(parents=True)
                    receipt.write_bytes(raw)
                    if failure == 'index':
                        raise SystemExit('injected indexing failure')
                elif args[1:3] == ('database', 'finalize'):
                    captured['finalize_reached'] = True
                    receipt = evidence / 'routing.json'
                    self.assertTrue(receipt.is_file(), 'receipt missing before finalize')
                    self.assertEqual(receipt.read_bytes(), captured['raw'], 'receipt bytes changed before finalize')
                    shutil.rmtree(Path(args[3]) / 'trap')
                    if failure == 'finalize':
                        raise SystemExit('injected finalize failure')
                elif args[1:3] == ('query', 'run'):
                    raise StopAfterFinalize()
                else:
                    raise AssertionError(f'unexpected command: {args}')
                return ''

            with mock.patch.object(smoke, 'PACK', pack), \
                 mock.patch.object(smoke.shutil, 'which', return_value='/fake/codeql'), \
                 mock.patch.object(smoke, 'command', side_effect=command), \
                 mock.patch.dict(os.environ, {'CODEQL_UCODE_HELPER_EVIDENCE_DIR': str(evidence)}), \
                 contextlib.redirect_stdout(stdout):
                if failure is None:
                    with self.assertRaises(StopAfterFinalize):
                        smoke.main()
                else:
                    message = {'index': 'injected indexing failure',
                               'validation': 'unexpected routing decision',
                               'finalize': 'injected finalize failure'}[failure]
                    with self.assertRaisesRegex(SystemExit, message):
                        smoke.main()

            receipt = evidence / 'routing.json'
            self.assertTrue(receipt.is_file(), 'raw receipt not retained')
            self.assertEqual(receipt.read_bytes(), captured['raw'])
            self.assertIn(str(receipt), stdout.getvalue())
            self.assertIn(hashlib.sha256(captured['raw']).hexdigest(), stdout.getvalue())
            self.assertEqual(bool(captured.get('finalize_reached')), failure in (None, 'finalize'))

    def test_receipt_survives_successful_finalize(self):
        self.run_smoke(None)

    def test_receipt_survives_invalid_routing(self):
        self.run_smoke('validation')

    def test_receipt_survives_failed_index_when_emitted(self):
        self.run_smoke('index')

    def test_receipt_survives_failed_finalize(self):
        self.run_smoke('finalize')


if __name__ == '__main__':
    unittest.main()
