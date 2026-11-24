#!/usr/bin/env python3
"""Frozen source-first oracle for query eligibility; no application coverage claim."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ownership', ROOT / 'scripts/rpc-ownership-verify.py')
ownership = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ownership)
BASE = 'usr/share/rpcd/ucode/'
ALLOWED = [BASE + n + '.uc' for n in
           ('docker_rpc', 'ddns', 'tailscale', 'example', 'rustdesk-server', 'wifihistory', 'weechat')]
EXCLUDED = [BASE + 'not-allowed.uc', 'elsewhere/example.uc',
            'modules/example/root/usr/share/rpcd/ucode/example.uc']
ALL = ALLOWED + EXCLUDED
TEXT = 'let methods = { test: { call: function(request) { system(request.args.value); } } };\n'


def load_json(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            ownership.require(key not in result, f'duplicate JSON key in {path}: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def preflight(source):
    ownership.require(not source.is_symlink(), f'symlink source root: {source}')
    source = source.resolve(strict=True)
    entries = list(source.rglob('*'))
    ownership.require(not any(p.is_symlink() for p in entries), 'symlink in fixture tree')
    observed = sorted(p.relative_to(source).as_posix() for p in entries if p.is_file())
    ownership.require(observed == sorted(ALL), f'fixture inventory differs: {observed}')
    for path in ALL:
        p = source / path
        ownership.require(not p.is_symlink() and p.read_bytes() == TEXT.encode('utf-8'), f'fixture changed: {path}')
    return source


def verify_routing(source, receipt):
    source = preflight(source)
    data = load_json(receipt)
    ownership.require(isinstance(data, dict), 'routing receipt must be an object')
    expected = {
        str(source / path): {
            'path': str(source / path), 'installed_path': path,
            'classification': 'plain',
            'reason': 'rpcd_raw_mode_full_path' if path.startswith(BASE) else 'ucode_extension',
            'status': 'plain_route_selected',
        } for path in ALL
    }
    for key, value in {'input_count': 10, 'plain_count': 10, 'markup_count': 0,
                       'markup_inconclusive_count': 0, 'uncertain_count': 0,
                       'excluded_count': 0, 'duplicate_input_count': 0}.items():
        ownership.require(type(data.get(key)) is int and data[key] == value, f'routing {key}: {data}')
    decisions = data.get('decisions')
    ownership.require(isinstance(decisions, list) and len(decisions) == len(expected), 'routing decision count')
    for row in decisions:
        ownership.require(isinstance(row, dict) and row.get('path') in expected, f'unexpected route: {row}')
        ownership.require(row == expected.pop(row['path']), f'routing decision differs: {row}')
    ownership.require(not expected, f'missing routes: {expected}')


def verify(source, output, mutant=False, candidate=None):
    source = preflight(source)
    verify_routing(source, output / 'routing.json')
    def rows(name):
        return ownership.tuples(load_json(output / (name + '.json')))
    ownership.file_identities(load_json(output / 'extracted.json'), source, ALL)
    ownership.require(not rows('errors'), 'unexpected extraction diagnostics')
    def entity(path, label, start, end):
        return {'label': label, 'path': path, 'span': [1, start, 1, end]}
    expected_inventory = []
    for path in ALL:
        expected_inventory += [[entity(path, 'MemberExpression', 58, 75), 'request-args', 'test'],
                               [entity(path, 'MemberExpression', 58, 69), 'request-args', 'test'],
                               [entity(path, 'CallExpression', 51, 76), 'system', 'test']]
    ownership.exact_counter(ownership.normalized(rows('inventory'), source), expected_inventory, 'modeled eligibility inventory')
    expected = [[entity(path, 'MemberExpression', 58, 75), 'test request.args reaches system',
                 entity(path, 'CallExpression', 51, 76), 'system'] for path in (ALL if mutant else ALLOWED)]
    actual = ownership.normalized(rows(candidate or ('mutant' if mutant else 'request')), source)
    ownership.exact_counter(actual, expected, 'query identities')
    return actual


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--preflight':
        preflight(Path(sys.argv[2]))
        return
    if len(sys.argv) != 3:
        raise SystemExit('usage: request-args-scope-verify.py SOURCE OUTPUT | --preflight SOURCE')
    source, output = map(Path, sys.argv[1:])
    verify(source, output)
    try:
        # Apply the unchanged baseline oracle directly to mutant output.
        verify(source, output, candidate='mutant')
    except SystemExit:
        pass
    else:
        raise SystemExit('baseline oracle accepted the path-gate mutant')
    verify(source, output, mutant=True)
    print('PASS exact 10-file extraction and model inventory; seven query rows; path mutation rejected')

if __name__ == '__main__':
    main()
