#!/usr/bin/env python3
"""Query synthetic sources independently at the production-relative path."""
import csv
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / 'extractor-pack'
DB = ROOT / '.codeql-database/m4-backend-declarations-control'
SEARCH = f'{PACK}:{ROOT}/ql/lib:{ROOT}/ql/src'
CASES = {
    'two-module-const': ('''const methods = { first: { call: function() {} } };
const methods = { second: { call: function() {} } };
return { luci: methods };
''', []),
    'string-call-key': ('''const methods = { first: { 'call': function() {} } };
return { luci: methods };
''', []),
    'sequence-return': ('''const methods = { first: { call: function() {} } };
const other = {};
return { luci: methods }, { luci: other };
''', []),
    'parenthesized-return': ('''const methods = { first: { call: function() {} } };
return ({ luci: methods });
''', []),
    'parse-error': ('''const methods = { first: { call: function() {} } };
return { luci: methods };
const broken = ;
''', []),
    'duplicate-valid-method': ('''const methods = {
  first: { call: function() {} },
  first: { call: function(request) {} },
};
return { luci: methods };
''', []),
    'duplicate-method': ('''const methods = {
  first: { call: function() {} },
  first: { call: 7 },
};
return { luci: methods };
''', []),
    'shorthand-alias': ('''const methods = { first: { call: function() {} } };
const alias = { methods };
return { luci: methods };
''', []),
    'alias': ('''const methods = { first: { call: function() {} } };
let alias = methods;
return { luci: methods };
''', []),
    'duplicate-return': ('''const methods = { first: { call: function() {} } };
return { luci: methods, luci: 7 };
''', []),
    'duplicate-call': ('''const methods = { first: { call: function() {}, call: 7 } };
return { luci: methods };
''', []),
    'duplicate-call-functions': ('''const methods = { first: { call: function() {}, call: function() {} } };
return { luci: methods };
''', []),
    'duplicate-noncall-field': ('''const methods = { first: { args: {}, args: {}, call: function() {} } };
return { luci: methods };
''', []),
    'missing-call': ('''const methods = { good: { call: function() {} }, first: { args: {} } };
return { luci: methods };
''', []),
    'positive': ('''const decoy = { lookalike: { call: function() {} } };
const methods = {
  first: { call: function(request) {} },
  second: { call: function() {} },
};
return { luci: methods };
''', [
        {'observation_kind': 'source_declared_callback', 'ubus_object': 'luci', 'method': 'first', 'source_path': 'usr/share/rpcd/ucode/luci', 'start_line': '3', 'start_column': '18', 'end_line': '3', 'end_column': '37'},
        {'observation_kind': 'source_declared_callback', 'ubus_object': 'luci', 'method': 'second', 'source_path': 'usr/share/rpcd/ucode/luci', 'start_line': '4', 'start_column': '19', 'end_line': '4', 'end_column': '31'},
    ]),
    'wrong-path': ('''const methods = { first: { call: function() {} } };
return { luci: methods };
''', []),
    'nested-only': ('''function outer() {
  const methods = { first: { call: function() {} } };
  return { luci: methods };
}
return {};
''', []),
    'wrong-return': ('''const methods = { first: { call: function() {} } };
const other = {};
return { luci: other };
''', []),
    'nested-ambiguity': ('''const methods = { first: { call: function() {} } };
function outer() { const methods = {}; }
return { luci: methods };
''', []),
    'mutation': ('''const methods = { first: { call: function() {} } };
methods.first = {};
return { luci: methods };
''', []),
    'nested-use': ('''const methods = { first: { call: function() {} } };
function other() { return methods; }
return { luci: methods };
''', []),
    'multiple-return': ('''const methods = { first: { call: function() {} } };
return { luci: methods };
return {};
''', []),
    'let-binding': ('''let methods = { first: { call: function() {} } };
return { luci: methods };
''', []),
    'computed-method': ('''const methods = { good: { call: function() {} }, ['first']: { call: function() {} } };
return { luci: methods };
''', []),
    'string-method': ('''const methods = { good: { call: function() {} }, 'first': { call: function() {} } };
return { luci: methods };
''', []),
    'spread-method': ('''const extra = {};
const methods = { good: { call: function() {} }, ...extra };
return { luci: methods };
''', []),
    'shorthand-method': ('''const first = {};
const methods = { good: { call: function() {} }, first };
return { luci: methods };
''', []),
    'computed-call': ('''const methods = { good: { call: function() {} }, first: { ['call']: function() {} } };
return { luci: methods };
''', []),
    'spread-call': ('''const extra = {};
const methods = { good: { call: function() {}, ...extra } };
return { luci: methods };
''', []),
    'indirect-callback': ('''const cb = function() {};
const methods = { good: { call: function() {} }, first: { call: cb } };
return { luci: methods };
''', []),
    'arrow-callback': ('''const methods = { good: { call: function() {} }, first: { call: () => 1 } };
return { luci: methods };
''', []),
    'nonfunction-callback': ('''const methods = { good: { call: function() {} }, first: { call: 7 } };
return { luci: methods };
''', []),
    'computed-return': ('''const methods = { first: { call: function() {} } };
return { luci: methods, ['luci']: 7 };
''', []),
    'spread-return': ('''const extra = {};
const methods = { first: { call: function() {} } };
return { luci: methods, ...extra };
''', []),
}

