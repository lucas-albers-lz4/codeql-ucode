"""End-to-end routing checks against the built extractor binary."""
import json
import os

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
                'ql/test/extractor-smoke/luci',
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
            immediate = receipt['decisions'][5]
            self.assertEqual(immediate, {
                'path': str(paths[5]), 'installed_path': 'ql/test/extractor-smoke/luci',
                'classification': 'excluded', 'reason': 'no_ucode_route',
                'status': 'excluded',
            })
            self.assertEqual(receipt['plain_count'], 0)
            self.assertEqual(receipt['excluded_count'], 8)
            self.assertEqual([d['reason'] for d in receipt['decisions']],
                             ['no_ucode_route'] * 6 + ['outside_staged_root'] * 2)

    def test_env_transport_is_opt_in_and_direct_cli_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            root = temp / 'stagé & (x) ! % ^'
            plugin = root / 'usr/share/rpcd/ucode/luci'
            marker = root / 'ql/test/extractor-smoke/luci'
            for path in (plugin, marker):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('let x = 1;\n')
            inputs = temp / 'inputs'
            inputs.write_text(f'{plugin}\n{marker}\n')
            for name, flag, ambient, expected in (
                ('env', ['--staged-root-from-env'], str(root) + '/',
                 ['rpcd_raw_mode_full_path', 'no_ucode_route']),
                ('flagless', [], str(root),
                 ['no_ucode_route', 'explicit_extractor_smoke_input']),
                ('direct', ['--staged-root', str(root)], str(temp / 'missing'),
                 ['rpcd_raw_mode_full_path', 'no_ucode_route']),
            ):
                with self.subTest(name=name):
                    env = os.environ.copy()
                    env['CODEQL_UCODE_STAGED_ROOT'] = ambient
                    trap = temp / name / 'trap'
                    cmd = [str(EXTRACTOR), 'extract', '--source-archive-dir',
                           str(temp / name / 'archive'), '--output-dir', str(trap),
                           '--file-list', str(inputs), *flag]
                    result = subprocess.run(cmd, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    receipt = json.loads((trap / 'routing.json').read_text())
                    self.assertEqual([d['path'] for d in receipt['decisions']],
                                     [str(plugin), str(marker)])
                    self.assertEqual([d['reason'] for d in receipt['decisions']], expected)
                    self.assertEqual(receipt['plain_count'], 1)
                    self.assertEqual(receipt['excluded_count'], 1)

    def test_env_transport_errors_fail_closed_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            marker = temp / 'stage/ql/test/extractor-smoke/luci'
            marker.parent.mkdir(parents=True)
            marker.write_text('let x = 1;\n')
            inputs = temp / 'inputs'
            inputs.write_text(str(marker) + '\n')
            for name, value, extra in (
                ('missing', None, []), ('empty', '', []),
                ('nonexistent', str(temp / 'absent-root'), []), ('file', str(inputs), []),
                ('conflict', str(temp / 'stage'), ['--staged-root', str(temp / 'stage')]),
            ):
                with self.subTest(name=name):
                    env = os.environ.copy()
                    env.pop('CODEQL_UCODE_STAGED_ROOT', None)
                    if value is not None:
                        env['CODEQL_UCODE_STAGED_ROOT'] = value
                    out = temp / name
                    out.mkdir()
                    for directory in ('archive', 'trap', 'diagnostics'):
                        (out / directory).mkdir()
                        (out / directory / 'sentinel').write_text('unchanged')
                    env['CODEQL_EXTRACTOR_UCODE_DIAGNOSTIC_DIR'] = str(out / 'diagnostics')
                    cmd = [str(EXTRACTOR), 'extract', '--source-archive-dir',
                           str(out / 'archive'), '--output-dir', str(out / 'trap'),
                           '--file-list', str(inputs), '--staged-root-from-env', *extra]
                    result = subprocess.run(cmd, env=env, text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, name)
                    for directory in ('archive', 'trap', 'diagnostics'):
                        self.assertEqual(sorted(p.name for p in (out / directory).iterdir()),
                                         ['sentinel'])
                        self.assertEqual((out / directory / 'sentinel').read_text(), 'unchanged')
                    if name == 'conflict':
                        self.assertIn('cannot be used with', result.stderr)
                    elif name in ('missing', 'empty'):
                        self.assertIn('CODEQL_UCODE_STAGED_ROOT', result.stderr)

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
