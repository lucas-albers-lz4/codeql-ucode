#!/usr/bin/env python3
"""Fresh real-extractor and query gate for the bounded receiver table."""
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent.parent
QUERY = ROOT / 'ql/src/m4/FsReceiverProvenance.ql'
FILES = ['aliased-import.uc', 'argument-escape.uc', 'captured-receiver.uc', 'default-import.uc',
         'escaped-import.uc', 'escaped-receiver.uc', 'formal-shadow.uc',
         'imported-receiver.uc', 'local-shadow.uc', 'member-write.uc',
         'namespace-import.uc', 'no-import.uc', 'optional-call.uc', 'positive.uc', 'reassigned.uc',
         'shadowed-factory.uc', 'shorthand-escape.uc', 'unrelated-object.uc', 'unsupported-callee.uc',
         'unsupported-parenthesized.uc', 'unsupported-subscript.uc',
         'wrong-import.uc', 'usr/share/rpcd/ucode/luci']


def require(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def bag(rows):
    return collections.Counter(json.dumps(r, sort_keys=True) for r in rows)


def expected():
    rows = []
    def pair(path, declaration, init, calls, receiver_length=2):
        for line, col, end, method in calls:
            rows.append([[path, [line, col, line, end]],
                         [path, [line, col, line, col + receiver_length - 1]],
                         [path, declaration], [path, init], method, 'popen'])
    pair('positive.uc', [3, 9, 3, 37], [3, 14, 3, 37], [(5, 5, 18, 'read'), (6, 5, 14, 'close')])
    pair('local-shadow.uc', [3, 9, 3, 37], [3, 14, 3, 37], [(9, 3, 16, 'read'), (10, 3, 12, 'close')])
    pair('formal-shadow.uc', [3, 9, 3, 37], [3, 14, 3, 37], [(8, 3, 16, 'read'), (9, 3, 12, 'close')])
    p = 'usr/share/rpcd/ucode/luci'
    pair(p, [26, 7, 26, 75], [26, 12, 26, 75], [(29, 20, 33, 'read'), (32, 4, 13, 'close')])
    pair(p, [37, 7, 37, 67], [37, 12, 37, 67], [(40, 20, 33, 'read'), (43, 4, 13, 'close')])
    pair(p, [343, 10, 343, 88], [343, 16, 343, 88], [(350, 21, 36, 'read'), (350, 60, 75, 'read'), (384, 5, 15, 'close')], 3)
    pair(p, [400, 10, 400, 88], [400, 16, 400, 88], [(405, 21, 36, 'read'), (405, 60, 75, 'read'), (454, 5, 15, 'close')], 3)
    pair(p, [481, 10, 481, 54], [481, 18, 481, 54], [(486, 21, 38, 'read'), (486, 62, 79, 'read'), (500, 5, 17, 'close')], 5)
    pair(p, [585, 10, 585, 45], [585, 15, 585, 45], [(591, 34, 47, 'read')])
    return rows


def check_rows(actual, want):
    a, e = bag(actual), bag(want)
    require(a == e, f'provenance witness mismatch: missing={e-a} extra={a-e}')


def check_files(actual, source):
    require(collections.Counter(actual) == collections.Counter(FILES), f'extracted file identities mismatch: {actual}')


def entity(value, source, file_only=False):
    url = value['url']
    parsed = urlsplit(url['uri'])
    require(parsed.scheme == 'file' and not parsed.netloc and not parsed.query and not parsed.fragment, f'bad uri {url}')
    path = Path(unquote(parsed.path, errors='strict'))
    require(path.is_absolute() and '..' not in path.parts, f'bad path {path}')
    name = path.relative_to(source).as_posix()
    coords = [url[k] for k in ('startLine', 'startColumn', 'endLine', 'endColumn')]
    require(all(type(n) is int for n in coords), f'bad coords {url}')
    if file_only:
        require(coords == [0, 0, 0, 0], f'bad file entity {url}')
        return name
    require(all(n > 0 for n in coords), f'bad span {url}')
    return [name, coords]


def main():
    require(QUERY.is_file(), f'missing query: {QUERY}')
    codeql = shutil.which('codeql')
    require(codeql is not None, 'codeql missing from PATH')
    pack = ROOT / 'extractor-pack'
    require(pack.is_dir(), 'extractor-pack missing: build it first')
    work = Path(tempfile.mkdtemp(prefix='receiver-provenance-')).resolve()
    print(f'evidence directory: {work}', flush=True)
    source = work / 'source/ql/test/extractor-smoke'
    source.mkdir(parents=True)
    for f in FILES:
        inp = ROOT / ('ql/test/extractor-smoke/' + f if f.endswith('/luci') else 'ql/test/receiver-provenance/' + f)
        out = source / f
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inp, out)
    # A genuine source file exists beneath the staged root but is outside the
    # selected inputs and the index include patterns. It must remain unindexed.
    substitute = 'ssa_neg'
    substitute_input = ROOT / 'ql/test/extractor-smoke' / substitute
    require(substitute not in FILES and substitute_input.is_file(), 'invalid out-of-set substitute')
    shutil.copyfile(substitute_input, source / substitute)
    require((source / substitute).is_file(), 'out-of-set substitute missing')
    production = source / 'usr/share/rpcd/ucode/luci'
    require(hashlib.sha256(production.read_bytes()).hexdigest() == '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e', 'production fixture digest mismatch')
    db = work / 'db'
    search = os.pathsep.join(map(str, [pack, ROOT / 'ql/lib', ROOT / 'ql/src']))
    def run(*args, cwd=ROOT):
        cmd = [str(codeql), *map(str, args)]
        result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        (work / ('command-%02d.log' % len(list(work.glob('command-*.log'))))).write_text(json.dumps(cmd) + '\n' + result.stdout + result.stderr)
        require(result.returncode == 0, f'command failed {cmd}: {result.stdout}\n{result.stderr}')
        return result.stdout
    run('database', 'init', db, '--language=ucode', f'--search-path={search}', f'--source-root={source}')
    try:
        run('database', 'index-files', db, '--language=ucode', '--include=**/*.uc', '--include=**/luci', f'--working-dir={source}')
    finally:
        receipt = db / 'trap/ucode/routing.json'
        if receipt.is_file():
            shutil.copyfile(receipt, work / 'routing.json')
    routing = json.loads((work / 'routing.json').read_text())
    decisions = routing['decisions']
    routed = [Path(d['path']).relative_to(source).as_posix() for d in decisions if d['status'] == 'plain_route_selected']
    check_files(routed, source)
    require(len(decisions) == len(FILES), 'unexpected routing decisions')
    run('database', 'finalize', db)
    def query(path, label, library=None):
        out = work / (label + '.bqrs')
        library = library or ROOT / 'ql/lib'
        run('query', 'run', path, f'--database={db}', f'--search-path={search}', f'--additional-packs={library}', f'--output={out}', '--threads=1', '--ram=2048', '--no-default-compilation-cache', '--no-use-precompiled', f'--compilation-cache={work / ("cache-" + label)}')
        data = run('bqrs', 'decode', '--format=json', '--entities=url,string', out)
        (work / (label + '.json')).write_text(data)
        return json.loads(data)['#select']['tuples']
    success = query(ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', 'files')
    check_files([entity(row[0], source, True) for row in success], source)
    require(not query(ROOT / 'ql/src/diagnostics/ExtractionErrors.ql', 'errors'), 'extraction errors')
    raw = query(QUERY, 'provenance')
    rows = [[entity(x, source) for x in row[:4]] + row[4:] for row in raw]
    check_rows(rows, expected())
    # Guard against oracle weakening: equal-count wrong file and each witness.
    wrong_files = list(FILES); wrong_files[0] = substitute
    require(len(wrong_files) == len(FILES) and (source / substitute).is_file(), 'invalid substitution control')
    try: check_files(wrong_files, source)
    except RuntimeError: pass
    else: raise RuntimeError('same-count file substitution passed')
    for column in range(4):
        altered = [list(row) for row in rows]
        altered[0][column] = rows[1][column] if rows[1][column] != rows[0][column] else rows[-1][column]
        try: check_rows(altered, expected())
        except RuntimeError: pass
        else: raise RuntimeError(f'same-count witness substitution passed: {column}')
    # An actual query substitutes the other branch's declaration and initializer
    # without changing the call, receiver, strings, or overall row count.
    mutant = work / 'fault-pack'
    (mutant / 'ql').mkdir(parents=True)
    shutil.copyfile(ROOT / '.codeqlmanifest.json', mutant / '.codeqlmanifest.json')
    shutil.copytree(ROOT / 'ql/src', mutant / 'ql/src')
    shutil.copytree(ROOT / 'ql/lib', mutant / 'ql/lib')
    inventory = mutant / 'ql/src/m4/ReceiverInventory.ql'
    inventory.write_text('''import codeql.ucode.ast.internal.TreeSitter
from UCODE::CallExpression call, UCODE::MemberExpression member
where member = call.getFunction() and member.getProperty().getValue() = ["read", "close"]
select call, member.getObject(), member.getProperty().getValue()
''')
    inventory_rows = query(inventory, 'member-inventory', mutant / 'ql/lib')
    member_files = {entity(row[0], source)[0] for row in inventory_rows}
    require(member_files == set(FILES), f'controls missing member-call observations: {set(FILES) - member_files}')
    print(f'PASS nonvacuous member-call inventory in all {len(FILES)} files')

    # Source-level fault injections: the real unchanged query must expose the
    # designated false bindings/uses and fail the same full witness oracle.
    module = mutant / 'ql/src/m4/FsReceiverOrigin.qll'
    original = module.read_text()
    faults = [
        ('binding', 'variable.getAstNode() = TVariableDeclarator(decl) and',
         'decl.getName().getValue() = receiver.getValue() and\n    decl.getLocation().getFile() = call.getLocation().getFile() and',
         {('local-shadow.uc', 6), ('local-shadow.uc', 7)}),

        ('escape', '    not exists(VariableAccess other |\n      other.getVariable() = variable and not allowedUse(other, decl)\n    )',
         '    variable.getName() = receiver.getValue()',
         {('escaped-receiver.uc', 5), ('argument-escape.uc', 5), ('shorthand-escape.uc', 5)}),
    ]
    for name, before, after, wanted in faults:
        require(original.count(before) == 1, f'cannot isolate {name} mutation')
        mutated = original.replace(before, after) + f'\n// fault {name}\n'
        (work / ('fault-' + name + '.qll')).write_text(mutated)
        module.write_text(mutated)
        result = [[entity(x, source) for x in row[:4]] + row[4:]
                  for row in query(mutant / 'ql/src/m4/FsReceiverProvenance.ql', 'fault-' + name, mutant / 'ql/lib')]
        ids = {(row[0][0], row[0][1][0]) for row in result}
        require(wanted <= ids, f'{name} fault did not expose intended control calls: {wanted - ids}')
        try: check_rows(result, expected())
        except RuntimeError: pass
        else: raise RuntimeError(f'{name} fault unexpectedly passed')
        print(f'PASS real {name} guard fault rejected; rows={len(result)}')
    # Each optional syntax has its own receiver and full source-derived witness.
    # Removing only the corresponding guard must add exactly that witness.
    optional_faults = [
        ('optional-member',
         '    not exists(call.getOptionalChain()) and\n    not exists(member.getOptionalChain())',
         '    not exists(call.getOptionalChain())', 'unsupported-callee.uc', 17),
        ('optional-call',
         '    not exists(call.getOptionalChain()) and\n', '', 'optional-call.uc', 18),
    ]
    for name, before, after, path, end in optional_faults:
        require(original.count(before) == 1, f'cannot isolate {name} mutation')
        mutated = original.replace(before, after) + f'\n// fault {name}\n'
        (work / ('fault-' + name + '.qll')).write_text(mutated)
        module.write_text(mutated)
        result = [[entity(x, source) for x in row[:4]] + row[4:]
                  for row in query(mutant / 'ql/src/m4/FsReceiverProvenance.ql', 'fault-' + name, mutant / 'ql/lib')]
        extra = [[path, [4, 3, 4, end]], [path, [4, 3, 4, 4]],
                 [path, [3, 9, 3, 37]], [path, [3, 14, 3, 37]], 'read', 'popen']
        require(bag(result) == bag(expected() + [extra]), f'{name} fault has unexpected full witness delta')
        try: check_rows(result, expected())
        except RuntimeError: pass
        else: raise RuntimeError(f'{name} fault unexpectedly passed')
        print(f'PASS real {name} guard fault rejected with exact extra witness')
    module.write_text(original)
    fault = mutant / 'ql/src/m4/FsReceiverWrongWitness.ql'
    fault.write_text('''import FsReceiverOrigin
from UCODE::CallExpression call, UCODE::VariableDeclarator decl,
  UCODE::CallExpression initializer, UCODE::Identifier receiver,
  UCODE::VariableDeclarator reported, string method, string factory
where
  receiverOrigin(call, decl, initializer, method, factory) and
  directMember(call, receiver, method) and
  (
    call.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
    decl.getLocation().getStartLine() = 26 and
    reported.getLocation().getFile() = call.getLocation().getFile() and
    reported.getLocation().getStartLine() = 37
    or
    not (call.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
         decl.getLocation().getStartLine() = 26) and reported = decl
  )
select call, receiver, reported, reported.getValue(), method, factory
''')
    wrong = [[entity(x, source) for x in row[:4]] + row[4:]
             for row in query(fault, 'wrong-witness', mutant / 'ql/lib')]
    intended = []
    for row in expected():
        r = list(row)
        if r[0][0] == 'usr/share/rpcd/ucode/luci' and r[2][1][0] == 26:
            r[2] = [r[2][0], [37, 7, 37, 67]]
            r[3] = [r[3][0], [37, 12, 37, 67]]
        intended.append(r)
    require(len(wrong) == len(rows) and bag(wrong) == bag(intended), 'wrong-witness query did not exercise the intended exact substitution')
    try: check_rows(wrong, expected())
    except RuntimeError: pass
    else: raise RuntimeError('real same-count wrong-witness query passed')
    print('PASS real same-count wrong-declaration/initializer query rejected')
    print(f'PASS exact clean files={len(FILES)}, exact source-provenance witnesses={len(rows)}')


if __name__ == '__main__':
    main()
