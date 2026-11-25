#!/usr/bin/env python3
"""Focused source-declared two-argument rename model regression."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'ql/test/issue155-rename'
PACK=ROOT/'extractor-pack'
# Reuse the stat gate's retained command, routing, archive and exact-node helpers.
import importlib.util
spec=importlib.util.spec_from_file_location('stat_gate',ROOT/'scripts/issue155-stat-ci.py')
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
oracle=common.oracle
require=common.require

def stage_inputs(stage):
    manifest=common.inputs.load(FIXTURES/'manifest.json')
    entries=[manifest['real']]+manifest['controls']
    paths=[e['path'] for e in entries]
    require(len(paths)==len(set(paths))==20,'fixture inventory identities')
    for e in entries:
        require(type(e['expected_model_rows']) is int and e['expected_model_rows'] in (0,1),f"model multiplicity: {e['path']}")
        data=(FIXTURES/e['path']).read_bytes()
        require(len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],f"fixture bytes: {e['path']}")
        dest=stage/e['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return manifest,entries

def verify_witnesses(raw_data,edges_data,entries):
    raw=oracle.tuples(raw_data);edges=oracle.tuples(edges_data); expected=[]
    for e in entries:
        path=e['path'];a=e['anchors']
        def n(kind,key):return oracle.node(raw,path,kind,a[key])
        def targets(source,field):return [(r[4],r[5]['id']) for r in edges if r[0]==path and r[1]=={'id':source} and r[3]==field]
        def only(source,field,target,idx=-1):require(targets(source,field)==[(idx,target)],f'{path}: {field} identity')
        if 'import_statement' in a:
            imp=n('ImportStatement','import_statement');spec=n('ImportSpecifier','import_specifier')
            mod=n('String','import_module');name=n('Identifier','import_name')
            only(imp,'import-source',mod);only(spec,'import-name',name)
            only(mod,'string-child',n('StringFragment','module_fragment'),0)
            owners=[r for r in raw if r[0]==path and r[7]=={'id':imp}]
            require(len(owners)==1 and owners[0][8]=='Program',f'{path}: import top-level')
            call_anchor=a.get('call',a.get('wrapped_call'))
            if call_anchor is not None:
                require(a['import_statement']['end_exclusive']<=call_anchor['start'],f'{path}: import precedence')
            clause=targets(imp,'import-clause');require(len(clause)==1,f'{path}: import clause')
            named=targets(clause[0][1],'import-named');require(len(named)==1,f'{path}: named imports')
            require(sum(v==spec for _,v in targets(named[0][1],'named-import'))==1,f'{path}: import owner')
            if 'alias' in a:only(spec,'import-alias',n('Identifier','alias'))
            else:require(not targets(spec,'import-alias'),f'{path}: unexpected import alias')
        if 'second_import' in a:
            imp2=n('ImportStatement','second_import');spec2=n('ImportSpecifier','second_specifier')
            mod2=n('String','second_module');only(imp2,'import-source',mod2);only(mod2,'string-child',n('StringFragment','second_fragment'),0)
            only(spec2,'import-alias',n('Identifier','second_alias'))
            only(spec2,'import-name',n('Identifier','second_name'))
            owners=[r for r in raw if r[0]==path and r[7]=={'id':imp2}]
            require(len(owners)==1 and owners[0][8]=='Program' and a['second_import']['end_exclusive']<=a['call']['start'],f'{path}: second import top-level/precedence')
            c=targets(imp2,'import-clause');require(len(c)==1,f'{path}: second import clause')
            q=targets(c[0][1],'import-named');require(len(q)==1 and sum(v==spec2 for _,v in targets(q[0][1],'named-import'))==1,f'{path}: second import owner')
        if 'import_statement' not in a:
            require(not any(r[0]==path and r[1]=='ImportStatement' for r in raw),f'{path}: unexpected import')
        if 'property' in a:
            member=n('MemberExpression','property');only(member,'member-object',n('Identifier','property_object'));only(member,'member-property',n('PropertyIdentifier','property_name'))
            require(not any(r[0]==path and r[1]=='CallExpression' for r in raw),f'{path}: property unexpectedly a call')
            continue
        wrapped='wrapped_call' in a
        if wrapped:
            call=n('CallExpression','wrapped_call');callee=n('ParenthesizedExpression','wrapped_callee');arguments=a['wrapped_arguments']
            only(callee,'parenthesized-child',n('Identifier','wrapped_identifier'))
        else:
            call=n('CallExpression','call');callee=n('Identifier','callee');arguments=a['arguments']
            names=[r[2] for r in raw if r[0]==path and r[7]=={'id':callee}]
            require(names==['rename'],f'{path}: callee spelling')
        only(call,'call-function',callee)
        owner=targets(call,'call-arguments');require(len(owner)==1,f'{path}: argument owner')
        ids=[oracle.node(raw,path,arg['kind'],arg) for arg in arguments]
        require(sorted(targets(owner[0][1],'argument'))==list(enumerate(ids)),f'{path}: argument indexes/arity')
        optional=targets(call,'call-optional')
        if 'optional' in a:only(call,'call-optional',n('OptionalChain','optional'))
        else:require(not optional,f'{path}: unexpected optional call')
        if 'shadow' in a:
            ident=n('Identifier','shadow')
            require(sum(1 for x in edges if x[0]==path and x[3]=='formal' and x[5]=={'id':ident})==1,f'{path}: shadow formal')
        if 'shadow_lexical' in a:
            ident=n('Identifier','shadow_lexical')
            require(sum(1 for x in edges if x[0]==path and x[3]=='declarator-name' and x[5]=={'id':ident})==1,f'{path}: shadow declarator')
        if 'write' in a:
            ident=n('Identifier','write')
            require(sum(1 for x in edges if x[0]==path and x[3]=='assignment-left' and x[5]=={'id':ident})==1,f'{path}: assignment write')
        if e['expected_model_rows']:
            require(len(ids)==2,f'{path}: positive arity')
            expected.append((path,call,callee,ids[0],ids[1]))
    return expected

def verify_import_fragments(raw_data,fragments_data,entries):
    raw=oracle.tuples(raw_data);expected=[]
    for e in entries:
        path=e['path'];a=e['anchors']
        for imp,frag in [('import_statement','module_fragment'),('second_import','second_fragment')]:
            if imp in a:
                expected.append((path,oracle.node(raw,path,'ImportStatement',a[imp]),oracle.node(raw,path,'StringFragment',a[frag]),a[frag]['text']))
    rows=oracle.tuples(fragments_data)
    got=Counter((r[0],r[1]['id'],r[2]['id'],r[3]) for r in rows)
    require(got==Counter(expected),'import fragment identities or values')

def verify_models(model_data,membership_data,wrong_data,expected):
    cols=['path','call_node','callee_node','source_node','destination_node']
    require(model_data['#select']['columns']==[{'name':x,'kind':'String' if x=='path' else 'Entity'} for x in cols],'rename model columns')
    def rows(data):return Counter((r[0],*(v['id'] for v in r[1:])) for r in oracle.tuples(data))
    def check_candidate(data):
        require(rows(data)==Counter(expected),'rename model identities or multiplicity')
    require(bool(expected),'missing positive controls')
    check_candidate(model_data)
    require(Counter((r[0],r[1]['id']) for r in oracle.tuples(membership_data))==Counter((r[0],r[1]) for r in expected),'rename membership identities or multiplicity')
    wrong=Counter((p,c,f,s,s) for p,c,f,s,d in expected)
    require(rows(wrong_data)==wrong,'wrong-destination mutant identities or multiplicity')
    try:
        check_candidate(wrong_data)
    except ValueError as exc:
        require(str(exc)=='rename model identities or multiplicity','wrong-destination mutation failed for wrong reason')
    else:
        raise ValueError('wrong-destination mutation passed exact model oracle')

def guard_mutations():
    """Use the shared helper's single-guard mutations with rename's exact shape."""
    source=(ROOT/'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text()
    variants=common.inputs.model_mutations(source)
    marker='from UCODE::CallExpression call, UCODE::AstNode arg\n'
    tail="""from UCODE::CallExpression call, UCODE::AstNode src, UCODE::AstNode dst
