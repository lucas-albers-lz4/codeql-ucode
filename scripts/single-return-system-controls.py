#!/usr/bin/env python3
"""Run real QL mutations against the already accepted isolated database."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORK, DB = map(Path, sys.argv[1:3])
SPEC = importlib.util.spec_from_file_location('shape_oracle', ROOT / 'scripts/single-return-system-oracle.py')
oracle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oracle)
BODY = '''    not exists(UCODE::AstNode other |
      other = fn.getBody().getChild(_) and other != ret
    ) and
'''
LITERAL = '''    not exists(UCODE::AstNode child |
      child = literal.getChild(_) and not child instanceof UCODE::StringFragment
    )'''
source = (ROOT / 'ql/src/m4/SingleReturnFixedSystemSourceShape.ql').read_text()
COLUMN = 'c.getLocation().getStartColumn() as start_column'
if source.count(BODY) != 1 or source.count(LITERAL) != 1 or source.count(COLUMN) != 1:
    raise SystemExit('source-shape mutation seams changed')
pack = WORK / 'mutation-pack'
(pack / 'ql').mkdir(parents=True)
shutil.copyfile(ROOT / '.codeqlmanifest.json', pack / '.codeqlmanifest.json')
shutil.copytree(ROOT / 'ql/src', pack / 'ql/src')
shutil.copytree(ROOT / 'ql/lib', pack / 'ql/lib')
extra_body = [[oracle.PREFIX.format(case), 4, 22, 4, 40, '/bin/true']
              for case in ('guard-no-call', 'member-guard', 'unknown-helper')]
extra_literal = [[oracle.PREFIX.format('escaped-literal'), 3, 22, 3, 43, '/bin/tre']]
wrong_spans = [[r[0], r[1], r[2] + 1, *r[3:]] for r in oracle.EXPECTED]
variants = [('body-veto', source.replace(BODY, ''), oracle.EXPECTED + extra_body),
            ('literal-veto', source.replace(LITERAL, 'literal instanceof UCODE::String'), oracle.EXPECTED + extra_literal),
            ('wrong-start-column', source.replace(COLUMN, 'c.getLocation().getStartColumn() + 1 as start_column'), wrong_spans)]
for name, mutant, expected in variants:
    query = pack / 'ql/src/m4' / ('SingleReturnMutation-' + name + '.ql')
    query.write_text(mutant)
    result = WORK / ('mutation-' + name + '.bqrs')
    cmd = ['codeql', 'query', 'run', str(query), f'--database={DB}',
           f'--search-path={ROOT / "extractor-pack"}:{pack / "ql/lib"}:{pack / "ql/src"}',
           f'--additional-packs={pack / "ql/lib"}', '--threads=1', '--ram=2048',
           '--no-default-compilation-cache', f'--compilation-cache={WORK / ("mutation-cache-" + name)}',
           f'--output={result}']
    subprocess.run(cmd, check=True)
    decoded = subprocess.check_output(['codeql', 'bqrs', 'decode', '--format=json', '--entities=url,string', str(result)])
    json_path = WORK / ('mutation-' + name + '.json')
    json_path.write_bytes(decoded)
    rows = json.loads(decoded)['#select']['tuples']
    key = lambda row: json.dumps(row, separators=(',', ':'))
    if Counter(map(key, rows)) != Counter(map(key, expected)):
        raise SystemExit(f'{name}: mutant output differs from its complete predicted row multiset')
    checked = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/single-return-system-oracle.py'), str(json_path)], capture_output=True, text=True)
    if checked.returncode != 1 or 'source-shape multiset mismatch' not in checked.stderr:
        raise SystemExit(f'{name}: unchanged oracle did not reject mutant rows: {checked.stderr}')
    print(f'PASS {name}: exact {len(rows)} mutant rows rejected by unchanged oracle', flush=True)
