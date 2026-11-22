#!/usr/bin/env python3
"""Exact-entity Models local-helper and both production-consumer regression.

Expected spans are specified from fixture source, not generated from QL output.
This script runs real extraction and queries; it is deliberately not a Python
substitute for those checks. Each run owns a fresh temporary source and DB.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import platform
import tempfile
from contextlib import nullcontext
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / 'ql/test/models-local-helper-controls'
ORACLE = json.loads((CORPUS / 'oracle.json').read_text())
PACK = ROOT / 'extractor-pack'


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def entity(cell, source):
    require(isinstance(cell, dict) and set(cell) == {'label', 'url'}, f'not an entity: {cell}')
    url = cell['url']
    require(isinstance(url, dict) and set(url) == {'uri', 'startLine', 'startColumn', 'endLine', 'endColumn'}, f'bad entity URL: {url}')
    parsed = urlsplit(url['uri'])
    require(parsed.scheme == 'file' and not parsed.netloc and not parsed.query and not parsed.fragment, f'bad URI: {url}')
    require(not re.search(r'%(?![0-9a-fA-F]{2})', parsed.path), f'bad escape: {url}')
    try:
        path = Path(unquote(parsed.path, errors='strict'))
        require(path.is_absolute() and '..' not in path.parts and '\0' not in str(path), f'bad path: {path}')
        rel = path.relative_to(source).as_posix()
    except (UnicodeError, ValueError) as error:
        raise SystemExit(f'entity outside source: {url}') from error
    coords = [url[k] for k in ('startLine', 'startColumn', 'endLine', 'endColumn')]
    require(all(type(v) is int and v > 0 for v in coords) and tuple(coords[:2]) <= tuple(coords[2:]), f'bad span: {url}')
    return [rel, *coords]


def row_counts(rows):
    return Counter(json.dumps(row, sort_keys=True) for row in rows)


def assert_rows(name, actual, expected):
    a, e = row_counts(actual), row_counts(expected)
    require(a == e, f'{name} mismatch; missing={e-a}; extra={a-e}')


def assert_delta(name, actual, baseline, added, removed):
    a, b = row_counts(actual), row_counts(baseline)
    require(a - b == row_counts(added) and b - a == row_counts(removed),
            f'{name} unexpected delta; added={a-b}; removed={b-a}')


def command(*args):
    p = subprocess.run([str(a) for a in args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(p.returncode == 0, f'command failed ({p.returncode}): {args}\n{p.stdout[-8000:]}')
    return p.stdout


def index_with_routing(codeql, db, source, receipt):
    """Preserve any emitted raw routing receipt, even when indexing fails."""
    routing_file = db / 'trap/ucode/routing.json'
    try:
        command(codeql, 'database', 'index-files', db, '--language=ucode',
                '--include=**/*.uc', f'--working-dir={source}')
    finally:
        if routing_file.is_file():
            raw = routing_file.read_bytes()
            receipt.write_bytes(raw)
            print(f'Routing receipt: {receipt} sha256={hashlib.sha256(raw).hexdigest()}')
    require(receipt.is_file(), f'routing receipt missing: {routing_file}')
    return json.loads(receipt.read_bytes())


def query(codeql, db, source, out, path, name, columns, search, *, complete=False) -> list[list[Any]]:
    bqrs = out / (name + '.bqrs')
    command(codeql, 'query', 'run', path, f'--database={db}', f'--search-path={search}', f'--output={bqrs}', '--ram=2048', '--threads=1')
    decoded = command(codeql, 'bqrs', 'decode', '--format=json', '--entities=url,string', bqrs)
    (out / (name + '.json')).write_text(decoded)
    result = json.loads(decoded)
    require('#select' in result, f'{name}: missing #select')
    rows = result['#select']['tuples']
    if complete:
        return [[{'label': cell['label'], 'entity': entity(cell, source)} if isinstance(cell, dict) else cell
                 for cell in row] for row in rows]
    return [[entity(row[i], source) for i in columns] for row in rows]


def assert_added(name, rows, baseline, row):
    added = row_counts(rows) - row_counts(baseline)
    removed = row_counts(baseline) - row_counts(rows)
    require(row_counts([row]) <= added, f'{name}: exact intended added row missing; added={added}; removed={removed}')
    print(f'{name}: exact row added; all deltas added={added}; removed={removed}')


def rejected(name, rows, expected, must_include):
    require(any(row[0][0] == must_include for row in rows), f'{name}: expected mutant row absent: {must_include}')
    try:
        assert_rows(name, rows, expected)
    except SystemExit:
        print(f'PASS {name}: exact oracle rejected the mutant and observed {must_include}')
    else:
        raise SystemExit(f'{name}: mutant unexpectedly accepted')


IDENTITY_CASES = [
        ('wrong-call', 'bindings', 0, 'UCODE::CallExpression',
         ['issue_positive.uc', 4, 3, 4, 35], ['issue_shadow.uc', 4, 3, 4, 35],
         'select call,', 'select reportIdentity(call),'),
        ('wrong-helper', 'bindings', 1, 'UCODE::Identifier',
         ['issue_positive.uc', 2, 10, 2, 32], ['issue_shadow.uc', 2, 10, 2, 32],
         'select call, declaration.getName()', 'select call, reportIdentity(declaration.getName())'),
        ('wrong-sink', 'effects', 2, 'UCODE::CallExpression',
         ['issue_positive.uc', 2, 41, 2, 53], ['issue_shadow.uc', 2, 41, 2, 53],
         ', popen,\n', ', reportIdentity(popen),\n'),
        ('wrong-source', 'taints', 0, 'RequestArgsAccess',
         ['taint_positive.uc', 2, 47, 2, 58], ['taint_shadow.uc', 2, 47, 2, 58],
         'select src,', 'select reportIdentity(src),'),
]


def identity_mutant_text(text, case):
    label, _, _, qltype, original_id, wrong_id, old, new = case

    def location(var, identity):
        path, sl, sc, el, ec = identity
        loc = f'{var}.getLocation()'
        return (f'{loc}.getFile().getRelativePath() = "{path}" and\n    '
                f'{loc}.getStartLine() = {sl} and {loc}.getStartColumn() = {sc} and\n    '
                f'{loc}.getEndLine() = {el} and {loc}.getEndColumn() = {ec}')

    require(text.count(old) == 1 and len(re.findall(r'\nfrom\b', text)) == 1, f'cannot isolate identity fault: {label}')
    helper = (f'\n{qltype} reportIdentity({qltype} original) {{\n'
              f'  if {location("original", original_id)} then\n'
              f'    {location("result", wrong_id)}\n'
              f'  else result = original\n}}\n')
    return re.sub(r'\n(?=from\b)', lambda _: helper + '\n', text.replace(old, new, 1), count=1)


def identity_faults(codeql, db, source, out, mutant, search, queries):
    """Schedule count-preserving substitutions in actual decoded query results."""
    baselines = {}
    for case in IDENTITY_CASES:
        label, group, column, _, original_id, wrong_id, _, _ = case
        path, columns = queries[group]
        if group not in baselines:
            full = query(codeql, db, source, out, ROOT / path, 'identity-baseline-' + group,
                         columns, search, complete=True)
            assert_rows('identity baseline ' + group,
                        [[row[i]['entity'] for i in columns] for row in full], ORACLE[group])
            baselines[group] = full
        baseline = baselines[group]
        selected = [row for row in baseline if isinstance(row[column], dict) and row[column]['entity'] == original_id]
        require(len(selected) == 1, f'{label}: original identity not unique')
        before = selected[0]
        after = list(before)
        after[column] = dict(before[column], entity=wrong_id)
        text = identity_mutant_text((ROOT / path).read_text(), case)
        qp = mutant / 'ql/src/extractor-smoke' / ('HelperIdentityFault-' + label + '.ql')
        qp.write_text(text)
        rows = query(codeql, db, source, out, qp, 'identity-' + label, columns, search, complete=True)
        # Complete rows include labels and scalar messages, not just entity spans.
        require(len(rows) == len(baseline), f'{label}: not count preserving')
        assert_delta(label, rows, baseline, [after], [before])
        projected = [[row[i]['entity'] for i in columns] for row in rows]
        old_projected = [before[i]['entity'] for i in columns]
        new_projected = [after[i]['entity'] for i in columns]
        assert_delta(label + '-oracle', projected, ORACLE[group], [new_projected], [old_projected])
        try:
            assert_rows(label + '-oracle', projected, ORACLE[group])
        except SystemExit:
            print(f'PASS {label}: same-count full-row substitution rejected')
        else:
            raise SystemExit(f'{label}: unchanged oracle accepted wrong entity')


def main():
    codeql = shutil.which('codeql')
    require(codeql is not None, 'codeql CLI must be on PATH')
    system = {'Linux': 'linux64', 'Darwin': 'osx64'}.get(platform.system())
    require(system is not None, f'unsupported OS: {platform.system()}')
    require((PACK / 'tools' / system / 'extractor').is_file(), 'build extractor-pack first')
    retained = os.environ.get('CODEQL_UCODE_HELPER_EVIDENCE_DIR')
    if retained:
        evidence = Path(retained).expanduser().resolve()
        evidence.mkdir(parents=True, exist_ok=False)
        print(f'Retaining evidence at {evidence}')
        context = nullcontext(str(evidence))
    else:
        parent = Path(os.environ.get('CODEQL_UCODE_SMOKE_TMPDIR', tempfile.gettempdir())).resolve()
        parent.mkdir(parents=True, exist_ok=True)
        context = tempfile.TemporaryDirectory(prefix='models-helper-91-', dir=parent)
    with context as tmp:
        tmp = Path(tmp)
        source = tmp / 'source/ql/test/extractor-smoke'
        source.mkdir(parents=True)
        require(set(ORACLE['inputs']) == {p.name for p in CORPUS.glob('*.uc')} | {'pinned.uc'}, 'fixture manifest mismatch')
        for filename, digest in ORACLE['inputs'].items():
            origin = (ROOT / 'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci'
                      if filename == 'pinned.uc' else CORPUS / filename)
            data = origin.read_bytes()
            require(hashlib.sha256(data).hexdigest() == digest, f'fixture digest mismatch: {filename}')
            (source / filename).write_bytes(data)
        db = tmp / 'database'
        command(codeql, 'database', 'init', db, '--language=ucode', f'--search-path={PACK}', f'--source-root={source}')
        routing = index_with_routing(codeql, db, source, tmp / 'routing.json')
        paths = [Path(d['path']).relative_to(source).as_posix() for d in routing['decisions']]
        require(Counter(paths) == Counter(ORACLE['inputs'].keys()), 'routing input identity mismatch')
        require(all(d['classification'] == 'plain' and d['status'] == 'plain_route_selected' for d in routing['decisions']), 'unexpected routing decision')
        require(routing['duplicate_input_count'] == 0 and routing['excluded_count'] == 0, 'unexpected routing counters')
        command(codeql, 'database', 'finalize', db)
        out = tmp / 'results'
        out.mkdir()
        search = os.pathsep.join(map(str, (PACK, ROOT / 'ql/lib', ROOT / 'ql/src')))
        # This inventory distinguishes an extracted file with errors from a clean file.
        inv = out / 'files.bqrs'
        command(codeql, 'query', 'run', ROOT / 'ql/src/extractor-smoke/ModelsFsPopenFileInventory.ql', f'--database={db}', f'--search-path={search}', f'--output={inv}', '--ram=2048', '--threads=1')
        decoded_inventory = command(codeql, 'bqrs', 'decode', '--format=json', '--entities=url,string', inv)
        (out / 'files.json').write_text(decoded_inventory)
        data = json.loads(decoded_inventory)['#select']['tuples']
        expected_files = [[name, 'error' if name in ORACLE['errors'] else 'ok'] for name in ORACLE['inputs']]
        assert_rows('file diagnostics', data, expected_files)
        queries = {
            'raw': ('ql/src/extractor-smoke/ModelsLocalHelperRawCalls.ql', [0]),
            'wrapped_raw': ('ql/src/extractor-smoke/ModelsLocalHelperWrappedRaw.ql', [0]),
            'bindings': ('ql/src/extractor-smoke/ModelsLocalHelperBindings.ql', [0, 1]),
            'effects': ('ql/src/m3/GetFeaturesPopen.ql', [0, 2]),
            'taints': ('ql/src/m3/GetFeaturesHelperTaint.ql', [0, 2]),
            'generic_raw': ('ql/src/extractor-smoke/ModelsLocalHelperGenericRaw.ql', [0]),
            'generic_bindings': ('ql/src/extractor-smoke/ModelsLocalHelperGenericBindings.ql', [0, 1]),
            'generic_effects': ('ql/src/extractor-smoke/ModelsLocalHelperGenericEffects.ql', [0, 1]),
            'generic_taints': ('ql/src/extractor-smoke/ModelsLocalHelperGenericTaints.ql', [0, 1]),
        }
        for name, (path, columns) in queries.items():
            rows = query(codeql, db, source, out, ROOT / path, name, columns, search)
            assert_rows(name, rows, ORACLE[name])
            print(f'PASS {name}: {len(rows)} exact entity rows')
        # Revert only the shared predicate in a copied pack. The unchanged oracle
        # must reject the issue shadow; each consumer bypass is also tested alone.
        mutant = tmp / 'mutant'
        (mutant / 'ql').mkdir(parents=True)
        shutil.copyfile(ROOT / '.codeqlmanifest.json', mutant / '.codeqlmanifest.json')
        shutil.copytree(ROOT / 'ql/lib', mutant / 'ql/lib')
        shutil.copytree(ROOT / 'ql/src', mutant / 'ql/src')
        models = mutant / 'ql/lib/codeql/ucode/m3/Models.qll'
        original = models.read_text()

        def model_mutation(name, text):
            models.write_text(text)
            (out / (name + '.qll')).write_text(text)

        start = original.index('predicate sameFileCall(')
        end = original.index('\n}\n', start) + 2
        legacy = '''predicate sameFileCall(NamedCall c, UCODE::FunctionDeclaration def) {
  def = functionDecl(c.getName()) and
  c.getLocation().getFile() = def.getLocation().getFile()
}'''
        model_mutation('legacy-models', original[:start] + legacy + original[end:])
        mutant_search = os.pathsep.join(map(str, (PACK, mutant / 'ql/lib', mutant / 'ql/src')))
        for name, negative in (('bindings', 'issue_shadow.uc'), ('effects', 'issue_shadow.uc'), ('taints', 'taint_shadow.uc')):
            path, columns = queries[name]
            rows = query(codeql, db, source, out, mutant / path, 'legacy-' + name, columns, mutant_search)
            rejected('legacy-' + name, rows, ORACLE[name], negative)
        models.write_text(original)
        # Each isolated guard mutation is run against the unchanged binding
        # oracle; named rows establish which control actually killed it.
        order = '''  (def.getLocation().getEndLine() < c.getLocation().getStartLine() or
    def.getLocation().getEndLine() = c.getLocation().getStartLine() and
    def.getLocation().getEndColumn() < c.getLocation().getStartColumn()) and
'''
        identifiers = '''  not exists(UCODE::Identifier id |
    id.getLocation().getFile() = c.getLocation().getFile() and
    id.getValue() = c.getName() and
    id != def.getName() and
    not id = calleeIdent(any(NamedCall call))
  ) and
'''
        shorthand = '''  not exists(UCODE::ShorthandPropertyIdentifier id |
    id.getLocation().getFile() = c.getLocation().getFile() and
    id.getValue() = c.getName()
  ) and
'''
        mutations = [
            ('top-level', '  def.getParent() instanceof UCODE::Program and\n', '', 'sibling_only.uc'),
            ('order', order, '', 'forward.uc'),
            ('same-line-inequality', '    def.getLocation().getEndColumn() < c.getLocation().getStartColumn()', '    def.getLocation().getEndColumn() >= 0', 'same_line_before.uc'),
            ('duplicate-declaration', '    id != def.getName() and', '    not exists(UCODE::FunctionDeclaration f | id = f.getName()) and', 'duplicate.uc'),
            ('identifier-guard', identifiers, '', 'write_after_closure.uc'),
            ('shorthand-guard', shorthand, '', 'shorthand.uc'),
            ('optional-guard', '  not exists(c.getOptionalChain()) and\n', '', 'optional.uc'),
            ('error-guard', '  not exists(ExtractionError error | error.getLocation().getFile() = c.getLocation().getFile())', '  1 = 1', 'malformed.uc'),
        ]
        path, columns = queries['bindings']
        for name, old, new, negative in mutations:
            require(original.count(old) == 1, f'cannot isolate mutation: {name}')
            model_mutation('guard-' + name, original.replace(old, new, 1))
            rows = query(codeql, db, source, out, mutant / path, 'guard-' + name, columns, mutant_search)
            exact = {
                'identifier-guard': [['write_after_closure.uc', 4, 17, 4, 49], ['write_after_closure.uc', 2, 10, 2, 32]],
                'error-guard': [['malformed.uc', 4, 3, 4, 35], ['malformed.uc', 2, 10, 2, 32]],
            }
            if name in exact:
                assert_added('guard-' + name, rows, ORACLE['bindings'], exact[name])
            rejected('guard-' + name, rows, ORACLE['bindings'], negative)
        # Review controls use isolated mutants with exact call/target AND
        # production-effect deltas, rather than relying on a textual anchor.
        cases = [
            ('declaration-start', order, order.replace('def.getLocation().getEnd', 'def.getLocation().getStart'),
             [['within_declaration.uc', 5, 5, 5, 37], ['within_declaration.uc', 2, 10, 2, 32]],
             [['within_declaration.uc', 5, 5, 5, 37], ['within_declaration.uc', 3, 3, 3, 15]]),
            ('argument-escape', '    not id = calleeIdent(any(NamedCall call))',
             '    not id = calleeIdent(any(NamedCall call)) and\n    not exists(NamedCall outer | id = outer.getArgument(_))',
             [['argument_escape.uc', 5, 3, 5, 35], ['argument_escape.uc', 2, 10, 2, 32]],
             [['argument_escape.uc', 5, 3, 5, 35], ['argument_escape.uc', 2, 41, 2, 53]]),
        ]
        for name, old, new, binding, effect in cases:
            require(original.count(old) == 1, f'cannot isolate {name}')
            model_mutation('review-' + name, original.replace(old, new, 1))
            for group, expected_row in (('bindings', binding), ('effects', effect)):
                path, columns = queries[group]
                rows = query(codeql, db, source, out, mutant / path, f'review-{name}-{group}', columns, mutant_search)
                assert_delta(f'{name}-{group}', rows, ORACLE[group], [expected_row], [])
                rejected(f'{name}-{group}', rows, ORACLE[group], expected_row[0][0])
        # Test the public predicate's name/argument generality against both
        # generic consumer-shaped queries as well as binding inventory.
        restrict = '  def = functionDecl(c.getName()) and'
        require(original.count(restrict) == 1, 'cannot isolate name restriction')
        restrictions = [
            ('name-only', '  c.getName() = "callPackageVersionCheck" and\n'),
            ('selector-only', '  c instanceof CallPackageVersionCheckNetifd and\n'),
            ('argument-only', '  stringLiteralValue(c.getArgument(0).(UCODE::String)) = "netifd" and\n'),
        ]
        for restriction_name, predicate in restrictions:
            model_mutation('review-' + restriction_name, original.replace(restrict, predicate + restrict, 1))
            for group in ('generic_bindings', 'generic_effects', 'generic_taints'):
                path, columns = queries[group]
                rows = query(codeql, db, source, out, mutant / path, 'review-' + restriction_name + '-' + group, columns, mutant_search)
                assert_delta(restriction_name + '-' + group, rows, ORACLE[group], [], ORACLE[group])
                require(not rows, f'{group}: {restriction_name} mutant retained a row')
        models.write_text(original)
        # The line-only order mutant induces an expensive Cartesian join on
        # the full corpus. Exercise it on a fresh single-file database instead;
        # require the unmodified model to produce the independently pinned row
        # there first, so empty extraction cannot masquerade as a mutant kill.
        require(original.count(order) == 1, 'cannot isolate same-line support')
        mini_source = tmp / 'same-line-source/ql/test/extractor-smoke'
        mini_source.mkdir(parents=True)
        shutil.copyfile(source / 'same_line_positive.uc', mini_source / 'same_line_positive.uc')
        mini_db = tmp / 'same-line-database'
        command(codeql, 'database', 'init', mini_db, '--language=ucode', f'--search-path={PACK}', f'--source-root={mini_source}')
        mini_routing = index_with_routing(codeql, mini_db, mini_source, tmp / 'same-line-routing.json')
        require(len(mini_routing['decisions']) == 1 and
                Path(mini_routing['decisions'][0]['path']) == mini_source / 'same_line_positive.uc' and
                mini_routing['decisions'][0]['status'] == 'plain_route_selected' and
                mini_routing['decisions'][0]['classification'] == 'plain' and
                mini_routing['duplicate_input_count'] == 0 and mini_routing['excluded_count'] == 0,
                'same-line routing input mismatch')
        command(codeql, 'database', 'finalize', mini_db)
        mini_inventory = out / 'same-line-files.bqrs'
        command(codeql, 'query', 'run', ROOT / 'ql/src/extractor-smoke/ModelsFsPopenFileInventory.ql',
                f'--database={mini_db}', f'--search-path={search}', f'--output={mini_inventory}', '--ram=2048', '--threads=1')
        mini_files = command(codeql, 'bqrs', 'decode', '--format=json', '--entities=url,string', mini_inventory)
        (out / 'same-line-files.json').write_text(mini_files)
        assert_rows('same-line file diagnostics', json.loads(mini_files)['#select']['tuples'], [['same_line_positive.uc', 'ok']])
        path, columns = queries['bindings']
        expected = [row for row in ORACLE['bindings'] if row[0][0] == 'same_line_positive.uc']
        require(len(expected) == 1, 'same-line positive oracle must have exactly one row')
        baseline = query(codeql, mini_db, mini_source, out, ROOT / path, 'same-line-baseline', columns, search)
        assert_rows('same-line baseline', baseline, expected)
        model_mutation('guard-same-line-positive', original.replace(order, '  def.getLocation().getEndLine() < c.getLocation().getStartLine() and\n', 1))
        rows = query(codeql, mini_db, mini_source, out, mutant / path, 'guard-same-line-positive', columns, mutant_search)
        assert_delta('same-line positive', rows, baseline, [], expected)
        try:
            assert_rows('same-line positive', rows, expected)
        except SystemExit:
            print('PASS same-line positive: exact oracle rejected removal')
        else:
            raise SystemExit('same-line positive mutant unexpectedly accepted')
        models.write_text(original)
        for name, negative in (('effects', 'issue_shadow.uc'), ('taints', 'taint_shadow.uc')):
            path, columns = queries[name]
            qp = mutant / path
            text = qp.read_text()
            before = 'sameFileCall(helperCall, helper)'
            after = 'helper = functionDecl(helperCall.getName()) and helperCall.getLocation().getFile() = helper.getLocation().getFile()'
            require(text.count(before) == 1, f'cannot isolate {name} consumer bypass')
            changed_query = text.replace(before, after)
            qp.write_text(changed_query)
            (out / ('bypass-' + name + '.ql')).write_text(changed_query)
            rows = query(codeql, db, source, out, qp, 'bypass-' + name, columns, mutant_search)
            rejected('bypass-' + name, rows, ORACLE[name], negative)
            qp.write_text(text)
        identity_faults(codeql, db, source, out, mutant, mutant_search, queries)
        print('PASS shared legacy, both consumer bypass controls, and identity faults')


if __name__ == '__main__':
    main()
