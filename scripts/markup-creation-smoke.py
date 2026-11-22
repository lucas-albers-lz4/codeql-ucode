"""Fresh extraction and exact bounded import/function creation graph checks."""
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('markup_ast_smoke', ROOT / 'scripts/markup-ast-smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
SOURCE = ROOT / 'tests/data/markup-creation'

# These lists specify complete immediate paths; the top-level path has no exit.
PATHS = {
 ('supported.ut', 'top'): [
  ('import-completion', 'ImportStatement:1:4:1:21:Markup:1'),
  ('object-identifier', 'Identifier:1:23:1:23:MemberExpression:0'),
  ('member-reference', 'MemberExpression:1:23:1:25:AssignmentExpression:0'),
  ('function-creation', 'FunctionExpression:1:29:1:54:AssignmentExpression:2'),
  ('assignment-completion', 'AssignmentExpression:1:23:1:54:ExpressionStatement:0'),
  ('statement-completion', 'ExpressionStatement:1:23:1:55:Markup:2')],
 ('supported.ut', 'callable:1:29'): [
  ('entry', 'entry'), ('initializer', 'Number:1:51:1:51:VariableDeclarator:2'),
  ('declaration-completion', 'LexicalDeclaration:1:43:1:52:StatementBlock:1'), ('exit', 'exit')],
 ('empty-body.ut', 'top'): [
  ('object-identifier', 'Identifier:1:4:1:4:MemberExpression:0'),
  ('member-reference', 'MemberExpression:1:4:1:6:AssignmentExpression:0'),
  ('function-creation', 'FunctionExpression:1:10:1:22:AssignmentExpression:2'),
  ('assignment-completion', 'AssignmentExpression:1:4:1:22:ExpressionStatement:0'),
  ('statement-completion', 'ExpressionStatement:1:4:1:23:Markup:1')],
 ('empty-body.ut', 'callable:1:10'): [('entry', 'entry'), ('exit', 'exit')],
 ('body-call.ut', 'top'): [
  ('object-identifier', 'Identifier:1:4:1:4:MemberExpression:0'),
  ('member-reference', 'MemberExpression:1:4:1:6:AssignmentExpression:0'),
  ('function-creation', 'FunctionExpression:1:10:1:31:AssignmentExpression:2'),
  ('assignment-completion', 'AssignmentExpression:1:4:1:31:ExpressionStatement:0'),
  ('statement-completion', 'ExpressionStatement:1:4:1:32:Markup:1')],
 ('uhttpd.uc', 'top'): [
  ('import-completion', 'ImportStatement:3:1:3:39:Markup:1'),
  ('import-completion', 'ImportStatement:4:1:4:32:Markup:2'),
  ('object-identifier', 'Identifier:6:1:6:6:MemberExpression:0'),
  ('member-reference', 'MemberExpression:6:1:6:21:AssignmentExpression:0'),
  ('function-creation', 'FunctionExpression:6:25:12:1:AssignmentExpression:2'),
  ('assignment-completion', 'AssignmentExpression:6:1:12:1:ExpressionStatement:0'),
  ('statement-completion', 'ExpressionStatement:6:1:12:2:Markup:3')],
}

# Independent AST oracle for the source-pinned real file, including parameter,
# property, import binding and body identities, regardless of CFG membership.
REAL_AST = {
 ('Identifier','dispatch','3','8','3','15','ImportClause','0'),
 ('Identifier','request','4','8','4','14','ImportClause','0'),
 ('Identifier','global','6','1','6','6','MemberExpression','0'),
 ('Identifier','env','6','34','6','36','FormalParameters','1'),
 ('StringFragment','luci.dispatcher','3','23','3','37','String','1'),
 ('StringFragment','luci.http','4','22','4','30','String','1'),
 ('Markup','Markup','1','1','12','3','<root>','-1'),
 ('String','String','3','22','3','38','ImportStatement','3'),
 ('String','String','4','21','4','31','ImportStatement','3'),
 ('PropertyIdentifier','handle_request','6','8','6','21','MemberExpression','2'),
 ('ImportClause','ImportClause','3','8','3','15','ImportStatement','1'),
 ('ImportClause','ImportClause','4','8','4','14','ImportStatement','1'),
 ('StatementBlock','StatementBlock','6','39','12','1','FunctionExpression','2'),
 ('ImportStatement','ImportStatement','3','1','3','39','Markup','1'),
 ('ImportStatement','ImportStatement','4','1','4','32','Markup','2'),
 ('FormalParameters','FormalParameters','6','33','6','37','FunctionExpression','1'),
 ('MemberExpression','MemberExpression','6','1','6','21','AssignmentExpression','0'),
 ('FunctionExpression','FunctionExpression','6','25','12','1','AssignmentExpression','2'),
 ('ExpressionStatement','ExpressionStatement','6','1','12','2','Markup','3'),
 ('AssignmentExpression','AssignmentExpression','6','1','12','1','ExpressionStatement','0'),
}

SUPPORTED_AST = {
 ('Identifier','x','1','23','1','23','MemberExpression','0'),
 ('Identifier','a','1','11','1','11','ImportClause','0'),
 ('Identifier','p','1','38','1','38','FormalParameters','1'),
 ('StringFragment','a','1','19','1','19','String','1'),
 ('Markup','Markup','1','1','1','55','<root>','-1'),
 ('String','String','1','18','1','20','ImportStatement','3'),
 ('PropertyIdentifier','y','1','25','1','25','MemberExpression','2'),
 ('ImportClause','ImportClause','1','11','1','11','ImportStatement','1'),
 ('StatementBlock','StatementBlock','1','41','1','54','FunctionExpression','2'),
 ('ImportStatement','ImportStatement','1','4','1','21','Markup','1'),
 ('FormalParameters','FormalParameters','1','37','1','39','FunctionExpression','1'),
 ('MemberExpression','MemberExpression','1','23','1','25','AssignmentExpression','0'),
 ('FunctionExpression','FunctionExpression','1','29','1','54','AssignmentExpression','2'),
 ('ExpressionStatement','ExpressionStatement','1','23','1','55','Markup','2'),
 ('AssignmentExpression','AssignmentExpression','1','23','1','54','ExpressionStatement','0'),
}

def rows(db, name, output):
    return list(csv.reader(io.StringIO(smoke.query(db, name, output, 'csv'))))[1:]

def graph(db, base, keys):
    nodes = {(f, scope, role, identity) for (f, scope) in keys for role, identity in PATHS[f, scope]}
    edges = {(f, scope, a[1], b[1]) for f, scope in keys for a, b in zip(PATHS[f, scope], PATHS[f, scope][1:])}
    actual_nodes = rows(db, 'markup-creation-nodes-test.ql', base / 'nodes.bqrs')
    actual_edges = rows(db, 'markup-creation-edges-test.ql', base / 'edges.bqrs')
    assert len(actual_nodes) == len(nodes) and {tuple(r) for r in actual_nodes} == nodes, actual_nodes
    assert len(actual_edges) == len(edges) and {tuple(r) for r in actual_edges} == edges, actual_edges

def main():
    with tempfile.TemporaryDirectory(prefix='ucode-markup-creation-') as tmp:
        base = Path(tmp)
        db = base / 'fixtures'
        smoke.run('codeql','database','create',db,'--language=ucode', f'--search-path={smoke.PACK}', f'--source-root={SOURCE}', '--build-mode=none')
        diagnostics = rows(db, 'markup-cfg-diagnostics-test.ql', base / 'diagnostics.bqrs')
        assert len(diagnostics) == 1 and diagnostics[0][0] == 'malformed.ut', diagnostics
        files = json.loads(smoke.query(db, 'diagnostics/SuccessfullyExtractedFiles.ql', base / 'files.bqrs'))['#select']['tuples']
        assert {r[0]['url']['uri'] for r in files} == {p.resolve().as_uri() for p in SOURCE.glob('*.ut') if p.name != 'malformed.ut'}, files
        ast = rows(db, 'markup-creation-ast-test.ql', base / 'ast.bqrs')
        assert len(ast) == len(SUPPORTED_AST) and {tuple(r[1:]) for r in ast if r[0] == 'supported.ut'} == SUPPORTED_AST, ast
        graph(db, base, set(PATHS) - {('uhttpd.uc','top')})
        scopes = rows(db, 'markup-creation-scopes-test.ql', base / 'scopes.bqrs')
        assert {tuple(r) for r in scopes} == {('supported.ut','1','29','1','54','covered'), ('empty-body.ut','1','10','1','22','covered'), ('body-call.ut','1','10','1','31','unsupported')} and len(scopes) == 3, scopes
        roots = rows(db, 'markup-creation-root-test.ql', base / 'roots.bqrs')
        assert {tuple(r) for r in roots} == {(name,'top-observed') for name in ['supported.ut','empty-body.ut','body-call.ut']} and len(roots) == 3, roots
        # Inject a warning into an unchanged supported AST to isolate the
        # file-diagnostic veto from all syntax and shape checks.
        warning_db = base / 'warning-db'
        smoke.run('codeql','database','init',warning_db,'--language=ucode',f'--search-path={smoke.PACK}', f'--source-root={SOURCE}')
        smoke.run('codeql','database','index-files',warning_db,'--language=ucode','--include=**/supported.ut',f'--working-dir={SOURCE}')
        source_id = json.dumps(str((SOURCE / 'supported.ut').resolve()) + ';sourcefile')
        trap = (f'#1=@{source_id}\n#2=*\nlocations_default(#2,#1,1,1,1,1)\n'
                '#3=*\ndiagnostics(#3,30,"test_warning","injected warning","injected warning",#2)\n')
        with gzip.open(warning_db / 'trap/ucode/injected-warning.trap.gz', 'wt') as out:
            out.write(trap)
        smoke.run('codeql','database','finalize',warning_db)
        warned_ast = rows(warning_db, 'markup-creation-ast-test.ql', base / 'warned-ast.bqrs')
        assert sorted(warned_ast) == sorted(ast), (warned_ast, ast)
        assert rows(warning_db, 'markup-cfg-diagnostics-test.ql', base / 'warning.bqrs') == [['supported.ut','test_warning','injected warning']]
        assert not rows(warning_db, 'markup-creation-nodes-test.ql', base / 'warned-nodes.bqrs')
        assert not rows(warning_db, 'markup-creation-scopes-test.ql', base / 'warned-scopes.bqrs')
        source = smoke.SOURCE / 'usr/share/ucode/luci/uhttpd.uc'
        assert hashlib.sha256(source.read_bytes()).hexdigest() == 'a2b2694f52c021af16dd06ac8c988b8a0a726d9e8186d308708268ebb8849493'
        real = base / 'real'
        real.mkdir()
        db, receipt = smoke.database(real, ['uhttpd.uc'])
        assert receipt['input_count'] == 1 and receipt['markup_count'] == 1, receipt
        files = json.loads(smoke.query(db, 'diagnostics/SuccessfullyExtractedFiles.ql', real / 'files.bqrs'))['#select']['tuples']
        assert {r[0]['url']['uri'] for r in files} == {(smoke.SOURCE / 'usr/share/ucode/luci/uhttpd.uc').resolve().as_uri()}, files
        assert not rows(db, 'markup-cfg-diagnostics-test.ql', real / 'diagnostics.bqrs')
        ast = rows(db, 'markup-creation-ast-test.ql', real / 'ast.bqrs')
        assert len(ast) == len(REAL_AST) and {tuple(r[1:]) for r in ast if r[0] == 'uhttpd.uc'} == REAL_AST, ast
        body = rows(db, 'markup-creation-body-ast-test.ql', real / 'body-ast.bqrs')
        expected_body = {
            ('LexicalDeclaration','7','2','7','50','StatementBlock','1'),
            ('CallExpression','7','12','7','49','VariableDeclarator','2'),
            ('ExpressionStatement','9','2','9','15','StatementBlock','2'),
            ('CallExpression','9','2','9','14','ExpressionStatement','0'),
            ('ExpressionStatement','11','2','11','13','StatementBlock','3'),
            ('CallExpression','11','2','11','12','ExpressionStatement','0'),
        }
        assert len(body) == len(expected_body) and {tuple(r) for r in body} == expected_body, body
        graph(db, real, {('uhttpd.uc','top')})
        assert rows(db, 'markup-creation-scopes-test.ql', real / 'scopes.bqrs') == [['uhttpd.uc','6','25','12','1','unsupported']]
        assert rows(db, 'markup-creation-root-test.ql', real / 'roots.bqrs') == [['uhttpd.uc','top-observed']]
        print('Exact import/function paths, scopes, source identities and diagnostics verified')

if __name__ == '__main__':
    main()
