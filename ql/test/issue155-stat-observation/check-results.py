"""Source-first identity oracle for the #155 testing-only observation."""
from collections import Counter

COLUMNS = ['path', 'call_node', 'callee_node', 'import_node', 'specifier_node', 'handler_node',
           'formal_node', 'argument_node', 'substitution_node', 'property_node', 'args_node', 'receiver_node']
KINDS = ['CallExpression', 'Identifier', 'ImportStatement', 'ImportSpecifier', 'FunctionExpression',
         'Identifier', 'TemplateString', 'TemplateSubstitution', 'MemberExpression', 'MemberExpression', 'Identifier']
ANCHORS = [('source_anchors', 'call_expression'), ('source_anchors', 'callee_identifier'),
           ('source_witnesses', 'import_statement_source'), ('source_witnesses', 'stat_import_specifier_source'),
           ('source_witnesses', 'handler_function_expression_source'), ('source_witnesses', 'request_formal_identifier'),
           ('source_anchors', 'argument_zero_template'), ('source_anchors', 'request_substitution'),
           ('source_anchors', 'request_property'), ('source_anchors', 'request_args_receiver'),
           ('source_anchors', 'request_receiver_identifier')]

def require(ok, message):
    if not ok:
        raise ValueError(message)

def tuples(data):
    require(type(data) is dict and set(data) == {'#select'}, 'result set')
    result = data['#select']
    require(type(result) is dict and set(result) == {'columns', 'tuples'} and type(result['tuples']) is list, 'table')
    return result['tuples']

def node(raw, path, kind, anchor):
    sl, sc = anchor['start']
    el, ec = anchor['end_exclusive']
    require(ec > 1, 'unsupported end column')
    found = [r for r in raw if r[0] == path and r[1] == kind and r[3:7] == [sl, sc, el, ec - 1]]
    require(len(found) == 1 and type(found[0][7]) is dict and set(found[0][7]) == {'id'},
            f'raw identity ambiguous or missing: {path} {kind} {sl}:{sc}')
    return found[0][7]['id']

def expected(raw, entry, duplicate=False):
    path = entry.get('staged_path', entry.get('path'))
    if duplicate:
        anchors = [entry['tuple'][c] for c in COLUMNS[1:]]
    else:
        source = dict(entry)
        source['source_anchors'] = entry.get('source_anchors', entry.get('expected_ast_anchor'))
        anchors = [source[section][key] for section, key in ANCHORS]
    return (path, *(node(raw, path, kind, a) for kind, a in zip(KINDS, anchors)))

def verify(raw_data, access_data, edges_data, result_data, entries, positive_paths, duplicate=False):
    raw, accesses, edges = map(tuples, (raw_data, access_data, edges_data))
    result = result_data['#select']
    require(result['columns'] == [{'name': c, 'kind': 'String' if c == 'path' else 'Entity'} for c in COLUMNS], 'candidate columns')
    rows = tuples(result_data)
    got = []
    for row in rows:
        require(type(row) is list and len(row) == len(COLUMNS) and type(row[0]) is str, 'candidate row')
        require(all(type(v) is dict and set(v) == {'id'} and type(v['id']) is int for v in row[1:]), 'candidate entity')
        got.append((row[0], *(v['id'] for v in row[1:])))
    selected = {e.get('staged_path', e.get('path')): e for e in entries}
    want = [expected(raw, selected[p], duplicate) for p in positive_paths]
    require(Counter(got) == Counter(want), 'candidate identities or multiplicity')
    for row in want:
        path, call, callee, imp, spec, handler, formal, arg, sub, prop, args, receiver = row
        reads = [r for r in accesses if r[0] == path and r[1] == 'read' and r[3] == {'id': receiver}]
        require(len(reads) == 1 and reads[0][10] == {'id': formal}, f'request read binding: {path}')
        def edge(source, field):
            return [r for r in edges if r[0] == path and r[1] == {'id': source} and r[3] == field]
        require(len(edge(call, 'call-function')) == 1 and edge(call, 'call-function')[0][5] == {'id': callee}, 'call function')
        require(not edge(call, 'call-optional'), 'call optional')
        require(len(edge(prop, 'member-object')) == 1 and edge(prop, 'member-object')[0][5] == {'id': args}, 'property receiver')
        require(len(edge(args, 'member-object')) == 1 and edge(args, 'member-object')[0][5] == {'id': receiver}, 'args receiver')
        anchors = selected[path].get('source_anchors', selected[path].get('expected_ast_anchor', {}))
        if anchors.get('post_call_member'):
            outer = node(raw, path, 'MemberExpression', anchors['post_call_member'])
            optional = node(raw, path, 'OptionalChain', anchors['member_optional_token'])
            require(len(edge(outer, 'member-object')) == 1 and edge(outer, 'member-object')[0][5] == {'id': call}, 'outer member object')
            require(len(edge(outer, 'member-optional')) == 1 and edge(outer, 'member-optional')[0][5] == {'id': optional}, 'outer optional member')
    return want

