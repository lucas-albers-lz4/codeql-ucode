#!/usr/bin/env python3
"""Opt-in #155 source-observation smoke; requires prebuilt pack and resolved dependencies."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import re
import subprocess
import tempfile
import zipfile
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('oracle', HERE / 'check-results.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)

LOG = None
RUN_OUTPUT = None
ACTIVE_GENERATED = None
ACTIVE_QUERY_HASHES = None
INPUT_GUARD = None
PACK_RECEIPT = None
PACK_BUILD_REVISION = None

def run(*args, env=None):
    argv = [str(a) for a in args]
    if INPUT_GUARD is not None: INPUT_GUARD()
    if LOG is None:
        return subprocess.run(argv, env=env, check=True, stdout=subprocess.PIPE, text=True).stdout
    index = len(list(LOG.glob('*.argv.json')))
    prefix = LOG / f'{index:03d}'
    (LOG / f'{index:03d}.argv.json').write_text(json.dumps(argv, indent=2) + '\n')
    (LOG / f'{index:03d}.env.json').write_text(json.dumps(dict(env or os.environ), indent=2) + '\n')
    started = time.time()
    result = subprocess.run(argv, env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    (LOG / f'{index:03d}.stdout').write_text(result.stdout)
    (LOG / f'{index:03d}.stderr').write_text(result.stderr)
    (LOG / f'{index:03d}.result.json').write_text(json.dumps({'returncode':result.returncode,'cwd':str(ROOT),'started_unix':started,'ended_unix':time.time()})+'\n')
    if result.returncode: raise subprocess.CalledProcessError(result.returncode, argv)
    if INPUT_GUARD is not None: INPUT_GUARD()
    return result.stdout

def tree_hash(root, excluded=None):
    """Canonical sorted tree records: path, type, mode, size, per-file SHA-256."""
    require(root.is_dir() and not root.is_symlink(), f'missing or aliased tree: {root}')
    records=[]
    for p in sorted(root.rglob('*'), key=lambda x:x.relative_to(root).as_posix()):
        if excluded is not None and (p == excluded or excluded in p.parents): continue
        mode=p.lstat().st_mode
        require(not stat.S_ISLNK(mode), f'symlink in pinned tree: {p}')
        record={'path':p.relative_to(root).as_posix(),'mode':stat.S_IMODE(mode)}
        if stat.S_ISREG(mode):
            h=hashlib.sha256()
            with p.open('rb') as f:
                while chunk := f.read(1024*1024): h.update(chunk)
            record.update({'type':'file','size':p.stat().st_size,'sha256':h.hexdigest()})
        elif stat.S_ISDIR(mode): record.update({'type':'directory','size':None,'sha256':None})
        else: raise ValueError(f'non-regular tree entry: {p}')
        records.append(record)
    return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

def require(ok, message):
    if not ok: raise ValueError(message)

def load(path): return strict_json(path.read_text())

PACKAGES = ('controlflow/1.0.12', 'dataflow/1.1.6', 'regex/1.0.12', 'ssa/1.0.12',
            'threat-models/1.1.1', 'typetracking/1.0.12', 'util/1.0.12', 'yaml/1.0.61')

def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result, 'duplicate JSON key')
            result[key]=value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def check_query_resolution(raw, queries):
    resolved=strict_json(raw)
    require(type(resolved) is list and all(type(p) is str for p in resolved), 'resolver query format')
    require(Counter(resolved)==Counter(str(q) for q in queries), 'resolved query identities')

def check_library_resolution(raw, query, output):
    result=strict_json(raw)
    require(type(result) is dict and set(result)=={'libraryPath','dbscheme','compilationCache','relativeName','qlPackName'}, 'library resolver format')
    packages=output / 'cache/common/packages/codeql'
    library=[ROOT / 'ql/src',ROOT / 'ql/lib']+[packages / p for p in PACKAGES]
    require(result['libraryPath']==[str(p) for p in library], 'resolved library identities')
    require(result['dbscheme']==str(ROOT / 'ql/lib/ucode.dbscheme'), 'resolved dbscheme')
    require(result['compilationCache']==[str(output / 'cache/compilation')], 'resolved compilation cache')
    require(result['qlPackName']=='lucas-albers-lz4/ucode-queries', 'resolved query pack')
    require(result['relativeName']=='lucas-albers-lz4/ucode-queries/'+str(query.relative_to(ROOT / 'ql/src')), 'resolved query relative name')
    return {p:tree_hash(packages / p) for p in PACKAGES}

def workspace_inventory():
    directories = [ROOT / 'ql/src', ROOT / 'ql', ROOT] + list(ROOT.parents)
    paths = [d / 'codeql-workspace.yml' for d in directories]
    return {str(p):{'physical_path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} if p.is_file() else None for p in paths}

def git_head():
    return subprocess.run(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,check=True,text=True,stdout=subprocess.PIPE).stdout.strip()

def verify_producer_head(expected, actual):
    require(re.fullmatch(r'[0-9a-f]{40}',expected) is not None, 'producer head')
    require(actual==expected, 'unexpected producer HEAD')

def git_status():
    return subprocess.run(['/usr/bin/git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,check=True,text=True,stdout=subprocess.PIPE).stdout

def verify_snapshot(expected, observed):
    require(expected==observed, 'effective inputs changed')

def source_snapshot(cli,pack):
    return {'git_head':git_head(), 'cli_path':str(cli), 'pack_receipt_path':str(PACK_RECEIPT), 'pack_build_revision':PACK_BUILD_REVISION,
            'pack_receipt_sha256':hashlib.sha256(PACK_RECEIPT.read_bytes()).hexdigest(), 'workspace_files':workspace_inventory(), 'cwd':str(ROOT), 'search_path':[str(pack),str(ROOT / 'ql/lib'),str(ROOT / 'ql/src')],
            'cli_sha256':hashlib.sha256(cli.read_bytes()).hexdigest(), 'pack_tree_sha256':tree_hash(pack),
            'lib_tree_sha256':tree_hash(ROOT / 'ql/lib'), 'src_tree_sha256':tree_hash(ROOT / 'ql/src',ACTIVE_GENERATED),
            'codeql_config_sha256':tree_hash(ROOT / '.codeql'),
            'manifest_sha256':hashlib.sha256((ROOT / '.codeqlmanifest.json').read_bytes()).hexdigest(),
            'extractor_descriptor_sha256':hashlib.sha256((ROOT / 'codeql-extractor.yml').read_bytes()).hexdigest(),
            'smoke_input_hashes':smoke_input_hashes()}

def verify_generated(directory, expected):
    if directory is None:
        require(expected is None, 'generated query guard state')
        return
    require(directory.is_dir() and not directory.is_symlink(), 'generated query directory')
    files=list(directory.iterdir())
    require(all(p.is_file() and not p.is_symlink() for p in files), 'unexpected generated query entry')
    actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    require(actual==expected, 'generated query identities or bytes changed')

def mutations(source):
    guards = {
      'competing': '  not exists(UCODE::Identifier id | id.getLocation().getFile() = call.getLocation().getFile() and\n    id.getValue() = "stat" and statCompetingBindingOrWrite(id)) and\n',
      'request': 'read.getVariable().getAstNode() = TIdentifier(formal) and\n  ',
      'unique': '  strictcount(UCODE::ImportStatement other, UCODE::Identifier id |\n    id = statImportBinding(other) and other.getLocation().getFile() = call.getLocation().getFile() and\n    id.getValue() = "stat") = 1 and\n',
    }
    result = {}
    for name, guard in guards.items():
        require(source.count(guard) == 1, f'mutation target changed: {name}')
        result[name] = source.replace(guard, '').replace('ucode/inventory/issue-155-stat-observation', f'ucode/testing/issue-155-{name}-mutant')
    return result

def source_declared_fs_guard_queries(source, *, family, id_prefix, selection):
    guards = {
      'declaration': '  exists(UCODE::VariableDeclarator d | d.getName() = id)\n  or ',
      'write': '  or exists(UCODE::AssignmentExpression a | a.getLeft() = id)\n',
      'module': '    imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "fs" and\n',
      'alias': '    not exists(spec.getAlias()) and\n',
      'optional': '  not exists(raw.getOptionalChain()) and\n',
      'unique': '    strictcount(UCODE::ImportStatement other, UCODE::Identifier id |\n      id = fsImportBinding(other) and\n      other.getLocation().getFile() = raw.getLocation().getFile() and id.getValue() = name\n    ) = 1 and\n',
      'diagnostic': '    not exists(ExtractionError error | error.getLocation().getFile() = raw.getLocation().getFile())\n',
    }
    output = {}
    for name, guard in guards.items():
        require(source.count(guard) == 1, f'model mutation target changed: {name}')
        body = source.replace(guard, '    1 = 1\n' if name == 'diagnostic' else '')
        output[name] = (f"/** @name Testing-only {family} {name} guard mutation\n * @kind table\n * @id ucode/testing/{id_prefix}{name}-mutant\n * @tags testing\n */\nimport codeql.files.FileSystem\n" + body + selection)
    return output

def model_mutations(source):
    return source_declared_fs_guard_queries(source, family='stat', id_prefix='issue155-model-', selection="""
