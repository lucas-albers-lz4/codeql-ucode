"""Synthetic diagnostic acceptance tests for the init-action guard smoke."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ('usr/share/rpcd/ucode/luci', 'usr/share/ucode/luci/sys.uc',
         'usr/share/ucode/other/sys.uc', 'usr/share/ucode/private/sys.uc')
FAKE = r'''#!/usr/bin/env python3
import csv,json,os,sys
from pathlib import Path
r=Path(os.environ['T_ROOT']); db=r/'.codeql-database/m4-init-action-guard'; a=sys.argv[1:]; reg=Path(os.environ['T_REG'])
with open(os.environ['T_LOG'],'a') as f: f.write(json.dumps(a)+'\n')
def die(s): sys.exit('adapter rejected: '+s)
if a[:2]==['database','init']:
    if len(a)!=6 or a[2]!=str(db) or a[3]!='--language=ucode' or a[4]!='--search-path='+str(r/'extractor-pack') or not a[5].startswith('--source-root='): die('init')
    src=Path(a[5].split('=',1)[1]); reg.write_text(str(src)); db.mkdir(parents=True)
elif a[:2]==['database','index-files']:
    src=Path(reg.read_text())
    if a[2:]!=['--language=ucode','--include=**/rpcd/ucode/luci','--include=**/sys.uc','--working-dir='+str(src),str(db)]: die('index')
elif a[:2]==['database','finalize']:
    if a[2:]!=[str(db)]: die('finalize')
elif a[:2]==['query','run']:
    if len(a)!=6 or sorted(x.split('=',1)[0] for x in a[3:])!=['--database','--output','--search-path']: die('query options')
    allowed=[r/'ql/src'/x for x in ('diagnostics/SuccessfullyExtractedFiles.ql','diagnostics/ExtractionErrors.ql','m4/InitActionSystem.ql','m4/InitActionCallerSinkPair.ql')]
    query=Path(a[2]); opts=dict(x.split('=',1) for x in a[3:])
    if query not in allowed or not query.is_file(): die('query operand')
    if opts['--database']!=str(db) or opts['--search-path']!=':'.join(str(r/p) for p in ('extractor-pack','ql/lib','ql/src')) or Path(opts['--output']).parent!=db: die('query paths')
    Path(opts['--output']).write_text(query.stem)
elif a[:2]==['bqrs','decode']:
    flags=a[2:-1]; name=Path(a[-1]).read_text(); fault=os.environ['T_FAULT']
    if name in ('SuccessfullyExtractedFiles','ExtractionErrors'):
        if flags not in (['--format=csv'],['--format=json','--entities=url,string']): die('diagnostic flags')
        src=Path(reg.read_text()); paths=[src/x for x in json.loads(os.environ['T_FILES'])]; i=int(os.environ['T_INDEX'])
        if fault=='omit': paths.pop(i)
        elif fault=='duplicate': paths[i]=paths[(i+1)%len(paths)]
        elif fault=='substitute': paths[i]=r/'ql/test/extractor-smoke/taint_neg'
        def receipt(p): return [{'label':str(p),'url':{'uri':p.as_uri(),'startLine':0,'startColumn':0,'endLine':0,'endColumn':0}},'']
        rows=list(map(receipt,paths)) if name=='SuccessfullyExtractedFiles' else ([[{'label':'synthetic error'},'error',2]] if fault=='error' else [])
        if flags==['--format=csv']:
            w=csv.writer(sys.stdout); w.writerow(['f'] if name=='SuccessfullyExtractedFiles' else ['error']); w.writerows([[str(p)] for p in paths] if name=='SuccessfullyExtractedFiles' else [['error'] for _ in rows])
        else:
            cols=[{'name':'f','kind':'Entity'},{'kind':'String'}] if name=='SuccessfullyExtractedFiles' else [{'name':'error','kind':'Entity'},{'kind':'String'},{'kind':'Integer'}]
            print(json.dumps({'#select':{'columns':cols,'tuples':rows}}))
    elif name in ('InitActionSystem','InitActionCallerSinkPair'):
        if flags!=['--format=csv']: die('semantic flags')
        print('entity,message')
    else: die('decode')
else: die('unknown')
'''

class InitActionDiagnostics(unittest.TestCase):
    def run_smoke(self,fault='valid',index=0,mutant=None):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d); r=t/'checkout'; shutil.copytree(ROOT/'scripts',r/'scripts'); shutil.copytree(ROOT/'ql',r/'ql')
            for q in ('diagnostics/SuccessfullyExtractedFiles.ql','diagnostics/ExtractionErrors.ql','m4/InitActionSystem.ql','m4/InitActionCallerSinkPair.ql'):
                self.assertTrue((r/'ql/src'/q).is_file(),q)
            self.assertTrue((r/'ql/test/extractor-smoke/taint_neg').is_file())
            if mutant in ('errors','identity'):
                p=r/'scripts/m4-smoke-diagnostics.py'; s=p.read_text(); old='if errors:' if mutant=='errors' else 'if Counter(map(encode, success)) != Counter(map(encode, wanted)):'; self.assertEqual(s.count(old),1); p.write_text(s.replace(old,old.replace('if ','if False and ',1)))
            if mutant in ('wiring','late'):
                p=r/'scripts/m4-init-action-guard-smoke.sh'; s=p.read_text(); start=s.index('check_m4_extraction '); end=s.index('\n\n',start); check=s[start:end]; s=s[:start]+':'+s[end:]
                if mutant=='late':
                    line='\tcodeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"'; self.assertEqual(s.count(line),1); s=s.replace(line,line+'\n'+check)
                p.write_text(s)
            ex=r/'extractor-pack/tools/linux64/extractor'; ex.parent.mkdir(parents=True); ex.touch(mode=0o755)
            binary=t/'bin'; binary.mkdir(); cli=binary/'codeql'; cli.write_text(FAKE); cli.chmod(0o755)
            env=os.environ.copy(); env.update(PATH=str(binary)+os.pathsep+env['PATH'],T_ROOT=str(r),T_REG=str(t/'reg'),T_LOG=str(t/'log'),T_FAULT=fault,T_INDEX=str(index),T_FILES=json.dumps(FILES),CODEQL_UCODE_SMOKE_PACKS_READY=str(r),PYTHONOPTIMIZE=str(sys.flags.optimize),PYTHONDONTWRITEBYTECODE='1')
            res=subprocess.run(['bash',str(r/'scripts/m4-init-action-guard-smoke.sh')],cwd=r,env=env,text=True,capture_output=True)
            trace=[json.loads(x) for x in (t/'log').read_text().splitlines()] if (t/'log').exists() else []
            return res,trace
    def semantic(self,trace):
        return any(a[:2]==['query','run'] and '/m4/' in a[2] for a in trace)
    def test_pristine(self):
        r,t=self.run_smoke(); self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(self.semantic(t))
    def test_identity_independent(self):
        for fault in ('omit','duplicate','substitute'):
            for i in range(len(FILES)):
                with self.subTest(fault=fault,index=i):
                    r,t=self.run_smoke(fault,i); self.assertNotEqual(r.returncode,0,r.stdout); self.assertIn('expected exact successful-file multiset',r.stderr); self.assertNotIn('expected zero extraction errors',r.stderr); self.assertFalse(self.semantic(t),t)
    def test_error_independent(self):
        r,t=self.run_smoke('error'); self.assertNotEqual(r.returncode,0); self.assertIn('expected zero extraction errors',r.stderr); self.assertNotIn('expected exact successful-file multiset',r.stderr); self.assertFalse(self.semantic(t),t)
    def test_late_gate_order(self):
        r,t=self.run_smoke('error',mutant='late'); self.assertNotEqual(r.returncode,0); self.assertIn('expected zero extraction errors',r.stderr); self.assertTrue(self.semantic(t),t)
    def test_guard_necessity(self):
        for mutant,fault in [('identity','omit'),('identity','duplicate'),('identity','substitute'),('errors','error'),('wiring','error')]:
            with self.subTest(mutant=mutant,fault=fault):
                r,t=self.run_smoke(fault,mutant=mutant); self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(self.semantic(t),t)

if __name__ == '__main__':
    unittest.main()
