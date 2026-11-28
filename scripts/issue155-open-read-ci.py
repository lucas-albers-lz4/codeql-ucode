#!/usr/bin/env python3
"""WIP focused source-declared literal-r open regression."""
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'ql/test/issue155-open-read'
PACK = (ROOT / 'extractor-pack').resolve()
spec = importlib.util.spec_from_file_location('stat_gate', ROOT / 'scripts/issue155-stat-ci.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
require = common.require


def model_rows(data):
    return Counter((r[0], *(x['id'] for x in r[1:])) for r in common.oracle.tuples(data))


def raw_node(rows, path, kind, coordinates):
    found = [r[7]['id'] for r in rows if r[0] == path and r[1] == kind and r[3:7] == coordinates]
    require(len(found) == 1, f'{path}: raw {kind} at {coordinates} is absent or ambiguous')
    return found[0]


def verify_projection(results, manifest):
    raw = common.oracle.tuples(results['raw'])
    edges = common.oracle.tuples(results['edges'])
    expected = []
    optional = []
    expected_fragments = []
    expected_imports = []
    entries = [manifest['real']] + manifest['controls']
    for entry in entries:
        if not entry['expected_count']:
            continue
        path = entry['path']
        selected = entry.get('selected', entry)
        call_pos = selected['call'] if isinstance(selected['call'], list) else selected['call']['start'] + selected['call']['end_inclusive']
        call = raw_node(raw, path, 'CallExpression', call_pos)
        callee = raw_node(raw, path, 'Identifier', selected['callee'])
        imp = raw_node(raw, path, 'ImportStatement', selected['import_statement'])
        specifier = raw_node(raw, path, 'ImportSpecifier', selected['import_specifier'])
        imported_name = raw_node(raw, path, 'Identifier', selected['import_specifier'])
        module = raw_node(raw, path, 'String', selected['import_module'])
        module_fragment = raw_node(raw, path, 'StringFragment', selected['module_fragment'])
        argument = raw_node(raw, path, 'CallExpression' if path.endswith('luci.upnp') else 'String', selected['path_argument'])
        mode = raw_node(raw, path, 'String', selected['mode_argument'])
        def targets(source, field):
            return [(r[4], r[5]['id']) for r in edges if r[0] == path and r[1] == {'id':source} and r[3] == field]
        require(targets(imp, 'import-source') == [(-1,module)] and targets(module, 'string-child') == [(0,module_fragment)], f'{path}: source module edges')
        require(targets(specifier, 'import-name') == [(-1,imported_name)] and not targets(specifier, 'import-alias'), f'{path}: import name/alias')
        clause = targets(imp, 'import-clause')
        require(len(clause) == 1, f'{path}: import clause')
        named = targets(clause[0][1], 'import-named')
        require(len(named) == 1 and sum(target == specifier for _,target in targets(named[0][1], 'named-import')) == 1, f'{path}: specifier ownership')
        expected_imports.append((path,imp,module_fragment,'fs'))
        require(targets(call, 'call-function') == [(-1, callee)], f'{path}: callee edge')
        arguments = targets(call, 'call-arguments')
        require(len(arguments) == 1, f'{path}: argument list identity')
        children = sorted(targets(arguments[0][1], 'argument'))
        expected_children = [(0, argument), (1, mode)]
        if 'third_argument' in selected:
            third = raw_node(raw, path, 'Identifier', selected['third_argument'])
            expected_children.append ( (2, third) )
            optional.append((path, call, third))
        require(children == expected_children, f'{path}: exact argument edges')
        fragment = raw_node(raw, path, 'StringFragment', selected['mode_fragment'])
        fragments = targets(mode, 'string-child')
        require(fragments == [(0, fragment)], f'{path}: sole mode fragment')
        expected_fragments.append((path, call, 1, mode, fragment, 'r'))
        frag = [r for r in raw if r[0] == path and r[7] == {'id':fragments[0][1]}]
        require(len(frag) == 1 and frag[0][1] == 'StringFragment', f'{path}: mode fragment identity')
        expected.append((path, call, callee, argument, mode))
    imports = Counter((r[0],r[1]['id'],r[2]['id'],r[3]) for r in common.oracle.tuples(results['import_fragments']))
    for imported in expected_imports:
        require(imports[imported] == 1, 'import module fragment value/identity')
    actual_fragments = Counter((r[0], r[1]['id'], r[2], r[3]['id'], r[4]['id'], r[5]) for r in common.oracle.tuples(results['argument_fragments']))
    for fragment in expected_fragments:
        require(actual_fragments[fragment] == 1, 'mode fragment value/identity')
    def exact_model(data):
        require(model_rows(data) == Counter(expected), 'model exact identities')
    exact_model(results['model'])
    require(model_rows(results['membership']) == Counter((r[0],r[1]) for r in expected), 'membership exact identities')
    require(model_rows(results['permission']) == Counter(optional), 'third argument identities')
    wrong = [(p,c,f,m,m) for p,c,f,a,m in expected]
    require(model_rows(results['wrong_path']) == Counter(wrong), 'wrong path mutant projection')
    try:
        exact_model(results['wrong_path'])
    except ValueError as exc:
        require(str(exc) == 'model exact identities', 'wrong path failed for unrelated reason')
    else:
        raise ValueError('wrong path mutant passed model comparator')
    return expected




def verify_control_witnesses(results, manifest, stage):
    raw = common.oracle.tuples(results['raw'])
    edges = common.oracle.tuples(results['edges'])
    for entry in manifest['controls']:
        path = entry['path']
        data = (stage/path).read_bytes().splitlines()
        for anchor in entry['calls']:
            line, column = anchor['start']
            endline, endcolumn = anchor['end_inclusive']
            require(line == endline and data[line-1][column-1:endcolumn] == anchor['text'].encode(), f'{path}: call anchor bytes')
            raw_node(raw, path, 'CallExpression', anchor['start'] + anchor['end_inclusive'])
    zero = next(e for e in manifest['controls'] if e['path'] == 'controls/zero.uc')
    a = zero['calls'][0]
    call = raw_node(raw, zero['path'], 'CallExpression', a['start']+a['end_inclusive'])
    args = [r[5]['id'] for r in edges if r[0] == zero['path'] and r[1] == {'id':call} and r[3] == 'call-arguments']
    require(len(args) == 1 and not any(r[0] == zero['path'] and r[1] == {'id':args[0]} and r[3] == 'argument' for r in edges), 'zero-argument raw witness')
    for name in ('wrapped','property-read'):
        path = 'controls/'+name+'.uc'
        require(any(r[0] == path and r[1] == ('ParenthesizedExpression' if name == 'wrapped' else 'MemberExpression') for r in raw), path+': raw syntax witness')
    path = 'controls/property-read.uc'
    require(not any(r[0] == path and r[1] == 'CallExpression' for r in raw), 'property read has a call')
    path = 'controls/wrapped.uc'
    line = (stage/path).read_bytes().splitlines()[1]
    close = line.rfind(b')')+1
    wrapped_call = raw_node(raw,path,'CallExpression',[2,1,2,close])
    paren = raw_node(raw,path,'ParenthesizedExpression',[2,1,2,6])
    wrapped_id = raw_node(raw,path,'Identifier',[2,2,2,5])
    require(any(r[0] == path and r[1] == {'id':wrapped_call} and r[3] == 'call-function' and r[5] == {'id':paren} for r in edges), 'wrapped call edge')
    require(any(r[0] == path and r[1] == {'id':paren} and r[3] == 'parenthesized-child' and r[5] == {'id':wrapped_id} for r in edges), 'wrapped identifier edge')
    path = 'controls/property-read.uc'
    line = (stage/path).read_bytes().splitlines()[1]
    start = line.index(b'open.name')+1
    member = raw_node(raw,path,'MemberExpression',[2,start,2,start+8])
    object_id = raw_node(raw,path,'Identifier',[2,start,2,start+3])
    property_id = raw_node(raw,path,'PropertyIdentifier',[2,start+5,2,start+8])
    require(any(r[0] == path and r[1] == {'id':member} and r[3] == 'member-object' and r[5] == {'id':object_id} for r in edges), 'property receiver edge')
    require(any(r[0] == path and r[1] == {'id':member} and r[3] == 'member-property' and r[5] == {'id':property_id} for r in edges), 'property name edge')
    kinds = {'omitted':['String'], 'read-plus':['String','String'], 'write':['String','String'],
             'dynamic':['String','Identifier'], 'extra-fragment':['String','String'],
             'wrong-slot':['String','String'], 'spread-path':['SpreadElement','String'],
             'spread-mode':['String','SpreadElement'], 'spread-third':['String','String','SpreadElement'],
             'four':['String','String','Identifier','Identifier'], 'malformed':['String','String']}
    for name, wanted in kinds.items():
        entry = next(e for e in manifest['controls'] if e['path'] == 'controls/'+name+'.uc')
        anchor = entry['calls'][0]
        call = raw_node(raw, entry['path'], 'CallExpression', anchor['start']+anchor['end_inclusive'])
        owners = [r[5]['id'] for r in edges if r[0] == entry['path'] and r[1] == {'id':call} and r[3] == 'call-arguments']
        require(len(owners) == 1, name+': arguments owner')
        children = sorted((r[4],r[5]['id']) for r in edges if r[0] == entry['path'] and r[1] == {'id':owners[0]} and r[3] == 'argument')
        require([i for i,_ in children] == list(range(len(wanted))), name+': argument indexes')
        for (_,child),kind in zip(children,wanted):
            matches = [r for r in raw if r[0] == entry['path'] and r[7] == {'id':child}]
            require(len(matches) == 1 and matches[0][1] == kind, name+': argument type')
        if name == 'extra-fragment':
            mode = children[1][1]
            fragments = sorted((r[4],r[5]['id']) for r in edges if r[0] == entry['path'] and r[1] == {'id':mode} and r[3] == 'string-child')
            require([i for i,_ in fragments] == [0,1], 'escaped mode has two children')
            require([next(r[1] for r in raw if r[0] == entry['path'] and r[7] == {'id':child}) for _,child in fragments] == ['StringFragment','EscapeSequence'], 'escaped mode child types')
    def identifier(path, line_number, offset=0):
        line = (stage/path).read_bytes().splitlines()[line_number-1]
        index = line.find(b'open', offset)
        require(index >= 0, path+': source identifier anchor')
        return raw_node(raw, path, 'Identifier', [line_number,index+1,line_number,index+4]), index
    for name, line, field in (('shadow-lexical',2,'declarator-name'), ('write-binding',2,'assignment-left'), ('competing',2,'formal')):
        path = 'controls/'+name+'.uc'
        ident,_ = identifier(path,line)
        matches = [r for r in edges if r[0] == path and r[3] == field and r[5] == {'id':ident}]
        require(len(matches) == 1, path+': competing binding/write edge')
    path = 'controls/alias.uc'
    imported, start = identifier(path,1)
    alias,_ = identifier(path,1,start+4)
    names = [r[1]['id'] for r in edges if r[0] == path and r[3] == 'import-name' and r[5] == {'id':imported}]
    require(len(names) == 1 and any(r[0] == path and r[1] == {'id':names[0]} and r[3] == 'import-alias' and r[5] == {'id':alias} for r in edges), 'same-name alias edge')
    path = 'controls/wrong-module.uc'
    fragments = [r for r in common.oracle.tuples(results['import_fragments']) if r[0] == path]
    require(len(fragments) == 1 and fragments[0][3] == 'other', 'wrong module fragment')
    path = 'controls/duplicate-name.uc'
    require(len([r for r in common.oracle.tuples(results['import_fragments']) if r[0] == path]) == 2, 'duplicate import witness')
    fragments = common.oracle.tuples(results['argument_fragments'])
    for name, index, wanted, call_index in (('read-plus',1,'r+',0), ('write',1,'w',0),
                                            ('wrong-slot',0,'r',0), ('wrong-slot',1,'/tmp/a',0),
                                            ('same-file-wx',1,'wx',1), ('extra-fragment',1,'r',0)):
        entry = next(e for e in manifest['controls'] if e['path'] == 'controls/'+name+'.uc')
        anchor = entry['calls'][call_index]
        call = raw_node(raw,entry['path'],'CallExpression',anchor['start']+anchor['end_inclusive'])
        matches = [r for r in fragments if r[0] == entry['path'] and r[1] == {'id':call} and r[2] == index]
        require(len(matches) == 1 and matches[0][5] == wanted, name+': mode/path fragment value')
        require(any(r[0] == entry['path'] and r[1] == matches[0][3] and r[3] == 'string-child' and r[5] == matches[0][4] for r in edges), name+': literal fragment edge')
    path = 'controls/before-import.uc'
    before = next(e for e in manifest['controls'] if e['path'] == path)['calls'][0]
    call = raw_node(raw,path,'CallExpression',before['start']+before['end_inclusive'])
    imports = [r for r in raw if r[0] == path and r[1] == 'ImportStatement']
    require(len(imports) == 1 and imports[0][3] == 2 and before['end_inclusive'][0] < imports[0][3], 'source order witness')
    path = 'controls/duplicate-name.uc'
    imports = [r for r in raw if r[0] == path and r[1] == 'ImportStatement']
    require(len(imports) == 2 and {r[3] for r in imports} == {1,2}, 'duplicate source order')
    for line in (1,2):
        ident,_ = identifier(path,line)
        require(len([r for r in edges if r[0] == path and r[3] == 'import-name' and r[5] == {'id':ident}]) == 1, 'duplicate name edge')
    path = 'controls/optional.uc'
    entry = next(e for e in manifest['controls'] if e['path'] == path)
    anchor = entry['calls'][0]
    call = raw_node(raw, path, 'CallExpression', anchor['start']+anchor['end_inclusive'])
    require(len([r for r in edges if r[0] == path and r[1] == {'id':call} and r[3] == 'call-optional']) == 1, 'optional chain witness')

def verify_mutations(results, manifest, expected):
    raw = common.oracle.tuples(results['raw'])
    entries = {e['path']:e for e in manifest['controls']}
    baseline = Counter((r[0],r[1]) for r in expected)
    def call(name, index=0):
        entry = entries['controls/'+name+'.uc']
        anchor = entry['calls'][index]
        return (entry['path'], raw_node(raw, entry['path'], 'CallExpression', anchor['start']+anchor['end_inclusive']))
    def call_rows(key):
        return Counter((r[0],r[1]['id']) for r in common.oracle.tuples(results[key]))
    require(call_rows('extra_fragment') == baseline + Counter([call('extra-fragment')]), 'extra-fragment mutant')
    require(call_rows('wrong_mode') == Counter([call('wrong-slot')]), 'wrong mode slot mutant')
    require(call_rows('wx_membership') == Counter([call('same-file-wx', 1)]), 'wx disjointness')
    any_mode = [call('read-plus'), call('write'), call('wrong-slot'), call('same-file-wx', 1)]
    require(call_rows('any_mode') == baseline + Counter(any_mode), 'literal mode mutant')
    shapes = Counter((kind,p,c) for kind in ('arity','spread-path','spread-permission') for p,c in baseline.elements())
    for kind, name in (('arity','four'), ('spread-path','spread-path'), ('spread-permission','spread-third')):
        p,c = call(name)
        shapes[(kind,p,c)] += 1
    actual_shapes = Counter((r[0],r[1],r[2]['id']) for r in common.oracle.tuples(results['shape']))
    require(actual_shapes == shapes, 'shape mutants')
    guards = {'declaration':'shadow-lexical', 'write':'write-binding', 'module':'wrong-module',
              'alias':'alias', 'optional':'optional', 'unique':'duplicate-name', 'diagnostic':'malformed'}
    for guard, name in guards.items():
        require(call_rows('guard_'+guard) == baseline + Counter([call(name)]), guard+' guard mutant')


def guard_mutations():
    tail = """
from UCODE::CallExpression call, UCODE::AstNode pathArg, UCODE::String mode
where sourceDeclaredFsCall(call, "open") and pathArg = call.getArguments().getChild(0) and pathArg instanceof UCODE::Expression and
  mode = call.getArguments().getChild(1) and mode.getChild(0).(UCODE::StringFragment).getValue() = "r" and not exists(mode.getChild(1)) and
  (not exists(call.getArguments().getChild(2)) or call.getArguments().getChild(2) instanceof UCODE::Expression) and
  not exists(int i | i != 0 and i != 1 and i != 2 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node
"""
    source = (ROOT/'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text()
    return common.inputs.source_declared_fs_guard_queries(source, family='open read', id_prefix='issue155-open-read-guard-', selection=tail)

def stage_inputs(stage):
    manifest = common.inputs.load(FIXTURES / 'manifest.json')
    entries = [manifest['real']] + manifest['controls']
    names = {'positive-two','positive-three','same-file-wx','omitted','read-plus','write','dynamic',
             'extra-fragment','wrong-slot','alias','wrong-module','duplicate','competing','write-binding',
             'optional','spread-path','spread-mode','spread-third','four','malformed','zero','wrapped',
             'before-import','duplicate-name','property-read','shadow-lexical'}
    require({e['path'] for e in manifest['controls']} == {'controls/'+n+'.uc' for n in names}, 'control inventory')
    require(len(entries) == 27 and len({e['path'] for e in entries}) == 27, 'fixture inventory')
    require(FIXTURES.resolve() == FIXTURES and not any(path.is_symlink() for path in FIXTURES.rglob('*')), 'fixture path alias')
    actual_controls = {str(path.relative_to(FIXTURES)) for path in (FIXTURES/'controls').rglob('*') if path.is_file()}
    require(actual_controls == {e['path'] for e in manifest['controls']}, 'control file inventory')
    positive = {'positive-two','positive-three','same-file-wx','duplicate'}
    for entry in manifest['controls']:
        require(type(entry['expected_count']) is int and entry['expected_count'] == int(Path(entry['path']).stem in positive), 'control cohort')
    require(manifest['real']['path'] == 'usr/share/rpcd/ucode/luci.upnp' and manifest['real']['expected_count'] == 1, 'real cohort')
    for entry in entries:
        source = FIXTURES / entry['path']
        require(not source.is_symlink() and source.resolve() == source and source.is_file(), f'fixture file: {source}')
        data = source.read_bytes()
        require(len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], f'fixture bytes: {source}')
        if entry['expected_count']:
            selected = entry.get('selected', entry)
            lines = data.splitlines()
            def slice_at(coords):
                line, start, endline, end = coords
                require(line == endline and 0 < line <= len(lines) and 0 < start <= end <= len(lines[line-1]), 'anchor bounds')
                return lines[line-1][start-1:end]
            roles = {'callee':b'open', 'import_specifier':b'open', 'import_module':b"'fs'",
                     'module_fragment':b'fs', 'mode_argument':b"'r'", 'mode_fragment':b'r',
                     'path_argument':b"uci.get('upnpd', 'config', 'upnp_lease_file')" if entry is manifest['real'] else b"'/tmp/a'"}
            if 'third_argument' in selected: roles['third_argument'] = b'mode'
            for role, value in roles.items():
                require(slice_at(selected[role]) == value, f'{entry["path"]}: source anchor {role}')
            call = selected['call']
            call_coords = call if isinstance(call,list) else call['start'] + call['end_inclusive']
            require(slice_at(call_coords).startswith(b'open(') and slice_at(call_coords).endswith(b')'), f'{entry["path"]}: call anchor')
        target = stage / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return manifest, entries


def verify_diagnostics(stage, manifest, entries, results):
    bad = manifest['malformed_diagnostic']
    good = [entry for entry in entries if entry['path'] != bad['path']]
    require(results['success']['#select']['columns'] == [{'name':'f','kind':'Entity'},{'kind':'String'}], 'success schema')
    require(results['errors']['#select']['columns'] == [{'name':'error','kind':'Entity'},{'kind':'String'},{'kind':'Integer'}], 'diagnostic schema')
    success = common.oracle.tuples(results['success'])
    expected_success = Counter((str(stage/e['path']), (stage/e['path']).as_uri()) for e in good)
    require(all(len(r) == 2 and r[1] == '' for r in success), 'successful file shape')
    require(Counter((r[0].get('label'),r[0]['url']['uri']) for r in success) == expected_success, 'successful file identities')
    errors = common.oracle.tuples(results['errors'])
    require(len(errors) == bad['count'], 'diagnostic count')
    title = 'A parse error occurred. Check the syntax of the file. If the file is invalid, correct the error or exclude the file from analysis.'
    require(errors[0][0].get('label') == title and errors[0][1:] == [f'Extraction failed in {stage / bad["path"]} with error {title}', 2], 'diagnostic text/severity')
    require(errors[0][0]['url'] == {'uri':(stage/bad['path']).as_uri(), 'startLine':bad['start'][0], 'startColumn':bad['start'][1], 'endLine':bad['end_inclusive'][0], 'endColumn':bad['end_inclusive'][1]}, 'diagnostic identity')



def queries_for_tests():
    tests = ROOT / 'ql/src/testing/issue155-open-read'
    queries = {'success':ROOT/'ql/src/diagnostics/SuccessfullyExtractedFiles.ql',
               'errors':ROOT/'ql/src/diagnostics/ExtractionErrors.ql',
               'raw':tests/'OpenAstInventory.ql', 'edges':tests/'TypedEdges.ql'}
    for key, name in (('model','OpenModel'), ('membership','OpenMembership'), ('permission','OpenPermission'),
                      ('wrong_path','OpenWrongPath'), ('wrong_mode','OpenWrongMode'),
                      ('extra_fragment','OpenAllowExtraFragment'), ('wx_membership','OpenWxMembership'),
                      ('argument_fragments','OpenArgumentFragments'), ('import_fragments','OpenImportFragments'),
                      ('any_mode','OpenAnyLiteralMode'), ('shape','OpenShapeMutants')):
        queries[key] = tests / (name+'.ql')
    return queries


def preflight(cli, base, queries, extra):
    version = common.inputs.strict_json(common.run(cli, 'version', '--format=json'))
    require(version.get('version') == '2.27.4', 'expected CodeQL 2.27.4')
    require(PACK.is_dir() and (PACK/'codeql-extractor.yml').is_file(), 'physical extractor pack')
    search = f'--search-path={PACK}:{ROOT/"ql/lib"}:{ROOT/"ql/src"}'
    for name, query in queries.items():
        resolved = common.inputs.strict_json(common.run(cli, 'resolve', 'queries', '--format=bylanguage', search, *extra, '--', query))
        require(set(resolved.get('byLanguage', {})) == {'ucode'} and set(resolved['byLanguage']['ucode']) == {str(query.resolve())} and not resolved.get('noDeclaredLanguage') and not resolved.get('multipleDeclaredLanguages'), f'{name}: query resolution')
        libs = common.inputs.strict_json(common.run(cli, 'resolve', 'library-path', '--format=json', search, *extra, '--query='+str(query)))
        require(libs['dbscheme'] == str(ROOT/'ql/lib/ucode.dbscheme'), f'{name}: dbscheme')
        if extra:
            require(libs['libraryPath'] == [str(ROOT/'ql/src'),str(ROOT/'ql/lib')]+extra[0].split('=',1)[1].split(':'), f'{name}: library order')
        common.run(cli, 'query', 'compile', '--check-only', '--threads=1', '--ram=2048', search, *extra, '--', query)

def execute(base):
    common.LOG_DIR = base / 'commands'
    common.LOG_DIR.mkdir()
    run = common.run
    stage = base / 'stage'
    stage.mkdir()
    manifest, entries = stage_inputs(stage)
    db = base / 'db'
    extra_value = os.environ.get('OPEN_READ_ADDITIONAL_PACKS')
    extra = ['--additional-packs='+extra_value] if extra_value else []
    cli = shutil.which('codeql')
    require(cli is not None, 'CodeQL executable missing')
    results = {}
    with tempfile.TemporaryDirectory(prefix='open-read-mutants-', dir=ROOT/'ql/src') as tmp:
        queries = queries_for_tests()
        for name, text in guard_mutations().items():
            query = Path(tmp)/(name+'.ql')
            query.write_text(text)
            (base/('guard_'+name+'.ql')).write_text(text)
            queries['guard_'+name] = query
        preflight(cli, base, queries, extra)
        run(cli, 'database', 'init', db, '--language=ucode', f'--search-path={PACK}', f'--source-root={stage}')
        env = os.environ.copy()
        env['CODEQL_UCODE_STAGED_ROOT'] = str(stage)
        run(cli, 'database', 'index-files', db, '--language=ucode', '--include=**/*', f'--working-dir={stage}', env=env)
        routing = common.inputs.load(db / 'trap/ucode/routing.json')
        (base / 'routing.json').write_text(json.dumps(routing, indent=2)+'\n')
        common.inputs.check_routes(routing, stage, entries)
        run(cli, 'database', 'finalize', db)
        common.inputs.check_archive(db / 'src.zip', stage, entries)
        for name, query in queries.items():
            bqrs = base / (name+'.bqrs')
            run(cli, 'query', 'run', query, f'--database={db}', f'--search-path={PACK}:{ROOT/"ql/lib"}:{ROOT/"ql/src"}', *extra, f'--output={bqrs}', '--threads=1', '--ram=2048')
            entities = 'url,string' if name in ('success','errors') else 'id'
            decoded = run(cli, 'bqrs', 'decode', '--format=json', f'--entities={entities}', bqrs)
            (base/(name+'.json')).write_text(decoded)
            results[name] = common.inputs.strict_json(decoded)
    verify_diagnostics(stage, manifest, entries, results)
    verify_control_witnesses(results, manifest, stage)
    expected = verify_projection(results, manifest)
    verify_mutations(results, manifest, expected)
    common.inputs.check_sources(stage, entries)
    print('open read model: exact source identities, diagnostics, projections and counterfactuals verified')


def main():
    requested = os.environ.get('OPEN_READ_MODEL_OUT')
    if requested:
        base = Path(requested)
        require(base.is_absolute() and not base.exists(), 'OPEN_READ_MODEL_OUT must be a fresh absolute path')
        base.mkdir()
    else:
        base = Path(tempfile.mkdtemp(prefix='open-read-model-ci-'))
    base = base.resolve()
    print(f'open read evidence directory: {base}', flush=True)
    try:
        execute(base)
    except Exception as exc:
        print(f'open read smoke failed: {exc}; evidence retained at {base}', flush=True)
        raise


if __name__ == '__main__':
    main()