where sourceDeclaredFsCall(call, "rename") and
  src = call.getArguments().getChild(0) and src instanceof UCODE::Expression and
  dst = call.getArguments().getChild(1) and dst instanceof UCODE::Expression and
  not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  call.getFunction() as callee_node, src as source_node, dst as destination_node
"""
    result={}
    for name,text in variants.items():
        require(text.count(marker)==1,f'{name}: guard mutant template')
        result[name]=text.split(marker)[0].replace('issue155-model-','issue155-rename-guard-').replace('Testing-only stat','Testing-only rename')+tail
    return result

def verify_guard_mutants(raw_data,results,entries,baseline):
    raw=oracle.tuples(raw_data);by_path={e['path']:e for e in entries}
    controls={'declaration':'shadow-lexical','write':'reassignment','module':'wrong-module',
              'alias':'alias','optional':'optional','unique':'duplicate','diagnostic':'malformed'}
    for mutation,filename in controls.items():
        path='rename-controls/'+filename+'.uc';a=by_path[path]['anchors']
        call=oracle.node(raw,path,'CallExpression',a['call']);callee=oracle.node(raw,path,'Identifier',a['callee'])
        nodes=[oracle.node(raw,path,arg['kind'],arg) for arg in a['arguments']]
        require(len(nodes)==2,f'{path}: guard mutant arity')
        extra=(path,call,callee,*nodes)
        got=Counter((r[0],*(x['id'] for x in r[1:])) for r in oracle.tuples(results['guard_'+mutation]))
        require(got==Counter(baseline+[extra]),f'{mutation}: guard mutant identities or multiplicity')

def verify_shape_mutants(raw_data,shape_data,entries,baseline):
    raw=oracle.tuples(raw_data);by_path={e['path']:e for e in entries}
    additions={'arity':['three'], 'spread-first':['spread-first'], 'spread-second':['spread-second'],
               'missing':['zero','one','spread-first','spread-second']}
    expected=[]
    for mutation,names in additions.items():
        expected.extend((mutation,row[0],row[1]) for row in baseline)
        for name in names:
            path='rename-controls/'+name+'.uc';call=oracle.node(raw,path,'CallExpression',by_path[path]['anchors']['call'])
            expected.append((mutation,path,call))
    got=Counter((r[0],r[1],r[2]['id']) for r in oracle.tuples(shape_data))
    require(got==Counter(expected),'rename shape mutant identities or multiplicity')

def verify_diagnostics(stage,results,manifest,entries):
    bad=manifest['malformed_diagnostic'];good=[e for e in entries if e['path']!=bad['path']]
    expected=Counter((stage/e['path']).as_uri() for e in good)
    require(Counter(r[0]['url']['uri'] for r in oracle.tuples(results['success']))==expected,'successful-file identities')
    errors=oracle.tuples(results['errors']);require(len(errors)==bad['count'],'malformed diagnostic count')
    require(errors[0][0]['url']=={'uri':(stage/bad['path']).as_uri(),'startLine':bad['start'][0], 'startColumn':bad['start'][1], 'endLine':bad['end_inclusive'][0], 'endColumn':bad['end_inclusive'][1]},'malformed diagnostic identity')

def execute(base):
    common.LOG_DIR=base/'commands';common.LOG_DIR.mkdir();run=common.run
    stage=base/'stage';stage.mkdir();manifest,entries=stage_inputs(stage)
    db=base/'db';cli=shutil.which('codeql');require(cli is not None,'CodeQL executable missing')
    run(cli,'database','init',db,'--language=ucode',f'--search-path={PACK}',f'--source-root={stage}')
    env=os.environ.copy();env['CODEQL_UCODE_STAGED_ROOT']=str(stage)
    run(cli,'database','index-files',db,'--language=ucode','--include=**/*.uc',f'--working-dir={stage}',env=env)
    routing=common.inputs.load(db/'trap/ucode/routing.json');(base/'routing.json').write_text(json.dumps(routing,indent=2)+'\n')
    common.inputs.check_routes(routing,stage,entries)
    run(cli,'database','finalize',db);common.inputs.check_archive(db/'src.zip',stage,entries)
    queries={'success':ROOT/'ql/src/diagnostics/SuccessfullyExtractedFiles.ql','errors':ROOT/'ql/src/diagnostics/ExtractionErrors.ql',
             'raw':ROOT/'ql/src/testing/issue155-stat/StatAstInventory.ql','edges':ROOT/'ql/src/testing/issue155-stat/TypedEdges.ql',
             'model':ROOT/'ql/src/testing/issue155-rename/RenameModel.ql','membership':ROOT/'ql/src/testing/issue155-rename/RenameMembership.ql',
             'wrong':ROOT/'ql/src/testing/issue155-rename/RenameWrongDestination.ql',
             'shape':ROOT/'ql/src/testing/issue155-rename/RenameShapeMutants.ql',
             'fragments':ROOT/'ql/src/testing/issue155-rename/RenameImportFragments.ql'}
    results={}
    with tempfile.TemporaryDirectory(prefix='rename-model-mutants-',dir=ROOT/'ql/src') as tmp:
        for name,text in guard_mutations().items():
            key='guard_'+name;query=Path(tmp)/(key+'.ql');query.write_text(text)
            (base/(key+'.ql')).write_text(text);queries[key]=query
        for name,query in queries.items():
            bqrs=base/(name+'.bqrs');run(cli,'query','run',query,f'--database={db}',f'--search-path={PACK}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}',f'--output={bqrs}','--threads=1','--ram=2048')
            entities='url,string' if name in ('success','errors') else 'id'
            decoded=run(cli,'bqrs','decode','--format=json',f'--entities={entities}',bqrs);(base/(name+'.json')).write_text(decoded);results[name]=common.inputs.strict_json(decoded)
    verify_diagnostics(stage,results,manifest,entries)
    expected=verify_witnesses(results['raw'],results['edges'],entries)
    verify_import_fragments(results['raw'],results['fragments'],entries)
    verify_models(results['model'],results['membership'],results['wrong'],expected)
    verify_guard_mutants(results['raw'],results,entries,expected)
    verify_shape_mutants(results['raw'],results['shape'],entries,expected)
    common.inputs.check_sources(stage,entries)
    print('rename model: exact route, diagnostics, source witnesses, destination and wrong-index control verified')

def main():
    requested=os.environ.get('RENAME_MODEL_OUT')
    if requested:
        base=Path(requested);require(base.is_absolute() and not base.exists(),'RENAME_MODEL_OUT must be a fresh absolute path');base.mkdir()
    else:base=Path(tempfile.mkdtemp(prefix='rename-model-ci-'))
    base=base.resolve();print(f'rename model evidence directory: {base}',flush=True)
    try:execute(base)
    except Exception as exc:
        print(f'rename model smoke failed: {exc}; evidence retained at {base}',file=sys.stderr,flush=True);raise

if __name__=='__main__':main()