def verify_witnesses(raw_data, access_data, edges_data, entries, duplicate=False):
    """Require independently identified source witnesses for every control, including negatives."""
    raw, accesses, edges = map(tuples, (raw_data, access_data, edges_data))
    for entry in entries:
        path = entry.get('staged_path', entry.get('path'))
        if duplicate:
            anchors = entry['tuple']
            def n(kind, key): return node(raw, path, kind, anchors[key])
            call=n('CallExpression','call_node'); callee=n('Identifier','callee_node')
            imp=n('ImportStatement','import_node'); spec=n('ImportSpecifier','specifier_node')
            handler=n('FunctionExpression','handler_node'); formal=n('Identifier','formal_node')
            arg=n('TemplateString','argument_node'); sub=n('TemplateSubstitution','substitution_node')
            prop=n('MemberExpression','property_node'); args=n('MemberExpression','args_node'); recv=n('Identifier','receiver_node')
            source_anchors = {}; witnesses = {}
        else:
            source_anchors = entry.get('source_anchors', entry.get('expected_ast_anchor'))
            witnesses = entry['source_witnesses']
            def a(kind, key): return node(raw,path,kind,source_anchors[key])
            def w(kind, key): return node(raw,path,kind,witnesses[key])
            call=a('CallExpression','call_expression'); callee=a('Identifier','callee_identifier')
            imp=w('ImportStatement','import_statement_source'); spec=w('ImportSpecifier','stat_import_specifier_source')
            handler=w('FunctionExpression','handler_function_expression_source'); formal=w('Identifier','request_formal_identifier')
            arg=a('TemplateString','argument_zero_template')
            sub = a('TemplateSubstitution','request_substitution') if source_anchors.get('request_substitution') else None
            prop = a('MemberExpression','request_property') if source_anchors.get('request_property') else None
            args = a('MemberExpression','request_args_receiver') if source_anchors.get('request_args_receiver') else None
            recv = a('Identifier','request_receiver_identifier') if source_anchors.get('request_receiver_identifier') else None
        def targets(source, field):
            return [(r[4], r[5]['id']) for r in edges if r[0] == path and r[1] == {'id': source} and r[3] == field]
        def only(source, field, target, index=-1):
            require(targets(source,field) == [(index,target)], f'{path} witness {field}')
        only(call,'call-function',callee)
        argument_nodes=targets(call,'call-arguments'); require(len(argument_nodes)==1, f'{path} argument owner')
        only(argument_nodes[0][1],'argument',arg,0)
        parameter_nodes=targets(handler,'function-parameters'); require(len(parameter_nodes)==1, f'{path} parameters owner')
        only(parameter_nodes[0][1],'formal',formal,0)
        clauses=targets(imp,'import-clause'); require(len(clauses)==1, f'{path} import clause')
        named=targets(clauses[0][1],'import-named'); require(len(named)==1, f'{path} named imports')
        require(sum(target == spec for _,target in targets(named[0][1],'named-import')) == 1, f'{path} import specifier edge')
        if not duplicate:
            module = w('String','import_module_literal')
            only(imp,'import-source',module)
            if witnesses.get('stat_import_alias_identifier'):
                alias=w('Identifier','stat_import_alias_identifier'); only(spec,'import-alias',alias)
        if sub is not None:
            require(sum(target == sub for _,target in targets(arg,'template-child'))==1, f'{path} template substitution')
            only(sub,'substitution-child',prop); only(prop,'member-object',args); only(args,'member-object',recv)
            reads=[r for r in accesses if r[0]==path and r[1]=='read' and r[3]=={'id':recv}]
            require(len(reads)==1, f'{path} receiver read')
            if path.endswith('negative-request-shadow.uc'):
                shadow=w('Identifier','shadow_request_declaration_name')
                match=[r for r in raw if r[0]==path and r[7]=={'id':shadow}]
                require(len(match)==1 and match[0][8]=='VariableDeclarator' and reads[0][10]==match[0][14], f'{path} shadow target')
            else: require(reads[0][10]=={'id':formal}, f'{path} formal target')
        optional = targets(call,'call-optional')
        require(len(optional) == (1 if path.endswith('negative-optional-call.uc') else 0), f'{path} call optional witness')
        if optional:
            token=node(raw,path,'OptionalChain',source_anchors['call_optional_token'])
            require(optional==[(-1,token)], f'{path} optional token identity')
        for key, field in [('competing_stat_declaration_name','declarator-name'),('competing_stat_write_identifier','assignment-left')]:
            if witnesses.get(key):
                ident=w('Identifier',key)
                require(sum(1 for r in edges if r[0]==path and r[3]==field and r[5]=={'id':ident})==1, f'{path} {field}')
        if duplicate and path.endswith('negative-duplicate.uc'):
            second_import = node(raw,path,'ImportStatement',{'start':[2,1],'end_exclusive':[2,39]})
            alias = node(raw,path,'Identifier',{'start':[2,22],'end_exclusive':[2,26]})
            second_clause=targets(second_import,'import-clause'); require(len(second_clause)==1, f'{path} second import clause')
            second_named=targets(second_clause[0][1],'import-named'); require(len(second_named)==1, f'{path} second named import')
            second_specs=targets(second_named[0][1],'named-import'); require(len(second_specs)==1, f'{path} second specifier')
            only(second_specs[0][1],'import-alias',alias)

