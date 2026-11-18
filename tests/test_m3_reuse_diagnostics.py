"""Reuse-branch acceptance wiring: synthetic diagnostics, not extraction evidence."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKES = ('m4-fixed-helpers-smoke.sh', 'm4-imported-callee-smoke.sh', 'm4-smoke.sh')
QUERIES = ('GetFeaturesDirectExec', 'ImportedCalleeTaint', 'RequestArgsExec')
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
r = Path(os.environ['TEST_ROOT'])
db = r / '.codeql-database/m3-luci'
with open(os.environ['TEST_LOG'], 'a') as f: f.write(json.dumps(a) + '\n')
def reject(): sys.exit('fake CLI rejected: ' + repr(a))
if a[:2] == ['resolve', 'database']:
    if a[2:] != ['--format=json', str(db)] or not (db / 'codeql-database.yml').is_file(): reject()
    prefix = (db / 'codeql-database.yml').read_text().splitlines()[1].removeprefix('sourceLocationPrefix: ')
    print(json.dumps({'sourceLocationPrefix': prefix}))
elif a[:2] == ['query', 'run']:
    if len(a) != 6: reject()
    q = Path(a[2])
    allowed = [r / ('ql/src/diagnostics/' + n + '.ql') for n in ('SuccessfullyExtractedFiles', 'ExtractionErrors')]
    allowed += [r / ('ql/src/m4/' + os.environ['TEST_QUERY'] + '.ql')]
    if q not in allowed or not q.is_file(): reject()
    opts = a[3:]
    if sorted(x.split('=', 1)[0] for x in opts) != ['--database', '--output', '--search-path']: reject()
    if '--database=' + str(db) not in opts or '--search-path=' + ':'.join(str(r / p) for p in ('extractor-pack', 'ql/lib', 'ql/src')) not in opts: reject()
    output = next(x[len('--output='):] for x in opts if x.startswith('--output='))
    if Path(output).parent != db: reject()
    if q.parent.name == 'm4': sys.exit('SEMANTIC QUERY REACHED')
    Path(output).write_text(q.stem)
elif a[:2] == ['bqrs', 'decode']:
    if len(a) != 5 or a[2:4] != ['--format=json', '--entities=url,string']: reject()
    p = Path(a[4])
    if p.parent != db or not p.is_file(): reject()
    name = p.read_text()
    if name not in ('SuccessfullyExtractedFiles', 'ExtractionErrors'): reject()
    print(json.dumps(json.loads(Path(os.environ['TEST_DIAGS']).read_text())[name]))
else: reject()
'''


class M3ReuseDiagnostics(unittest.TestCase):
    def run_case(self, smoke, fault, mutant=None):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            root = t / 'checkout'
            shutil.copytree(ROOT / 'scripts', root / 'scripts')
            shutil.copytree(ROOT / 'ql', root / 'ql')
            if mutant in ('wrong-query', 'wrong-flags', 'bad-option'):
                helper = root / 'scripts/m4-smoke-diagnostics.sh'
                text = helper.read_text()
                before, after = {'wrong-query': ('ql/src/diagnostics/', 'ql/src/m4/'),
                                 'wrong-flags': ('--entities=url,string', '--entities=string'),
                                 'bad-option': ('--output="$DB/$diagnostic.bqrs"', '--output="$DB/$diagnostic.bqrs" --bogus')}[mutant]
                self.assertEqual(text.count(before), 1)
                helper.write_text(text.replace(before, after))
            if mutant == 'late':
                script = root / 'scripts' / smoke
                text = script.read_text()
                self.assertEqual(text.count('check_m3_reuse_extraction\n'), 1)
                text = text.replace('check_m3_reuse_extraction\n', '')
                marker = '--database="$DB" --search-path="$QLPATH" --output='
                lines = text.splitlines(keepends=True)
                index = next(i for i, line in enumerate(lines) if marker in line)
                lines.insert(index + 1, 'check_m3_reuse_extraction\n')
                script.write_text(''.join(lines))
            db = root / '.codeql-database/m3-luci'
            (db / 'db-ucode').mkdir(parents=True)
            src = root / 'ql/test/extractor-smoke'
            for q in QUERIES:
                self.assertTrue((root / ('ql/src/m4/' + q + '.ql')).is_file())
            for q in ('SuccessfullyExtractedFiles', 'ExtractionErrors'):
                self.assertTrue((root / ('ql/src/diagnostics/' + q + '.ql')).is_file())
            (db / 'codeql-database.yml').write_text('---\nsourceLocationPrefix: ' + str(src if fault != 'foreign' else t / 'foreign') + '\nfinalised: true\n')
            if fault == 'missing-root':
                (db / 'codeql-database.yml').unlink()
            def receipt(p):
                return [{'label': str(p), 'url': {'uri': p.as_uri(), 'startLine': 0, 'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']
            files = [src / p for p in ('taint_neg', 'taint_pos', 'usr/share/rpcd/ucode/luci')]
            self.assertTrue(all(p.is_file() for p in files))
            success = list(map(receipt, files))
            if fault == 'omit': success.pop()
            if fault == 'duplicate': success.append(success[0])
            if fault == 'substitute':
                replacement = src / 'ssa_pos'
                self.assertTrue(replacement.is_file())
                self.assertNotIn(replacement, files)
                success[0] = receipt(replacement)
            errors = [[{'label': 'synthetic error'}, 'parse error', 2]] if fault == 'error' else []
            data = {'SuccessfullyExtractedFiles': {'#select': {'columns': [{'name':'f','kind':'Entity'}, {'kind':'String'}], 'tuples':success}}, 'ExtractionErrors': {'#select': {'columns':[{'name':'error','kind':'Entity'}, {'kind':'String'}, {'kind':'Integer'}], 'tuples':errors}}}
            diag = t / 'diags.json'; diag.write_text(json.dumps(data))
            binary = t / 'bin'; binary.mkdir(); cli = binary / 'codeql'; cli.write_text(FAKE); cli.chmod(0o755)
            log = t / 'commands'; log.touch()
            env = dict(os.environ, PATH=str(binary) + ':' + os.environ['PATH'], TEST_ROOT=str(root), TEST_LOG=str(log), TEST_DIAGS=str(diag), TEST_QUERY=QUERIES[SMOKES.index(smoke)], CODEQL_UCODE_SMOKE_PACKS_READY=str(root), PYTHONDONTWRITEBYTECODE='1')
            p = subprocess.run(['bash', str(root / 'scripts' / smoke)], cwd=root, env=env, text=True, capture_output=True)
            return p, [json.loads(line) for line in log.read_text().splitlines()]

    def test_rejects_bad_diagnostics_before_semantic_queries(self):
        for smoke in SMOKES:
            for fault in ('error', 'omit', 'duplicate', 'substitute'):
                with self.subTest(smoke=smoke, fault=fault):
                    p, commands = self.run_case(smoke, fault)
                    self.assertNotEqual(p.returncode, 0)
                    self.assertIn('M4 extraction rejected:', p.stderr)
                    self.assertIn('zero extraction errors' if fault == 'error' else 'exact successful-file multiset', p.stderr)
                    self.assertFalse(any(c[:2] == ['query', 'run'] and '/ql/src/m4/' in c[2] for c in commands), commands)

    def test_foreign_root_rejected_before_queries(self):
        for smoke in SMOKES:
            for fault in ('foreign', 'missing-root'):
                with self.subTest(smoke=smoke, fault=fault):
                    p, commands = self.run_case(smoke, fault)
                    self.assertNotEqual(p.returncode, 0)
                    self.assertIn('source root', p.stderr)
                    self.assertFalse(any(c[:2] == ['query', 'run'] for c in commands), commands)

    def test_adapter_rejects_invalid_diagnostic_commands(self):
        for mutant in ('wrong-query', 'wrong-flags', 'bad-option'):
            with self.subTest(mutant=mutant):
                p, commands = self.run_case(SMOKES[0], 'good', mutant)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn('fake CLI rejected:', p.stderr)
                self.assertFalse(any(c[:2] == ['query', 'run'] and '/ql/src/m4/' in c[2] and Path(c[2]).stem in QUERIES for c in commands))

    def test_late_gate_mutant_executes_semantics_first(self):
        for smoke in SMOKES:
            with self.subTest(smoke=smoke):
                p, commands = self.run_case(smoke, 'error', 'late')
                self.assertNotEqual(p.returncode, 0)
                self.assertIn('SEMANTIC QUERY REACHED', p.stderr)
                self.assertTrue(any(c[:2] == ['query', 'run'] and '/ql/src/m4/' in c[2] for c in commands))

    def test_good_receipts_reach_semantics(self):
        for smoke in SMOKES:
            with self.subTest(smoke=smoke):
                p, commands = self.run_case(smoke, 'good')
                self.assertIn('SEMANTIC QUERY REACHED', p.stderr)
                self.assertEqual(sum(c[:2] == ['query', 'run'] and '/ql/src/diagnostics/' in c[2] for c in commands), 2)

if __name__ == '__main__': unittest.main()
