"""Fresh database checks for markup AST identities and malformed diagnostics."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tests/data/markup'
PACK = ROOT / 'extractor-pack'


def run(*args):
    return subprocess.run([str(a) for a in args], check=True, text=True,
                          stdout=subprocess.PIPE).stdout


def query(db, path, output, fmt='json'):
    run('codeql', 'query', 'run', ROOT / 'ql/src' / path, f'--database={db}',
        f'--search-path={PACK}', f'--output={output}', '--threads=1', '--ram=2048')
    return run('codeql', 'bqrs', 'decode', f'--format={fmt}', '--entities=url,string', output)


def database(base, includes):
    db = base / 'db'
    run('codeql', 'database', 'init', db, '--language=ucode', f'--search-path={PACK}',
        f'--source-root={SOURCE}')
    run('codeql', 'database', 'index-files', db, '--language=ucode',
        *[f'--include=**/{name}' for name in includes], f'--working-dir={SOURCE}')
    receipt = json.loads((db / 'trap/ucode/routing.json').read_text())
    run('codeql', 'database', 'finalize', db)
    return db, receipt


def main():
    with tempfile.TemporaryDirectory(prefix='ucode-markup-') as tmp:
        base = Path(tmp)
        valid = base / 'valid'
        valid.mkdir()
        db, receipt = database(valid, ['uhttpd.uc', 'mixed.ut', 'plain.uc'])
        assert receipt['input_count'] == 3 and receipt['markup_count'] == 2 and receipt['plain_count'] == 1, receipt
        extracted = json.loads(query(db, 'diagnostics/SuccessfullyExtractedFiles.ql', valid / 'files.bqrs'))['#select']['tuples']
        uris = {row[0]['url']['uri'] for row in extracted}
        assert uris == {(SOURCE / p).resolve().as_uri() for p in ['usr/share/ucode/luci/uhttpd.uc', 'usr/share/ucode/controls/mixed.ut', 'usr/share/ucode/controls/plain.uc']}, uris
        errors = json.loads(query(db, 'diagnostics/ExtractionErrors.ql', valid / 'errors.bqrs'))['#select']['tuples']
        assert not errors, errors
        rows = list(csv.reader(io.StringIO(query(db, 'markup-issue56-test.ql', valid / 'ast.bqrs', 'csv'))))[1:]
        assert len(rows) == 19, rows
        assert sum(r[0] == 'uhttpd.uc' and r[1] == 'Markup' for r in rows) == 1, rows
        assert sum(r[0] == 'mixed.ut' and r[1] == 'Markup' for r in rows) == 1, rows
        assert ['mixed.ut', 'Identifier', 'name', '1', '10'] in rows, rows
        assert ['mixed.ut', 'Identifier', 'x', '2', '8'] in rows, rows
        assert ['mixed.ut', 'Identifier', 'x', '2', '26'] in rows, rows
        assert ['uhttpd.uc', 'Identifier', 'dispatch', '3', '8'] in rows, rows
        assert sum(r[0] == 'mixed.ut' and r[1] == 'ExpressionTag' for r in rows) == 2, rows
        assert not any(r[0] == 'plain.uc' for r in rows), rows
        malformed = base / 'malformed'
        malformed.mkdir()
        db, receipt = database(malformed, ['malformed.ut'])
        errors = json.loads(query(db, 'diagnostics/ExtractionErrors.ql', malformed / 'errors.bqrs'))['#select']['tuples']
        assert len(errors) == 2, errors
        messages = {row[0]["label"] for row in errors}
        assert any("expected identifier symbol" in message for message in messages), messages
        assert "Missing value for field: expression_tag::child" in messages, messages
        assert all(row[0]["url"]["uri"] == (SOURCE / "usr/share/ucode/controls/malformed.ut").resolve().as_uri() for row in errors), errors
        print('valid file identities, AST locations, and malformed diagnostics verified')


if __name__ == '__main__':
    main()
