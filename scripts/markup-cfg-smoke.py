"""Fresh extraction and complete bounded markup CFG node and edge checks."""
import csv
import io
import gzip
import json
from pathlib import Path
import tempfile
import importlib.util
spec = importlib.util.spec_from_file_location("markup_ast_smoke", Path(__file__).with_name("markup-ast-smoke.py"))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

ROOT = smoke.ROOT
SOURCE = ROOT / 'tests/data/markup-cfg'
PATHS = {
    'empty.ut': ['entry', 'exit'],
    'adjacent.ut': ['entry', 'Identifier:1:4:1:4:ExpressionTag:1', 'ExpressionTag:1:1:1:7:Markup:0', 'Identifier:1:11:1:11:ExpressionTag:1', 'ExpressionTag:1:8:1:14:Markup:1', 'exit'],
    'empty-text.ut': ['entry', 'Number:1:12:1:12:VariableDeclarator:2', 'LexicalDeclaration:1:4:1:13:Markup:1', 'Number:1:28:1:28:VariableDeclarator:2', 'LexicalDeclaration:1:20:1:29:Markup:3', 'exit'],
    'reopen.ut': ['entry', 'Number:1:12:1:12:VariableDeclarator:2', 'LexicalDeclaration:1:4:1:13:Markup:1', 'RawText:1:17:1:17:TextStatement:1', 'Identifier:1:21:1:21:ExpressionTag:1', 'ExpressionTag:1:18:1:24:TextStatement:2', 'Number:1:36:1:36:VariableDeclarator:2', 'LexicalDeclaration:1:28:1:37:Markup:3', 'exit'],
    'repeated.ut': ['entry', 'RawText:1:1:1:1:Markup:0', 'Identifier:1:5:1:5:ExpressionTag:1', 'ExpressionTag:1:2:1:8:Markup:1', 'RawText:1:9:1:9:Markup:2', 'Identifier:1:13:1:13:ExpressionTag:1', 'ExpressionTag:1:10:1:16:Markup:3', 'exit'],
    'mixed.ut': ['entry', 'RawText:1:1:1:6:Markup:0', 'Identifier:1:10:1:13:ExpressionTag:1', 'ExpressionTag:1:7:1:16:Markup:1', 'RawText:1:17:1:18:Markup:2', 'Number:2:12:2:12:VariableDeclarator:2', 'LexicalDeclaration:2:4:2:13:Markup:4', 'RawText:2:17:2:22:TextStatement:1', 'Identifier:2:26:2:26:ExpressionTag:1', 'ExpressionTag:2:23:2:29:TextStatement:2', 'RawText:2:30:2:30:TextStatement:3', 'exit'],
}

def rows(db, query, output):
    return list(csv.reader(io.StringIO(smoke.query(db, query, output, 'csv'))))[1:]

def check_graph(db, directory, names):
    expected_edges = {(f, a, b) for f in names for a, b in zip(PATHS[f], PATHS[f][1:])}
    roles = {'RawText': 'raw-text', 'Identifier': 'identifier', 'Number': 'initializer', 'ExpressionTag': 'tag-completion', 'LexicalDeclaration': 'declaration-completion'}
    expected_nodes = {(f, n if n in ('entry', 'exit') else roles[n.split(':')[0]], n) for f in names for n in PATHS[f]}
    actual_edges = rows(db, 'markup-cfg-test.ql', directory / 'edges.bqrs')
    actual_nodes = rows(db, 'markup-cfg-nodes-test.ql', directory / 'nodes.bqrs')
    assert len(actual_edges) == len(expected_edges) and {tuple(r) for r in actual_edges} == expected_edges, actual_edges
    assert len(actual_nodes) == len(expected_nodes) and {tuple(r) for r in actual_nodes} == expected_nodes, actual_nodes

