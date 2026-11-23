import os, subprocess, json, pathlib
p=pathlib.Path('/private/tmp/issue54-query-comparison'); main=pathlib.Path('/private/tmp/ucode-issue54-assessment'); old=pathlib.Path('/private/tmp/openwrt-typed-handoff-live-20261123'); cli='/Users/lalbers/gitroot/ucode/.tools/codeql-2.27.4/codeql/codeql'
env={'HOME':str(p/'runtime/home'),'TMPDIR':str(p/'runtime/tmp'),'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}
additional=':'.join(str(old/'packs/codeql'/a/b) for a,b in [('controlflow','1.0.12'),('dataflow','1.1.6'),('regex','1.0.12'),('ssa','1.0.12'),('threat-models','1.1.1'),('typetracking','1.0.12'),('util','1.0.12'),('yaml','1.0.61')])
commands=[]
for name in ['ShellInjection','RequestArgsExec']:
 q=[cli,'query','run',str(main/'ql/src/m4'/f'{name}.ql'),f'--database={p}/database',f'--search-path={old}/extractor-pack:{main}/ql/lib:{main}/ql/src',f'--additional-packs={additional}','--no-default-compilation-cache',f'--compilation-cache={p}/runtime/cache',f'--common-caches={p}/runtime/common',f'--output={p}/{name}.bqrs','--threads=1','--ram=2048']
 for label,cmd in [('query',q),('decode',[cli,'bqrs','decode','--format=csv',str(p/f'{name}.bqrs')]),('decode2',[cli,'bqrs','decode','--format=csv',str(p/f'{name}.bqrs')])]:
  x=subprocess.run(cmd,env=env,cwd=main,capture_output=True); (p/f'{name}.{label}.stdout').write_bytes(x.stdout); (p/f'{name}.{label}.stderr').write_bytes(x.stderr); commands.append({'argv':cmd,'exit':x.returncode}); (p/'commands.json').write_text(json.dumps({'environment':env,'commands':commands},indent=2)); print(name,label,x.returncode,flush=True)
  if x.returncode: raise SystemExit(x.returncode)
