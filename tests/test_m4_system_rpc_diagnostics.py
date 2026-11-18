"""Synthetic CLI wiring controls for the system-rpc extraction gate.

These receipts exercise the shell/verifier contract, not real extraction.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAKE = r'''#!/usr/bin/env python3
import csv, json, os, sys
from pathlib import Path
r = Path(os.environ['TEST_ROOT']); a = sys.argv[1:]
db = r / '.codeql-database/m4-system-rpc'; src = r / 'ql/test/system-binding'
with open(os.environ['TEST_COMMANDS'], 'a') as f: f.write(json.dumps(a) + '\n')
def reject(s): sys.exit('adapter rejected: ' + s)
def fileurl(p): return {'uri': p.as_uri(), 'startLine': 0, 'startColumn': 0, 'endLine': 0, 'endColumn': 0}
expected = src / 'usr/share/rpcd/ucode/luci'
if a[:2] == ['database', 'init']:
    if a[2:] != [str(db), '--language=ucode', '--search-path='+str(r/'extractor-pack'), '--source-root='+str(src)]: reject('init')
    db.mkdir(parents=True)
elif a[:2] == ['database', 'index-files']:
    if a[2:] != ['--language=ucode', '--include=**/luci', '--working-dir='+str(src), str(db)]: reject('index')
elif a[:2] == ['database', 'finalize']:
    if a[2:] != [str(db)]: reject('finalize')
elif a[:2] == ['query', 'run']:
    allowed = [r/'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', r/'ql/src/diagnostics/ExtractionErrors.ql', r/'ql/src/m3/LocalTaint.ql', r/'ql/src/m4/RequestArgsExec.ql']
    if len(a) != 6 or sorted(x.split('=', 1)[0] for x in a[3:]) != ['--database', '--output', '--search-path']: reject('query options')
    q = Path(a[2]); opts = dict(x.split('=', 1) for x in a[3:])
    if q not in allowed or not q.is_file(): reject('query operand')
    if opts['--database'] != str(db) or opts['--search-path'] != ':'.join(str(r/p) for p in ('extractor-pack','ql/lib','ql/src')) or Path(opts['--output']).parent != db: reject('query paths')
    Path(opts['--output']).write_text(q.stem)
elif a[:2] == ['bqrs', 'decode']:
    name = Path(a[-1]).read_text(); flags = a[2:-1]; fault = os.environ['TEST_FAULT']
    if name in ('SuccessfullyExtractedFiles', 'ExtractionErrors'):
        if flags not in (['--format=csv'], ['--format=json','--entities=url,string']): reject('diagnostic flags')
        paths = [expected]
        if fault == 'substitute': paths = [r/'wrong/system-binding/usr/share/rpcd/ucode/luci']
        if fault == 'omit': paths = []
        if fault == 'duplicate': paths.append(expected)
        rows = [[{'label': str(p), 'url': fileurl(p)}, ''] for p in paths] if name == 'SuccessfullyExtractedFiles' else ([[{'label':'error'}, 'error', 2]] if fault == 'error' else [])
        if flags == ['--format=csv']:
            w=csv.writer(sys.stdout); w.writerow(['f'] if name == 'SuccessfullyExtractedFiles' else ['error']); w.writerows([[str(p)] for p in paths] if name == 'SuccessfullyExtractedFiles' else [['error'] for row in rows])
        else:
            cols = [{'name':'f','kind':'Entity'},{'kind':'String'}] if name == 'SuccessfullyExtractedFiles' else [{'name':'error','kind':'Entity'},{'kind':'String'},{'kind':'Integer'}]
            print(json.dumps({'#select':{'columns':cols,'tuples':rows}}))
    elif name == 'LocalTaint':
        if flags != ['--format=json','--entities=url']: reject('local flags')
        url=fileurl(expected); url.update(startLine=11,startColumn=7,endColumn=34)
        row=[{'url':url},'request.args reaches system in luci',{'url':url},'system']
        print(json.dumps({'#select':{'tuples':[row,row]}}))
    elif name == 'RequestArgsExec':
        if flags != ['--format=csv']: reject('rpc flags')
        w=csv.writer(sys.stdout); w.writerow(['entity','message']); w.writerow(['x','builtin request.args reaches system'])
    else: reject('unknown result')
else: reject('unknown command')
'''

class SystemRpcDiagnostics(unittest.TestCase):
    def run_smoke(self, fault='valid', mutant=None):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d); root = tmp / 'checkout'
            shutil.copytree(ROOT / 'scripts', root / 'scripts')
            shutil.copytree(ROOT / 'ql', root / 'ql')
            if mutant in ('errors', 'identity'):
                p = root / 'scripts/m4-smoke-diagnostics.py'; text = p.read_text()
                old = 'if errors:' if mutant == 'errors' else 'if Counter(map(encode, success)) != Counter(map(encode, wanted)):'
                self.assertEqual(text.count(old), 1)
                p.write_text(text.replace(old, old.replace('if ', 'if False and ', 1)))
            if mutant in ('wiring', 'late'):
                p = root / 'scripts/m4-system-rpc-smoke.sh'; text = p.read_text()
                old = 'check_m4_extraction "$SRC/usr/share/rpcd/ucode/luci"'
                self.assertEqual(text.count(old), 1)
                text = text.replace(old, ':')
                if mutant == 'late':
                    line = '  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"'
                    self.assertEqual(text.count(line), 1)
                    text = text.replace(line, line + '\n  ' + old)
                p.write_text(text)
            substitute = root / 'wrong/system-binding/usr/share/rpcd/ucode/luci'
            substitute.parent.mkdir(parents=True)
            shutil.copyfile(root / 'ql/test/system-binding/usr/share/rpcd/ucode/luci', substitute)
            self.assertTrue(substitute.is_file())
            self.assertNotEqual(substitute, root / 'ql/test/system-binding/usr/share/rpcd/ucode/luci')
            for q in ('diagnostics/SuccessfullyExtractedFiles.ql', 'diagnostics/ExtractionErrors.ql', 'm3/LocalTaint.ql', 'm4/RequestArgsExec.ql'):
                self.assertTrue((root / 'ql/src' / q).is_file(), q)
            extractor = root / 'extractor-pack/tools/linux64/extractor'; extractor.parent.mkdir(parents=True); extractor.touch(mode=0o755)
            binary = tmp / 'bin'; binary.mkdir(); cli = binary / 'codeql'; cli.write_text(FAKE); cli.chmod(0o755)
            commands = tmp / 'commands'; env = os.environ.copy()
            env.update(PATH=str(binary)+os.pathsep+env['PATH'], TEST_ROOT=str(root), TEST_FAULT=fault, TEST_COMMANDS=str(commands), CODEQL_UCODE_SMOKE_PACKS_READY=str(root), PYTHONOPTIMIZE=str(sys.flags.optimize), PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run(['bash', str(root/'scripts/m4-system-rpc-smoke.sh')], cwd=root, env=env, capture_output=True, text=True)
            trace = [json.loads(line) for line in commands.read_text().splitlines()] if commands.exists() else []
            return result, trace

    def test_pristine(self):
        result, trace = self.run_smoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(a[:2] == ['query','run'] and a[2].endswith('/m3/LocalTaint.ql') for a in trace))

    def test_identity_independent_of_errors(self):
        for fault in ('omit', 'duplicate', 'substitute'):
            with self.subTest(fault=fault):
                result, trace = self.run_smoke(fault)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('expected exact successful-file multiset', result.stderr)
                self.assertNotIn('expected zero extraction errors', result.stderr)
                self.assertFalse(any(a[:2] == ['query','run'] and '/diagnostics/' not in a[2] for a in trace), trace)

    def test_error_independent_of_identity(self):
        result, trace = self.run_smoke('error')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('expected zero extraction errors', result.stderr)
        self.assertNotIn('expected exact successful-file multiset', result.stderr)
        self.assertFalse(any(a[:2] == ['query','run'] and '/diagnostics/' not in a[2] for a in trace), trace)

    def test_late_gate_still_rejects_but_trace_exposes_semantics(self):
        result, trace = self.run_smoke('error', 'late')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('expected zero extraction errors', result.stderr)
        self.assertTrue(any(a[:2] == ['query','run'] and '/m3/LocalTaint.ql' in a[2] for a in trace), trace)

    def test_guard_necessity(self):
        for mutant, fault in [('errors','error'), ('identity','omit'), ('identity','duplicate'), ('identity','substitute'), ('wiring','error')]:
            with self.subTest(mutant=mutant):
                result, trace = self.run_smoke(fault, mutant)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(any(a[:2] == ['query','run'] and '/m3/LocalTaint.ql' in a[2] for a in trace), trace)

if __name__ == '__main__':
    unittest.main()
