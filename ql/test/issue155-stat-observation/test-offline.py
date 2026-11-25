#!/usr/bin/env python3
"""Unit checks for source-first comparison and guard mutation construction."""
import importlib.util
from pathlib import Path
import unittest
import tempfile
import json
import os

HERE = Path(__file__).resolve().parent

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

oracle = module('oracle', 'check-results.py')
runner = module('runner', 'run-smoke.py')

class Offline(unittest.TestCase):
    def test_mutations_remove_exact_guard_and_fail_if_missing(self):
        source = (runner.ROOT / 'ql/src/inventory/Issue155StatObservation.ql').read_text()
        mutants = runner.mutations(source)
        self.assertEqual(set(mutants), {'competing', 'request', 'unique'})
        self.assertNotIn('id.getValue() = "stat" and statCompetingBindingOrWrite(id)) and', mutants['competing'])
        self.assertNotIn('read.getVariable().getAstNode() = TIdentifier(formal)', mutants['request'])
        self.assertNotIn('strictcount(UCODE::ImportStatement other', mutants['unique'])
        with self.assertRaisesRegex(ValueError, 'mutation target changed'):
            runner.mutations(source.replace('strictcount(UCODE::ImportStatement other', 'strictcount(UCODE::ImportStatement missing'))

    def test_canonical_tree_hash_detects_files_modes_and_empty_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); file=root/'item'; file.write_bytes(b'a\x00b')
            initial=runner.tree_hash(root)
            file.write_bytes(b'a'); self.assertNotEqual(initial,runner.tree_hash(root))
            file.write_bytes(b'a\x00b'); self.assertEqual(initial,runner.tree_hash(root))
            file.chmod(0o600); different=runner.tree_hash(root)
            file.chmod(0o700); self.assertNotEqual(different,runner.tree_hash(root))
            (root/'empty').mkdir(); self.assertNotEqual(initial,runner.tree_hash(root))
            (root/'link').symlink_to(file)
            with self.assertRaisesRegex(ValueError,'symlink'):
                runner.tree_hash(root)

    def test_resolved_query_identity_and_json_validation(self):
        queries=[Path('/a/one.ql'),Path('/a/two.ql')]
        runner.check_query_resolution(json.dumps([str(x) for x in queries]),queries)
        with self.assertRaisesRegex(ValueError,'query identities'):
            runner.check_query_resolution(json.dumps(['/a/one.ql','/a/one.ql']),queries)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
            runner.strict_json('{"key":1,"key":2}')

    def test_effective_input_snapshot_detects_change(self):
        runner.verify_snapshot({'lib':'one','pack':'two'},{'lib':'one','pack':'two'})
        with self.assertRaisesRegex(ValueError,'effective inputs changed'):
            runner.verify_snapshot({'lib':'one','pack':'two'},{'lib':'changed','pack':'two'})

    def test_library_resolver_rejects_wrong_pack_identity(self):
        old_root, old_packages=runner.ROOT, runner.PACKAGES
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=root/'out'; runner.ROOT=root; runner.PACKAGES=('sample/1.0',)
            try:
                (out/'cache/common/packages/codeql/sample/1.0').mkdir(parents=True)
                q=root/'ql/src/test.ql'
                result={'libraryPath':[str(root/'ql/src'),str(root/'ql/lib'),str(out/'cache/common/packages/codeql/sample/1.0')],
                        'dbscheme':str(root/'ql/lib/ucode.dbscheme'), 'compilationCache':[str(out/'cache/compilation')],
                        'relativeName':'lucas-albers-lz4/ucode-queries/test.ql', 'qlPackName':'lucas-albers-lz4/ucode-queries'}
                self.assertEqual(set(runner.check_library_resolution(json.dumps(result),q,out)),{'sample/1.0'})
                result['libraryPath'][-1]=str(root/'other')
                with self.assertRaisesRegex(ValueError,'library identities'):
                    runner.check_library_resolution(json.dumps(result),q,out)
            finally:
                runner.ROOT=old_root; runner.PACKAGES=old_packages

    def test_producer_head_uses_explicit_pin(self):
        baseline='a'*40; feature='b'*40
        runner.verify_producer_head(baseline,baseline)
        runner.verify_producer_head(feature,feature)
        with self.assertRaisesRegex(ValueError,'unexpected producer HEAD'):
            runner.verify_producer_head(baseline,feature)
        with self.assertRaisesRegex(ValueError,'producer head'):
            runner.verify_producer_head('not-a-commit',feature)

    def test_generated_query_guard_rejects_changes_and_unexpected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); query=root/'test.ql'; query.write_text('query body')
            import hashlib
            expected={'test.ql':hashlib.sha256(query.read_bytes()).hexdigest()}
            runner.verify_generated(root,expected)
            query.write_text('changed')
            with self.assertRaisesRegex(ValueError,'identities or bytes changed'):
                runner.verify_generated(root,expected)
            query.write_text('query body'); (root/'unexpected.ql').write_text('extra')
            with self.assertRaisesRegex(ValueError,'identities or bytes changed'):
                runner.verify_generated(root,expected)
            (root/'unexpected.ql').unlink(); (root/'link.ql').symlink_to(query)
            with self.assertRaisesRegex(ValueError,'unexpected generated query entry'):
                runner.verify_generated(root,expected)

    def test_model_guard_mutations_fail_closed(self):
        source = (runner.ROOT / 'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text()
        variants = runner.model_mutations(source)
        self.assertEqual(set(variants), {'declaration','write','module','alias','optional','unique','diagnostic'})
        self.assertNotIn('exists(UCODE::VariableDeclarator d | d.getName() = id)', variants['declaration'])
        self.assertNotIn('exists(UCODE::AssignmentExpression a | a.getLeft() = id)', variants['write'])
        self.assertNotIn('    not exists(spec.getAlias()) and\n', variants['alias'])
        with self.assertRaisesRegex(ValueError, 'model mutation target changed'):
            runner.model_mutations(source.replace('not exists(raw.getOptionalChain())', 'true'))

    def test_raw_identity_requires_kind_position_and_uniqueness(self):
        anchor = {'start': [2, 3], 'end_exclusive': [2, 6]}
        row = ['file', 'Identifier', 'abc', 2, 3, 2, 5, {'id': 8}]
        self.assertEqual(oracle.node([row], 'file', 'Identifier', anchor), 8)
        with self.assertRaisesRegex(ValueError, 'ambiguous or missing'):
            oracle.node([row, row], 'file', 'Identifier', anchor)
        with self.assertRaisesRegex(ValueError, 'ambiguous or missing'):
            oracle.node([row], 'file', 'CallExpression', anchor)

    def test_malformed_requires_recovered_call_diagnostic_and_mutation(self):
        def table(rows): return {'#select': {'columns': [], 'tuples': rows}}
        path = 'model-controls/malformed.uc'; stage = Path('/tmp/issue155')
        def row(kind, start, end, ident): return [path,kind,'',2,start,2,end,{'id':ident}]
        raw = table([row('CallExpression',1,16,1),row('Identifier',1,4,2),row('String',6,15,3)])
        def edge(src,field,idx,target): return [path,{'id':src},'',field,idx,{'id':target}]
        edges = table([edge(1,'call-function',-1,2),edge(1,'call-arguments',-1,4),edge(4,'argument',0,3)])
        loc={'uri':(stage / path).as_uri(),'startLine':3,'startColumn':12,'endLine':3,'endColumn':12}
        result={'raw':raw,'edges':edges,'success':table([]),'errors':table([[{'url':loc}]]),
                'baseline':table([]),'model':table([]),'member':table([]),
                'model_diagnostic':table([[path,{'id':1},{'id':2},{'id':3}]])}
        manifest={'malformed_preliminary_diagnostic':{'start':[3,12],'end_inclusive':[3,12]}}
        oracle.verify_malformed(result,stage,{'path':path},manifest)
        result['model_diagnostic']=table([])
        with self.assertRaisesRegex(ValueError,'diagnostic mutation'):
            oracle.verify_malformed(result,stage,{'path':path},manifest)
        result['model_diagnostic']=table([[path,{'id':1},{'id':2},{'id':3}]])
        result['errors']=table([])
        with self.assertRaisesRegex(ValueError,'diagnostic count'):
            oracle.verify_malformed(result,stage,{'path':path},manifest)

    def test_diagnostics_reject_duplicate_or_wrong_file(self):
        def table(rows): return {'#select': {'columns': [], 'tuples': rows}}
        stage = Path('/tmp/issue155'); entries = [{'path': 'controls/a.uc'}]
        item = [{'url': {'uri': (stage / 'controls/a.uc').as_uri()}}]
        runner.check_diagnostics(table([item]), table([]), stage, entries)
        with self.assertRaisesRegex(ValueError, 'success identities'):
            runner.check_diagnostics(table([item, item]), table([]), stage, entries)
        with self.assertRaisesRegex(ValueError, 'extraction errors'):
            runner.check_diagnostics(table([item]), table([['error']]), stage, entries)

if __name__ == '__main__': unittest.main()
