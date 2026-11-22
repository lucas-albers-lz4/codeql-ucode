"""Compare fresh 12-file outputs with the retained base and exact real graph."""
import csv
from collections import Counter
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parents[1]
base = root / 'docs/evidence/markup-cfg-real'
out = Path(sys.argv[1])

def rows(directory, name):
    with (directory / name).open(newline='') as f:
        reader = csv.reader(f)
        next(reader)
        return Counter(map(tuple, reader))

# Both queries have a fixed complete expected row set in the pinned baseline.
for name in ['markup-measure-measurement.csv', 'markup-measure-witness.csv',
             'markup-measure-controls2-measurement.csv',
             'markup-measure-controls2-ExtractionErrors.csv']:
    assert rows(out, name) == rows(base, name), name
assert rows(out, 'markup-measure-controls2-SuccessfullyExtractedFiles.csv') == Counter(
    (str((base / 'controls' / n).resolve()), '') for n in
    ['creation-positive.ut', 'creation-negative.ut', 'ordinary-positive.ut', 'ordinary-negative.ut'])
assert rows(out, 'markup-measure-measurement-callable.csv') == Counter([
    ('usr/share/ucode/luci/uhttpd.uc', '6', '25', '12', '1', 'covered')])
assert rows(out, 'markup-measure-controls2-measurement-callable.csv') == Counter([
    ('creation-positive.ut', '1', '34', '1', '58', 'covered'),
    ('creation-negative.ut', '1', '34', '1', '55', 'covered')])
paths = runpy.run_path(str(root / 'scripts/markup-creation-smoke.py'))['PATHS']
keys = [('uhttpd.uc', 'top'), ('uhttpd.uc', 'callable:6:25')]
nodes = Counter((file, scope, role, ident) for file, scope in keys for role, ident in paths[file, scope])
edges = Counter((file, scope, a[1], file, scope, b[1]) for file, scope in keys
                for a, b in zip(paths[file, scope], paths[file, scope][1:]))
assert rows(out, 'markup-measure-markup-creation-nodes-test.csv') == nodes
assert rows(out, 'markup-measure-markup-creation-edges-test.csv') == edges
print('12 root results, witnesses, controls and complete real callable graph match')
