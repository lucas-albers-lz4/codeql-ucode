#!/usr/bin/env python3
"""Check retained or regenerated CSV against source-first witnesses and expectations."""
import csv
import pathlib
import runpy
import sys
from collections import Counter

if len(sys.argv) not in (4, 5) or len(sys.argv) == 5 and sys.argv[4] != '--call-bundle':
    sys.exit('usage: check.py OUTPUT_DIRECTORY STAGE CONTROLS_ROOT [--call-bundle]')
out, stage, controls_root = map(lambda p: pathlib.Path(p).resolve(), sys.argv[1:4])
call_bundle = len(sys.argv) == 5
prefix = 'usr/share/ucode/luci/'
# Relative path, unsupported AST kind, inclusive location, parent and index, source bytes.
witnesses = [
('template/admin_status/index.ut','CallExpression',7,4,7,20,'ExpressionStatement',0,"include('header')"),
('template/csrftoken.ut','CallExpression',6,4,6,20,'ExpressionStatement',0,"include('header')"),
('template/error404.ut','CallExpression',7,4,7,20,'ExpressionStatement',0,"include('header')"),
('template/error500.ut','MemberExpression',63,27,63,43,'ExpressionTag',1,'exception.message'),
('template/footer.ut','CallExpression',6,21,6,49,'VariableDeclarator',2,'dispatcher.rollback_pending()'),
('template/header.ut','CallExpression',7,2,7,34,'ExpressionStatement',0,'include(`themes/${theme}/header`)'),
('template/sysauth.ut','CallExpression',7,4,7,20,'ExpressionStatement',0,"include('header')"),
('template/themes/bootstrap/footer.ut','CallExpression',9,17,9,58,'ExpressionTag',1,"entityencode(version.disturl ?? '#', true)"),
('template/themes/bootstrap/header.ut','CallExpression',11,20,11,47,'VariableDeclarator',2,"ubus.call('system', 'board')"),
('template/themes/bootstrap/sysauth.ut','CallExpression',6,4,6,42,'ExpressionStatement',0,"include('header', { blank_page: true })"),
('template/view.ut','CallExpression',1,4,1,20,'ExpressionStatement',0,"include('header')"),
('uhttpd.uc','CallExpression',7,12,7,49,'VariableDeclarator',2,'request(env, uhttpd.recv, uhttpd.send)'),
]
headers = {
    'markup-measure-witness.csv': ['col0','col1','col2','col3','col4','col5','col6','col7'],
    'markup-measure-measurement.csv': ['col0','ordinary','creation','col3'],
    'markup-measure-measurement-callable.csv': ['col0','col1','col2','col3','col4','coverage'],
    'markup-measure-markup-creation-nodes-test.csv': ['col0','col1','col2','col3'],
    'markup-measure-markup-creation-edges-test.csv': ['col0','col1','col2','col3','col4','col5'],
    'markup-measure-controls2-measurement.csv': ['col0','ordinary','creation','col3'],
    'markup-measure-controls2-measurement-callable.csv': ['col0','col1','col2','col3','col4','coverage'],
    'markup-measure-controls2-ExtractionErrors.csv': ['error','col1','col2'],
    'markup-measure-controls2-SuccessfullyExtractedFiles.csv': ['f','col1'],
}
def rows(name):
    with (out / name).open(newline='') as f:
        r = csv.reader(f, strict=True)
        if next(r, None) != headers[name]:
            raise ValueError(f'incorrect header: {name}')
        result = list(r)
        if any(len(row) != len(headers[name]) for row in result):
            raise ValueError(f'incorrect row arity: {name}')
        return Counter(tuple(x) for x in result)
def require(ok, message):
    if not ok: raise ValueError(message)
actual = rows('markup-measure-witness.csv')
for path, kind, sl, sc, el, ec, parent, index, source in witnesses:
    expected = (prefix+path, kind, str(sl), str(sc), str(el), str(ec), parent, str(index))
    require(actual[expected] == 1, f'missing or duplicate witness {expected}')
    require(sl == el, 'witness must fit one line')
    line = (stage / prefix / path).read_bytes().splitlines()[sl-1]
    require(line[sc-1:ec] == source.encode(), f'source mismatch {path}:{sl}')
