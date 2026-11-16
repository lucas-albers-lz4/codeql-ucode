"""End-to-end routing checks against the built extractor binary."""
import json

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / 'extractor-pack/tools/linux64/extractor'
FIXTURE = ROOT / 'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci'


class StagedRouting(unittest.TestCase):
    def test_explicit_staged_root_extracts_selected_plugin(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            root = temp / 'ordinary-root'
            plugin = root / 'usr/share/rpcd/ucode/luci'
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(FIXTURE.read_bytes())
            inputs = temp / 'inputs'
            inputs.write_text(str(plugin) + '\n')
            cmd = [str(EXTRACTOR), 'extract', '--source-archive-dir', str(temp / 'archive'),
                   '--output-dir', str(temp / 'trap'), '--file-list', str(inputs),
                   '--staged-root', str(root)]
            result = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((temp / 'trap/routing.json').read_text())
            self.assertEqual(receipt['plain_count'], 1)
            self.assertEqual(receipt['excluded_count'], 0)
            decision, = receipt['decisions']
            self.assertEqual(decision['path'], str(plugin))
            self.assertEqual(decision['installed_path'], 'usr/share/rpcd/ucode/luci')
            self.assertEqual(decision['reason'], 'rpcd_raw_mode_full_path')
            self.assertEqual(len(list((temp / 'trap').rglob('luci.trap.gz'))), 1)

    def test_explicit_root_excludes_markers_and_canonical_escapes(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            root = temp / 'root'
            root.mkdir()
            outside = temp / 'outside/modules/pkg/root/usr/share/rpcd/ucode/luci'
            outside.parent.mkdir(parents=True)
            outside.write_text('// ordinary content\n')
            paths = [root / p for p in (
                'elsewhere/luci',
                'usr/share/rpcd/ucodeish/luci',
                'prefix/usr/share/rpcd/ucode/luci',
                'modules/pkg/root/usr/share/rpcd/ucode/luci',
                'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci',
            )]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('// ordinary content\n')
            escape = root / 'usr/share/rpcd/ucode/escape'
            escape.parent.mkdir(parents=True)
            escape.symlink_to(outside)
            inputs = temp / 'inputs'
            inputs.write_text('\n'.join(map(str, [*paths, outside, escape])) + '\n')
            result = subprocess.run([str(EXTRACTOR), 'extract', '--source-archive-dir',
                str(temp / 'archive'), '--output-dir', str(temp / 'trap'), '--file-list',
                str(inputs), '--staged-root', str(root)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((temp / 'trap/routing.json').read_text())
            self.assertEqual(receipt['plain_count'], 0)
            self.assertEqual(receipt['excluded_count'], 7)
            self.assertEqual([d['reason'] for d in receipt['decisions']],
                             ['no_ucode_route'] * 5 + ['outside_staged_root'] * 2)

    def test_staged_root_must_exist_and_be_a_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            inputs = temp / 'inputs'
            inputs.write_text('')
            for root in (temp / 'missing', inputs):
                result = subprocess.run([str(EXTRACTOR), 'extract', '--source-archive-dir',
                    str(temp / 'archive'), '--output-dir', str(temp / 'trap'), '--file-list',
                    str(inputs), '--staged-root', str(root)], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0, str(root))


if __name__ == '__main__':
    unittest.main()
