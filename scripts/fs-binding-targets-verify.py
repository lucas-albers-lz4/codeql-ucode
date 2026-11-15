#!/usr/bin/env python3
"""Verify real extracted call identities and the bounded fs binding contract."""
from collections import Counter
import csv
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

src, db, manifest_path = map(Path, sys.argv[1:])
manifest = json.loads(manifest_path.read_text())
paths = set(manifest['hashes'])
for path, digest in manifest['hashes'].items():
    assert hashlib.sha256((src / path).read_bytes()).hexdigest() == digest, path
route = json.loads((db / 'routing.json').read_text())
assert route['input_count'] == route['plain_count'] == len(paths), route
assert route['duplicate_input_count'] == route['excluded_count'] == 0, route
assert len(route['decisions']) == len(paths)
assert {d['path'] for d in route['decisions']} == {str(src / p) for p in paths}
assert all(d['classification'] == 'plain' for d in route['decisions'])
with (db / 'extracted.csv').open(newline='') as f:
    extracted = list(csv.DictReader(f))
assert len(extracted) == len(paths) - 1
assert {r['f'] for r in extracted} == {str(src / p) for p in paths - {'readfile__malformed.uc'}}
errors = json.loads((db / 'errors.json').read_text())['#select']['tuples']
assert len(errors) == 1 and unquote(urlparse(errors[0][0]['url']['uri']).path) == str(src / 'readfile__malformed.uc')
rows = json.loads((db / 'targets.json').read_text())['#select']['tuples']
actual_calls = []
actual_targets = []
keys = {'popen', 'basename', 'access', 'open', 'readfile', 'readlink'}
for entity, path, line, col, kind, ident, cfg, libs in rows:
    url = entity['url']
    assert unquote(urlparse(url['uri']).path) == str(src / path), (path, url)
    assert (line, col) == (url['startLine'], url['startColumn']), (path, url)
    span = [path, line, col, url['endLine'], url['endColumn']]
    actual_calls.append(span + [kind, ident])
    if ident in keys:
        assert cfg, ('missing CFG-backed control call', span, ident)
    for key in keys.intersection(libs.split(',')):
        assert cfg and kind == 'Identifier' and ident == key, (span, kind, ident, cfg, libs)
        actual_targets.append([key] + span)
expected_calls = Counter(map(tuple, manifest['calls']))
observed_calls = Counter(map(tuple, actual_calls))
assert observed_calls == expected_calls, ('call entity inventory mismatch', observed_calls - expected_calls, expected_calls - observed_calls)
expected_targets = Counter(map(tuple, manifest['targets']))
observed_targets = Counter(map(tuple, actual_targets))
assert observed_targets == expected_targets, ('fs target identity mismatch', observed_targets - expected_targets, expected_targets - observed_targets)
print(f'verified {len(paths)} routed files, {len(extracted)} extracted, 1 diagnostic, {len(rows)} exact calls, {len(actual_targets)} exact fs targets')
