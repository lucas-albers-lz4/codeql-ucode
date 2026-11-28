#!/usr/bin/env python3
"""Exact, testing-only WOL map/join query regression on fresh fixture bytes."""

import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'ql/test/wol-unquoted-map-join'
STAGE = FIXTURES / 'installed'
QUERY = ROOT / 'ql/src/testing/WolUnquotedMapJoin.ql'
WITNESS = ROOT / 'ql/src/testing/WolBindingWitness.ql'
PACK = (ROOT / 'extractor-pack').resolve()
CLI = shutil.which('codeql')


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(label, argv, cwd, env, out, records):
    start = time.perf_counter()
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True)
    wall = round(time.perf_counter() - start, 3)
    (out / (label + '.stdout')).write_bytes(result.stdout)
    (out / (label + '.stderr')).write_bytes(result.stderr)
    records.append({'label': label, 'argv': argv, 'exit': result.returncode,
                    'wall_seconds': wall,
                    'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                    'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
    (out / 'commands.json').write_text(json.dumps(records, sort_keys=True, indent=2) + '\n')
    need(result.returncode == 0,
         label + ' failed: ' + result.stderr.decode(errors='replace')[-1200:])
    return result.stdout


def relative_uri(value, stage):
    need(value.startswith('file://'), 'expected file URI')
    return str(Path(value.removeprefix('file://')).relative_to(stage))


def verify_binding_witnesses(binding_rows, witnesses):
    groups = {}
    for witness in witnesses:
        occurrence = witness['occurrence']; declaration = witness['declaration']; path = witness['path']
        matches = [row for row in binding_rows if row[0] == path
            and row[3:7] == [occurrence['line'], occurrence['start_column'], occurrence['line'], occurrence['end_column']]]
        need(len(matches) == 1 and matches[0][1] == 'read'
             and matches[0][9:14] == [witness['declaration_kind'], declaration['line'],
                 declaration['start_column'], declaration['line'], declaration['end_column']]
             and set(matches[0][2]) == {'id'} and set(matches[0][7]) == {'id'}
             and set(matches[0][8]) == {'id'}, 'binding witness missing or ambiguous: ' + path)
        key = (path, witness['variable_group']); identity = (matches[0][7]['id'], matches[0][8]['id'])
        need(key not in groups or groups[key] == identity, 'binding witness group differs: ' + path)
        groups[key] = identity
    for path in {key[0] for key in groups}:
        identities = [value for (candidate, _), value in groups.items() if candidate == path]
        need(len(identities) == len({item[0] for item in identities}) == len({item[1] for item in identities}),
             'distinct binding groups collapsed: ' + path)

def check_variable_sync():
    spec = importlib.util.spec_from_file_location('wol_variable_sync', ROOT / 'scripts/wol_variable_sync.py')
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    sync.verify_files()


def execute(mutant_query):
    check_variable_sync()
    need(CLI is not None, 'CodeQL CLI is unavailable')
    manifest = json.loads((FIXTURES / 'expected.json').read_text())
    need(manifest['schema'] == 'wol-unquoted-map-join-fixtures-v1', 'fixture schema changed')
    need(digest(QUERY) == manifest['expected_query_sha256'], 'testing query bytes changed')
    need(digest(WITNESS) == manifest['binding_witness_query_sha256'], 'binding witness query bytes changed')
    files = manifest['files']
    need(not any(p.is_symlink() for p in STAGE.rglob('*')), 'fixture symlink unsupported')
    actual_files = {str(p.relative_to(STAGE)) for p in STAGE.rglob('*') if p.is_file()}
    need(actual_files == set(files), 'fixture file set changed')
    need(all(digest(STAGE / path) == sha for path, sha in files.items()),
         'fixture bytes changed')
    need(digest(STAGE / 'usr/share/rpcd/ucode/luci.wol') ==
         manifest['real_wol_source_sha256'], 'real WOL source changed')
    need((PACK / 'codeql-extractor.yml').is_file(), 'extractor pack unavailable')
    version = json.loads(subprocess.check_output([CLI, 'version', '--format=json']))
    need(version['version'] == '2.27.4', 'unexpected CodeQL version')

    requested = os.environ.get('WOL_QUERY_OUT')
    if requested:
        work = Path(requested)
        need(work.is_absolute() and not work.exists(), 'WOL_QUERY_OUT must be fresh and absolute')
        work.mkdir()
    else:
        base = ROOT / '.codeql-database'
        base.mkdir(exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix='wol-query-local-', dir=base))
    work = work.resolve()
    db = work / 'db'
    out = work / 'out'
    out.mkdir()
    home = work / 'home'
    (home / '.codeql').mkdir(parents=True)
    additional = os.environ.get('WOL_QUERY_ADDITIONAL_PACKS')
    if not additional:
        packages = Path.home() / '.codeql/packages'
        need(packages.is_dir(), 'install locked CodeQL packs before this smoke')
        shutil.copytree(packages, home / '.codeql/packages')
    tmp = work / 'tmp'
    tmp.mkdir()
    cache = work / 'xdg-cache'
    config = work / 'xdg-config'
    cache.mkdir()
    config.mkdir()
    env = dict(os.environ, HOME=str(home), TMPDIR=str(tmp), TMP=str(tmp),
               TEMP=str(tmp), XDG_CACHE_HOME=str(cache), XDG_CONFIG_HOME=str(config))
    env.pop('CODEQL_UCODE_STAGED_ROOT', None)
    search = ':'.join(map(str, (PACK, ROOT / 'ql/lib', ROOT / 'ql/src')))
    records = []
    options = ['--additional-packs=' + additional] if additional else []
    all_queries = {'success': ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql',
                   'errors': ROOT / 'ql/src/diagnostics/ExtractionErrors.ql',
                   'rule': QUERY, 'binding': WITNESS, 'owner-mutant': mutant_query}
    for name, query in all_queries.items():
        resolved = json.loads(run('resolve-' + name, [CLI, 'resolve', 'queries', '--format=bylanguage',
            '--search-path=' + search, *options, '--', str(query)], ROOT, env, out, records))
        by_language = resolved.get('byLanguage', {})
        need(set(by_language) == {'ucode'} and set(by_language['ucode']) == {str(query.resolve())}
             and not resolved.get('noDeclaredLanguage') and not resolved.get('multipleDeclaredLanguages'),
             'query resolution differs: ' + name)
        library = json.loads(run('libraries-' + name, [CLI, 'resolve', 'library-path', '--format=json',
            '--search-path=' + search, *options, '--query=' + str(query)], ROOT, env, out, records))
        need(library['libraryPath'][:2] == [str(ROOT / 'ql/src'), str(ROOT / 'ql/lib')]
             and library['dbscheme'] == str(ROOT / 'ql/lib/ucode.dbscheme'),
             'library resolution differs: ' + name)
        if additional:
            need(library['libraryPath'] == [str(ROOT / 'ql/src'), str(ROOT / 'ql/lib')] + additional.split(':'),
                 'dependency identities differ: ' + name)
    run('init', [CLI, 'database', 'init', str(db), '--language=ucode',
                 '--search-path=' + str(PACK), '--source-root=' + str(STAGE)],
        ROOT, env, out, records)
    run('index', [CLI, 'database', 'index-files', '--language=ucode',
                  '--include=**/rpcd/ucode/*', '--working-dir=' + str(STAGE), str(db)],
        ROOT, env, out, records)
    routing_path = db / 'trap/ucode/routing.json'
    need(routing_path.is_file(), 'missing pre-finalize routing receipt')
    shutil.copy2(routing_path, out / 'routing.json')
    run('finalize', [CLI, 'database', 'finalize', str(db)], ROOT, env, out, records)
    with zipfile.ZipFile(db / 'src.zip') as archive:
        infos = archive.infolist()
        expected_archive = {str(STAGE / path).lstrip('/'): sha for path, sha in files.items()}
        need(len(infos) == len(expected_archive) and len({item.filename for item in infos}) == len(infos)
             and {item.filename for item in infos} == set(expected_archive), 'source archive identities differ')
        need(all(not item.is_dir() and hashlib.sha256(archive.read(item)).hexdigest() == expected_archive[item.filename]
                 for item in infos), 'source archive bytes differ')

    for name, query in (
        ('success', ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql'),
        ('errors', ROOT / 'ql/src/diagnostics/ExtractionErrors.ql'),
        ('rule', QUERY),
        ('binding', WITNESS),
    ):
        bqrs = out / (name + '.bqrs')
        run(name, [CLI, 'query', 'run', str(query), '--database=' + str(db),
                   '--search-path=' + search, *options, '--output=' + str(bqrs), '--threads=1'],
            ROOT, env, out, records)
        run(name + '-decode', [CLI, 'bqrs', 'decode', '--format=json',
                              '--entities=' + ('id' if name == 'binding' else 'url,string'), str(bqrs),
                              '--output=' + str(out / (name + '.json'))],
            ROOT, env, out, records)
    run('sarif', [CLI, 'database', 'analyze', str(db), str(QUERY),
                  '--format=sarif-latest', '--output=' + str(out / 'rule.sarif'),
                  '--search-path=' + search, *options, '--threads=1'], ROOT, env, out, records)

    expected = collections.Counter(manifest['expected_successful_multiset'])
    routing = json.loads((out / 'routing.json').read_text())
    decisions = routing['decisions']
    routes = collections.Counter(str(Path(item['path']).relative_to(STAGE))
                                 for item in decisions
                                 if item['status'] == 'plain_route_selected')
    reasons = {str(Path(item['path']).relative_to(STAGE)): item['reason']
               for item in decisions}
    need(routing['input_count'] == len(files) and len(decisions) == len(files) and
         routing['plain_count'] == len(files) and routes == expected and
         reasons == manifest['expected_route_reasons'] and
         all(routing[key] == 0 for key in ('markup_count', 'markup_inconclusive_count',
              'uncertain_count', 'excluded_count', 'duplicate_input_count')),
         'routing differs from source-first fixture set')
    success = json.loads((out / 'success.json').read_text())['#select']['tuples']
    identities = collections.Counter(relative_uri(row[0]['url']['uri'], STAGE)
                                     for row in success)
    need(identities == expected, 'successful extraction multiset differs')
    errors = json.loads((out / 'errors.json').read_text())['#select']['tuples']
    need(errors == manifest['expected_extraction_errors'], 'extraction errors differ')
    rows = json.loads((out / 'rule.json').read_text())['#select']['tuples']
    bqrs = collections.Counter((relative_uri(row[0]['url']['uri'], STAGE),
                                row[0]['url']['startLine'], row[0]['url']['startColumn'],
                                row[0]['url']['endColumn']) for row in rows)
    expected_bqrs = collections.Counter((path, site['line'], site['start_column'],
                                         site['end_column'] - 1)
                                        for path, site in manifest['expected_result_locations'].items())
    need(bqrs == expected_bqrs, 'BQRS candidate locations or multiplicity differ')
    prefix = 'Modeled request-argument map/join assembly uses an identity callback before this source-declared fs.popen call; executable guard: '
    guard_rows = collections.Counter((relative_uri(row[0]['url']['uri'], STAGE), row[1]) for row in rows)
    expected_guards = collections.Counter((path, prefix + shape + '.')
        for path, shape in manifest['expected_guard_shapes'].items())
    need(guard_rows == expected_guards, 'BQRS guard classifications differ')
    sarif = json.loads((out / 'rule.sarif').read_text())
    sites = collections.Counter((result['ruleId'],
        result['locations'][0]['physicalLocation']['artifactLocation']['uri'],
        result['locations'][0]['physicalLocation']['region']['startLine'],
        result['locations'][0]['physicalLocation']['region']['startColumn'],
        result['locations'][0]['physicalLocation']['region']['endColumn'])
        for one_run in sarif['runs'] for result in one_run.get('results', []))
    expected_sites = collections.Counter(('ucode/testing/wol-unquoted-map-join', path,
        site['line'], site['start_column'], site['end_column'])
        for path, site in manifest['expected_result_locations'].items())
    need(sites == expected_sites, 'SARIF candidate locations or multiplicity differ')
    sarif_guards = collections.Counter((result['locations'][0]['physicalLocation']['artifactLocation']['uri'],
        result['message']['text']) for one_run in sarif['runs'] for result in one_run.get('results', []))
    need(sarif_guards == expected_guards, 'SARIF guard classifications differ')
    binding_rows = json.loads((out / 'binding.json').read_text())['#select']['tuples']
    verify_binding_witnesses(binding_rows, manifest['binding_witnesses'])
    (out / 'WolOwnerMutant.ql').write_bytes(mutant_query.read_bytes())
    mutant_bqrs = out / 'owner-mutant.bqrs'
    run('owner-mutant', [CLI, 'query', 'run', str(mutant_query), '--database=' + str(db),
        '--search-path=' + search, *options, '--output=' + str(mutant_bqrs), '--threads=1'], ROOT, env, out, records)
    run('owner-mutant-decode', [CLI, 'bqrs', 'decode', '--format=json', '--entities=url,string',
        str(mutant_bqrs), '--output=' + str(out / 'owner-mutant.json')], ROOT, env, out, records)
    mutated = json.loads((out / 'owner-mutant.json').read_text())['#select']['tuples']
    def exact_guard_row(row):
        location = row[0]['url']
        return (relative_uri(location['uri'], STAGE), location['startLine'], location['startColumn'],
                location['endLine'], location['endColumn'], row[1])
    mutated_guards = collections.Counter(exact_guard_row(row) for row in mutated)
    mutant_expected = collections.Counter(exact_guard_row(row) for row in rows)
    shadow = 'usr/share/rpcd/ucode/path_binding_shadow.uc'
    site = manifest['expected_result_locations'][shadow]
    shadow_site = (shadow, site['line'], site['start_column'], site['line'], site['end_column'] - 1)
    mutant_expected[shadow_site + (prefix + 'no-matching-comparison.',)] -= 1
    mutant_expected[shadow_site + (prefix + 'fixed-path-comparison.',)] += 1
    mutant_expected += collections.Counter()
    need(mutated_guards == mutant_expected and mutated_guards != collections.Counter(exact_guard_row(row) for row in rows),
         'fixed-path owner mutant did not change only intended classification')
    need(all(digest(STAGE / path) == sha for path, sha in files.items()),
         'fixture changed during smoke')
    print(json.dumps({'status': 'matched_source_first_fixture', 'files': len(files),
                      'routes': len(decisions), 'extracted': len(success),
                      'errors': len(errors), 'results': len(rows),
                      'query_sha256': digest(QUERY), 'work': str(work)}, sort_keys=True))


def main():
    # Preserve the owner-only mutation for the entire resolver and query run.
    anchor = 'lexical = pathDecl.getParent() and\n    lexical.getParent() instanceof UCODE::Program and'
    original = QUERY.read_text()
    need(original.count(anchor) == 1, 'fixed-path mutation anchor')
    mutant = original.replace(anchor, 'lexical = pathDecl.getParent() and\n    1 = 1 and')
    with tempfile.TemporaryDirectory(prefix='wol-owner-mutant-', dir=ROOT / 'ql/src') as tmpdir:
        mutant_query = Path(tmpdir) / 'WolOwnerMutant.ql'
        mutant_query.write_text(mutant)
        execute(mutant_query)


if __name__ == '__main__':
    main()
