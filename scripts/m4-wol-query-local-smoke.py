#!/usr/bin/env python3
"""Exact, testing-only WOL map/join query regression on fresh fixture bytes."""

import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'ql/test/wol-unquoted-map-join'
STAGE = FIXTURES / 'installed'
QUERY = ROOT / 'ql/src/testing/WolUnquotedMapJoin.ql'
PACK = ROOT / 'extractor-pack'
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


def relative_uri(value, stage):
    need(value.startswith('file://'), 'expected file URI')
    return str(Path(value.removeprefix('file://')).relative_to(stage))


def main():
    need(CLI is not None, 'CodeQL CLI is unavailable')
    manifest = json.loads((FIXTURES / 'expected.json').read_text())
    need(manifest['schema'] == 'wol-unquoted-map-join-fixtures-v1', 'fixture schema changed')
    need(digest(QUERY) == manifest['expected_query_sha256'], 'testing query bytes changed')
    files = manifest['files']
    actual_files = {str(p.relative_to(STAGE)) for p in STAGE.rglob('*') if p.is_file()}
    need(actual_files == set(files), 'fixture file set changed')
    need(all(digest(STAGE / path) == sha for path, sha in files.items()),
         'fixture bytes changed')
    need(digest(STAGE / 'usr/share/rpcd/ucode/luci.wol') ==
         manifest['real_wol_source_sha256'], 'real WOL source changed')
    need((PACK / 'codeql-extractor.yml').is_file(), 'extractor pack unavailable')
    version = json.loads(subprocess.check_output([CLI, 'version', '--format=json']))
    need(version['version'] == '2.27.4', 'unexpected CodeQL version')

    base = ROOT / '.codeql-database'
    base.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='wol-query-local-', dir=base))
    db = work / 'db'
    out = work / 'out'
    out.mkdir()
    home = work / 'home'
    (home / '.codeql').mkdir(parents=True)
    packages = Path.home() / '.codeql/packages'
    need(packages.is_dir(), 'install locked CodeQL packs before this smoke')
    shutil.copytree(packages, home / '.codeql/packages')
    tmp = work / 'tmp'
    tmp.mkdir()
    env = dict(os.environ, HOME=str(home), TMPDIR=str(tmp))
    search = ':'.join(map(str, (PACK, ROOT / 'ql/lib', ROOT / 'ql/src')))
    records = []
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

    for name, query in (
        ('success', ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql'),
        ('errors', ROOT / 'ql/src/diagnostics/ExtractionErrors.ql'),
        ('rule', QUERY),
    ):
        bqrs = out / (name + '.bqrs')
        run(name, [CLI, 'query', 'run', str(query), '--database=' + str(db),
                   '--search-path=' + search, '--output=' + str(bqrs), '--threads=1'],
            ROOT, env, out, records)
        run(name + '-decode', [CLI, 'bqrs', 'decode', '--format=json',
                              '--entities=url,string', str(bqrs),
                              '--output=' + str(out / (name + '.json'))],
            ROOT, env, out, records)
    run('sarif', [CLI, 'database', 'analyze', str(db), str(QUERY),
                  '--format=sarif-latest', '--output=' + str(out / 'rule.sarif'),
                  '--search-path=' + search, '--threads=1'], ROOT, env, out, records)

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
    need(all(digest(STAGE / path) == sha for path, sha in files.items()),
         'fixture changed during smoke')
    print(json.dumps({'status': 'matched_source_first_fixture', 'files': len(files),
                      'routes': len(decisions), 'extracted': len(success),
                      'errors': len(errors), 'results': len(rows),
                      'query_sha256': digest(QUERY), 'work': str(work)}, sort_keys=True))


if __name__ == '__main__':
    main()
