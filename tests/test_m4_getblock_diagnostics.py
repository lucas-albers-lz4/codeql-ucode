"""Synthetic CLI contract tests for the getBlockDevices diagnostic gate.

The receipts and semantic rows model wiring, not actual extraction.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('negative-command', 'negative-import', 'negative-member', 'negative-method', 'positive', 'real')
REL = tuple(f'modules/{name}/root/usr/share/rpcd/ucode/luci' for name in NAMES)

FAKE = r'''#!/usr/bin/env python3
import csv,json,os,sys
from pathlib import Path
r=Path(os.environ['T_ROOT']); db=r/'.codeql-database/m4-getblock-effect-table'
qlsrc=r/'ql/src'
a=sys.argv[1:]; registry=Path(os.environ['T_REGISTRY'])
with open(os.environ['T_LOG'],'a') as f: f.write(json.dumps(a)+'\n')
def die(s): sys.exit('adapter rejected: '+s)
if a[:2]==['database','init']:
    if len(a)!=6 or a[2]!=str(db) or a[3]!='--language=ucode' or a[4]!='--search-path='+str(r/'extractor-pack') or not a[5].startswith('--source-root='): die('init')
    src=Path(a[5].split('=',1)[1]); registry.write_text(str(src)); db.mkdir(parents=True)
elif a[:2]==['database','index-files']:
    src=Path(registry.read_text())
    if a[2:]!=['--language=ucode','--include=**/rpcd/ucode/luci','--working-dir='+str(src),str(db)]: die('index')
elif a[:2]==['database','finalize']:
    if a[2:]!=[str(db)]: die('finalize')
elif a[:2]==['query','run']:
    if len(a)!=6 or sorted(x.split('=',1)[0] for x in a[3:])!=['--database','--output','--search-path']: die('query options')
    allowed=[qlsrc/'diagnostics/SuccessfullyExtractedFiles.ql',qlsrc/'diagnostics/ExtractionErrors.ql',qlsrc/'m4/GetBlockDevicesEffectTable.ql']
    query=Path(a[2]); opts=dict(x.split('=',1) for x in a[3:])
    if query not in allowed or not query.is_file(): die('query operand')
    if opts['--database']!=str(db) or opts['--search-path']!=':'.join(str(r/p) for p in ('extractor-pack','ql/lib','ql/src')) or Path(opts['--output']).parent!=db: die('query paths')
    Path(opts['--output']).write_text(query.stem)
elif a[:2]==['bqrs','decode']:
    flags=a[2:-1]; name=Path(a[-1]).read_text(); fault=os.environ['T_FAULT']
    if name in ('SuccessfullyExtractedFiles','ExtractionErrors'):
        if flags not in (['--format=csv'],['--format=json','--entities=url,string']): die('diagnostic decode')
        src=Path(registry.read_text()); paths=[src/x for x in json.loads(os.environ['T_REL'])]
        index=int(os.environ['T_INDEX'])
        if fault=='omit': paths.pop(index)
        elif fault=='duplicate': paths[index]=paths[(index+1)%len(paths)]
        elif fault=='substitute': paths[index]=r/'ql/test/extractor-smoke/taint_neg'
        def receipt(p): return [{'label':str(p),'url':{'uri':p.as_uri(),'startLine':0,'startColumn':0,'endLine':0,'endColumn':0}},'']
        rows=list(map(receipt,paths)) if name=='SuccessfullyExtractedFiles' else ([[{'label':'synthetic error'},'error',2]] if fault=='error' else [])
        if flags==['--format=csv']:
            w=csv.writer(sys.stdout); w.writerow(['f'] if name=='SuccessfullyExtractedFiles' else ['error']); w.writerows([[str(p)] for p in paths] if name=='SuccessfullyExtractedFiles' else [['error'] for _ in rows])
        else:
            cols=[{'name':'f','kind':'Entity'},{'kind':'String'}] if name=='SuccessfullyExtractedFiles' else [{'name':'error','kind':'Entity'},{'kind':'String'},{'kind':'Integer'}]
            print(json.dumps({'#select':{'columns':cols,'tuples':rows}}))
    elif name=='GetBlockDevicesEffectTable':
        if flags!=['--format=csv']: die('semantic decode')
        w=csv.writer(sys.stdout); w.writerow(['observation_kind','method','sink_kind','command','source_path','start_line','start_column','end_line','end_column'])
        for p,sl,sc,el,ec in [('real',481,18,481,54),('positive',4,5,4,41)]:
            w.writerow(['callback_body_call','getBlockDevices','popen','/sbin/block info 2>/dev/null',f'modules/{p}/root/usr/share/rpcd/ucode/luci',sl,sc,el,ec])
    else: die('decode')
else: die('unknown')
'''

class GetBlockDevicesDiagnostics(unittest.TestCase):
    def run_smoke(self, fault='valid', mutant=None, index=0):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d); root=t/'checkout'
            shutil.copytree(ROOT/'scripts',root/'scripts'); shutil.copytree(ROOT/'ql',root/'ql')
            for q in ('diagnostics/SuccessfullyExtractedFiles.ql','diagnostics/ExtractionErrors.ql','m4/GetBlockDevicesEffectTable.ql'):
                self.assertTrue((root/'ql/src'/q).is_file(),q)
            self.assertTrue((root/'ql/test/extractor-smoke/taint_neg').is_file())
            if mutant in ('identity','errors'):
                p=root/'scripts/m4-smoke-diagnostics.py'; s=p.read_text()
                old='if errors:' if mutant=='errors' else 'if Counter(map(encode, success)) != Counter(map(encode, wanted)):'
                self.assertEqual(s.count(old),1); p.write_text(s.replace(old,old.replace('if ','if False and ',1)))
            if mutant in ('wiring','late'):
                p=root/'scripts/m4-getblock-effect-table-smoke.sh'; s=p.read_text(); start=s.index('check_m4_extraction '); end=s.index('\n\n',start)
                check=s[start:end]; s=s[:start]+':'+s[end:]
                if mutant=='late':
                    line='codeql query run "$ROOT/ql/src/m4/GetBlockDevicesEffectTable.ql" --database="$DB" --search-path="$QLPATH" --output="$DB/effects.bqrs"'
                    self.assertEqual(s.count(line),1); s=s.replace(line,line+'\n'+check)
                p.write_text(s)
            if mutant in ('bad-option','bad-flags','bad-query'):
                p=root/'scripts/m4-smoke-diagnostics.sh'; s=p.read_text()
                old,new={'bad-option':('--output="$DB/$diagnostic.bqrs"','--output="$DB/$diagnostic.bqrs" --fake-option'), 'bad-flags':('--entities=url,string','--entities=string'), 'bad-query':('ql/src/diagnostics/','ql/src/m4/')}[mutant]
                self.assertEqual(s.count(old),1); p.write_text(s.replace(old,new))
            extractor=root/'extractor-pack/tools/linux64/extractor'; extractor.parent.mkdir(parents=True); extractor.touch(mode=0o755)
            binary=t/'bin'; binary.mkdir(); cli=binary/'codeql'; cli.write_text(FAKE); cli.chmod(0o755)
            env=os.environ.copy(); env.update(PATH=str(binary)+os.pathsep+env['PATH'],T_ROOT=str(root),T_LOG=str(t/'commands'),T_REGISTRY=str(t/'src'),T_REL=json.dumps(REL),T_FAULT=fault,T_INDEX=str(index),CODEQL_UCODE_SMOKE_PACKS_READY=str(root),PYTHONOPTIMIZE=str(sys.flags.optimize),PYTHONDONTWRITEBYTECODE='1')
            res=subprocess.run(['bash',str(root/'scripts/m4-getblock-effect-table-smoke.sh')],cwd=root,env=env,text=True,capture_output=True)
            trace=[json.loads(x) for x in (t/'commands').read_text().splitlines()] if (t/'commands').exists() else []
            return res,trace
    def semantic(self,trace):
        return any(a[:2]==['query','run'] and a[2].endswith('/m4/GetBlockDevicesEffectTable.ql') for a in trace)
    def test_pristine(self):
        r,trace=self.run_smoke(); self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(self.semantic(trace))
    def test_identity_independent(self):
        for fault in ('omit','duplicate','substitute'):
            for index in range(len(REL)):
                with self.subTest(fault=fault,index=index):
                    r,trace=self.run_smoke(fault,index=index); self.assertNotEqual(r.returncode,0,r.stdout); self.assertIn('expected exact successful-file multiset',r.stderr); self.assertNotIn('expected zero extraction errors',r.stderr); self.assertFalse(self.semantic(trace),trace)
    def test_error_independent(self):
        r,trace=self.run_smoke('error'); self.assertNotEqual(r.returncode,0,r.stdout); self.assertIn('expected zero extraction errors',r.stderr); self.assertNotIn('expected exact successful-file multiset',r.stderr); self.assertFalse(self.semantic(trace),trace)
    def test_late_gate_ordering(self):
        r,trace=self.run_smoke('error','late'); self.assertNotEqual(r.returncode,0); self.assertIn('expected zero extraction errors',r.stderr); self.assertTrue(self.semantic(trace),trace)
    def test_adapter_rejects_bad_helper_commands(self):
        for mutant in ('bad-option','bad-flags','bad-query'):
            with self.subTest(mutant=mutant):
                r,trace=self.run_smoke(mutant=mutant); self.assertNotEqual(r.returncode,0); self.assertIn('adapter rejected',r.stderr); self.assertFalse(self.semantic(trace),trace)
    def test_guard_necessity(self):
        for mutant,fault in [('identity','omit'),('identity','duplicate'),('identity','substitute'),('errors','error'),('wiring','error')]:
            with self.subTest(mutant=mutant,fault=fault):
                r,trace=self.run_smoke(fault,mutant); self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(self.semantic(trace))

if __name__ == '__main__':
    unittest.main()