def main():
    with tempfile.TemporaryDirectory(prefix='ucode-markup-cfg-') as tmp:
        base = Path(tmp)
        fixture_db = base / 'fixtures'
        smoke.run('codeql', 'database', 'create', fixture_db, '--language=ucode', f'--search-path={smoke.PACK}', f'--source-root={SOURCE}', '--build-mode=none')
        errors = json.loads(smoke.query(fixture_db, 'diagnostics/ExtractionErrors.ql', base / 'errors.bqrs'))['#select']['tuples']
        assert len(errors) == 2 and all(r[0]['url']['uri'] == (SOURCE / 'malformed.ut').resolve().as_uri() for r in errors), errors
        messages = {r[0]['label'] for r in errors}
        assert any('expected identifier symbol' in m for m in messages) and 'Missing value for field: expression_tag::child' in messages, messages
        diagnostics = rows(fixture_db, 'markup-cfg-diagnostics-test.ql', base / 'diagnostics.bqrs')
        assert len(diagnostics) == 2 and all(r[0] == 'malformed.ut' for r in diagnostics), diagnostics
        extracted = json.loads(smoke.query(fixture_db, 'diagnostics/SuccessfullyExtractedFiles.ql', base / 'files.bqrs'))['#select']['tuples']
        assert {r[0]['url']['uri'] for r in extracted} == {p.resolve().as_uri() for p in SOURCE.glob('*.ut') if p.name != 'malformed.ut'}, extracted
        comments = rows(fixture_db, 'markup-cfg-comments-test.ql', base / 'comments.bqrs')
        assert {tuple(r) for r in comments} == {
            ('code-comment.ut', 'Comment', 'no-parent'),
            ('doc-comment.ut', 'DocComment', 'no-parent'),
            ('expression-comment.ut', 'Comment', 'no-parent'),
        } and len(comments) == 3, comments
        ast = rows(fixture_db, 'markup-cfg-ast-test.ql', base / 'ast.bqrs')
        expected_ast = {
            ('Markup', 'Markup', '1', '1', '1', '40', '<root>', '-1'),
            ('TextStatement', 'TextStatement', '1', '15', '1', '26', 'Markup', '2'),
            ('TextStatement', 'TextStatement', '1', '39', '1', '40', 'Markup', '4'),
            ('LexicalDeclaration', 'LexicalDeclaration', '1', '4', '1', '13', 'Markup', '1'),
            ('LexicalDeclaration', 'LexicalDeclaration', '1', '28', '1', '37', 'Markup', '3'),
            ('VariableDeclarator', 'VariableDeclarator', '1', '8', '1', '12', 'LexicalDeclaration', '1'),
            ('VariableDeclarator', 'VariableDeclarator', '1', '32', '1', '36', 'LexicalDeclaration', '1'),
            ('Identifier', 'x', '1', '8', '1', '8', 'VariableDeclarator', '0'),
            ('Identifier', 'y', '1', '32', '1', '32', 'VariableDeclarator', '0'),
            ('Number', '1', '1', '12', '1', '12', 'VariableDeclarator', '2'),
            ('Number', '2', '1', '36', '1', '36', 'VariableDeclarator', '2'),
            ('RawText', 'A', '1', '17', '1', '17', 'TextStatement', '1'),
            ('Identifier', 'x', '1', '21', '1', '21', 'ExpressionTag', '1'),
            ('ExpressionTag', 'ExpressionTag', '1', '18', '1', '24', 'TextStatement', '2'),
        }
        assert len(ast) == len(expected_ast) and {tuple(r) for r in ast} == expected_ast, ast
        check_graph(fixture_db, base, set(PATHS) - {'mixed.ut'})
        # Inject a warning into an otherwise unchanged, successfully extracted
        # supported file. This isolates the diagnostic veto from syntax checks.
        diagnostic_db = base / 'diagnostic-veto'
        smoke.run('codeql', 'database', 'init', diagnostic_db, '--language=ucode',
                  f'--search-path={smoke.PACK}', f'--source-root={SOURCE}')
        smoke.run('codeql', 'database', 'index-files', diagnostic_db, '--language=ucode',
                  '--include=**/adjacent.ut', f'--working-dir={SOURCE}')
        source_id = json.dumps(str((SOURCE / 'adjacent.ut').resolve()) + ';sourcefile')
        trap = (f'#1=@{source_id}\n#2=*\nlocations_default(#2,#1,1,1,1,1)\n'
                '#3=*\ndiagnostics(#3,30,"test_warning","injected warning",'
                '"injected warning",#2)\n')
        with gzip.open(diagnostic_db / 'trap/ucode/injected-warning.trap.gz', 'wt') as out:
            out.write(trap)
        smoke.run('codeql', 'database', 'finalize', diagnostic_db)
        clean_ast = rows(fixture_db, 'markup-cfg-adjacent-ast-test.ql', base / 'clean-ast.bqrs')
        warned_ast = rows(diagnostic_db, 'markup-cfg-adjacent-ast-test.ql', base / 'warned-ast.bqrs')
        assert clean_ast and sorted(clean_ast) == sorted(warned_ast), (clean_ast, warned_ast)
        warnings = rows(diagnostic_db, 'markup-cfg-diagnostics-test.ql', base / 'warning.bqrs')
        assert warnings == [['adjacent.ut', 'test_warning', 'injected warning']], warnings
        files = json.loads(smoke.query(diagnostic_db, 'diagnostics/SuccessfullyExtractedFiles.ql', base / 'warned-files.bqrs'))['#select']['tuples']
        assert {r[0]['url']['uri'] for r in files} == {(SOURCE / 'adjacent.ut').resolve().as_uri()}, files
        assert not rows(diagnostic_db, 'markup-cfg-nodes-test.ql', base / 'warned-nodes.bqrs')
        assert not rows(diagnostic_db, 'markup-cfg-test.ql', base / 'warned-edges.bqrs')
        mixed = base / 'mixed'
        mixed.mkdir()
        db, receipt = smoke.database(mixed, ['mixed.ut'])
        assert receipt['input_count'] == 1 and receipt['markup_count'] == 1, receipt
        errors = json.loads(smoke.query(db, 'diagnostics/ExtractionErrors.ql', mixed / 'errors.bqrs'))['#select']['tuples']
        assert not errors, errors
        files = json.loads(smoke.query(db, 'diagnostics/SuccessfullyExtractedFiles.ql', mixed / 'files.bqrs'))['#select']['tuples']
        assert {r[0]['url']['uri'] for r in files} == {(smoke.SOURCE / 'usr/share/ucode/controls/mixed.ut').resolve().as_uri()}, files
        assert not rows(db, 'markup-cfg-diagnostics-test.ql', mixed / 'diagnostics.bqrs')
        check_graph(db, mixed, {'mixed.ut'})
        print('Exact covered node and edge sets and extraction diagnostics verified')

if __name__ == '__main__':
    main()
