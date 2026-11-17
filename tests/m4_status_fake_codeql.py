#!/usr/bin/env python3
"""Strict status-smoke CLI adapter; semantic rows match the real baseline."""
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
root = Path(os.environ['STATUS_TEST_ROOT'])
fault_leg = os.environ.get('STATUS_TEST_LEG', '')
fault = os.environ.get('STATUS_TEST_FAULT', '')

def reject(message):
    sys.exit('fake codeql rejected: ' + message)

QUERY_RUN_OPTIONS = ('--database=', '--search-path=', '--output=')

def option(prefix):
    values = [x[len(prefix):] for x in args if x.startswith(prefix)]
    if len(values) != 1:
        reject('missing or duplicate ' + prefix)
    return values[0]

def state(db):
    return json.loads((db / 'state.json').read_text())

if args[:2] == ['database', 'init']:
    db = Path(args[2])
    src = Path(option('--source-root='))
    db.mkdir(parents=True)
    leg = 'main' if db.name == 'm4-luci-sys-status' else db.parent.name
    if leg not in ('main', 'dispatch', 'evidence'):
        reject('unknown database')
    (db / 'state.json').write_text(json.dumps({'source': str(src), 'leg': leg}))
elif args[:2] == ['database', 'index-files']:
    db = Path(args[-1])
    st = state(db)
    if option('--working-dir=') != st['source'] or sorted(x for x in args if x.startswith('--include=')) != ["--include=**/rpcd/ucode/luci", "--include=**/sys.uc"]:
        reject('wrong selection')
    src = Path(st['source'])
    paths = [src / 'usr/share/rpcd/ucode/luci', src / 'usr/share/ucode/luci/sys.uc']
    if not all(p.is_file() for p in paths):
        reject('missing input')
    if st['leg'] == fault_leg and fault == 'malformed':
        with paths[1].open('ab') as stream:
            stream.write(b'\nconst audit_broken = ;\n')
    st['malformed'] = paths[1].read_bytes().endswith(b'\nconst audit_broken = ;\n')
    st['paths'] = list(map(str, paths))
    st['routed'] = str(src).endswith('/ql/test/extractor-smoke')
    (db / 'state.json').write_text(json.dumps(st))
elif args[:2] == ['database', 'finalize']:
    state(Path(args[2]))
elif args[:2] == ['query', 'run']:
    allowed = [root / 'ql/src/m4/LuciSysStatusExec.ql', root / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', root / 'ql/src/diagnostics/ExtractionErrors.ql']
    if len(args) < 3 or Path(args[2]) not in allowed:
        reject('unknown query')
    rest = args[3:]
    unknown = [x for x in rest if not x.startswith(QUERY_RUN_OPTIONS)]
    if unknown:
        reject('unknown query run option ' + ' '.join(unknown))
    for prefix in QUERY_RUN_OPTIONS:
        option(prefix)
    if len(rest) != len(QUERY_RUN_OPTIONS):
        reject('duplicate query run option')
    db = Path(option('--database='))
    st = state(db)
    if option('--search-path=') != os.pathsep.join(
            (str(root / 'extractor-pack'), str(root / 'ql/lib'), str(root / 'ql/src'))):
        reject('wrong search path')
    output = Path(option('--output='))
    if output.parent != db:
        reject('query output not in database')
    output.write_text(json.dumps({'query': Path(args[2]).stem, 'state': st}))
elif args[:2] == ['bqrs', 'decode']:
    info = json.loads(Path(args[-1]).read_text())
    name, st = info['query'], info['state']
    if name == 'LuciSysStatusExec':
        if args[2:-1] != ['--format=csv']:
            reject('semantic decode flags')
        print('"c","col1","c","col3"')
        if st['leg'] == 'main':
            print('"CallExpression","getProcessList via process_list popen /bin/busybox top -bn1 at line 7","CallExpression","popen"')
            print('"CallExpression","getConntrackList via conntrack_list popen /usr/sbin/conntrack -L -o extended at line 49","CallExpression","popen"')
    elif name in ('SuccessfullyExtractedFiles', 'ExtractionErrors'):
        if args[2:-1] != ['--format=json', '--entities=url,string']:
            reject('diagnostic decode flags')
        active = st['leg'] == fault_leg
        paths = st['paths'] if st['routed'] else st['paths'][1:]
        if st['malformed']:
            paths = paths[:1]
        elif active and fault in ('omit0', 'omit1'):
            paths = [path for index, path in enumerate(paths) if index != int(fault[-1])]
        def receipt(p):
            return [{'label': p, 'url': {'uri': Path(p).as_uri(), 'startLine': 0, 'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']
        if name == 'SuccessfullyExtractedFiles':
            columns = [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}]
            tuples = list(map(receipt, paths))
        else:
            columns = [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}]
            message = 'parse error for ' + st['leg']
            tuples = [[{'label': message}, message, 2]] if st['malformed'] or (active and fault == 'error_only') else []
        print(json.dumps({'#select': {'columns': columns, 'tuples': tuples}}))
    else:
        reject('unknown bqrs')
else:
    reject(repr(args))