def verify_model(raw_data, edges_data, model_data, member_data, manifest, duplicate=False):
    raw, edges = map(tuples, (raw_data, edges_data))
    wanted=[]
    def site(path, line, start, end, argstart, argend, kind, callee_span=None):
        def anchor(a,b): return {'start':[line,a],'end_exclusive':[line,b]}
        call=node(raw,path,'CallExpression',anchor(start,end))
        callee_start,callee_end=callee_span if callee_span is not None else (start,start+4)
        callee=node(raw,path,'Identifier',anchor(callee_start,callee_end)); arg=node(raw,path,kind,anchor(argstart,argend))
        names=[r[2] for r in raw if r[0]==path and r[7]=={'id':callee}]
        require(names==['stat'], f'{path} model callee value')
        def targets(source, field): return [(r[4],r[5]['id']) for r in edges if r[0]==path and r[1]=={'id':source} and r[3]==field]
        require(targets(call,'call-function') == [(-1,callee)], f'{path} model callee witness')
        owner=targets(call,'call-arguments'); require(len(owner)==1, f'{path} model argument owner')
        require(targets(owner[0][1],'argument') == [(0,arg)], f'{path} model argument witness')
        return (path,call,callee,arg)
    if duplicate:
        wanted.append(site('controls/positive-direct.uc',9,16,64,21,63,'TemplateString'))
    else:
        for item in manifest['real_sites']:
            wanted.append(site(manifest['real_path'],item['line'],*item['call'],*item['argument'],item['argument_kind'],item['callee']))
        for path, info in manifest['synthetic_positive'].items(): wanted.append(site(path,*info))
    cols=['path','call_node','callee_node','argument_node']
    require(model_data['#select']['columns']==[{'name':x,'kind':'String' if x=='path' else 'Entity'} for x in cols], 'model columns')
    got=Counter((r[0],*(v['id'] for v in r[1:])) for r in tuples(model_data))
    require(got==Counter(wanted),'model exact identities or multiplicity')
    require(Counter((r[0],r[1]['id']) for r in tuples(member_data))==Counter((r[0],r[1]) for r in wanted),'model membership identities')
    return wanted

def verify_model_control_witnesses(raw_data, edges_data, manifest):
    raw, edges = map(tuples, (raw_data,edges_data))
    for path, item in manifest['control_witnesses'].items():
        if path.endswith('malformed.uc'): continue
        if 'property' in item:
            line,start,end=item['property']
            member=node(raw,path,'MemberExpression',{'start':[line,start],'end_exclusive':[line,end]})
            receiver=node(raw,path,'Identifier',{'start':[line,1],'end_exclusive':[line,5]})
            prop=node(raw,path,'PropertyIdentifier',{'start':[line,6],'end_exclusive':[line,10]})
            require(sum(1 for r in edges if r[0]==path and r[1]=={'id':member} and r[3]=='member-object' and r[5]=={'id':receiver})==1, f'{path} property receiver')
            require(sum(1 for r in edges if r[0]==path and r[1]=={'id':member} and r[3]=='member-property' and r[5]=={'id':prop})==1, f'{path} property name')
            require(not any(r[0]==path and r[1]=='CallExpression' and r[3:5]==[line,start] for r in raw), f'{path} property is a call')
            continue
        line,start,end=item['call']; a={'start':[line,start],'end_exclusive':[line,end]}
        call=node(raw,path,'CallExpression',a)
        def targets(source,field): return [(r[4],r[5]['id']) for r in edges if r[0]==path and r[1]=={'id':source} and r[3]==field]
        callee=node(raw,path,'Identifier',{'start':[line,start],'end_exclusive':[line,start+4]})
        require(targets(call,'call-function')==[(-1,callee)], f'{path} callee')
        owner=targets(call,'call-arguments'); require(len(owner)==1, f'{path} argument owner')
        wanted=[]
        for idx,(l,s,e,kind) in enumerate(item['arguments']):
            wanted.append((idx,node(raw,path,kind,{'start':[l,s],'end_exclusive':[l,e]})))
        require(sorted(targets(owner[0][1],'argument'))==wanted, f'{path} argument witnesses')

