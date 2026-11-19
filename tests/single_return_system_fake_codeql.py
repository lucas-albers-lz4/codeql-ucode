"""Strict synthetic CodeQL shim for composed single-return smoke tests only."""
import json
import os
from pathlib import Path
import sys

root = Path(os.environ['SHAPE_FAKE_ROOT']).resolve()
state_path = Path(os.environ['SHAPE_FAKE_STATE'])
trace_path = Path(os.environ['SHAPE_FAKE_TRACE'])
case = os.environ['SHAPE_FAKE_CASE']
args = sys.argv[1:]
NAMES = ('comment-positive conditional-expression duplicate-method escaped-literal extra-arg '
         'guard-no-call member-guard member methods-alias nested nonliteral positive '
         'shadow unknown-helper real').split()
COLUMNS = [{'name': 'source_path', 'kind': 'String'}, {'name': 'start_line', 'kind': 'Integer'},
           {'name': 'start_column', 'kind': 'Integer'}, {'name': 'end_line', 'kind': 'Integer'},
           {'name': 'end_column', 'kind': 'Integer'}, {'name': 'command', 'kind': 'String'}]


def reject(message):
    sys.exit('fake codeql rejected: ' + message + ': ' + repr(args))


def require(value, message):
    if not value:
        reject(message)


def record(kind, name=''):
    with trace_path.open('a') as f:
        f.write(json.dumps({'kind': kind, 'name': name, 'args': args}) + '\n')


def get_state():
    require(state_path.is_file(), 'missing init state')
    return json.loads(state_path.read_text())


def table(columns, rows):
    return {'#select': {'columns': columns, 'tuples': rows}}


