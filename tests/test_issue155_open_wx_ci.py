"""Offline tests for source-first literal wx model checks."""
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('open_wx_ci',ROOT/'scripts/issue155-open-wx-ci.py')
ci=importlib.util.module_from_spec(spec);spec.loader.exec_module(ci)
def table(rows,columns=None):return {'#select':{'columns':columns or [],'tuples':rows}}

class OpenWxCiTests(unittest.TestCase):
    def test_stages_exact_inventory_and_source_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);manifest,entries=ci.stage_inputs(stage);self.assertEqual(len(entries),29)
            for e in entries:
                data=(stage/e['path']).read_bytes();lines=data.splitlines(keepends=True)
                for v in e['anchors'].values():
                    for a in v if isinstance(v,list) else [v]:
                        sl,sc=a['start'];el,ec=a['end_exclusive'];self.assertEqual(sl,el)
                        self.assertEqual(lines[sl-1][sc-1:ec-1].decode(),a['text'])
            (stage/'open-controls/spread-path.uc').write_text('changed')
            with self.assertRaisesRegex(ValueError,'source bytes: open-controls/spread-path.uc'):
                ci.common.inputs.check_sources(stage,entries)

    def test_manifest_multiplicity_rejects_nonbinary_and_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixtures=root/'fixtures';shutil.copytree(ci.FIXTURES,fixtures);manifest=fixtures/'manifest.json';original=json.loads(manifest.read_text())
            with patch.object(ci,'FIXTURES',fixtures):
                for i,value in enumerate((2,True,-1)):
                    data=copy.deepcopy(original);data['controls'][0]['expected_model_rows']=value;manifest.write_text(json.dumps(data))
                    stage=root/f'stage-{i}';stage.mkdir()
                    with self.subTest(value=value),self.assertRaisesRegex(ValueError,'model multiplicity'):
                        ci.stage_inputs(stage)

    def test_permission_relation_and_wrong_path_oracle(self):
        cols=[{'name':x,'kind':'String' if x=='path' else 'Entity'} for x in ['path','call_node','callee_node','path_node','mode_node']]
        expected=[('two',1,2,3,4),('three',5,6,7,8)]
        model=table([['two',{'id':1},{'id':2},{'id':3},{'id':4}],['three',{'id':5},{'id':6},{'id':7},{'id':8}]],cols)
        results={'model':model,'membership':table([['two',{'id':1}],['three',{'id':5}]]),
                 'permission':table([['three',{'id':5},{'id':9}]]),
                 'wrong_path':table([['two',{'id':1},{'id':2},{'id':4},{'id':4}],['three',{'id':5},{'id':6},{'id':8},{'id':8}]],cols)}
        ci.verify_model(results,expected,[('three',5,9)])
        bad=copy.deepcopy(results);bad['permission']['#select']['tuples'].append(['two',{'id':1},{'id':9}])
        with self.assertRaisesRegex(ValueError,'permission identities'):ci.verify_model(bad,expected,[('three',5,9)])
        bad=copy.deepcopy(results);bad['model']=bad['wrong_path']
        with self.assertRaisesRegex(ValueError,'open model identities'):ci.verify_model(bad,expected,[('three',5,9)])

    def test_fragment_multiset_rejects_changed_wx(self):
        results={'argument_fragments':table([['p',{'id':1},1,{'id':2},{'id':3},'wx']]),
                 'import_fragments':table([['p',{'id':4},{'id':5},'fs']])}
        ci.verify_fragments(results,[('p',1,1,2,3,'wx')],[('p',4,5,'fs')])
        results['argument_fragments']['#select']['tuples'][0][-1]='w'
        with self.assertRaisesRegex(ValueError,'argument fragment identities or values'):
            ci.verify_fragments(results,[('p',1,1,2,3,'wx')],[('p',4,5,'fs')])

    def test_guard_templates_keep_exact_open_shape(self):
        variants=ci.guard_mutations();self.assertEqual(set(variants),{'declaration','write','module','alias','optional','unique','diagnostic'})
        for q in variants.values():
            self.assertIn('sourceDeclaredFsCall(call, "open")',q);self.assertIn('mode.getChild(0)',q)
            self.assertIn('not exists(mode.getChild(1))',q);self.assertIn('pathArg as path_node',q)
        self.assertNotIn('exists(UCODE::VariableDeclarator d | d.getName() = id)',variants['declaration'])

    def test_counterfactuals_require_independent_expected_extras(self):
        m=ci.common.inputs.load(ci.FIXTURES/'manifest.json');entries=m['controls'];by={e['path']:e for e in entries}
        names={'shadow-lexical','reassignment','wrong-module','alias','optional','duplicate','malformed',
               'read','write','alternate-mode','wrong-slot-path','wrong-slot-permission','mode-escape','four','spread-path','spread-permission'}
        raw=[];candidate={};calls={}
        for i,name in enumerate(sorted(names),10):
            path='open-controls/'+name+'.uc';a=by[path]['anchors'];nodes=[]
            for j,(kind,anchor) in enumerate([('CallExpression',a['call']),('Identifier',a['callee'])]+[(v['kind'],v) for v in a['arguments']]):
                sl,sc=anchor['start'];el,ec=anchor['end_exclusive'];ident=i*10+j
                raw.append([path,kind,'',sl,sc,el,ec-1,{'id':ident}]);nodes.append(ident)
            calls[name]=(path,nodes[0]);candidate[name]=(path,*nodes[:4])
        baseline=[('base',1,2,3,4)]
        def row(t):return [t[0],*({'id':x} for x in t[1:])]
        guards={'declaration':'shadow-lexical','write':'reassignment','module':'wrong-module','alias':'alias','optional':'optional','unique':'duplicate','diagnostic':'malformed'}
        results={'guard_'+g:table([row(baseline[0]),row(candidate[n])]) for g,n in guards.items()}
        modes=['read','write','alternate-mode','wrong-slot-path','wrong-slot-permission']
        results['any_mode']=table([row(x) for x in baseline+[candidate[n] for n in modes]])
        results['extra_fragment']=table([row(baseline[0]),row(candidate['mode-escape'])])
        results['wrong_mode']=table([row(candidate['wrong-slot-path'])])
        shape=[]
        for mutation,name in [('arity','four'),('spread-path','spread-path'),('spread-permission','spread-permission')]:
            shape += [[mutation,'base',{'id':1}],[mutation,calls[name][0],{'id':calls[name][1]}]]
        results['shape']=table(shape)
        ci.verify_mutants(table(raw),results,entries,baseline)
        results['extra_fragment']['#select']['tuples'].pop()
        with self.assertRaisesRegex(ValueError,'extra-fragment mutant identities'):
            ci.verify_mutants(table(raw),results,entries,baseline)

    def test_any_mode_counterfactual_retains_single_fragment_guard(self):
        text=(ROOT/'ql/src/testing/issue155-open-wx/OpenAnyLiteralMode.ql').read_text()
        self.assertIn('mode.getChild(0) instanceof UCODE::StringFragment',text)
        self.assertIn('not exists(mode.getChild(1))',text)
        self.assertNotIn('getValue() = "wx"',text)

    def test_diagnostics_require_exact_malformed_identity(self):
        stage=Path('/tmp/open-wx-test');bad='open-controls/malformed.uc';good='open-controls/literal-two.uc'
        manifest={'malformed_diagnostic':{'path':bad,'count':1,'start':[3,12],'end_inclusive':[3,12]}}
        results={'success':table([[{'url':{'uri':(stage/good).as_uri()}}]]),
                 'errors':table([[{'url':{'uri':(stage/bad).as_uri(),'startLine':3,'startColumn':12,'endLine':3,'endColumn':12}}]])}
        ci.verify_diagnostics(stage,results,manifest,[{'path':good},{'path':bad}])
        results['errors']['#select']['tuples'][0][0]['url']['startColumn']=13
        with self.assertRaisesRegex(ValueError,'malformed diagnostic identity'):
            ci.verify_diagnostics(stage,results,manifest,[{'path':good},{'path':bad}])

if __name__=='__main__':unittest.main()
