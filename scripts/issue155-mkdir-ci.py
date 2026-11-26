#!/usr/bin/env python3
"""Focused source-declared mkdir test; retains extraction and query evidence."""
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'ql/test/issue155-mkdir'
PACK = (ROOT / 'extractor-pack').resolve()
spec = importlib.util.spec_from_file_location('stat_gate', ROOT / 'scripts/issue155-stat-ci.py')
common = importlib.util.module_from_spec(spec); spec.loader.exec_module(common)
oracle, require = common.oracle, common.require

def stage_inputs(stage):
    manifest = common.inputs.load(FIXTURES / 'source-first.json')
    entries = manifest['entries']; paths = [e['path'] for e in entries]
    require(len(paths) == len(set(paths)) == 20, 'fixture inventory identities')
    for entry in entries:
        source = ROOT / entry['fixture_path'] if 'fixture_path' in entry else FIXTURES / entry['path']
        data = source.read_bytes()
        require(len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], 'fixture bytes: ' + entry['path'])
        for key in ('anchors',):
            for a in entry.get(key, {}).values():
                for item in a if isinstance(a, list) else [a]:
                    line = data.splitlines()[item['line'] - 1]
                    require(line[item['start_column']-1:item['end_column_exclusive']-1] == item['text'].encode('utf-8'), 'anchor bytes: ' + entry['path'])
        for key in ('negative_anchor', 'guard_call', 'guard_callee', 'guard_path', 'mutation_call', 'formal_anchor'):
            if key in entry:
                a = entry[key]; line = data.splitlines()[a['line']-1]
                require(line[a['start_column']-1:a['end_column_exclusive']-1] == a['text'].encode('utf-8'), 'anchor bytes: ' + entry['path'])
        dest = stage / entry['path']; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        entry['expected_route'] = {'classification': 'plain', 'reason': 'rpcd_raw_mode_full_path' if entry['path'].startswith('usr/') else 'ucode_extension', 'status': 'plain_route_selected'}
    return manifest, entries

