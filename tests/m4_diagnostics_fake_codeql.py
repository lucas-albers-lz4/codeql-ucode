#!/usr/bin/env python3
"""Strict fake CLI used only to replay captured real semantic output."""
import gzip
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
root = Path(os.environ['M4_TEST_ROOT'])
data = Path(os.environ['M4_TEST_DATA'])
queries = {
    'extractor-smoke/SsaReads.ql': 'ssa.csv',
    'extractor-smoke/VariableWrites.ql': 'writes.csv',
    'extractor-smoke/LocalFlowStep.ql': 'flow.csv',
    'm4/SsaReachesSystem.ql': 'ssaSys.csv',
    'extractor-smoke/StoreRead.ql': 'store-read.csv.gz',
    'extractor-smoke/StoreReadSemantics.ql': 'store-read-semantics.csv',
    'extractor-smoke/StoreReadComposition.ql': 'store-read-composition.csv',
    'diagnostics/SuccessfullyExtractedFiles.ql': 'SuccessfullyExtractedFiles',
    'diagnostics/ExtractionErrors.ql': 'ExtractionErrors',
}
allowed_compile = set(queries) | {'m3/LocalTaint.ql', 'm4/RequestArgsExec.ql'}
if args[:2] == ['query', 'compile']:
    if args[2] not in [str(root / 'ql/src' / q) for q in allowed_compile]:
        sys.exit('fake codeql rejected compile query')
elif args[:2] == ['database', 'init']:
    Path(args[2]).mkdir(parents=True)
elif args[:2] in (['database', 'index-files'], ['database', 'finalize']):
    pass
elif args[:2] == ['query', 'run']:
    mapping = {str(root / 'ql/src' / k): v for k, v in queries.items()}
    if args[2] not in mapping:
        sys.exit('fake codeql rejected query: ' + args[2])
    output = next(x.split('=', 1)[1] for x in args if x.startswith('--output='))
    Path(output).write_text(mapping[args[2]])
elif args[:2] == ['bqrs', 'decode']:
    name = Path(args[-1]).read_text()
    if name in ('SuccessfullyExtractedFiles', 'ExtractionErrors'):
        if args[2:-1] != ['--format=json', '--entities=url,string']:
            sys.exit('fake codeql rejected diagnostic decode flags')
        value = json.loads(Path(os.environ['M4_TEST_DIAGNOSTICS']).read_text())[name]
        print(value if isinstance(value, str) else json.dumps(value))
    else:
        if args[2:-1] != ['--format=csv'] or name not in queries.values():
            sys.exit('fake codeql rejected semantic decode')
        path = data / name
        sys.stdout.write(gzip.open(path, 'rt').read() if path.suffix == '.gz' else path.read_text())
else:
    sys.exit('fake codeql rejected command: ' + repr(args))
