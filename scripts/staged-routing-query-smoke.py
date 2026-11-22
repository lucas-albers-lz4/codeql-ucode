"""Extract both layouts and verify real diagnostic and AST entity identities."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'extractor-pack'
FIXTURE = ROOT / 'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci'
RELATIVE = Path('usr/share/rpcd/ucode/luci')


def run(*args, env=None):
    return subprocess.run([str(a) for a in args], check=True, text=True, env=env,
                          stdout=subprocess.PIPE).stdout


def verify_extracted(source, extracted):
    rows = extracted['#select']['tuples']
    assert len(rows) == 1, rows
    assert rows[0][0]['url']['uri'] == (source / RELATIVE).as_uri(), rows


def verify(source, receipt, extracted, errors, ast):
    plugin = source / RELATIVE
    decisions = receipt['decisions']
    assert receipt['input_count'] == 1 and receipt['plain_count'] == 1, receipt
    assert receipt['excluded_count'] == receipt['uncertain_count'] == 0, receipt
    assert len(decisions) == 1 and decisions[0] == {
        'path': str(plugin), 'installed_path': str(RELATIVE), 'classification': 'plain',
        'reason': 'rpcd_raw_mode_full_path', 'status': 'plain_route_selected'}, decisions
    verify_extracted(source, extracted)
    assert errors['#select']['tuples'] == [], errors
    target = {'uri': plugin.as_uri(), 'startLine': 17, 'startColumn': 1,
              'endLine': 19, 'endColumn': 1}
    matches = [r for r in ast['#select']['tuples']
               if r[0].get('url') == target and r[1] == 'FunctionDeclaration']
    assert len(matches) == 1, matches


def execute(base, layout, staged):
    source = base / layout
    plugin = source / RELATIVE
    plugin.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE, plugin)
    if layout == 'src' and not staged:
        # Keep a nonempty database so missing input is tested at the query gate.
        (source / 'control.uc').write_text('let control = 1;\n')
    db = base / 'db'
    run('codeql', 'database', 'init', db, '--language=ucode', f'--search-path={PACK}',
        f'--source-root={source}')
    env = os.environ.copy()
    env.pop('CODEQL_UCODE_STAGED_ROOT', None)
    if staged:
        env['CODEQL_UCODE_STAGED_ROOT'] = str(source)
    run('codeql', 'database', 'index-files', db, '--language=ucode',
        '--include=**/rpcd/ucode/luci', '--include=**/*.uc',
        f'--working-dir={source}', env=env)
    receipt = json.loads((db / 'trap/ucode/routing.json').read_text())
    run('codeql', 'database', 'finalize', db)
    results = []
    for label, query in [('extracted', 'diagnostics/SuccessfullyExtractedFiles.ql'),
                         ('errors', 'diagnostics/ExtractionErrors.ql'),
                         ('ast', 'extractor-smoke/PrintLuciAst.ql')]:
        output = base / (label + '.bqrs')
        run('codeql', 'query', 'run', ROOT / 'ql/src' / query, f'--database={db}',
            f'--search-path={PACK}', f'--output={output}', '--threads=1', '--ram=2048')
        results.append(json.loads(run('codeql', 'bqrs', 'decode', '--format=json',
                                      '--entities=url,string', output)))
    return source, receipt, *results


def main():
    with tempfile.TemporaryDirectory(prefix='ucode-staged-routing-') as directory:
        root = Path(directory).resolve()
        for name, layout, staged in [('ordinary', 'src', True),
                                     ('recognized', 'ql/test/extractor-smoke', False)]:
            data = execute(root / name, layout, staged)
            verify(*data)
            print(f'{name}: routing, extracted identity, empty errors and AST span verified', flush=True)
        # Real missing-input mutation: omit explicit trust from the ordinary root.
        source, receipt, extracted, errors, ast = execute(root / 'missing', 'src', False)
        try:
            verify_extracted(source, extracted)
        except AssertionError:
            assert receipt['plain_count'] == 1 and receipt['excluded_count'] == 1
            assert {d['reason'] for d in receipt['decisions']} == {'no_ucode_route', 'ucode_extension'}
            assert len(extracted['#select']['tuples']) == 1
            assert extracted['#select']['tuples'][0][0]['url']['uri'] == (source / 'control.uc').as_uri()
            assert errors['#select']['tuples'] == [] and ast['#select']['tuples'] == []
            print('missing-input mutation rejected by unchanged identity verifier', flush=True)
        else:
            raise AssertionError('missing-input mutation passed the verifier')


if __name__ == '__main__':
    main()
