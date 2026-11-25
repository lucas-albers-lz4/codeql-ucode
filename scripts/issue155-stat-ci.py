#!/usr/bin/env python3
"""Focused extraction regression for the source-declared unary stat model."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'ql/test/issue155-stat-observation'
PACK = ROOT / 'extractor-pack'

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

oracle = load_module('issue155_oracle', FIXTURES / 'check-results.py')
inputs = load_module('issue155_runner', FIXTURES / 'run-smoke.py')

def require(ok, message):
    if not ok:
        raise ValueError(message)

LOG_DIR = None

def run(*args, env=None):
    argv=[str(x) for x in args]
    require(LOG_DIR is not None, 'command log not initialized')
    index=len(list(LOG_DIR.glob('*.argv.json')))
    (LOG_DIR/f'{index:03d}.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
    result=subprocess.run(argv,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (LOG_DIR/f'{index:03d}.stdout').write_text(result.stdout)
    (LOG_DIR/f'{index:03d}.stderr').write_text(result.stderr)
    (LOG_DIR/f'{index:03d}.exit').write_text(str(result.returncode)+'\n')
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {argv!r}; stderr: {result.stderr[-2000:]}')
    return result.stdout

def stage_inputs(stage):
    manifest = inputs.load(FIXTURES / 'source-manifest.json')
    duplicate = inputs.load(FIXTURES / 'duplicate-source-manifest.json')
    model = inputs.load(FIXTURES / 'model-manifest.json')
    entries = [manifest['real_source']] + manifest['controls']
    selected = [(FIXTURES, e) for e in entries]
    direct = next(e for e in entries if e.get('path') == 'controls/positive-direct.uc')
    duplicate_positive = next(e for e in duplicate['files'] if e['path'] == direct['path'])
    require((direct['bytes'],direct['sha256']) == (duplicate_positive['bytes'],duplicate_positive['sha256']),
            'duplicate positive differs from main source')
    duplicate_bytes=(FIXTURES/'duplicate'/duplicate_positive['path']).read_bytes()
    require(len(duplicate_bytes)==duplicate_positive['bytes'] and hashlib.sha256(duplicate_bytes).hexdigest()==duplicate_positive['sha256'],
            'duplicate positive source bytes')
    negative = next(e for e in duplicate['files'] if e['path'] == 'controls/negative-duplicate.uc')
    selected.append((FIXTURES / 'duplicate', negative))
    route={'classification':'plain','reason':'ucode_extension','status':'plain_route_selected'}
    selected.extend((FIXTURES,dict(e,expected_route=route)) for e in model['files'])
    paths=[e.get('staged_path',e.get('path')) for _,e in selected]
    require(len(paths)==len(set(paths))==18, 'fixture inventory identities')
    for root,entry in selected:
        path=entry.get('staged_path',entry.get('path')); source=root/path; dest=stage/path
        data=source.read_bytes()
        require(len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'], f'fixture bytes: {path}')
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    return entries, duplicate['files'], model, [entry for _,entry in selected]

def verify_mixed_diagnostics(stage, results, entries, model):
    path='model-controls/malformed.uc'
    good=[e for e in entries if e.get('staged_path',e.get('path')) != path]
    expected=sorted((stage/e.get('staged_path',e.get('path'))).as_uri() for e in good)
    actual=sorted(r[0]['url']['uri'] for r in oracle.tuples(results['success']))
    require(actual==expected, 'successful-file identities')
    errors=oracle.tuples(results['errors']); pred=model['malformed_preliminary_diagnostic']
    require(len(errors)==1, 'malformed diagnostic count')
    require(errors[0][0]['url']=={'uri':(stage/path).as_uri(), 'startLine':pred['start'][0],
            'startColumn':pred['start'][1], 'endLine':pred['end_inclusive'][0],
            'endColumn':pred['end_inclusive'][1]}, 'malformed diagnostic identity')
    raw=oracle.tuples(results['raw']); edges=oracle.tuples(results['edges'])
    anchor=lambda start,end:{'start':[2,start],'end_exclusive':[2,end]}
    call=oracle.node(raw,path,'CallExpression',anchor(1,17)); callee=oracle.node(raw,path,'Identifier',anchor(1,5))
    arg=oracle.node(raw,path,'String',anchor(6,16))
    def targets(source, field):
        return [(r[4],r[5]['id']) for r in edges if r[0]==path and r[1]=={'id':source} and r[3]==field]
    require(targets(call,'call-function')==[(-1,callee)], 'malformed recovered callee')
    owner=targets(call,'call-arguments')
    require(len(owner)==1 and targets(owner[0][1],'argument')==[(0,arg)], 'malformed recovered argument')

def execute(base):
    global LOG_DIR
    LOG_DIR=base/'commands'; LOG_DIR.mkdir()
    stage=base/'stage'; stage.mkdir(parents=True)
    normal, duplicate, model, entries=stage_inputs(stage)
    db=base/'db'; cli=shutil.which('codeql'); require(cli is not None, 'CodeQL executable missing')
    run(cli,'database','init',db,'--language=ucode',f'--search-path={PACK}',f'--source-root={stage}')
    env=os.environ.copy(); env['CODEQL_UCODE_STAGED_ROOT']=str(stage)
    run(cli,'database','index-files',db,'--language=ucode','--include=**/*.uc',f'--working-dir={stage}',env=env)
    routing=inputs.load(db/'trap/ucode/routing.json')
    (base/'routing.json').write_text(json.dumps(routing,indent=2)+'\n')
    inputs.check_routes(routing,stage,entries)
    run(cli,'database','finalize',db)
    inputs.check_archive(db/'src.zip',stage,entries)
    queries={'success':ROOT/'ql/src/diagnostics/SuccessfullyExtractedFiles.ql',
             'errors':ROOT/'ql/src/diagnostics/ExtractionErrors.ql'}
    queries.update({name:ROOT/f'ql/src/testing/issue155-stat/{filename}.ql' for name,filename in (
        ('raw','StatAstInventory'),('edges','TypedEdges'),('access','VariableAccesses'),
        ('model','StatModel'),('member','StatModelCalls'))})
    results={}
    for name,query in queries.items():
        bqrs=base/(name+'.bqrs')
        run(cli,'query','run',query,f'--database={db}',f'--search-path={PACK}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}',
            f'--output={bqrs}','--threads=1','--ram=2048')
        entity='url,string' if name in ('success','errors') else 'id'
        decoded=run(cli,'bqrs','decode','--format=json',f'--entities={entity}',bqrs)
        (base/(name+'.json')).write_text(decoded)
        results[name]=inputs.strict_json(decoded)
    verify_mixed_diagnostics(stage,results,entries,model)
    oracle.verify_witnesses(results['raw'],results['access'],results['edges'],normal)
    oracle.verify_witnesses(results['raw'],results['access'],results['edges'],duplicate,True)
    oracle.verify_model_control_witnesses(results['raw'],results['edges'],model)
    oracle.verify_model(results['raw'],results['edges'],results['model'],results['member'],model)
    inputs.check_sources(stage,entries)
    print('stat model: exact routes, diagnostics, source witnesses and model identities verified')

def main():
    requested=os.environ.get('STAT_MODEL_OUT')
    if requested:
        base=Path(requested); require(base.is_absolute() and not base.exists(),'STAT_MODEL_OUT must be a fresh absolute path')
        base.mkdir()
    else:
        base=Path(tempfile.mkdtemp(prefix='stat-model-ci-'))
    base=base.resolve()
    print(f'stat model evidence directory: {base}',flush=True)
    try:
        execute(base)
    except Exception as exc:
        print(f'stat model smoke failed: {exc}; evidence retained at {base}',file=sys.stderr,flush=True)
        raise

if __name__=='__main__': main()
