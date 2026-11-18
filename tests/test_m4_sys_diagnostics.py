"""Synthetic command/receipt tests for the M4 sys smoke's extraction gate."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ('usr/share/rpcd/ucode/luci', 'usr/share/ucode/luci/sys.uc')
FAKE = r'''#!INTERPRETER
import csv,json,os,sys
from pathlib import Path
r=Path(os.environ['T_ROOT']); db=r/'.codeql-database/m4-sys'; src=r/'ql/test/extractor-smoke'; a=sys.argv[1:]
with open(os.environ['T_LOG'],'a') as f: f.write(json.dumps(a)+'\n')
def die(s): sys.exit('adapter rejected: '+s)
if a[:2]==['database','init']:
    if a[2:]!=[str(db),'--language=ucode','--search-path='+str(r/'extractor-pack'),'--source-root='+str(src)]: die('init')
    db.mkdir(parents=True)
elif a[:2]==['database','index-files']:
    if a[2:]!=['--language=ucode','--include=**/rpcd/ucode/luci','--include=**/sys.uc','--working-dir='+str(src),str(db)]: die('index')
elif a[:2]==['database','finalize']:
    if a[2:]!=[str(db)]: die('finalize')
elif a[:2]==['query','run']:
    if len(a)!=6 or sorted(x.split('=',1)[0] for x in a[3:])!=['--database','--output','--search-path']: die('query options')
    allowed=[r/'ql/src'/x for x in ('diagnostics/SuccessfullyExtractedFiles.ql','diagnostics/ExtractionErrors.ql','m4/InitActionSystem.ql','m4/SetInitActionActionSwitch.ql','m4/InitActionCallerSinkPair.ql')]
    query=Path(a[2]); opts=dict(x.split('=',1) for x in a[3:])
    if query not in allowed or not query.is_file(): die('query operand')
    if Path(opts['--database']).resolve()!=db.resolve() or opts['--search-path']!=':'.join(str(r/p) for p in ('extractor-pack','ql/lib','ql/src')) or Path(opts['--output']).parent.resolve()!=db.resolve(): die('query paths')
    Path(opts['--output']).write_text(query.stem)
elif a[:2]==['bqrs','decode']:
    flags=a[2:-1]; name=Path(a[-1]).read_text(); fault=os.environ['T_FAULT']; i=int(os.environ['T_INDEX'])
    if name in ('SuccessfullyExtractedFiles','ExtractionErrors'):
        if flags not in (['--format=csv'],['--format=json','--entities=url,string']): die('diagnostic flags')
        paths=[src/x for x in json.loads(os.environ['T_FILES'])]
        if fault=='omit': paths.pop(i)
        elif fault=='duplicate': paths[i]=paths[(i+1)%len(paths)]
        elif fault=='substitute': paths[i]=r/'alternate'/str(i)/paths[i].name
        def receipt(p): return [{'label':str(p),'url':{'uri':p.as_uri(),'startLine':0,'startColumn':0,'endLine':0,'endColumn':0}},'']
        rows=list(map(receipt,paths)) if name=='SuccessfullyExtractedFiles' else ([[{'label':'synthetic error'},'error',2]] if fault=='error' else [])
        if flags==['--format=csv']:
            w=csv.writer(sys.stdout); w.writerow(['f'] if name=='SuccessfullyExtractedFiles' else ['error']); w.writerows([[str(p)] for p in paths] if name=='SuccessfullyExtractedFiles' else [['error'] for _ in rows])
        else:
            cols=[{'name':'f','kind':'Entity'},{'kind':'String'}] if name=='SuccessfullyExtractedFiles' else [{'name':'error','kind':'Entity'},{'kind':'String'},{'kind':'Integer'}]
            print(json.dumps({'#select':{'columns':cols,'tuples':rows}}))
    elif name in ('InitActionSystem','SetInitActionActionSwitch','InitActionCallerSinkPair'):
        if flags!=['--format=csv']: die('semantic flags')
        w=csv.writer(sys.stdout); w.writerow(['entity','message'])
        if name=='InitActionSystem': w.writerow(['node','builtin system not a modeled sanitizer'])
        elif name=='SetInitActionActionSwitch':
            for token in ('enable','disable','start','stop','restart','reload'): w.writerow(['node',"action token '%s' not a sanitizer of name"%token])
        else:
            for _ in range(2): w.writerow(['node','not interprocedural dataflow'])
    else: die('decode')
else: die('unknown')
'''

class M4SysDiagnostics(unittest.TestCase):
    def run_smoke(self, fault='valid', index=0, mutant=None):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d); root=(t/'checkout').resolve(); shutil.copytree(ROOT/'scripts',root/'scripts'); shutil.copytree(ROOT/'ql',root/'ql')
            for q in ('diagnostics/SuccessfullyExtractedFiles.ql','diagnostics/ExtractionErrors.ql','m4/InitActionSystem.ql','m4/SetInitActionActionSwitch.ql','m4/InitActionCallerSinkPair.ql'):
                self.assertTrue((root/'ql/src'/q).is_file(),q)
            for i, rel in enumerate(FILES):
                source = root/'ql/test/extractor-smoke'/rel
                alternate = root/'alternate'/str(i)/source.name
                alternate.parent.mkdir(parents=True)
                shutil.copyfile(source, alternate)
                self.assertTrue(alternate.is_file())
                self.assertNotEqual(alternate, source)
            if mutant in ('errors','identity'):
                p=root/'scripts/m4-smoke-diagnostics.py'; s=p.read_text(); old='if errors:' if mutant=='errors' else 'if Counter(map(encode, success)) != Counter(map(encode, wanted)):'; self.assertEqual(s.count(old),1); p.write_text(s.replace(old,old.replace('if ','if False and ',1)))
            if mutant in ('wiring','late'):
                p=root/'scripts/m4-sys-smoke.sh'; s=p.read_text(); start=s.index('check_m4_extraction '); end=s.index('\n\n',start); check=s[start:end]; s=s[:start]+':'+s[end:]
                if mutant=='late':
                    line='runq "$ROOT/ql/src/m4/InitActionSystem.ql" "$DB/init.bqrs"'; self.assertEqual(s.count(line),1); s=s.replace(line,line+'\n'+check)
                p.write_text(s)
            ex=root/'extractor-pack/tools/linux64/extractor'; ex.parent.mkdir(parents=True); ex.touch(mode=0o755)
            binary=t/'bin'; binary.mkdir(); cli=binary/'codeql'; cli.write_text(FAKE.replace('INTERPRETER',sys.executable,1)); cli.chmod(0o755)
            env=os.environ.copy(); env.update(PATH=str(binary)+os.pathsep+env['PATH'],T_ROOT=str(root),T_LOG=str(t/'log'),T_FAULT=fault,T_INDEX=str(index),T_FILES=json.dumps(FILES),CODEQL_UCODE_SMOKE_PACKS_READY=str(root),PYTHONOPTIMIZE=str(sys.flags.optimize),PYTHONDONTWRITEBYTECODE='1')
            res=subprocess.run(['bash',str(root/'scripts/m4-sys-smoke.sh')],cwd=root,env=env,text=True,capture_output=True)
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
