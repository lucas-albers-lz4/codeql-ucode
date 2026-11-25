#!/usr/bin/env python3
"""Focused source-declared literal wx open model regression."""
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'ql/test/issue155-open-wx'
PACK=ROOT/'extractor-pack'
spec=importlib.util.spec_from_file_location('stat_gate',ROOT/'scripts/issue155-stat-ci.py')
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
oracle=common.oracle
require=common.require

def stage_inputs(stage):
    manifest=common.inputs.load(FIXTURES/'manifest.json');entries=[manifest['real']]+manifest['controls']
    require(len(entries)==29 and len({e['path'] for e in entries})==29,'fixture inventory identities')
    for e in entries:
        require(type(e['expected_model_rows']) is int and e['expected_model_rows'] in (0,1),f"model multiplicity: {e['path']}")
        source=ROOT/e['fixture_path'] if 'fixture_path' in e else FIXTURES/e['path']
        data=source.read_bytes();require(len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],f"fixture bytes: {e['path']}")
        dest=stage/e['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return manifest,entries

def verify_witnesses(raw_data,edges_data,entries):
    raw=oracle.tuples(raw_data);edges=oracle.tuples(edges_data);expected=[];permissions=[];argument_fragments=[];import_fragments=[]
    for e in entries:
        path=e['path'];a=e['anchors']
        def n(kind,key):return oracle.node(raw,path,kind,a[key])
        def targets(source,field):return [(r[4],r[5]['id']) for r in edges if r[0]==path and r[1]=={'id':source} and r[3]==field]
        def only(source,field,target,idx=-1):require(targets(source,field)==[(idx,target)],f'{path}: {field} identity')
        if 'import_statement' in a:
            imp=n('ImportStatement','import_statement');spec=n('ImportSpecifier','import_specifier')
            mod=n('String','import_module');frag=n('StringFragment','module_fragment');name=n('Identifier','import_name')
            only(imp,'import-source',mod);only(mod,'string-child',frag,0);only(spec,'import-name',name)
            owners=[r for r in raw if r[0]==path and r[7]=={'id':imp}]
            require(len(owners)==1 and owners[0][8]=='Program',f'{path}: import top-level')
            call_anchor=a.get('call',a.get('wrapped_call'))
            if call_anchor is not None:require(a['import_statement']['end_exclusive']<=call_anchor['start'],f'{path}: import precedence')
            clause=targets(imp,'import-clause');require(len(clause)==1,f'{path}: import clause')
            named=targets(clause[0][1],'import-named');require(len(named)==1 and sum(v==spec for _,v in targets(named[0][1],'named-import'))==1,f'{path}: import owner')
            if 'alias' in a:only(spec,'import-alias',n('Identifier','alias'))
            else:require(not targets(spec,'import-alias'),f'{path}: unexpected import alias')
            import_fragments.append((path,imp,frag,a['module_fragment']['text']))
        else:require(not any(r[0]==path and r[1]=='ImportStatement' for r in raw),f'{path}: unexpected import')
        if 'second_import' in a:
            imp2=n('ImportStatement','second_import');spec2=n('ImportSpecifier','second_specifier');mod2=n('String','second_module');frag2=n('StringFragment','second_fragment')
            only(imp2,'import-source',mod2);only(mod2,'string-child',frag2,0);only(spec2,'import-name',n('Identifier','second_name'));only(spec2,'import-alias',n('Identifier','second_alias'))
            owners=[r for r in raw if r[0]==path and r[7]=={'id':imp2}]
            require(len(owners)==1 and owners[0][8]=='Program' and a['second_import']['end_exclusive']<=a['call']['start'],f'{path}: second import owner/precedence')
            clause=targets(imp2,'import-clause');require(len(clause)==1,f'{path}: second clause');named=targets(clause[0][1],'import-named')
            require(len(named)==1 and sum(v==spec2 for _,v in targets(named[0][1],'named-import'))==1,f'{path}: second import specifier')
            import_fragments.append((path,imp2,frag2,a['second_fragment']['text']))
        if 'property' in a:
            member=n('MemberExpression','property');only(member,'member-object',n('Identifier','property_object'));only(member,'member-property',n('PropertyIdentifier','property_name'))
            require(not any(r[0]==path and r[1]=='CallExpression' for r in raw),f'{path}: property unexpectedly a call');continue
        wrapped='wrapped_call' in a
        if wrapped:
            call=n('CallExpression','wrapped_call');callee=n('ParenthesizedExpression','wrapped_callee');only(callee,'parenthesized-child',n('Identifier','wrapped_identifier'));arguments=a['wrapped_arguments']
        else:
            call=n('CallExpression','call');callee=n('Identifier','callee');arguments=a['arguments']
            require([r[2] for r in raw if r[0]==path and r[7]=={'id':callee}]==['open'],f'{path}: callee spelling')
        only(call,'call-function',callee);owner=targets(call,'call-arguments');require(len(owner)==1,f'{path}: argument owner')
        nodes=[oracle.node(raw,path,arg['kind'],arg) for arg in arguments]
        require(sorted(targets(owner[0][1],'argument'))==list(enumerate(nodes)),f'{path}: argument indexes/arity')
        if 'optional' in a:only(call,'call-optional',n('OptionalChain','optional'))
        else:require(not targets(call,'call-optional'),f'{path}: unexpected optional call')
        for key,field in [('shadow','formal'),('shadow_lexical','declarator-name'),('write','assignment-left')]:
            if key in a:require(sum(1 for x in edges if x[0]==path and x[3]==field and x[5]=={'id':n('Identifier',key)})==1,f'{path}: {field}')
        if not wrapped:
            for idx,arg in enumerate(arguments):
                if arg['kind']=='String':
                    frag=n('StringFragment','fragment_'+str(idx))
                    if idx==1 and 'mode_escape' in a:
                        escape=n('EscapeSequence','mode_escape')
                        require(sorted(targets(nodes[idx],'string-child'))==[(0,frag),(1,escape)],f'{path}: mode string children')
                    else:only(nodes[idx],'string-child',frag,0)
                    argument_fragments.append((path,call,idx,nodes[idx],frag,a['fragment_'+str(idx)]['text']))
        if e['expected_model_rows']:
            require(len(nodes) in (2,3),f'{path}: positive arity')
            expected.append((path,call,callee,nodes[0],nodes[1]))
            if len(nodes)==3:permissions.append((path,call,nodes[2]))
    return expected,permissions,argument_fragments,import_fragments

def rows(data):return Counter((r[0],*(x['id'] for x in r[1:])) for r in oracle.tuples(data))

def verify_model(results,expected,permissions):
    columns=['path','call_node','callee_node','path_node','mode_node']
    require(results['model']['#select']['columns']==[{'name':c,'kind':'String' if c=='path' else 'Entity'} for c in columns],'model columns')
    def exact(data):require(rows(data)==Counter(expected),'open model identities or multiplicity')
    require(bool(expected),'missing positive controls');exact(results['model'])
    require(rows(results['membership'])==Counter((r[0],r[1]) for r in expected),'membership identities or multiplicity')
    require(rows(results['permission'])==Counter(permissions),'permission identities or multiplicity')
    wrong=Counter((p,c,f,m,m) for p,c,f,arg,m in expected)
    require(rows(results['wrong_path'])==wrong,'wrong-path mutant identities')
    try:exact(results['wrong_path'])
    except ValueError as exc:require(str(exc)=='open model identities or multiplicity','wrong-path mutation failed for wrong reason')
    else:raise ValueError('wrong-path mutation passed exact model oracle')

def verify_fragments(results,arguments,imports):
    a=Counter((r[0],r[1]['id'],r[2],r[3]['id'],r[4]['id'],r[5]) for r in oracle.tuples(results['argument_fragments']))
    i=Counter((r[0],r[1]['id'],r[2]['id'],r[3]) for r in oracle.tuples(results['import_fragments']))
    require(a==Counter(arguments),'argument fragment identities or values')
    require(i==Counter(imports),'import fragment identities or values')

def guard_mutations():
    variants=common.inputs.model_mutations((ROOT/'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text())
    marker='from UCODE::CallExpression call, UCODE::AstNode arg\n'
    tail='''from UCODE::CallExpression call, UCODE::AstNode pathArg, UCODE::String mode
where sourceDeclaredFsCall(call, "open") and pathArg = call.getArguments().getChild(0) and pathArg instanceof UCODE::Expression and
  mode = call.getArguments().getChild(1) and mode.getChild(0).(UCODE::StringFragment).getValue() = "wx" and not exists(mode.getChild(1)) and
  (not exists(call.getArguments().getChild(2)) or call.getArguments().getChild(2) instanceof UCODE::Expression) and
  not exists(int i | i != 0 and i != 1 and i != 2 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  call.getFunction() as callee_node, pathArg as path_node, mode as mode_node
'''
    result={}
    for name,text in variants.items():
        require(text.count(marker)==1,f'{name}: guard mutant template')
        result[name]=text.split(marker)[0].replace('issue155-model-','issue155-open-wx-guard-').replace('Testing-only stat','Testing-only open wx')+tail
    return result

def candidate_tuple(raw,path,e):
    a=e['anchors'];call=oracle.node(raw,path,'CallExpression',a['call']);callee=oracle.node(raw,path,'Identifier',a['callee'])
    args=[oracle.node(raw,path,x['kind'],x) for x in a['arguments']]
    require(len(args)>=2,f'{path}: candidate arity')
    return (path,call,callee,args[0],args[1])

def verify_mutants(raw_data,results,entries,baseline):
    raw=oracle.tuples(raw_data);by_path={e['path']:e for e in entries}
    guards={'declaration':'shadow-lexical','write':'reassignment','module':'wrong-module','alias':'alias','optional':'optional','unique':'duplicate','diagnostic':'malformed'}
    for guard,name in guards.items():
        path='open-controls/'+name+'.uc';require(rows(results['guard_'+guard])==Counter(baseline+[candidate_tuple(raw,path,by_path[path])]),f'{guard}: guard mutant identities or multiplicity')
    modes=['read','write','alternate-mode','wrong-slot-path','wrong-slot-permission']
    additions=[candidate_tuple(raw,'open-controls/'+n+'.uc',by_path['open-controls/'+n+'.uc']) for n in modes]
    require(rows(results['any_mode'])==Counter(baseline+additions),'mode mutant identities or multiplicity')
    path='open-controls/mode-escape.uc';require(rows(results['extra_fragment'])==Counter(baseline+[candidate_tuple(raw,path,by_path[path])]),'extra-fragment mutant identities or multiplicity')
    path='open-controls/wrong-slot-path.uc';require(rows(results['wrong_mode'])==Counter([candidate_tuple(raw,path,by_path[path])]),'wrong-mode slot identities')
    shapes={'arity':'four','spread-path':'spread-path','spread-permission':'spread-permission'};expected=[]
    for mutation,name in shapes.items():
        expected.extend((mutation,r[0],r[1]) for r in baseline)
        p='open-controls/'+name+'.uc';expected.append((mutation,p,oracle.node(raw,p,'CallExpression',by_path[p]['anchors']['call'])))
    got=Counter((r[0],r[1],r[2]['id']) for r in oracle.tuples(results['shape']))
    require(got==Counter(expected),'shape mutant identities or multiplicity')

def verify_diagnostics(stage,results,manifest,entries):
    bad=manifest['malformed_diagnostic'];good=[e for e in entries if e['path']!=bad['path']]
    require(Counter(r[0]['url']['uri'] for r in oracle.tuples(results['success']))==Counter((stage/e['path']).as_uri() for e in good),'successful-file identities')
    errors=oracle.tuples(results['errors']);require(len(errors)==bad['count'],'malformed diagnostic count')
    require(errors[0][0]['url']=={'uri':(stage/bad['path']).as_uri(),'startLine':bad['start'][0],'startColumn':bad['start'][1],'endLine':bad['end_inclusive'][0],'endColumn':bad['end_inclusive'][1]},'malformed diagnostic identity')

def execute(base):
    common.LOG_DIR=base/'commands';common.LOG_DIR.mkdir();run=common.run
    stage=base/'stage';stage.mkdir();manifest,entries=stage_inputs(stage)
    db=base/'db';cli=shutil.which('codeql');require(cli is not None,'CodeQL executable missing')
    run(cli,'database','init',db,'--language=ucode',f'--search-path={PACK}',f'--source-root={stage}')
    env=os.environ.copy();env['CODEQL_UCODE_STAGED_ROOT']=str(stage)
    run(cli,'database','index-files',db,'--language=ucode','--include=**/*.uc',f'--working-dir={stage}',env=env)
    routing=common.inputs.load(db/'trap/ucode/routing.json');(base/'routing.json').write_text(json.dumps(routing,indent=2)+'\n');common.inputs.check_routes(routing,stage,entries)
    run(cli,'database','finalize',db);common.inputs.check_archive(db/'src.zip',stage,entries)
    queries={'success':ROOT/'ql/src/diagnostics/SuccessfullyExtractedFiles.ql','errors':ROOT/'ql/src/diagnostics/ExtractionErrors.ql',
             'raw':ROOT/'ql/src/testing/issue155-stat/StatAstInventory.ql','edges':ROOT/'ql/src/testing/issue155-stat/TypedEdges.ql'}
    for name,file in [('model','OpenModel'),('membership','OpenMembership'),('permission','OpenPermission'),('wrong_path','OpenWrongPath'),('wrong_mode','OpenWrongMode'),('shape','OpenShapeMutants'),('any_mode','OpenAnyLiteralMode'),('import_fragments','OpenImportFragments'),('argument_fragments','OpenArgumentFragments'),('extra_fragment','OpenAllowExtraFragment')]:queries[name]=ROOT/f'ql/src/testing/issue155-open-wx/{file}.ql'
    results={}
    with tempfile.TemporaryDirectory(prefix='open-wx-mutants-',dir=ROOT/'ql/src') as tmp:
        for name,text in guard_mutations().items():
            key='guard_'+name;query=Path(tmp)/(key+'.ql');query.write_text(text);(base/(key+'.ql')).write_text(text);queries[key]=query
        for name,query in queries.items():
            bqrs=base/(name+'.bqrs');run(cli,'query','run',query,f'--database={db}',f'--search-path={PACK}:{ROOT / "ql/lib"}:{ROOT / "ql/src"}',f'--output={bqrs}','--threads=1','--ram=2048')
            entities='url,string' if name in ('success','errors') else 'id';decoded=run(cli,'bqrs','decode','--format=json',f'--entities={entities}',bqrs)
            (base/(name+'.json')).write_text(decoded);results[name]=common.inputs.strict_json(decoded)
    verify_diagnostics(stage,results,manifest,entries)
    expected,permissions,args,imports=verify_witnesses(results['raw'],results['edges'],entries)
    verify_fragments(results,args,imports);verify_model(results,expected,permissions);verify_mutants(results['raw'],results,entries,expected)
    common.inputs.check_sources(stage,entries)
    print('open wx model: exact routes, diagnostics, witnesses, model and counterfactuals verified')

def main():
    requested=os.environ.get('OPEN_WX_MODEL_OUT')
    if requested:
        base=Path(requested);require(base.is_absolute() and not base.exists(),'OPEN_WX_MODEL_OUT must be a fresh absolute path');base.mkdir()
    else:base=Path(tempfile.mkdtemp(prefix='open-wx-model-ci-'))
    base=base.resolve();print(f'open wx evidence directory: {base}',flush=True)
    try:execute(base)
    except Exception as exc:print(f'open wx smoke failed: {exc}; evidence retained at {base}',file=sys.stderr,flush=True);raise

if __name__=='__main__':main()
