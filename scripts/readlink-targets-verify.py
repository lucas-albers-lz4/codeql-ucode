#!/usr/bin/env python3
"""Verify real extracted call identities and diagnostics, not just row counts."""
import csv
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

src, results, expectation = map(Path, sys.argv[1:])
wanted = json.loads(expectation.read_text())
controls = {name + '.uc' for name in wanted['controls']}
pinned = {'usr/share/rpcd/ucode/luci', 'usr/share/ucode/luci/sys.uc'}
paths = controls | pinned
route = json.loads((results / 'routing.json').read_text())
assert route['input_count'] == route['plain_count'] == len(paths) == 68, route
assert route['duplicate_input_count'] == route['excluded_count'] == 0, route
assert {d['path'] for d in route['decisions']} == {str(src / p) for p in paths}
assert all(d['classification'] == 'plain' for d in route['decisions'])
with (results / 'extracted.csv').open(newline='') as f:
    extracted = list(csv.DictReader(f))
assert len(extracted) == 67 and {r['f'] for r in extracted} == {str(src / p) for p in paths - {'malformed.uc'}}, extracted
errors = json.loads((results / 'errors.json').read_text())['#select']['tuples']
assert len(errors) == 1 and unquote(urlparse(errors[0][0]['url']['uri']).path) == str(src / 'malformed.uc'), errors
rows = json.loads((results / 'targets.json').read_text())['#select']['tuples']
assert controls <= {r[1] for r in rows}, 'missing control call ASTs'
assert any(r[1] == 'malformed.uc' and r[5] == 'readlink' for r in rows), 'missing parse-recovered call'
# Each new negative is an actual, exact direct call, not just an empty file or
# a different call in the same fixture. Both inside/after-loop sites matter.
assert len(wanted['unresolved']) == 10 and len({tuple(x) for x in wanted['unresolved']}) == 10
for path, line, col, end_line, end_col in wanted['unresolved']:
    matches = [r for r in rows if r[1] == path and r[2] == line and r[3] == col]
    assert len(matches) == 1, ('missing unresolved call', path, line, col, matches)
    entity, _, _, _, kind, ident, libs = matches[0]
    url = entity['url']
    assert unquote(urlparse(url['uri']).path) == str(src / path), (path, url)
    assert (url['startLine'], url['startColumn'], url['endLine'], url['endColumn']) == (line, col, end_line, end_col), (path, url)
    assert kind == 'Identifier' and ident == 'readlink', (path, kind, ident)
    assert 'readlink' not in libs.split(','), ('unexpected unresolved target', path, line, col, libs)
found = []
for entity, path, line, col, kind, ident, libs in rows:
    if 'readlink' not in libs.split(','):
        continue
    url = entity['url']
    assert unquote(urlparse(url['uri']).path) == str(src / path), (path, url)
    assert (line, col) == (url['startLine'], url['startColumn']) and kind == 'Identifier' and ident == 'readlink', (path, url, line, col, kind, ident)
    found.append([path, url['startLine'], url['startColumn'], url['endLine'], url['endColumn']])
assert sorted(found) == wanted['targets'], f'readlink target identity mismatch: got={sorted(found)} expected={wanted["targets"]}'
print(f'verified {len(paths)} routed files, {len(extracted)} extracted, 1 parse error, {len(rows)} calls, {len(found)} exact readlink targets')
