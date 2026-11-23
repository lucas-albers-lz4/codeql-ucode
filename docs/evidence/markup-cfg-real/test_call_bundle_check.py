#!/usr/bin/env python3
"""Require optimized Python to reject absent, malformed and changed results."""
import pathlib
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 4:
    sys.exit('usage: test_call_bundle_check.py OUTPUT STAGE CONTROLS_ROOT')
evidence = pathlib.Path(__file__).resolve().parent
checker = evidence / 'check.py'
output, stage, controls = sys.argv[1:]
def run(directory, source_stage=stage):
    return subprocess.run([sys.executable, '-O', str(checker), str(directory), str(source_stage), controls, '--call-bundle'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode
with tempfile.TemporaryDirectory() as directory:
    copy = pathlib.Path(directory)
    if run(copy / 'missing') == 0:
        raise RuntimeError('missing output accepted under -O')
    for source in pathlib.Path(output).glob('*.csv'):
        shutil.copyfile(source, copy / source.name)
    if run(copy):
        raise RuntimeError('valid output rejected under -O')
    def mutate(name, change):
        path = copy / name
        original = path.read_text()
        path.write_text(change(original))
        if run(copy) == 0:
            raise RuntimeError(f'mutation accepted under -O: {name}')
        path.write_text(original)
    mutate('markup-measure-measurement-callable.csv', lambda s: s.replace('"covered"', '"unsupported"'))
    mutate('markup-measure-measurement.csv', lambda s: s.replace('"col0"', '"wrong"', 1))
    mutate('markup-measure-markup-creation-nodes-test.csv', lambda s: s.replace('"call-completion"', '"wrong"', 1))
    mutate('markup-measure-markup-creation-edges-test.csv', lambda s: s.replace('"entry"', '"wrong"', 1))
    stage_copy = copy / 'stage'
    shutil.copytree(stage, stage_copy)
    witness = stage_copy / 'usr/share/ucode/luci/uhttpd.uc'
    witness.write_bytes(witness.read_bytes().replace(b'request(env, uhttpd.recv, uhttpd.send)', b'request(ENV, uhttpd.recv, uhttpd.send)'))
    if run(copy, stage_copy) == 0:
        raise RuntimeError('source witness mutation accepted under -O')
print('Optimized-mode missing, result, header, node, edge and source mutations rejected')