def run(*args, stdout=None):
    subprocess.run(args, cwd=ROOT, check=True, stdout=stdout)

def decode(name):
    with (DB / f'{name}.csv').open('w') as f:
        run('codeql', 'bqrs', 'decode', '--format=csv', str(DB / f'{name}.bqrs'), stdout=f)
    with (DB / f'{name}.csv').open(newline='') as f:
        return list(csv.DictReader(f))

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp).resolve() / 'ql/test/extractor-smoke'
    for name, (source, expected) in CASES.items():
        if os.environ.get('BACKEND_CONTROL_CASE', name) != name:
            continue
        path = src / ('other/usr/share/rpcd/ucode/luci' if name == 'wrong-path' else 'usr/share/rpcd/ucode/luci')
        path.parent.mkdir(parents=True, exist_ok=True)
        print('CONTROL', name, flush=True)
        # The wrong-path lookalike is extensionless and outside rpcd's routed
        # installed tree. Give it a ucode shebang so it is genuinely extracted.
        if name == 'wrong-path':
            source = '#!/usr/bin/ucode\n' + source
        path.write_text(source)
        shutil.rmtree(DB, ignore_errors=True)
        run('codeql', 'database', 'init', str(DB), '--language=ucode', f'--search-path={PACK}', f'--source-root={src}')
        run('codeql', 'database', 'index-files', '--language=ucode', '--include=**/rpcd/ucode/luci', f'--working-dir={src}', str(DB))
        run('codeql', 'database', 'finalize', str(DB))
        for query, output in [('diagnostics/SuccessfullyExtractedFiles.ql', 'extracted'), ('diagnostics/ExtractionErrors.ql', 'errors'), ('m4/LuciBackendDeclarations.ql', 'table')]:
            run('codeql', 'query', 'run', str(ROOT / 'ql/src' / query), f'--database={DB}', f'--search-path={SEARCH}', f'--output={DB / (output + ".bqrs")}')
        extracted, errors, result = decode('extracted'), decode('errors'), decode('table')
        if name == 'parse-error':
            if extracted or not errors:
                raise SystemExit(f'{name}: expected failed extraction diagnostics: {extracted=} {errors=}')
        elif len(extracted) != 1 or extracted[0]['f'] != str(path) or errors:
            raise SystemExit(f'{name}: extraction diagnostics: {extracted=} {errors=}')
        if sorted(result, key=lambda row: row['method']) != sorted(expected, key=lambda row: row['method']):
            raise SystemExit(f'{name}: expected {expected}, got {result}')
        path.unlink()
        print('PASS', name, flush=True)
