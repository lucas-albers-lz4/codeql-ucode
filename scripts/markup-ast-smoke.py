"""Fresh database checks for markup AST identities and malformed diagnostics."""
import csv
import io
import json
import shutil
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
        expected = {
            ('Markup', 'Markup', '1', '1', '2', '30', '<root>', '-1'),
            ('RawText', 'Hello ', '1', '1', '1', '6', 'Markup', '0'),
            ('RawText', '!\n', '1', '17', '1', '18', 'Markup', '2'),
            ('RawText', 'Value ', '2', '17', '2', '22', 'TextStatement', '1'),
            ('RawText', '\n', '2', '30', '2', '30', 'TextStatement', '3'),
            ('Identifier', 'name', '1', '10', '1', '13', 'ExpressionTag', '1'),
            ('Identifier', 'x', '2', '8', '2', '8', 'VariableDeclarator', '0'),
            ('Identifier', 'x', '2', '26', '2', '26', 'ExpressionTag', '1'),
            ('TextStatement', 'TextStatement', '2', '15', '2', '30', 'Markup', '5'),
            ('ExpressionTag', 'ExpressionTag', '1', '7', '1', '16', 'Markup', '1'),
            ('ExpressionTag', 'ExpressionTag', '2', '23', '2', '29', 'TextStatement', '2'),
            ('LexicalDeclaration', 'LexicalDeclaration', '2', '4', '2', '13', 'Markup', '4'),
        }
        assert len(rows) == len(expected) and {tuple(row) for row in rows} == expected, rows
        rows = list(csv.reader(io.StringIO(query(db, 'markup-real-issue56-test.ql', valid / 'real.bqrs', 'csv'))))[1:]
        expected_real = {
            ('ImportStatement', '3', '1', '3', '39', 'Markup', '1'),
            ('ImportStatement', '4', '1', '4', '32', 'Markup', '2'),
            ('FunctionExpression', '6', '25', '12', '1', 'AssignmentExpression', '2'),
            ('AssignmentExpression', '6', '1', '12', '1', 'ExpressionStatement', '0'),
        }
        assert len(rows) == len(expected_real) and {tuple(row) for row in rows} == expected_real, rows

        # Exercise the actual default autobuilder, without --include overrides.
        discovery_source = base / 'discovery-source'
        discovery_source.mkdir()
        for name in ('mixed.ut', 'plain.uc'):
            shutil.copyfile(SOURCE / 'usr/share/ucode/controls' / name, discovery_source / name)
        discovery_db = base / 'discovery-db'
        run('codeql', 'database', 'create', discovery_db, '--language=ucode',
            f'--search-path={PACK}', f'--source-root={discovery_source}', '--build-mode=none')
        extracted = json.loads(query(discovery_db, 'diagnostics/SuccessfullyExtractedFiles.ql', base / 'discovery.bqrs'))['#select']['tuples']
        assert {row[0]['url']['uri'] for row in extracted} == {
            (discovery_source / name).resolve().as_uri() for name in ('mixed.ut', 'plain.uc')
        }, extracted
        errors = json.loads(query(discovery_db, 'diagnostics/ExtractionErrors.ql', base / 'discovery-errors.bqrs'))['#select']['tuples']
        assert not errors, errors
        discovery_rows = list(csv.reader(io.StringIO(query(discovery_db, 'markup-issue56-test.ql', base / 'discovery-ast.bqrs', 'csv'))))[1:]
        assert len(discovery_rows) == len(expected) and {tuple(row) for row in discovery_rows} == expected, discovery_rows
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