# Creation rejects RawText outside bodies; one explicit raw node per .ut file.
raw = [
('template/admin_status/index.ut',5,4,6,1,'Markup',1),('template/csrftoken.ut',4,4,5,1,'Markup',1),
('template/error404.ut',5,4,6,1,'Markup',1),('template/error500.ut',4,4,58,5,'Markup',1),
('template/footer.ut',4,4,5,1,'Markup',1),('template/header.ut',4,4,5,1,'Markup',1),
('template/sysauth.ut',5,4,6,1,'Markup',1),('template/themes/bootstrap/footer.ut',1,1,1,2,'Markup',0),
('template/themes/bootstrap/header.ut',6,4,7,1,'Markup',1),('template/themes/bootstrap/sysauth.ut',4,4,5,1,'Markup',1),
('template/view.ut',1,24,4,23,'TextStatement',1)]
for path,sl,sc,el,ec,parent,index in raw:
    row=(prefix+path,'RawText',str(sl),str(sc),str(el),str(ec),parent,str(index))
    require(actual[row] == 1, f'missing raw witness {row}')
expected = Counter((prefix+p,'unsupported','covered' if p == 'uhttpd.uc' else 'unsupported',str(n)) for p,n in [
('template/admin_status/index.ut',117),('template/csrftoken.ut',72),('template/error404.ut',95),('template/error500.ut',55),('template/footer.ut',182),('template/header.ut',293),('template/sysauth.ut',276),('template/themes/bootstrap/footer.ut',111),('template/themes/bootstrap/header.ut',663),('template/themes/bootstrap/sysauth.ut',143),('template/view.ut',46),('uhttpd.uc',78)])
require(rows('markup-measure-measurement.csv') == expected,'root result mismatch')
require(rows('markup-measure-measurement-callable.csv') == Counter([(prefix+'uhttpd.uc','6','25','12','1','covered' if call_bundle else 'unsupported')]),'callable mismatch')
# These source lines independently establish the two imports and assignment structure.
uhttpd = (stage / prefix / 'uhttpd.uc').read_bytes().splitlines()
for line, expected_line in [(3,b"import dispatch from 'luci.dispatcher';"),(4,b"import request from 'luci.http';"),(6,b'global.handle_request = function(env) {'),(12,b'};')]:
    require(uhttpd[line-1] == expected_line, f'uhttpd source mismatch at line {line}')
identities=['ImportStatement:3:1:3:39:Markup:1','ImportStatement:4:1:4:32:Markup:2','Identifier:6:1:6:6:MemberExpression:0','MemberExpression:6:1:6:21:AssignmentExpression:0','FunctionExpression:6:25:12:1:AssignmentExpression:2','AssignmentExpression:6:1:12:1:ExpressionStatement:0','ExpressionStatement:6:1:12:2:Markup:3']
roles=['import-completion','import-completion','object-identifier','member-reference','function-creation','assignment-completion','statement-completion']
expected_nodes = Counter(('uhttpd.uc','top',r,i) for r,i in zip(roles,identities))
expected_edges = Counter(('uhttpd.uc','top',a,'uhttpd.uc','top',b) for a,b in zip(identities,identities[1:]))
if call_bundle:
    paths = runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / 'scripts/markup-creation-smoke.py'))['PATHS']
    path = paths['uhttpd.uc', 'callable:6:25']
    expected_nodes.update(('uhttpd.uc','callable:6:25',role,identity) for role,identity in path)
    expected_edges.update(('uhttpd.uc','callable:6:25',a[1],'uhttpd.uc','callable:6:25',b[1]) for a,b in zip(path,path[1:]))
require(rows('markup-measure-markup-creation-nodes-test.csv') == expected_nodes,'node mismatch')
require(rows('markup-measure-markup-creation-edges-test.csv') == expected_edges,'edge mismatch')
controls = Counter([('ordinary-positive.ut','covered','unsupported','6'),('ordinary-negative.ut','unsupported','unsupported','9'),('creation-positive.ut','unsupported','covered','34'),('creation-negative.ut','unsupported','covered','34')])
require(rows('markup-measure-controls2-measurement.csv') == controls,'control roots mismatch')
require(rows('markup-measure-controls2-measurement-callable.csv') == Counter([('creation-positive.ut','1','34','1','58','covered'),('creation-negative.ut','1','34','1','55','covered' if call_bundle else 'unsupported')]),'control callable mismatch')
require(not rows('markup-measure-controls2-ExtractionErrors.csv'),'control diagnostics nonempty')
require(rows('markup-measure-controls2-SuccessfullyExtractedFiles.csv') == Counter((str(controls_root / name), '') for name in ['ordinary-positive.ut','ordinary-negative.ut','creation-positive.ut','creation-negative.ut']),'control identity mismatch')
print('Expected root, callable, witnesses, source bytes, nodes, edges and control rows matched.')