def verify(stage, manifest, entries, results):
    raw, edges = map(oracle.tuples, (results['raw'], results['edges']))
    def anchor(a):
        return {'start': [a['line'], a['start_column']], 'end_exclusive': [a['line'], a['end_column_exclusive']]}
    def node(path, kind, a): return oracle.node(raw, path, kind, anchor(a))
    def targets(path, source, field):
        return [(r[4], r[5]['id']) for r in edges if r[0] == path and r[1] == {'id': source} and r[3] == field]
    expected, modes = [], []
    for e in entries:
        if e['expected'] != 'model': continue
        path, a = e['path'], e['anchors']
        call = node(path, 'CallExpression', a['call']); callee = node(path, 'Identifier', a['callee'])
        args = [node(path, arg['kind'], arg) for arg in a['arguments']]
        require(targets(path, call, 'call-function') == [(-1, callee)], path + ': callee edge')
        owners = targets(path, call, 'call-arguments'); require(len(owners) == 1, path + ': argument owner')
        require(sorted(targets(path, owners[0][1], 'argument')) == list(enumerate(args)), path + ': argument edges')
        require(not targets(path, call, 'call-optional'), path + ': optional call')
        expected.append((path, call, callee, args[0]))
        if len(args) == 2: modes.append((path, call, args[1]))
    def rows(data): return Counter((r[0], *(v['id'] for v in r[1:])) for r in oracle.tuples(data))
    require(rows(results['class']) == Counter((p, c, f) for p, c, f, _ in expected), 'class identities or multiplicity')
    require(rows(results['membership']) == Counter(expected), 'model identities or multiplicity')
    require(rows(results['mode']) == Counter(modes), 'mode identities or multiplicity')
    by_path = {e['path']: e for e in entries}
    zero = by_path['controls/zero.uc']; call = node(zero['path'], 'CallExpression', zero['negative_anchor'])
    owners = targets(zero['path'], call, 'call-arguments')
    require(len(owners) == 1 and not targets(zero['path'], owners[0][1], 'argument'), 'zero argument witness')
    wrapped = by_path['controls/wrapper.uc']; call = node(wrapped['path'], 'CallExpression', wrapped['negative_anchor'])
    fn = targets(wrapped['path'], call, 'call-function')
    require(len(fn) == 1 and any(r[0] == wrapped['path'] and r[1] == 'ParenthesizedExpression' and r[7] == {'id': fn[0][1]} for r in raw), 'wrapped callee witness')
    prop = by_path['controls/property.uc']; member = node(prop['path'], 'MemberExpression', prop['negative_anchor'])
    require(len(targets(prop['path'], member, 'member-object')) == 1 and len(targets(prop['path'], member, 'member-property')) == 1 and not any(r[0] == prop['path'] and r[1] == 'CallExpression' for r in raw), 'property read witness')
    shadow = by_path['controls/shadow.uc']; call = node(shadow['path'], 'CallExpression', shadow['negative_anchor'])
    fn = targets(shadow['path'], call, 'call-function')
    formal = node(shadow['path'], 'Identifier', shadow['formal_anchor'])
    require(len(fn) == 1 and sum(1 for r in edges if r[0] == shadow['path'] and r[3] == 'formal' and r[5] == {'id': formal}) == 1, 'formal shadow witness')
    additions = {'arity': 'extra', 'path-expression': 'spread-path', 'mode-expression': 'spread-mode'}
    shape_expected = []
    for mutation, name in additions.items():
        shape_expected.extend((mutation, row[0], row[1]) for row in expected)
        path = 'controls/' + name + '.uc'
        shape_expected.append((mutation, path, node(path, 'CallExpression', by_path[path]['mutation_call'])))
    shape = Counter((r[0], r[1], r[2]['id']) for r in oracle.tuples(results['shape']))
    require(shape == Counter(shape_expected), 'shape mutant identities or multiplicity')
    guards = {'declaration': 'shadow-lexical', 'write': 'reassignment', 'module': 'wrong-module',
              'alias': 'alias', 'optional': 'optional', 'unique': 'duplicate', 'diagnostic': 'malformed'}
    for mutation, name in guards.items():
        path = 'controls/' + name + '.uc'; e = by_path[path]
        call = node(path, 'CallExpression', e['guard_call'])
        callee = node(path, 'Identifier', e['guard_callee'])
        arg = node(path, 'String', e['guard_path'])
        owners = targets(path, call, 'call-arguments')
        require(targets(path, call, 'call-function') == [(-1, callee)] and len(owners) == 1 and
                targets(path, owners[0][1], 'argument') == [(0, arg)], mutation + ': guard witness edges')
        require(rows(results['guard_' + mutation]) == Counter(expected + [(path, call, callee, arg)]), mutation + ': guard mutation identities')
    wrong = rows(results['wrong'])
    binary = {(p, c): mode for p, c, mode in modes}
    wrong_expected = Counter((p, c, f, binary[p, c]) for p, c, f, arg in expected if (p, c) in binary)
    correct_binary = Counter((p, c, f, arg) for p, c, f, arg in expected if (p, c) in binary)
    require(wrong == wrong_expected and wrong != correct_binary and len(wrong) == len(correct_binary), 'wrong path mutation was not detected')
    success = Counter(r[0]['url']['uri'] for r in oracle.tuples(results['success']))
    diagnostic = manifest['malformed_diagnostic']; bad = diagnostic['path']
    require(success == Counter((stage/e['path']).as_uri() for e in entries if e['path'] != bad), 'successful-file identities')
    require([c['kind'] for c in results['errors']['#select']['columns']] == ['Entity', 'String', 'Integer'], 'diagnostic schema')
    errors = oracle.tuples(results['errors'])
    require(len(errors) == diagnostic['count'] and errors[0][2] == 2 and errors[0][0]['url'] == {'uri': (stage/bad).as_uri(), 'startLine': diagnostic['start'][0], 'startColumn': diagnostic['start'][1], 'endLine': diagnostic['end_inclusive'][0], 'endColumn': diagnostic['end_inclusive'][1]}, 'malformed diagnostic identity')

