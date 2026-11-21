#!/usr/bin/env python3
"""Test-only direct syntax observer with pinned identity and extraction gates."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'ql/test/dispatcher-formvalue'
PACK = ROOT / 'extractor-pack'
EXPECTED = {533: 'sid = http.formvalue(m[2]);', 537: 'sid = http.formvalue(m[2], true);',
            699: 'let request_val = http.formvalue(param_name);',
            720: 'if (http.formvalue("token") != authtoken) {',
            935: "user = http.formvalue('luci_username');",
            936: "pass = http.formvalue('luci_password');"}


def verify_source(data):
    if hashlib.sha256(data).hexdigest() != '4f9923cf569aeebb956343d208bcc38f40d8a26d2f46f12c5539a9582fa4f037':
        raise ValueError('pinned dispatcher digest mismatch')
    lines = data.decode('utf-8').splitlines()
    if {n: lines[n - 1].strip() for n in EXPECTED} != EXPECTED:
        raise ValueError('pinned source site mismatch')


def verify_rows(rows, stage):
    # Compare full extracted entities, not labels or basenames alone.
    expected = {}
    shapes = {533: ('SubscriptExpression', 'none'), 537: ('SubscriptExpression', 'True'),
              699: ('Identifier', 'none'), 720: ('String', 'none'),
              935: ('String', 'none'), 936: ('String', 'none')}
    for name, sites in [('dispatcher.uc', shapes), ('controls.uc', {1: ('String', 'none')})]:
        path = stage / 'usr/share/ucode/luci' / name
        lines = path.read_text().splitlines()
        for number, (arg0, arg1) in sites.items():
            line = lines[number - 1]
            start = line.index('http.formvalue(')
            # Calls in this fixture have no nested parentheses in their arguments.
            end = line.index(')', start) + 1
            url = {'uri': path.as_uri(), 'startLine': number, 'startColumn': start + 1,
                   'endLine': number, 'endColumn': end}
            arity = 1 if arg1 == 'none' else 2
            message = f'direct formvalue at {name}:{number}:{arg0}:{arg1}:{arity}'
            expected[message] = url
    if len(rows) != len(expected):
        raise ValueError(f'unexpected observer row count: {len(rows)}')
    seen = set()
    for entity, message in rows:
        if message not in expected or message in seen or not isinstance(entity, dict) or entity.get('url') != expected[message]:
            raise ValueError(f'unexpected observer entity: {(entity, message)!r}')
        seen.add(message)
    if seen != set(expected):
        raise ValueError('missing observer rows')


def verify_routing(routing, stage, dest):
    decisions = routing['decisions']
    wanted = {str(dest / 'dispatcher.uc'), str(dest / 'controls.uc'), str(dest / 'unrelated.uc')}
    if (routing['input_count'] != 3 or routing['plain_count'] != 3 or
        routing['excluded_count'] != 0 or routing['uncertain_count'] != 0 or len(decisions) != 3 or
        {d['path'] for d in decisions} != wanted or
        any(d['classification'] != 'plain' or d['status'] != 'plain_route_selected' or
        d['reason'] != 'ucode_extension' or
        d['installed_path'] != str(Path(d['path']).relative_to(stage)) for d in decisions)):
        raise ValueError(f'unexpected routing: {routing!r}')



def run(*args, env=None):
    return subprocess.run([str(x) for x in args], check=True, text=True, env=env,
                          stdout=subprocess.PIPE).stdout


def main():
    verify_source((FIXTURE / 'dispatcher.uc').read_bytes())
    with tempfile.TemporaryDirectory(prefix='dispatcher-formvalue-') as tmp:
        base = Path(tmp).resolve()
        stage = base / 'stage'
        dest = stage / 'usr/share/ucode/luci'
        dest.mkdir(parents=True)
        for name in ('dispatcher.uc', 'controls.uc', 'unrelated.uc'):
            shutil.copyfile(FIXTURE / name, dest / name)
        db = base / 'db'
        run('codeql', 'database', 'init', db, '--language=ucode', f'--search-path={PACK}', f'--source-root={stage}')
        env = os.environ.copy()
        env['CODEQL_UCODE_STAGED_ROOT'] = str(stage)
        run('codeql', 'database', 'index-files', db, '--language=ucode', '--include=**/*.uc', f'--working-dir={stage}', env=env)
        routing = json.loads((db / 'trap/ucode/routing.json').read_text())
        verify_routing(routing, stage, dest)
        run('codeql', 'database', 'finalize', db)
        outputs = []
        for label, query in [('success', 'diagnostics/SuccessfullyExtractedFiles.ql'),
                             ('errors', 'diagnostics/ExtractionErrors.ql'),
                             ('observer', 'extractor-smoke/DispatcherFormvalueShape.ql')]:
            output = base / (label + '.bqrs')
            run('codeql', 'query', 'run', ROOT / 'ql/src' / query, f'--database={db}',
                f'--search-path={PACK}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}', f'--output={output}', '--threads=1', '--ram=2048')
            decoded = base / (label + '.json')
            decoded.write_text(run('codeql', 'bqrs', 'decode', '--format=json', '--entities=url,string', output))
            outputs.append(decoded)
        run('python3', ROOT / 'scripts/m4-smoke-diagnostics.py', outputs[0], outputs[1],
            dest / 'dispatcher.uc', dest / 'controls.uc', dest / 'unrelated.uc')
        rows = json.loads(outputs[2].read_text())['#select']['tuples']
        verify_rows(rows, stage)
        print('source identity, routing, diagnostics and direct call locations verified')


if __name__ == '__main__':
    main()