def entity(path):
    return [{'label': str(path), 'url': {'uri': path.as_uri(), 'startLine': 0,
             'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']


def shape_rows():
    prefix = 'modules/{}/root/usr/share/rpcd/ucode/luci'
    return [[prefix.format('comment-positive'), 4, 22, 4, 40, '/bin/true'],
            [prefix.format('positive'), 3, 22, 3, 40, '/bin/true'],
            [prefix.format('real'), 532, 21, 532, 68, '/sbin/block detect > /etc/config/fstab']]


def shape_for(name):
    rows = shape_rows()
    prefix = 'modules/{}/root/usr/share/rpcd/ucode/luci'
    if name == 'body-veto':
        rows += [[prefix.format(n), 4, 22, 4, 40, '/bin/true'] for n in ('guard-no-call', 'member-guard', 'unknown-helper')]
    elif name == 'literal-veto':
        rows += [[prefix.format('escaped-literal'), 3, 22, 3, 43, '/bin/tre']]
    elif name == 'wrong-start-column':
        rows = [[r[0], r[1], r[2] + 1, *r[3:]] for r in rows]
    return rows


if len(args) == 3 and args[:2] == ['pack', 'install']:
    require(args[2] in [str(root / 'ql/lib'), str(root / 'ql/src')], 'invalid pack')
    require(Path(args[2]).is_dir(), 'missing pack')
    record('pack', Path(args[2]).name)
elif args[:2] == ['database', 'init']:
    require(len(args) == 6, 'invalid init arity')
    db = Path(args[2])
    work = db.parent
    src = work / 'source'
    search = os.pathsep.join(map(str, (root / 'extractor-pack', root / 'ql/lib', root / 'ql/src')))
    require(work.parent == Path(os.environ['TMPDIR']).resolve() and work.name.startswith('single-return-system.'), 'invalid work root')
    require(args == ['database', 'init', str(work / 'database'), '--language=ucode',
                     '--search-path=' + search, '--source-root=' + str(src)], 'invalid init arguments')
    require(not state_path.exists(), 'duplicate init')
    expected = [src / 'modules' / n / 'root/usr/share/rpcd/ucode/luci' for n in NAMES]
    require(all(p.is_file() for p in expected), 'missing staged fixture')
    db.mkdir(parents=True)
    state_path.write_text(json.dumps({'work': str(work), 'db': str(db), 'src': str(src), 'search': search}))
    record('init')
elif args[:2] == ['database', 'index-files']:
    s = get_state()
    require(args == ['database', 'index-files', s['db'], '--language=ucode',
                     '--include=**/rpcd/ucode/luci', '--working-dir=' + s['src']], 'invalid index arguments')
    receipt = Path(s['db']) / 'trap/ucode/routing.json'
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{}')
    # Real file exists outside the selected identity set and has the same layout.
    outside = Path(s['src']) / 'modules/outside/root/usr/share/rpcd/ucode/luci'
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text('return {};\n')
    record('index')
elif args[:2] == ['database', 'finalize']:
    s = get_state()
    require(args == ['database', 'finalize', s['db']], 'invalid finalize arguments')
    record('finalize')
elif args[:2] == ['query', 'run']:
    s = get_state()
    require(len(args) >= 3, 'missing query operand')
    query = Path(args[2])
    require(query.is_file(), 'query operand missing')
    diagnostic_paths = {str(root / 'ql/src/diagnostics' / (n + '.ql')): n
                        for n in ('SuccessfullyExtractedFiles', 'ExtractionErrors')}
    baseline = str(root / 'ql/src/m4/SingleReturnFixedSystemSourceShape.ql')
    if str(query) in diagnostic_paths:
        name = diagnostic_paths[str(query)]
        output = str(Path(s['db']) / (name + '.bqrs'))
        require(args == ['query', 'run', str(query), '--database=' + s['db'], '--search-path=' + s['search'],
                         '--output=' + output, '--threads=1', '--ram=2048'], 'invalid diagnostic query args')
        kind = 'diagnostic'
    elif str(query) == baseline:
        name = 'baseline'
        output = str(Path(s['db']) / 'shape.bqrs')
        require(args == ['query', 'run', str(query), '--database=' + s['db'], '--search-path=' + s['search'],
                         '--output=' + output, '--threads=1', '--ram=2048'], 'invalid semantic query args')
        kind = 'semantic'
    else:
        work = Path(s['work'])
        pack = work / 'mutation-pack'
        possible = {str(pack / 'ql/src/m4' / ('SingleReturnMutation-' + n + '.ql')): n
                    for n in ('body-veto', 'literal-veto', 'wrong-start-column')}
        require(str(query) in possible, 'unknown query operand')
        name = possible[str(query)]
        output = str(work / ('mutation-' + name + '.bqrs'))
        search = os.pathsep.join(map(str, (root / 'extractor-pack', pack / 'ql/lib', pack / 'ql/src')))
        require(args == ['query', 'run', str(query), '--database=' + s['db'], '--search-path=' + search,
                         '--additional-packs=' + str(pack / 'ql/lib'), '--threads=1', '--ram=2048',
                         '--no-default-compilation-cache', '--compilation-cache=' + str(work / ('mutation-cache-' + name)),
                         '--output=' + output], 'invalid mutation query args')
        kind = 'semantic'
    Path(output).write_text(name)
    record(kind, name)
elif args[:2] == ['bqrs', 'decode']:
    s = get_state()
    require(len(args) == 5 and args[2:4] == ['--format=json', '--entities=url,string'], 'invalid decode flags')
    bqrs = Path(args[4])
    allowed = {str(Path(s['db']) / (name + '.bqrs')): name for name in ('SuccessfullyExtractedFiles', 'ExtractionErrors')}
    allowed[str(Path(s['db']) / 'shape.bqrs')] = 'baseline'
    for n in ('body-veto', 'literal-veto', 'wrong-start-column'):
        allowed[str(Path(s['work']) / ('mutation-' + n + '.bqrs'))] = n
    require(str(bqrs) in allowed and bqrs.is_file() and bqrs.read_text() == allowed[str(bqrs)], 'invalid bqrs operand')
    name = allowed[str(bqrs)]
    if name == 'SuccessfullyExtractedFiles':
        paths = [Path(s['src']) / 'modules' / n / 'root/usr/share/rpcd/ucode/luci' for n in NAMES]
        require(all(p.is_file() for p in paths), 'selected file missing')
        rows = [entity(p) for p in paths]
        if case == 'omission':
            rows.pop(0)
        elif case == 'duplicate':
            rows[0] = rows[1]
        elif case == 'substitution':
            outside = Path(s['src']) / 'modules/outside/root/usr/share/rpcd/ucode/luci'
            require(outside.is_file() and outside not in paths, 'substitution must exist and be out of set')
            rows[0] = entity(outside)
        result = table([{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}], rows)
    elif name == 'ExtractionErrors':
        errors = [[{'label': 'synthetic parse error'}, 'error', 2]] if case == 'error' else []
        result = table([{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}], errors)
    else:
        result = table(COLUMNS, shape_for(name))
    record('decode', name)
    print(json.dumps(result))
else:
    reject('unknown command')
