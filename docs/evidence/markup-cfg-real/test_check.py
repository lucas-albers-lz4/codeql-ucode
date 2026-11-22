#!/usr/bin/env python3
"""Exercise checker rejection using retained CSV with isolated mutations."""
import csv
import pathlib
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 3:
    sys.exit('usage: test_check.py STAGE CONTROLS_ROOT')
evidence = pathlib.Path(__file__).resolve().parent
checker = evidence / 'check.py'
with tempfile.TemporaryDirectory() as directory:
    copy = pathlib.Path(directory)
    for source in evidence.glob('*.csv'):
        shutil.copyfile(source, copy / source.name)
    def run():
        return subprocess.run([sys.executable, str(checker), str(copy), *sys.argv[1:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode
    if run(): raise RuntimeError('unmodified evidence rejected')
    def mutate(name, change):
        path = copy / name
        original = path.read_text()
        path.write_text(change(original))
        if run() == 0: raise RuntimeError(f'mutation accepted: {name}')
        path.write_text(original)
    mutate('markup-measure-controls2-ExtractionErrors.csv', lambda _: 'unrelated\n')
    mutate('markup-measure-controls2-SuccessfullyExtractedFiles.csv', lambda s: s.rstrip()[:-1])
    mutate('markup-measure-controls2-SuccessfullyExtractedFiles.csv', lambda s: s.replace(str(pathlib.Path(sys.argv[2]).resolve()), '/wrong/root'))
    mutate('markup-measure-controls2-SuccessfullyExtractedFiles.csv', lambda s: s.replace(',""', ',"unexpected"', 1))
    mutate('markup-measure-controls2-SuccessfullyExtractedFiles.csv', lambda s: s.replace('"f","col1"', '"f"'))
    mutate('markup-measure-controls2-ExtractionErrors.csv', lambda s: s + '"error","detail"\n')
    mutate('markup-measure-measurement.csv', lambda s: s.replace('"unsupported","covered",78', '"covered","covered",78'))
print('Seven isolated malformed schema, identity, message and result mutations rejected.')