def execute(base):
    common.LOG_DIR = base / 'commands'; common.LOG_DIR.mkdir(); run = common.run
    stage = base / 'stage'; stage.mkdir(); manifest, entries = stage_inputs(stage)
    cli = shutil.which('codeql'); require(cli is not None, 'CodeQL missing')
    db = base / 'db'
    run(cli, 'database', 'init', db, '--language=ucode', f'--search-path={PACK}', f'--source-root={stage}')
    env = os.environ.copy(); env['CODEQL_UCODE_STAGED_ROOT'] = str(stage)
    run(cli, 'database', 'index-files', db, '--language=ucode', '--include=**/*.uc', f'--working-dir={stage}', env=env)
    routing = common.inputs.load(db / 'trap/ucode/routing.json'); (base/'routing.json').write_text(json.dumps(routing, indent=2)+'\n')
    common.inputs.check_routes(routing, stage, entries)
    run(cli, 'database', 'finalize', db); common.inputs.check_archive(db/'src.zip', stage, entries)
    queries = {'success': ROOT/'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', 'errors': ROOT/'ql/src/diagnostics/ExtractionErrors.ql', 'raw': ROOT/'ql/src/testing/issue155-mkdir/MkdirAstInventory.ql', 'edges': ROOT/'ql/src/testing/issue155-mkdir/MkdirTypedEdges.ql', 'class': ROOT/'ql/src/testing/issue155-mkdir/MkdirClassMembership.ql', 'membership': ROOT/'ql/src/testing/issue155-mkdir/MkdirMembership.ql', 'mode': ROOT/'ql/src/testing/issue155-mkdir/MkdirMode.ql', 'wrong': ROOT/'ql/src/testing/issue155-mkdir/MkdirWrongPath.ql', 'shape': ROOT/'ql/src/testing/issue155-mkdir/MkdirShapeMutants.ql'}
    tail = """from UCODE::CallExpression call, UCODE::AstNode arg
where sourceDeclaredFsCall(call, "mkdir") and
  arg = call.getArguments().getChild(0) and arg instanceof UCODE::Expression and
  (not exists(call.getArguments().getChild(1)) or call.getArguments().getChild(1) instanceof UCODE::Expression) and
  not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  call.getFunction() as callee_node, arg as path_node
"""
    mutations = common.inputs.source_declared_fs_guard_queries((ROOT/'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text(), family='mkdir', id_prefix='issue155-mkdir-guard-', selection='\n'+tail)
    with tempfile.TemporaryDirectory(prefix='mkdir-mutants-', dir=ROOT/'ql/src') as temp:
        mutation_dir = Path(temp)
        for name, text in mutations.items():
            query = mutation_dir / ('guard_' + name + '.ql'); query.write_text(text)
            (base / ('guard_' + name + '.ql')).write_text(text); queries['guard_' + name] = query
        results = {}
        for name, query in queries.items():
            bqrs = base / (name+'.bqrs')
            extra = os.environ.get('MKDIR_MODEL_ADDITIONAL_PACKS')
            options = [f'--additional-packs={extra}'] if extra else []
            run(cli, 'query', 'run', query, f'--database={db}', f'--search-path={PACK}:{ROOT/"ql/lib"}:{ROOT/"ql/src"}', *options, f'--output={bqrs}', '--threads=1', '--ram=2048')
            decoded = run(cli, 'bqrs', 'decode', '--format=json', '--entities='+('url,string' if name in ('success','errors') else 'id'), bqrs)
            (base/(name+'.json')).write_text(decoded); results[name] = common.inputs.strict_json(decoded)
        verify(stage, manifest, entries, results); common.inputs.check_sources(stage, entries)
    print('mkdir model: exact call/argument identities, routing, diagnostics and wrong-slot control verified')

def main():
    requested = os.environ.get('MKDIR_MODEL_OUT')
    if requested:
        base = Path(requested); require(base.is_absolute() and not base.exists(), 'MKDIR_MODEL_OUT must be fresh and absolute'); base.mkdir()
    else: base = Path(tempfile.mkdtemp(prefix='mkdir-model-ci-'))
    base = base.resolve(); print('mkdir model evidence directory:', base, flush=True)
    try: execute(base)
    except Exception as exc:
        print(f'mkdir smoke failed: {exc}; evidence retained at {base}', file=sys.stderr, flush=True); raise

if __name__ == '__main__': main()