from UCODE::CallExpression call, UCODE::AstNode arg
where sourceDeclaredFsCall(call, "stat") and
  arg = call.getArguments().getChild(0) and arg instanceof UCODE::Expression and
  not exists(int i | i != 0 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  call.getFunction() as callee_node, arg as argument_node
""")

def check_sources(stage, entries):
    for e in entries:
        path = e.get('staged_path', e.get('path'))
        content = (stage / path).read_bytes()
        require(len(content) == e['bytes'] and hashlib.sha256(content).hexdigest() == e['sha256'], f'source bytes: {path}')

def check_routes(receipt, stage, entries):
    require(receipt['input_count'] == len(entries) and receipt['plain_count'] == len(entries), 'route counts')
    require(all(receipt[k] == 0 for k in ('excluded_count', 'uncertain_count', 'markup_count', 'markup_inconclusive_count', 'duplicate_input_count')), 'unexpected routes')
    expected = Counter((str(stage / e.get('staged_path', e.get('path'))), e.get('staged_path', e.get('path')), e['expected_route']['classification'], e['expected_route']['reason'], e['expected_route']['status']) for e in entries)
    keys = ('path', 'installed_path', 'classification', 'reason', 'status')
    require(Counter(tuple(row[k] for k in keys) for row in receipt['decisions']) == expected, 'route identities')

def check_archive(path, stage, entries):
    want = {str(stage / e.get('staged_path', e.get('path'))).lstrip('/'): e for e in entries}
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(len(infos) == len(want) and len({i.filename for i in infos}) == len(want) and {i.filename for i in infos} == set(want), 'archive identities')
        for info in infos:
            data = archive.read(info); entry = want[info.filename]
            require(not info.is_dir() and len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], 'archive content')

def check_diagnostics(success, errors, stage, entries):
    expected = Counter((stage / e.get('staged_path', e.get('path'))).as_uri() for e in entries)
    rows = oracle.tuples(success)
    require(Counter(row[0]['url']['uri'] for row in rows) == expected, 'success identities')
    require(oracle.tuples(errors) == [], 'extraction errors')

def smoke_input_hashes():
    paths = [p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.uc','.json','.py') and '__pycache__' not in p.parts]
    return {str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def preflight(cli, pack, output):
    """Resolve the actual query set and retain outputs; performs no extraction."""
    initial = source_snapshot(cli,pack)
    package_root=output / 'cache/common/packages/codeql'
    initial_packages={p:tree_hash(package_root / p) for p in PACKAGES}
    fixed = [ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', ROOT / 'ql/src/diagnostics/ExtractionErrors.ql',
             ROOT / 'ql/src/inventory/Issue155StatObservation.ql']
    fixed += sorted((ROOT / 'ql/src/testing/issue155-stat').glob('*.ql'))
    mutation_sets = mutations((ROOT / 'ql/src/inventory/Issue155StatObservation.ql').read_text())
    mutation_sets.update({'model_'+k:v for k,v in model_mutations((ROOT / 'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text()).items()})
    generated = output / 'query-sources'; generated.mkdir()
    global ACTIVE_GENERATED, ACTIVE_QUERY_HASHES
    with tempfile.TemporaryDirectory(prefix='issue155-resolve-', dir=ROOT / 'ql/src') as temp:
        temp = Path(temp); ACTIVE_GENERATED=temp; queries = list(fixed)
        global INPUT_GUARD
        def guard_preflight():
            verify_generated(ACTIVE_GENERATED,ACTIVE_QUERY_HASHES)
            verify_snapshot(initial,source_snapshot(cli,pack))
            require({p:tree_hash(package_root / p) for p in PACKAGES}==initial_packages, 'package content changed during resolution')
        for name, content in sorted(mutation_sets.items()):
            p = temp / (name + '.ql'); p.write_text(content); (generated / p.name).write_text(content); queries.append(p)
        ACTIVE_QUERY_HASHES={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in temp.iterdir()}
        INPUT_GUARD=guard_preflight
        INPUT_GUARD()
        paths = {q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in queries}
        require(len(paths)==len(queries), 'duplicate query names')
        (output / 'query-hashes.json').write_text(json.dumps(paths, indent=2)+'\n')
        search=f'--search-path={pack}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}'
        common=f'--common-caches={output / "cache/common"}'
        compile_cache=f'--compilation-cache={output / "cache/compilation"}'
        result = run(cli,'resolve','queries',*queries,'--format=json',search,common)
        (output / 'resolved-queries.json').write_text(result)
        check_query_resolution(result,queries)
        resolved_packages = None
        for index, query in enumerate(queries):
            result=run(cli,'resolve','library-path',f'--query={query}',search,common,compile_cache,'--no-default-compilation-cache','--format=json')
            (output / f'library-{index:03d}.json').write_text(result)
            observed=check_library_resolution(result,query,output)
            if resolved_packages is None: resolved_packages=observed
            require(observed==resolved_packages==initial_packages, 'library package content changed during resolution')
        require(all(hashlib.sha256(q.read_bytes()).hexdigest()==paths[q.name] for q in queries), 'query changed during resolution')
    ACTIVE_GENERATED=None
    ACTIVE_QUERY_HASHES=None
    INPUT_GUARD()
    INPUT_GUARD=None
    snapshot=source_snapshot(cli,pack)
    require(snapshot==initial, 'effective inputs changed before preflight completion')
    (output / 'preflight-complete.json').write_text(json.dumps({'query_hashes':paths,'inputs':snapshot,'packages':resolved_packages,'cache_tree_sha256':load(output / 'provenance.json')['cache_tree_sha256']},indent=2)+'\n')
    print('resolver commands completed; inspect retained outputs before extraction')

def execute(cli, pack, base, entries, duplicate, mutant_names, malformed=False):
    stage = base / 'stage'; stage.mkdir(parents=True)
    source_root = HERE / 'duplicate' if duplicate else HERE
    for e in entries:
        path = e.get('staged_path', e.get('path'))
        dest = stage / path; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / path, dest)
    check_sources(stage, entries)
    db = base / 'db'
    run(cli, 'database', 'init', db, '--language=ucode', f'--search-path={pack}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}', f'--common-caches={RUN_OUTPUT / "cache/common"}', f'--source-root={stage}')
    env = os.environ.copy(); env['CODEQL_UCODE_STAGED_ROOT'] = str(stage)
    run(cli, 'database', 'index-files', db, '--language=ucode', '--include=**/*.uc', f'--working-dir={stage}', f'--common-caches={RUN_OUTPUT / "cache/common"}', '--threads=1', '--ram=2048', env=env)
    receipt = load(db / 'trap/ucode/routing.json'); (base / 'routing.json').write_text(json.dumps(receipt, indent=2)+'\n'); check_routes(receipt, stage, entries)
    run(cli, 'database', 'finalize', db, f'--common-caches={RUN_OUTPUT / "cache/common"}', '--threads=1', '--ram=2048')
    check_archive(db / 'src.zip', stage, entries)
    source = (ROOT / 'ql/src/inventory/Issue155StatObservation.ql').read_text()
    mutants = mutations(source)
    model_guards = model_mutations((ROOT / 'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text())
    global ACTIVE_GENERATED, ACTIVE_QUERY_HASHES
    with tempfile.TemporaryDirectory(prefix='issue155-smoke-', dir=ROOT / 'ql/src') as temp:
        tmp = Path(temp); ACTIVE_GENERATED=tmp
        queries = {'raw': ROOT / 'ql/src/testing/issue155-stat/StatAstInventory.ql', 'edges': ROOT / 'ql/src/testing/issue155-stat/TypedEdges.ql', 'access': ROOT / 'ql/src/testing/issue155-stat/VariableAccesses.ql',
                   'success': ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', 'errors': ROOT / 'ql/src/diagnostics/ExtractionErrors.ql',
                   'baseline': ROOT / 'ql/src/inventory/Issue155StatObservation.ql',
                   'model': ROOT / 'ql/src/testing/issue155-stat/StatModel.ql', 'member': ROOT / 'ql/src/testing/issue155-stat/StatModelCalls.ql',
                   'arg_mutants': ROOT / 'ql/src/testing/issue155-stat/StatModelMutants.ql', 'empty_mutant': ROOT / 'ql/src/testing/issue155-stat/StatModelEmptyMutant.ql'}
        for name in mutant_names:
            queries[name] = tmp / (name + '.ql'); queries[name].write_text(mutants[name]); (base / (name + '.ql')).write_text(mutants[name])
        for name in (['diagnostic'] if malformed else ['unique'] if duplicate else ['declaration','write','module','alias','optional']):
            label = 'model_' + name; queries[label] = tmp / (label + '.ql'); queries[label].write_text(model_guards[name]); (base / (label + '.ql')).write_text(model_guards[name])
        ACTIVE_QUERY_HASHES={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp.iterdir()}
        verify_generated(ACTIVE_GENERATED,ACTIVE_QUERY_HASHES)
        results = {}
        pinned = load(RUN_OUTPUT / 'preflight-receipt.json')['query_hashes']
        for name, query in queries.items():
            require(pinned.get(query.name)==hashlib.sha256(query.read_bytes()).hexdigest(), f'query differs from preflight: {query.name}')
            resolved=run(cli,'resolve','library-path',f'--query={query}',f'--search-path={pack}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}',f'--common-caches={RUN_OUTPUT / "cache/common"}',f'--compilation-cache={RUN_OUTPUT / "cache/compilation"}','--no-default-compilation-cache','--format=json')
            (base / (name + '-library.json')).write_text(resolved)
            require(check_library_resolution(resolved,query,RUN_OUTPUT)==load(RUN_OUTPUT / 'preflight-receipt.json')['packages'], 'resolved library pack content')
            bqrs = base / (name + '.bqrs')
            run(cli, 'query', 'run', query, f'--database={db}', f'--search-path={pack}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}', f'--output={bqrs}', f'--common-caches={RUN_OUTPUT / "cache/common"}', f'--compilation-cache={RUN_OUTPUT / "cache/compilation"}', '--no-default-compilation-cache', '--threads=1', '--ram=2048')
            decoded = run(cli, 'bqrs', 'decode', '--format=json', '--entities=id', bqrs) if name not in ('success', 'errors') else run(cli, 'bqrs', 'decode', '--format=json', '--entities=url,string', bqrs)
            (base / (name + '.json')).write_text(decoded)
            results[name] = json.loads(decoded)
    ACTIVE_GENERATED=None
    ACTIVE_QUERY_HASHES=None
    check_sources(stage, entries)
    if malformed:
        oracle.verify_malformed(results, stage, entries[0], load(HERE / 'model-manifest.json'))
        print(f'{base.name}: preliminary malformed diagnostic and model exclusion verified')
        return
    check_diagnostics(results['success'], results['errors'], stage, entries)
    paths = ['controls/positive-direct.uc'] if duplicate else [e.get('staged_path', e.get('path')) for e in entries if e.get('expected_candidate_rows') == 1 or 'staged_path' in e]
    observed_entries = [e for e in entries if not e.get('path', '').startswith('model-controls/')]
    oracle.verify_witnesses(results['raw'], results['access'], results['edges'], observed_entries, duplicate)
    baseline = oracle.verify(results['raw'], results['access'], results['edges'], results['baseline'], observed_entries, paths, duplicate)
    if not duplicate: oracle.verify_model_control_witnesses(results['raw'], results['edges'], load(HERE / 'model-manifest.json'))
    expected_model = oracle.verify_model(results['raw'], results['edges'], results['model'], results['member'], load(HERE / 'model-manifest.json'), duplicate)
    if not duplicate: oracle.verify_model_mutants(results['raw'], results['arg_mutants'], results['empty_mutant'], expected_model)
    oracle.verify_model_guard_mutants(results['raw'], results, expected_model, observed_entries, duplicate)
    raw = oracle.tuples(results['raw']); by_path = {e.get('staged_path', e.get('path')): e for e in entries}
    additions = {'competing': ['controls/negative-shadow.uc', 'controls/negative-reassignment.uc'], 'request': ['controls/negative-request-shadow.uc'], 'unique': ['controls/negative-duplicate.uc']}
    for name in mutant_names:
        rows = oracle.tuples(results[name]); got = Counter((r[0], *(v['id'] for v in r[1:])) for r in rows)
        expected = baseline + [oracle.expected(raw, by_path[p], duplicate) for p in additions[name]]
        require(got == Counter(expected), f'{name} mutant identities or multiplicity')
    print(f'{base.name}: exact routes, archive, diagnostics, identities and mutants verified')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codeql', type=Path, required=True, help='absolute path to pinned CLI 2.27.4')
    parser.add_argument('--pack', type=Path, required=True, help='absolute path to prebuilt current-source extractor pack')
    parser.add_argument('--pack-sha256', required=True, help='reviewed canonical tree digest')
    parser.add_argument('--pack-provenance', type=Path, required=True, help='absolute independently reviewed pack build receipt')
    parser.add_argument('--pack-provenance-sha256', required=True, help='reviewed receipt SHA-256')
    parser.add_argument('--pack-build-revision', required=True, help='revision named in reviewed pack receipt')
    parser.add_argument('--producer-head', required=True, help='reviewed exact producer commit')
    parser.add_argument('--cache', type=Path, required=True, help='absolute pre-resolved CodeQL package cache')
    parser.add_argument('--cache-sha256', required=True, help='reviewed cache tree digest')
    parser.add_argument('--output', type=Path, required=True, help='fresh absolute caller-owned output path')
    parser.add_argument('--preflight-only', action='store_true', help='resolve actual query dependencies, do not extract')
    parser.add_argument('--preflight-receipt', type=Path, help='completed resolver preflight for these exact inputs')
    args = parser.parse_args(); cli = args.codeql; pack = args.pack
    global PACK_RECEIPT, PACK_BUILD_REVISION
    require(args.pack_provenance.is_absolute() and args.pack_provenance.is_file() and not args.pack_provenance.is_symlink(), 'pack provenance must be an absolute regular file')
    require(hashlib.sha256(args.pack_provenance.read_bytes()).hexdigest()==args.pack_provenance_sha256, 'pack provenance digest')
    require(re.fullmatch(r'[0-9a-f]{40}',args.pack_build_revision) is not None, 'pack build revision')
    PACK_RECEIPT=args.pack_provenance; PACK_BUILD_REVISION=args.pack_build_revision
    verify_producer_head(args.producer_head,git_head())
    require(args.output.is_absolute() and not args.output.exists(), 'output must be fresh absolute path')
    output = args.output.parent.resolve(strict=True) / args.output.name
    for protected in (ROOT.resolve(), args.pack.resolve(), args.cache.resolve()):
        require(not output.is_relative_to(protected) and not protected.is_relative_to(output), 'output overlaps protected input')
    args.output = output
    require(args.cache.is_absolute() and args.cache.is_dir(), 'cache must be an absolute directory')
    require(tree_hash(pack) == args.pack_sha256, 'pack digest')
    require(tree_hash(args.cache) == args.cache_sha256, 'cache digest')
    args.output.mkdir(); global LOG, RUN_OUTPUT; RUN_OUTPUT = args.output; LOG = args.output / 'commands'; LOG.mkdir()
    (args.output / 'producer-status.txt').write_text(git_status())
    (args.output / 'pack-provenance.receipt').write_bytes(args.pack_provenance.read_bytes())
    home = args.output / 'home'; home.mkdir(); private_cache = args.output / 'cache'; shutil.copytree(args.cache, private_cache)
    require(tree_hash(private_cache) == args.cache_sha256, 'copied cache digest')
    config = args.output / 'config'; config.mkdir()
    tmp = args.output / 'tmp'; tmp.mkdir()
    os.environ.clear()
    os.environ.update({'PATH':'/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL':'C', 'LANG':'C', 'TZ':'UTC',
      'HOME':str(home), 'TMPDIR':str(tmp), 'TMP':str(tmp), 'TEMP':str(tmp),
      'XDG_CACHE_HOME':str(private_cache), 'XDG_CONFIG_HOME':str(config),
      'XDG_DATA_HOME':str(home / 'data'), 'CODEQL_CONFIG_FILE':str(config / 'codeql-config'),
      'JAVA_TOOL_OPTIONS':f'-Duser.home={home} -Djava.io.tmpdir={tmp} -XX:-UsePerfData'})
    (config / 'codeql-config').write_text('')
    (args.output / 'environment.json').write_text(json.dumps(dict(os.environ),indent=2)+'\n')
    (args.output / 'provenance.json').write_text(json.dumps({'cli':str(cli), 'cli_sha256':hashlib.sha256(cli.read_bytes()).hexdigest(), 'pack':str(pack), 'pack_tree_sha256':args.pack_sha256, 'cache':str(args.cache), 'cache_tree_sha256':args.cache_sha256, 'producer_head':git_head(), 'pack_build_revision':args.pack_build_revision, 'pack_receipt':str(args.pack_provenance), 'pack_receipt_sha256':args.pack_provenance_sha256},indent=2)+'\n')
    require(cli.is_absolute() and cli.is_file() and os.access(cli, os.X_OK), 'CLI must be an absolute executable')
    require(pack.is_absolute() and pack.is_dir(), 'pack must be an absolute directory')
    require(run(cli, 'version', '--format=terse').strip() == '2.27.4', 'CLI version')
    if args.preflight_only:
        preflight(cli, pack, args.output)
        return
    require(args.preflight_receipt is not None and args.preflight_receipt.is_absolute(), 'completed preflight receipt required')
    receipt = load(args.preflight_receipt)
    require(receipt['inputs']==source_snapshot(cli,pack) and receipt['cache_tree_sha256']==args.cache_sha256, 'preflight input mismatch')
    def guard():
        verify_generated(ACTIVE_GENERATED,ACTIVE_QUERY_HASHES)
        verify_snapshot(receipt['inputs'],source_snapshot(cli,pack))
        packages=args.output / 'cache/common/packages/codeql'
        require({p:tree_hash(packages / p) for p in PACKAGES}==receipt['packages'], 'resolved package content changed')
    global INPUT_GUARD
    INPUT_GUARD=guard
    INPUT_GUARD()
    (args.output / 'preflight-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    manifest = load(HERE / 'source-manifest.json'); duplicate = load(HERE / 'duplicate-source-manifest.json')
    base = args.output.resolve()
    model = load(HERE / 'model-manifest.json')
    extra = [dict(e, expected_route={'classification':'plain','reason':'ucode_extension','status':'plain_route_selected'}) for e in model['files'] if not e['path'].endswith('malformed.uc')]
    execute(cli, pack, base / 'main', [manifest['real_source']] + manifest['controls'] + extra, False, ['competing', 'request'])
    execute(cli, pack, base / 'duplicate', duplicate['files'], True, ['unique'])
    bad = [dict(e, expected_route={'classification':'plain','reason':'ucode_extension','status':'plain_route_selected'}) for e in model['files'] if e['path'].endswith('malformed.uc')]
    execute(cli, pack, base / 'malformed', bad, False, [], True)
    INPUT_GUARD()

if __name__ == '__main__': main()