def verify_model_mutants(raw_data, arg_data, empty_data, baseline):
    raw=tuples(raw_data)
    def n(path,kind,line,start,end):
        return node(raw,path,kind,{'start':[line,start],'end_exclusive':[line,end]})
    two='model-controls/two.uc'; spread='model-controls/spread.uc'; empty='model-controls/empty.uc'
    extra_two=(two,n(two,'CallExpression',2,1,28),n(two,'Identifier',2,1,5),n(two,'String',2,6,16))
    extra_spread=(spread,n(spread,'CallExpression',2,1,15),n(spread,'Identifier',2,1,5),n(spread,'SpreadElement',2,6,14))
    got=Counter((r[0],r[1],*(v['id'] for v in r[2:])) for r in tuples(arg_data))
    expected=Counter([('arity',*r) for r in baseline+[extra_two]]+[('spread',*r) for r in baseline+[extra_spread]])
    require(got==expected,'argument mutant identities or multiplicity')
    empty_call=n(empty,'CallExpression',2,1,7)
    expected_members=Counter((r[0],r[1]) for r in baseline)+Counter([(empty,empty_call),(spread,extra_spread[1])])
    require(Counter((r[0],r[1]['id']) for r in tuples(empty_data))==expected_members,'missing-argument mutant membership')

def verify_model_guard_mutants(raw_data, results, baseline, entries, duplicate):
    raw=tuples(raw_data); by_path={e.get('staged_path', e.get('path')):e for e in entries}
    controls={'declaration':'controls/negative-shadow.uc','write':'controls/negative-reassignment.uc',
              'module':'controls/negative-other-module.uc','alias':'controls/negative-aliased-import.uc',
              'optional':'controls/negative-optional-call.uc','unique':'controls/negative-duplicate.uc'}
    for name in (['unique'] if duplicate else ['declaration','write','module','alias','optional']):
        path=controls[name]; entry=by_path[path]
        if duplicate: anchors=entry['tuple']; keys=['call_node','callee_node','argument_node']
        else: anchors=entry['source_anchors']; keys=['call_expression','callee_identifier','argument_zero_template']
        ids=[node(raw,path,kind,anchors[key]) for kind,key in zip(['CallExpression','Identifier','TemplateString'],keys)]
        expected=Counter(baseline+[(path,*ids)])
        got=Counter((r[0],*(v['id'] for v in r[1:])) for r in tuples(results['model_'+name]))
        require(got==expected,f'model {name} guard mutant identities or multiplicity')

def verify_malformed(results, stage, entry, manifest):
    path=entry['path']; raw=tuples(results['raw']); edges=tuples(results['edges'])
    require(tuples(results['success'])==[], 'malformed success unexpectedly recorded')
    errors=tuples(results['errors'])
    require(len(errors)==1, 'malformed diagnostic count')
    location=errors[0][0]['url']; prediction=manifest['malformed_preliminary_diagnostic']
    require(location=={'uri':(stage / path).as_uri(),'startLine':prediction['start'][0],
                      'startColumn':prediction['start'][1], 'endLine':prediction['end_inclusive'][0],
                      'endColumn':prediction['end_inclusive'][1]}, 'malformed diagnostic identity')
    require(tuples(results['baseline'])==[] and tuples(results['model'])==[] and tuples(results['member'])==[], 'malformed baseline not empty')
    call=node(raw,path,'CallExpression',{'start':[2,1],'end_exclusive':[2,17]})
    callee=node(raw,path,'Identifier',{'start':[2,1],'end_exclusive':[2,5]})
    arg=node(raw,path,'String',{'start':[2,6],'end_exclusive':[2,16]})
    targets=lambda source,field:[(r[4],r[5]['id']) for r in edges if r[0]==path and r[1]=={'id':source} and r[3]==field]
    require(targets(call,'call-function')==[(-1,callee)], 'malformed recovered callee')
    owner=targets(call,'call-arguments'); require(len(owner)==1 and targets(owner[0][1],'argument')==[(0,arg)], 'malformed recovered argument')
    got=Counter((r[0],*(v['id'] for v in r[1:])) for r in tuples(results['model_diagnostic']))
    require(got==Counter([(path,call,callee,arg)]), 'malformed diagnostic mutation')
