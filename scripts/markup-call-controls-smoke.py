"""Fresh extraction checks for the bounded callable call shapes."""
import csv
from collections import Counter
import importlib.util
import io
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('markup_ast_smoke', ROOT / 'scripts/markup-ast-smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
source = ROOT / 'tests/data/markup-call-controls'
with tempfile.TemporaryDirectory(prefix='ucode-call-controls-') as tmp:
    base = Path(tmp)
    db = base / 'db'
    smoke.run('codeql', 'database', 'create', db, '--language=ucode', f'--search-path={smoke.PACK}', f'--source-root={source}', '--build-mode=none')
    def rows(q):
        return list(csv.reader(io.StringIO(smoke.query(db, q, base / (q + '.bqrs'), 'csv'))))[1:]
    scopes = rows('markup-creation-scopes-test.ql')
    observed = {r[0]: r[-1] for r in scopes}
    expected = {'positive.ut':'covered', 'optional.ut':'unsupported', 'computed.ut':'unsupported', 'spread.ut':'unsupported', 'nested.ut':'unsupported', 'optional-member.ut':'unsupported', 'multihop.ut':'unsupported'}
    assert observed == expected and len(scopes) == len(expected), scopes
    graph_nodes = rows('markup-creation-nodes-test.ql')
    graph_edges = rows('markup-creation-edges-test.ql')
    unsupported = set(expected) - {'positive.ut'} | {'malformed.ut'}
    assert not [r for r in graph_nodes if r[0] in unsupported and r[1].startswith('callable:')], graph_nodes
    assert not [r for r in graph_edges if r[0] in unsupported and r[1].startswith('callable:')], graph_edges
    ast = rows('markup-call-controls-ast-test.ql')
    # Each witness isolates the specific excluded form in an otherwise qualifying callable.
    witnesses = [
        ('optional.ut', 'OptionalChain', '32', '33', 'CallExpression', '1'),
        ('optional-member.ut', 'OptionalChain', '34', '35', 'MemberExpression', '1'),
        ('computed.ut', 'SubscriptExpression', '36', '39', 'Arguments', '3'),
        ('spread.ut', 'SpreadElement', '33', '36', 'Arguments', '1'),
        ('nested.ut', 'CallExpression', '33', '36', 'Arguments', '1'),
        ('multihop.ut', 'MemberExpression', '33', '35', 'MemberExpression', '0'),
        ('multihop.ut', 'MemberExpression', '33', '37', 'Arguments', '1'),
    ]
    counts = Counter(map(tuple, ast))
    assert all(counts[w] == 1 for w in witnesses), (witnesses, ast)
    assert any(r[0] == 'positive.ut' and r[1].startswith('callable:') for r in graph_nodes), graph_nodes
    assert any(r[0] == 'positive.ut' and r[1].startswith('callable:') for r in graph_edges), graph_edges
    diagnostics = rows('markup-cfg-diagnostics-test.ql')
    assert {r[0] for r in diagnostics} == {'malformed.ut'}, diagnostics
    files = json.loads(smoke.query(db, 'diagnostics/SuccessfullyExtractedFiles.ql', base / 'files.bqrs'))['#select']['tuples']
    assert {r[0]['url']['uri'] for r in files} == {(source / n).resolve().as_uri() for n in expected}, files
    print('Call shape controls and malformed diagnostic verified')
