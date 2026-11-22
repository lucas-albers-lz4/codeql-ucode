#!/usr/bin/env python3
"""Extract the pinned controller and isolated helper controls, then check observations."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'ql/test/uci-helper-observation'
PACK = ROOT / 'extractor-pack'
NAMES = ('uci.uc', 'positive.uc', 'shadow.uc', 'unrelated.uc', 'reordered.uc', 'unknown.uc', 'formal-shadow.uc')

def run(*args, env=None):
    return subprocess.run([str(a) for a in args], check=True, text=True, env=env, stdout=subprocess.PIPE).stdout

def main():
    if hashlib.sha256((FIXTURE / 'uci.uc').read_bytes()).hexdigest() != 'ac75cfef7d74f87ed7f957778004a7bf486c76df699398c215795b4947e0c93e':
        raise ValueError('pinned controller digest mismatch')
    with tempfile.TemporaryDirectory(prefix='uci-helper-') as tmp:
        base = Path(tmp).resolve()
        stage = base / 'stage'
        stage.mkdir()
        for name in NAMES:
            shutil.copyfile(FIXTURE / name, stage / name)
        db = base / 'db'
        run('codeql', 'database', 'init', db, '--language=ucode', f'--search-path={PACK}', f'--source-root={stage}')
        env = os.environ.copy()
        env['CODEQL_UCODE_STAGED_ROOT'] = str(stage)
        run('codeql', 'database', 'index-files', db, '--language=ucode', '--include=**/*.uc', f'--working-dir={stage}', env=env)
        run('codeql', 'database', 'finalize', db)
        outputs = []
        for label, query in [('success', 'diagnostics/SuccessfullyExtractedFiles.ql'), ('errors', 'diagnostics/ExtractionErrors.ql'), ('observer', 'inventory/UciHelperObservation.ql')]:
            bqrs = base / (label + '.bqrs')
            run('codeql', 'query', 'run', ROOT / 'ql/src' / query, f'--database={db}', f'--search-path={PACK}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}', f'--output={bqrs}', '--threads=1', '--ram=2048')
            out = base / (label + '.json')
            out.write_text(run('codeql', 'bqrs', 'decode', '--format=json', '--entities=url,string', bqrs))
            outputs.append(out)
        run('python3', ROOT / 'scripts/m4-smoke-diagnostics.py', outputs[0], outputs[1], *(stage / n for n in NAMES))
        rows = json.loads(outputs[2].read_text())['#select']['tuples']
        def entity(name, sl, sc, el, ec):
            return {'label': 'CallExpression', 'url': {'uri': (stage / name).as_uri(),
                    'startLine': sl, 'startColumn': sc, 'endLine': el, 'endColumn': ec}}
        expected = [
            [entity('positive.uc', 4, 1, 4, 30), 'UCI commit helper observation: 1:2',
             entity('positive.uc', 2, 10, 2, 40), 'forwarding call'],
            [entity('uci.uc', 79, 9, 79, 81), 'UCI commit helper observation: 25:28',
             entity('uci.uc', 28, 12, 28, 42), 'forwarding call'],
        ]
        if len(rows) != len(expected) or any(row not in rows for row in expected):
            raise ValueError(f'unexpected observer rows: {rows!r}')
        print('verified pinned source, selected file identities, zero extraction errors, and exact call pairs')

if __name__ == '__main__':
    main()
