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
import tempfile
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


def assert_rows(name, actual, expected):
    def counts(rows):
        return Counter(json.dumps(row, sort_keys=True) for row in rows)
    a, e = counts(actual), counts(expected)
    require(a == e, f'{name} mismatch; missing={e-a}; extra={a-e}')


def command(*args):
    p = subprocess.run([str(a) for a in args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(p.returncode == 0, f'command failed ({p.returncode}): {args}\n{p.stdout[-8000:]}')
    return p.stdout


def query(codeql, db, source, out, path, name, columns, search):
    bqrs = out / (name + '.bqrs')
    command(codeql, 'query', 'run', path, f'--database={db}', f'--search-path={search}', f'--output={bqrs}', '--ram=2048', '--threads=1')
    result = json.loads(command(codeql, 'bqrs', 'decode', '--format=json', '--entities=url,string', bqrs))
    require('#select' in result, f'{name}: missing #select')
    rows = result['#select']['tuples']
    return [[entity(row[i], source) for i in columns] for row in rows]


def rejected(name, rows, expected, must_include):
    require(any(row[0][0] == must_include for row in rows), f'{name}: expected mutant row absent: {must_include}')
    try:
        assert_rows(name, rows, expected)
    except SystemExit:
        print(f'PASS {name}: exact oracle rejected the mutant and observed {must_include}')
    else:
        raise SystemExit(f'{name}: mutant unexpectedly accepted')


def main():
    codeql = shutil.which('codeql')
    require(codeql is not None, 'codeql CLI must be on PATH')
    require((PACK / 'tools/linux64/extractor').is_file(), 'build extractor-pack first')
    parent = Path(os.environ.get('CODEQL_UCODE_SMOKE_TMPDIR', tempfile.gettempdir())).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='models-helper-91-', dir=parent) as tmp:
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
        command(codeql, 'database', 'index-files', db, '--language=ucode', '--include=**/*.uc', f'--working-dir={source}')
        routing = json.loads((db / 'trap/ucode/routing.json').read_text())
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
        data = json.loads(command(codeql, 'bqrs', 'decode', '--format=json', '--entities=url,string', inv))['#select']['tuples']
        expected_files = [[name, 'error' if name in ORACLE['errors'] else 'ok'] for name in ORACLE['inputs']]
        assert_rows('file diagnostics', data, expected_files)
        queries = {
            'raw': ('ql/src/extractor-smoke/ModelsLocalHelperRawCalls.ql', [0]),
            'bindings': ('ql/src/extractor-smoke/ModelsLocalHelperBindings.ql', [0, 1]),
            'effects': ('ql/src/m3/GetFeaturesPopen.ql', [0, 2]),
            'taints': ('ql/src/m3/GetFeaturesHelperTaint.ql', [0, 2]),
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
        start = original.index('predicate sameFileCall(')
        end = original.index('\n}\n', start) + 2
        legacy = '''predicate sameFileCall(NamedCall c, UCODE::FunctionDeclaration def) {
  def = functionDecl(c.getName()) and
  c.getLocation().getFile() = def.getLocation().getFile()
}'''
        models.write_text(original[:start] + legacy + original[end:])
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
            models.write_text(original.replace(old, new, 1))
            rows = query(codeql, db, source, out, mutant / path, 'guard-' + name, columns, mutant_search)
            rejected('guard-' + name, rows, ORACLE['bindings'], negative)
        # Dropping same-line support removes the positive rather than adding a
        # negative, so prove the exact positive disappeared independently.
        require(original.count(order) == 1, 'cannot isolate same-line support')
        models.write_text(original.replace(order, '  def.getLocation().getEndLine() < c.getLocation().getStartLine() and\n', 1))
        rows = query(codeql, db, source, out, mutant / path, 'guard-same-line-positive', columns, mutant_search)
        require(not any(row[0][0] == 'same_line_positive.uc' for row in rows), 'same-line mutant did not remove positive')
        try:
            assert_rows('same-line positive', rows, ORACLE['bindings'])
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
            qp.write_text(text.replace(before, after))
            rows = query(codeql, db, source, out, qp, 'bypass-' + name, columns, mutant_search)
            rejected('bypass-' + name, rows, ORACLE[name], negative)
            qp.write_text(text)
        print('PASS shared legacy and both independent consumer bypass controls')


if __name__ == '__main__':
    main()
