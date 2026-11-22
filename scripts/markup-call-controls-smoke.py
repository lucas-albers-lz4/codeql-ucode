"""Fresh extraction checks for the bounded callable call shapes."""
import csv
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
    expected = {'positive.ut':'covered', 'optional.ut':'unsupported', 'computed.ut':'unsupported', 'spread.ut':'unsupported', 'nested.ut':'unsupported'}
    assert observed == expected and len(scopes) == len(expected), scopes
    diagnostics = rows('markup-cfg-diagnostics-test.ql')
    assert {r[0] for r in diagnostics} == {'malformed.ut'}, diagnostics
    files = json.loads(smoke.query(db, 'diagnostics/SuccessfullyExtractedFiles.ql', base / 'files.bqrs'))['#select']['tuples']
    assert {r[0]['url']['uri'] for r in files} == {(source / n).resolve().as_uri() for n in expected}, files
    print('Call shape controls and malformed diagnostic verified')
