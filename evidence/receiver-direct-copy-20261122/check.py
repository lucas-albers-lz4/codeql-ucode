import collections, copy, importlib.util, json
from pathlib import Path
from urllib.parse import unquote, urlsplit
W=Path(__file__).resolve().parent; S=Path('/STAGED_SOURCE'); R=W.parent.parent
def raw(name): return json.loads((W/(name+'.json')).read_text())['#select']['tuples']
def ent(e):
 u=e['url']; uri=urlsplit(u['uri'])
 if uri.scheme != 'file' or uri.netloc or uri.query or uri.fragment: raise ValueError('invalid entity URI')
 p=Path(unquote(uri.path,errors='strict')).relative_to(S).as_posix()
 return (p,tuple(u[x] for x in ('startLine','startColumn','endLine','endColumn')))
def canonical(row): return tuple(ent(e) for e in row[:4])+tuple(row[4:])
def serialized(row): return json.dumps(row,sort_keys=True,separators=(',',':'))
spec=importlib.util.spec_from_file_location('smoke',R/'scripts/m4-receiver-direct-copy-smoke.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
expected=collections.Counter()
for source,init,copy_decl,receiver,call,_ in m.EXPECTED:
 name='controls/direct-copy-controls.uc'; method='close' if call[0]==21 else 'read'; expected[((name,call),(name,receiver),(name,source),(name,init),method,'popen')]+=1
def compare(base, union):
 # Validate URI encoding for every row, and preserve all original raw JSON entities.
 a=collections.Counter(map(canonical,base)); b=collections.Counter(map(canonical,union))
 raw_a=collections.Counter(map(serialized,base)); raw_b=collections.Counter(map(serialized,union))
 if raw_a-raw_b: raise ValueError('original raw row removed or altered')
 if b-a != expected: raise ValueError('unexpected projected delta')
 counts=lambda x: collections.Counter(row[0][0] for row,n in x.items() for _ in range(n))
 if counts(a)!={'controls/direct-copy-controls.uc':1,'usr/share/rpcd/ucode/luci':14,'usr/share/ucode/luci/sys.uc':3}: raise ValueError('wrong baseline counts')
 if counts(b)!={'controls/direct-copy-controls.uc':6,'usr/share/rpcd/ucode/luci':14,'usr/share/ucode/luci/sys.uc':3}: raise ValueError('wrong union counts')
 return b-a
# Check staged inputs, route receipt, successful-file identities, and extraction errors.
import hashlib
pins={
 'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci':'6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e',
 'ql/test/extractor-smoke/usr/share/ucode/luci/sys.uc':'0380fba5d843a8950bab0ef70982cb40ab8f475e8d267c873e4199a736b55656',
 'ql/test/receiver-provenance/direct-copy-controls.uc':'a08377a54e42b09af7ff78557100bbd2031e7dc79ccfaf90134d5701554ebaf1',
}
for path,digest in pins.items():
 if hashlib.sha256((R/path).read_bytes()).hexdigest()!=digest: raise ValueError('input hash mismatch: '+path)
selected={'controls/direct-copy-controls.uc','usr/share/rpcd/ucode/luci','usr/share/ucode/luci/sys.uc'}
files=raw('files'); errors=raw('errors')
if len(files)!=3 or {ent(row[0])[0] for row in files}!=selected or errors: raise ValueError('invalid extraction diagnostics')
route=json.loads((W/'routing.json').read_text())
if (route['input_count'],route['plain_count'],route['excluded_count'],route['markup_count'],route['uncertain_count'],route['markup_inconclusive_count'],route['duplicate_input_count'])!=(3,3,0,0,0,0,0): raise ValueError('routing counts')
if {d['installed_path'] for d in route['decisions']}!=selected or any(d['status']!='plain_route_selected' for d in route['decisions']): raise ValueError('routing identities')
controls=collections.Counter((ent(row[0])[1],row[1]) for row in raw('calls') if ent(row[0])[0]=='controls/direct-copy-controls.uc')
if controls!=collections.Counter(m.EXPECTED_CALLS): raise ValueError('control call inventory')
if len(raw('request-args'))!=7: raise ValueError('request-args baseline count')
base=raw('FsReceiverProvenance'); union=raw('ReceiverMeasureUnion'); delta=compare(base,union)
# Controls independently exercise exact unchanged raw rows, URI validation, and added spans.
for kind in ('label','scheme','added_span'):
 altered=copy.deepcopy(union)
 if kind=='label':
  target=next(r for r in altered if serialized(r) in set(map(serialized,base))); target[0]['label']+=' altered'
 elif kind=='scheme': altered[0][0]['url']['uri']=altered[0][0]['url']['uri'].replace('file:', 'https:',1)
 else:
  target=next(r for r in altered if serialized(r) not in set(map(serialized,base))); target[0]['url']['startColumn']+=1
 try: compare(base,altered)
 except (ValueError,KeyError): pass
 else: raise RuntimeError('mutation survived: '+kind)
print('PASS baseline 18, union 23; all 18 baseline raw JSON rows retained; real 17 unchanged; synthetic 1 to 6; five projected deltas match')
print('PASS mutation controls: original entity label, URI scheme, added call coordinate')
for row,n in sorted(delta.items()): print(n,row)
