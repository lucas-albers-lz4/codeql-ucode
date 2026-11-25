"""Offline tests for the focused stat CI runner's staged and diagnostic contracts."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch
import subprocess

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('issue155_stat_ci',ROOT/'scripts/issue155-stat-ci.py')
ci=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

def table(rows): return {'#select':{'columns':[],'tuples':rows}}

class StatCiTests(unittest.TestCase):
    def test_stages_exact_pinned_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp)
            normal,duplicate,model,entries=ci.stage_inputs(stage)
            self.assertEqual(len(normal),11)
            self.assertEqual(len(duplicate),2)
            self.assertEqual(len(entries),18)
            self.assertEqual(len(list(stage.rglob('*.uc'))),18)
            ci.inputs.check_sources(stage,entries)
            (stage/'model-controls/spread.uc').write_text('changed')
            with self.assertRaisesRegex(ValueError,'source bytes: model-controls/spread.uc'):
                ci.inputs.check_sources(stage,entries)

    def test_rejects_changed_duplicate_copy_before_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixtures=root/'fixtures'; shutil.copytree(ci.FIXTURES,fixtures)
            (fixtures/'duplicate/controls/positive-direct.uc').write_text('changed')
            with patch.object(ci,'FIXTURES',fixtures):
                stage=root/'stage';stage.mkdir()
                with self.assertRaisesRegex(ValueError,'duplicate positive source bytes'):
                    ci.stage_inputs(stage)

    def test_failed_command_retains_streams_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous=ci.LOG_DIR; ci.LOG_DIR=Path(tmp)
            try:
                failed=subprocess.CompletedProcess(['fake'],17,stdout='output',stderr='intended failure')
                with patch.object(ci.subprocess,'run',return_value=failed):
                    with self.assertRaisesRegex(RuntimeError,'command failed .*intended failure'):
                        ci.run('fake','argument')
                self.assertEqual((Path(tmp)/'000.stdout').read_text(),'output')
                self.assertEqual((Path(tmp)/'000.stderr').read_text(),'intended failure')
                self.assertEqual((Path(tmp)/'000.exit').read_text(),'17\n')
            finally:
                ci.LOG_DIR=previous

    def test_explicit_output_survives_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'retained'
            with patch.dict(ci.os.environ,{'STAT_MODEL_OUT':str(output)}), patch.object(ci,'execute',side_effect=ValueError('synthetic failure')):
                with self.assertRaisesRegex(ValueError,'synthetic failure'):
                    ci.main()
            self.assertTrue(output.is_dir())

    def test_mixed_diagnostics_require_exact_files_error_and_recovered_edges(self):
        stage=Path('/tmp/stat-test'); path='model-controls/malformed.uc'
        entries=[{'path':'controls/one.uc'}, {'path':path}]
        model={'malformed_preliminary_diagnostic':{'start':[3,12],'end_inclusive':[3,12]}}
        def row(kind,start,end,ident): return [path,kind,'',2,start,2,end,{'id':ident}]
        def edge(src,field,idx,dst): return [path,{'id':src},'',field,idx,{'id':dst}]
        loc={'uri':(stage/path).as_uri(),'startLine':3,'startColumn':12,'endLine':3,'endColumn':12}
        results={'success':table([[{'url':{'uri':(stage/'controls/one.uc').as_uri()}}]]),
                 'errors':table([[{'url':loc}]]),
                 'raw':table([row('CallExpression',1,16,1),row('Identifier',1,4,2),row('String',6,15,3)]),
                 'edges':table([edge(1,'call-function',-1,2),edge(1,'call-arguments',-1,4),edge(4,'argument',0,3)])}
        ci.verify_mixed_diagnostics(stage,results,entries,model)
        bad=copy.deepcopy(results);bad['success']['#select']['tuples'].append(copy.deepcopy(bad['success']['#select']['tuples'][0]))
        with self.assertRaisesRegex(ValueError,'successful-file identities'):
            ci.verify_mixed_diagnostics(stage,bad,entries,model)
        bad=copy.deepcopy(results);bad['errors']['#select']['tuples'][0][0]['url']['startColumn']=13
        with self.assertRaisesRegex(ValueError,'malformed diagnostic identity'):
            ci.verify_mixed_diagnostics(stage,bad,entries,model)
        bad=copy.deepcopy(results);bad['edges']['#select']['tuples'].pop()
        with self.assertRaisesRegex(ValueError,'malformed recovered argument'):
            ci.verify_mixed_diagnostics(stage,bad,entries,model)

if __name__=='__main__': unittest.main()
