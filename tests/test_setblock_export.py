"""CLI contract controls. Inputs below are synthetic, not CodeQL receipts."""
import csv
import hashlib
import json
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/export_setblock_detect.py'
FIXTURES = ROOT / 'tests/fixtures'
SOURCE = ROOT / 'ql/test/extractor-smoke'
HEADER = ['observation_kind', 'method', 'sink_kind', 'command', 'source_path',
          'start_line', 'start_column', 'end_line', 'end_column']
ROW = ['callback_body_call', 'setBlockDetect', 'system', '/sbin/block detect > /etc/config/fstab',
       'usr/share/rpcd/ucode/luci', '532', '21', '532', '68']


def encode_csv(rows):
    s = io.StringIO(newline='')
    csv.writer(s, lineterminator='\n').writerows(rows)
    return s.getvalue().encode()


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.source = SOURCE
        self.files = {
            'csv': encode_csv([HEADER, ROW]),
            # Shape observed in CodeQL 2.27.4; constructed here, not a run receipt.
            'extracted': ('"f","col1"\n"' + str(SOURCE / ROW[4]) + '",""\n').encode(),
            'errors': b'"error","col1","col2"\n',
            'lock': (FIXTURES / 'setblock-lock-v1.json').read_bytes(),
        }

    def run_cli(self, omit=None):
        for name, data in self.files.items():
            if name != omit:
                (self.dir / name).write_bytes(data)
        cmd = [sys.executable, '-B', str(CLI), '--csv', str(self.dir / 'csv'),
               '--extracted', str(self.dir / 'extracted'), '--errors', str(self.dir / 'errors'),
               '--source-root', str(self.source), '--lock', str(self.dir / 'lock')]
        return subprocess.run(cmd, capture_output=True)

    def test_exact_synthetic_export(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout, (FIXTURES / 'setblock-typed-v1.json').read_bytes())
        self.assertEqual(result.stderr, b'')

    def test_table_rejections(self):
        cases = [encode_csv([HEADER]), encode_csv([HEADER, ROW, ROW]),
                 encode_csv([HEADER, ROW, ['other'] * 9]),
                 encode_csv([HEADER, ROW[:-1] + ['69']]),
                 encode_csv([HEADER[:-1], ROW]), b'"unterminated', b'\xff']
        for value in cases:
            with self.subTest(value=value):
                self.files['csv'] = value
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertTrue(result.stderr)

    def test_source_and_lock_rejections(self):
        original = self.files['lock']
        for value in [b'{}', b'[]', b'{', b'\xff',
                      b'{"repos":{"luci":{"sha":"bad"}}}',
                      b'{"repos":{"luci":{"sha":"b2e0be4b46ec0fd43394c081fa7c50657af14011"}},"x":NaN}',
                      b'{"repos":{"luci":{"sha":"wrong","sha":"b2e0be4b46ec0fd43394c081fa7c50657af14011"}}}']:
            with self.subTest(lock=value):
                self.files['lock'] = value
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
        self.files['lock'] = original
        self.source = self.dir / 'source'
        path = self.source / ROW[4]
        self.files['extracted'] = encode_csv([['f', 'col1'], [str(path), '']])
        path.parent.mkdir(parents=True)
        path.write_bytes(b'wrong source')
        self.assertNotEqual(self.run_cli().returncode, 0)
        path.unlink()
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')

    def test_missing_files_and_arguments_fail_without_output(self):
        for name in self.files:
            with self.subTest(name=name):
                (self.dir / name).unlink(missing_ok=True)
                result = self.run_cli(omit=name)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
        result = subprocess.run([sys.executable, '-B', str(CLI)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')

    def test_determinism_and_raw_lock_identity(self):
        first = self.run_cli()
        second = self.run_cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.files['lock'] += b'\n'
        changed = self.run_cli()
        self.assertEqual(changed.returncode, 0, changed.stderr)
        expected = json.loads(first.stdout)
        expected[0]['corpus_revision'] = 'sha256:' + hashlib.sha256(self.files['lock']).hexdigest()
        self.assertEqual(json.loads(changed.stdout), expected)
        self.assertNotEqual(changed.stdout, first.stdout)

    def test_diagnostics_rejections(self):
        good = self.files.copy()
        path = str(SOURCE / ROW[4])
        cases = [
            ('extracted', encode_csv([['f', 'col1']])),
            ('extracted', encode_csv([['f', 'col1'], [path, ''], [path, '']])),
            ('extracted', encode_csv([['f', 'col1'], [path + '.other', '']])),
            ('extracted', encode_csv([['f', 'col1'], ['', path]])),
            ('extracted', encode_csv([['file', 'col1'], [path, '']])),
            ('extracted', b'"broken'), ('extracted', b'\xff'),
            ('errors', encode_csv([['error', 'col1', 'col2'], ['failure', '', '']])),
            ('errors', encode_csv([['error', 'col1']])), ('errors', b''),
        ]
        for name, data in cases:
            with self.subTest(name=name, data=data):
                self.files = good.copy()
                self.files[name] = data
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertTrue(result.stderr)
