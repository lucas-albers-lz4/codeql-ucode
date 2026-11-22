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
def document(name): return json.loads((W/(name+'.json')).read_text())
files_doc=document('files'); errors_doc=document('errors'); route=document('routing'); observed_doc=document('observed')
def check_evidence(files_doc,errors_doc,route,observed_doc):
 def table(doc,columns):
  if set(doc)!={'#select'} or set(doc['#select'])!={'columns','tuples'} or doc['#select']['columns']!=columns or not isinstance(doc['#select']['tuples'],list): raise ValueError('diagnostic or observed schema')
  return doc['#select']['tuples']
 files=table(files_doc,[{'name':'f','kind':'Entity'},{'kind':'String'}])
 errors=table(errors_doc,[{'name':'error','kind':'Entity'},{'kind':'String'},{'kind':'Integer'}])
 expected_files=[]
 for name in sorted(selected):
  path='/STAGED_SOURCE/'+name
  expected_files.append([{'label':path,'url':{'uri':'file://'+path,'startLine':0,'startColumn':0,'endLine':0,'endColumn':0}},''])
 if collections.Counter(map(serialized,files))!=collections.Counter(map(serialized,expected_files)) or errors: raise ValueError('invalid diagnostics')
 expected_route={'input_count':3,'plain_count':3,'markup_count':0,'markup_inconclusive_count':0,'uncertain_count':0,'excluded_count':0,'duplicate_input_count':0}
 if set(route)!=set(expected_route)|{'decisions'} or any(type(route[k]) is not int or route[k]!=v for k,v in expected_route.items()): raise ValueError('routing counts or schema')
 decisions=[]
 for name in sorted(selected):
  reason='rpcd_raw_mode_full_path' if name=='usr/share/rpcd/ucode/luci' else 'ucode_extension'
  decisions.append({'path':'/STAGED_SOURCE/'+name,'installed_path':name,'classification':'plain','reason':reason,'status':'plain_route_selected'})
 if collections.Counter(map(serialized,route['decisions']))!=collections.Counter(map(serialized,decisions)): raise ValueError('routing decisions')
 columns=[{'name':n,'kind':k} for n,k in [('sourceDecl','Entity'),('initializer','Entity'),('copyDecl','Entity'),('receiver','Entity'),('call','Entity'),('relation','String')]]
 observations=table(observed_doc,columns)
 expected_observed=collections.Counter(tuple(coords for coords in row[:5])+(row[5],) for row in m.EXPECTED)
 actual_observed=collections.Counter()
 for row in observations:
  if len(row)!=6: raise ValueError('standalone row length')
  entities=[ent(e) for e in row[:5]]
  if any(name!='controls/direct-copy-controls.uc' for name,_ in entities): raise ValueError('unexpected standalone file')
  actual_observed[tuple(coords for _,coords in entities)+(row[5],)]+=1
 if actual_observed!=expected_observed: raise ValueError('standalone witness mismatch')
check_evidence(files_doc,errors_doc,route,observed_doc)
for mutation in ('route_path','route_duplicate','success_message','file_coordinate','error_schema','empty_witness'):
 f,e,r,o=map(copy.deepcopy,(files_doc,errors_doc,route,observed_doc))
 if mutation=='route_path': r['decisions'][0]['path']='/STAGED_SOURCE/wrong.uc'
 elif mutation=='route_duplicate': r['decisions'].append(copy.deepcopy(r['decisions'][0]))
 elif mutation=='success_message': f['#select']['tuples'][0][1]='changed'
 elif mutation=='file_coordinate': f['#select']['tuples'][0][0]['url']['startLine']=1
 elif mutation=='error_schema': e['#select']['columns']=[]
 else: o['#select']['tuples']=[]
 try: check_evidence(f,e,r,o)
 except (ValueError,KeyError): pass
 else: raise RuntimeError('evidence mutation survived: '+mutation)
print('PASS evidence mutations: route path, duplicate decision, success message, file coordinate, error schema, empty standalone witnesses')
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
