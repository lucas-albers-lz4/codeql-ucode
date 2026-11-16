"""The value-flow smoke must reject incomplete or erroneous extractions."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / 'scripts/value-flow-diagnostics.py'
SUCCESS_COLUMNS = [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}]
ERROR_COLUMNS = [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}]


def decoded(columns, rows):
    return {'#select': {'columns': columns, 'tuples': rows}}


def check(tmp_path, success_rows, error_rows, success_columns=SUCCESS_COLUMNS):
    success = tmp_path / 'success.json'
    errors = tmp_path / 'errors.json'
    success.write_text(json.dumps(decoded(success_columns, success_rows)))
    errors.write_text(json.dumps(decoded(ERROR_COLUMNS, error_rows)))
    return subprocess.run(
        [sys.executable, str(VERIFIER), str(tmp_path / 'src/ql/test/extractor-smoke/ssa_pos'),
         str(success), str(errors)], capture_output=True, text=True)


def receipt(path):
    return [{'label': str(path), 'url': {'uri': path.as_uri(), 'startLine': 0,
            'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']


def test_accepts_only_exact_file_and_zero_errors(tmp_path):
    target = tmp_path / 'src/ql/test/extractor-smoke/ssa_pos'
    result = check(tmp_path, [receipt(target)], [])
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'wrong_path', 'wrong_uri', 'span', 'schema', 'error'])
def test_rejects_bad_diagnostics(tmp_path, mutation):
    target = tmp_path / 'src/ql/test/extractor-smoke/ssa_pos'
    row = receipt(target)
    rows, errors, columns = [row], [], SUCCESS_COLUMNS
    if mutation == 'missing':
        rows = []
    elif mutation == 'duplicate':
        rows = [row, row]
    elif mutation == 'wrong_path':
        rows = [receipt(tmp_path / 'elsewhere/ssa_pos')]
    elif mutation == 'wrong_uri':
        row[0]['url']['uri'] = (tmp_path / 'elsewhere/ssa_pos').as_uri()
    elif mutation == 'span':
        row[0]['url']['startLine'] = 1
    elif mutation == 'schema':
        columns = []
    elif mutation == 'error':
        errors = [[{'label': 'parse error'}, 'parse error', 2]]
    result = check(tmp_path, rows, errors, columns)
    assert result.returncode != 0
    assert 'value-flow extraction' in result.stderr


def test_real_recovered_semantics_do_not_override_parse_error(tmp_path):
    data = ROOT / 'tests/data/value-flow-recovery'
    digests = {
        'out.csv': 'c8af2280007d043a23e9a580a2d938feb1bc2fe33039bd08dc013c06c813a1cb',
        'expr.csv': '0db1e34bbd0ad0a72125df9b1a82af36a001367a38892e90b982a25cca1afe01',
        'return.csv': 'a1d7c67f34d115fb2abe2a33663edf1a1312f6f9cfe751be3db5a80d3fab9747',
        'SuccessfullyExtractedFiles.json': 'f6fadf4ef24c7e643c82758f548c427e2c7d3f68d0135db83904a7d08fdfc707',
        'ExtractionErrors.json': 'b654d2b1c08941860b7d2b8405e0e813184c70c5dd959f13503624698b545ec7',
    }
    for name, digest in digests.items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == digest
    malformed = (data / 'ssa_value_flow').read_bytes()
    assert hashlib.sha256(malformed).hexdigest() == '6c8bbc36671e90bb07d131ba7390498be79368260fa43f066e644e47436443a5'
    source = tmp_path / 'src'
    target = source / 'ql/test/extractor-smoke/ssa_pos'
    target.parent.mkdir(parents=True)
    target.write_bytes(malformed)

    # Replay the smoke's actual semantic verifier on the real recovered CSVs.
    script = (ROOT / 'scripts/m4-value-flow-smoke.sh').read_text()
    verifier = script.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
    semantic = subprocess.run([sys.executable, '-', str(target), str(data / 'out.csv'),
                               str(data / 'expr.csv'), str(data / 'return.csv')],
                              input=verifier, text=True, capture_output=True)
    assert semantic.returncode == 0, semantic.stderr
    assert 'value-flow semantic assertions passed' in semantic.stdout

    raw_errors = (data / 'ExtractionErrors.json').read_text()
    assert raw_errors.count('__SOURCE_ROOT__') == 2
    errors = tmp_path / 'errors.json'
    errors.write_text(raw_errors.replace('__SOURCE_ROOT__', str(source)))
    result = subprocess.run([sys.executable, str(VERIFIER), str(target),
                             str(data / 'SuccessfullyExtractedFiles.json'), str(errors)],
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert 'expected zero extraction errors' in result.stderr
    assert 'expected exactly one successful-file receipt' in result.stderr


def test_real_smoke_wiring_rejects_recovered_snapshot(tmp_path):
    """Run the unmodified shell runner using retained decodes, not a fake pass."""
    root = tmp_path / 'checkout'
    (root / 'scripts').mkdir(parents=True)
    (root / 'extractor-pack').mkdir()
    fixture_dir = root / 'ql/test/extractor-smoke'
    fixture_dir.mkdir(parents=True)
    for name in ('m4-value-flow-smoke.sh', 'ql-smoke-pack-install.sh', 'value-flow-diagnostics.py'):
        shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
    shutil.copyfile(ROOT / 'tests/data/value-flow-recovery/ssa_value_flow', fixture_dir / 'ssa_value_flow')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    fake = bin_dir / 'codeql'
    fake.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
data = pathlib.Path(os.environ['SNAPSHOT'])
if args[:2] == ['database', 'init']:
    root = next(x.split('=', 1)[1] for x in args if x.startswith('--source-root='))
    pathlib.Path(os.environ['STATE']).write_text(root)
elif args[:2] == ['query', 'run']:
    query = pathlib.Path(args[2]).stem
    out = next(x.split('=', 1)[1] for x in args if x.startswith('--output='))
    pathlib.Path(out).write_text(query)
elif args[:2] == ['bqrs', 'decode']:
    query = pathlib.Path(args[-1]).read_text()
    names = {'ValueFlowRegression': 'out.csv', 'ExprFlowRegression': 'expr.csv',
             'ReturnFlowRegression': 'return.csv',
             'SuccessfullyExtractedFiles': 'SuccessfullyExtractedFiles.json',
             'ExtractionErrors': 'ExtractionErrors.json'}
    text = (data / names[query]).read_text()
    text = text.replace('__SOURCE_ROOT__', pathlib.Path(os.environ['STATE']).read_text())
    sys.stdout.write(text)
''')
    fake.chmod(0o755)
    env = os.environ.copy()
    env.update(PATH=str(bin_dir) + os.pathsep + env['PATH'], TMPDIR=str(tmp_path),
               SNAPSHOT=str(ROOT / 'tests/data/value-flow-recovery'),
               STATE=str(tmp_path / 'source-root'), CODEQL_UCODE_SMOKE_PACKS_READY=str(root))
    result = subprocess.run(['bash', str(root / 'scripts/m4-value-flow-smoke.sh')],
                            env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'value-flow semantic assertions passed' in result.stdout
    assert 'expected zero extraction errors' in result.stderr
    assert 'expected exactly one successful-file receipt' in result.stderr
    assert 'value-flow regressions passed' not in result.stdout
