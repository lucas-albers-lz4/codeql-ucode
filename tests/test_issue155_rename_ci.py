"""Offline checks of rename's source-first and destination-identity oracles."""
from collections import Counter
import copy
import importlib.util
from pathlib import Path
import tempfile
import shutil
import json
from unittest.mock import patch
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rename_ci',ROOT/'scripts/issue155-rename-ci.py')
ci=importlib.util.module_from_spec(spec);spec.loader.exec_module(ci)

def table(rows, columns=None):return {'#select':{'columns':columns or [],'tuples':rows}}

class RenameCiTests(unittest.TestCase):
    def test_stages_and_verifies_every_source_first_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);manifest,entries=ci.stage_inputs(stage)
            self.assertEqual(len(entries),20)
            def check(data,anchor):
                lines=data.splitlines(keepends=True); sl,sc=anchor['start']; el,ec=anchor['end_exclusive']
                self.assertEqual(sl,el,'anchor must be single line')
                self.assertEqual(lines[sl-1][sc-1:ec-1].decode(),anchor['text'])
            for e in entries:
                data=(stage/e['path']).read_bytes()
                for value in e['anchors'].values():
                    for anchor in value if isinstance(value,list) else [value]:check(data,anchor)
            (stage/'rename-controls/spread-first.uc').write_text('changed')
            with self.assertRaisesRegex(ValueError,'source bytes: rename-controls/spread-first.uc'):
                ci.common.inputs.check_sources(stage,entries)

    def test_manifest_rejects_nonbinary_or_boolean_multiplicity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixtures=root/'fixtures';shutil.copytree(ci.FIXTURES,fixtures)
            manifest=fixtures/'manifest.json';original=json.loads(manifest.read_text())
            with patch.object(ci,'FIXTURES',fixtures):
                for value in (2,True,-1):
                    data=copy.deepcopy(original);data['controls'][0]['expected_model_rows']=value
                    manifest.write_text(json.dumps(data));stage=root/f'stage-{value}';stage.mkdir(exist_ok=True)
                    with self.subTest(value=value),self.assertRaisesRegex(ValueError,'model multiplicity'):
                        ci.stage_inputs(stage)

    def test_exact_model_oracle_rejects_source_as_destination(self):
        expected=[('p',1,2,3,4)]
        columns=[{'name':x,'kind':'String' if x=='path' else 'Entity'} for x in ['path','call_node','callee_node','source_node','destination_node']]
        model=table([['p',{'id':1},{'id':2},{'id':3},{'id':4}]],columns)
        membership=table([['p',{'id':1}]])
        wrong=table([['p',{'id':1},{'id':2},{'id':3},{'id':3}]],columns)
        ci.verify_models(model,membership,wrong,expected)
        with self.assertRaisesRegex(ValueError,'rename model identities or multiplicity'):
            ci.verify_models(wrong,membership,wrong,expected)
        with self.assertRaisesRegex(ValueError,'wrong-destination mutant identities'):
            ci.verify_models(model,membership,model,expected)

    def test_raw_argument_order_and_arity_are_independent(self):
        def node(kind,name,sl,sc,el,ec,i):return ['p',kind,name,sl,sc,el,ec,{'id':i}]
        raw=table([node('CallExpression','',1,1,1,16,1),node('Identifier','rename',1,1,1,6,2),
                   node('String','',1,8,1,10,3),node('String','',1,13,1,15,4)])
        def edge(src,field,index,dst):return ['p',{'id':src},'',field,index,{'id':dst}]
        edges=table([edge(1,'call-function',-1,2),edge(1,'call-arguments',-1,5),edge(5,'argument',0,3),edge(5,'argument',1,4)])
        anchor=lambda s,e:{'start':[1,s],'end_exclusive':[1,e]}
        entry={'path':'p','expected_model_rows':1,'anchors':{'call':anchor(1,17),'callee':anchor(1,7),
               'arguments':[dict(anchor(8,11),kind='String'),dict(anchor(13,16),kind='String')]}}
        self.assertEqual(ci.verify_witnesses(raw,edges,[entry]),[('p',1,2,3,4)])
        injected=copy.deepcopy(raw); injected['#select']['tuples'].append(node('ImportStatement','',2,1,2,10,9))
        with self.assertRaisesRegex(ValueError,'unexpected import'):
            ci.verify_witnesses(injected,edges,[entry])
        changed=copy.deepcopy(edges);changed['#select']['tuples'][-1][4]=0
        with self.assertRaisesRegex(ValueError,'argument indexes/arity'):
            ci.verify_witnesses(raw,changed,[entry])

    def test_module_fragment_identity_and_value_are_exact(self):
        path='p';a={'import_statement':{'start':[1,1],'end_exclusive':[1,10]},
                    'module_fragment':{'text':'fs','start':[1,5],'end_exclusive':[1,7]}}
        raw=table([[path,'ImportStatement','',1,1,1,9,{'id':1}],
                   [path,'StringFragment','',1,5,1,6,{'id':2}]])
        entries=[{'path':path,'anchors':a}]
        rows=table([[path,{'id':1},{'id':2},'fs']])
        ci.verify_import_fragments(raw,rows,entries)
        bad=copy.deepcopy(rows);bad['#select']['tuples'][0][3]='other'
        with self.assertRaisesRegex(ValueError,'import fragment identities or values'):
            ci.verify_import_fragments(raw,bad,entries)

    def test_shape_mutants_reject_missing_expected_extra(self):
        manifest=ci.common.inputs.load(ci.FIXTURES/'manifest.json');entries=manifest['controls'];by_path={e['path']:e for e in entries}
        names=['three','spread-first','spread-second','zero','one'];raw=[];ids={}
        for i,name in enumerate(names,10):
            path='rename-controls/'+name+'.uc';a=by_path[path]['anchors']['call'];sl,sc=a['start'];el,ec=a['end_exclusive']
            raw.append([path,'CallExpression','',sl,sc,el,ec-1,{'id':i}]);ids[name]=i
        expected=[('base',1,2,3,4)]; extras={'arity':['three'],'spread-first':['spread-first'],'spread-second':['spread-second'],
            'missing':['zero','one','spread-first','spread-second']};rows=[]
        for mutation,names in extras.items():
            rows.append([mutation,'base',{'id':1}])
            rows.extend([mutation,'rename-controls/'+name+'.uc',{'id':ids[name]}] for name in names)
        ci.verify_shape_mutants(table(raw),table(rows),entries,expected)
        rows.pop()
        with self.assertRaisesRegex(ValueError,'shape mutant identities'):
            ci.verify_shape_mutants(table(raw),table(rows),entries,expected)

    def test_guard_mutations_are_distinct_and_keep_rename_shape(self):
        queries=ci.guard_mutations()
        self.assertEqual(set(queries),{'declaration','write','module','alias','optional','unique','diagnostic'})
        for query in queries.values():
            self.assertIn('sourceDeclaredFsCall(call, "rename")',query)
            self.assertIn('dst = call.getArguments().getChild(1)',query)
            self.assertIn('i != 0 and i != 1',query)
        self.assertNotIn('exists(UCODE::VariableDeclarator d | d.getName() = id)',queries['declaration'])
        self.assertNotIn('or exists(UCODE::AssignmentExpression a | a.getLeft() = id)',queries['write'])

    def test_guard_counterfactual_requires_exact_added_identity(self):
        pathnames={'declaration':'shadow-lexical','write':'reassignment','module':'wrong-module','alias':'alias',
                   'optional':'optional','unique':'duplicate','diagnostic':'malformed'}
        manifest=ci.common.inputs.load(ci.FIXTURES/'manifest.json');entries=[manifest['real']]+manifest['controls']
        by_path={e['path']:e for e in entries};raw=[];results={}
        baseline=[('base',1,2,3,4)]
        for idx,(guard,name) in enumerate(pathnames.items(),start=10):
            path='rename-controls/'+name+'.uc';a=by_path[path]['anchors']; nodes=[]
            for i,(kind,anchor) in enumerate([('CallExpression',a['call']),('Identifier',a['callee'])]+[(v['kind'],v) for v in a['arguments']]):
                sl,sc=anchor['start'];el,ec=anchor['end_exclusive'];ident=idx*10+i
                raw.append([path,kind,'',sl,sc,el,ec-1,{'id':ident}]);nodes.append(ident)
            results['guard_'+guard]=table([['base',{'id':1},{'id':2},{'id':3},{'id':4}],
                [path,*({'id':x} for x in nodes)]])
        ci.verify_guard_mutants(table(raw),results,entries,baseline)
        results['guard_alias']['#select']['tuples'].pop()
        with self.assertRaisesRegex(ValueError,'alias: guard mutant identities'):
            ci.verify_guard_mutants(table(raw),results,entries,baseline)

    def test_malformed_diagnostics_have_exact_identity_and_count(self):
        stage=Path('/tmp/rename-test');bad='rename-controls/malformed.uc';good='rename-controls/literal.uc'
        model={'malformed_diagnostic':{'path':bad,'count':1,'start':[3,12],'end_inclusive':[3,12]}}
        results={'success':table([[{'url':{'uri':(stage/good).as_uri()}}]]),
                 'errors':table([[{'url':{'uri':(stage/bad).as_uri(),'startLine':3,'startColumn':12,'endLine':3,'endColumn':12}}]])}
        ci.verify_diagnostics(stage,results,model,[{'path':good},{'path':bad}])
        changed=copy.deepcopy(results);changed['errors']['#select']['tuples'][0][0]['url']['startColumn']=13
        with self.assertRaisesRegex(ValueError,'malformed diagnostic identity'):
            ci.verify_diagnostics(stage,changed,model,[{'path':good},{'path':bad}])

if __name__=='__main__':unittest.main()
