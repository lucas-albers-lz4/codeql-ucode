#!/usr/bin/env python3
"""Verify exact extraction, binding, and source-to-read identities."""

import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def verify_inputs(source):
    if source.is_symlink() or not source.is_dir():
        raise SystemExit(f"invalid fixture source root: {source}")
    source = source.resolve(strict=True)
    expected = json.loads((ROOT / "ql/test/variable-order.json").read_text())["files"]
    if set(expected) != {"order.uc"}:
        raise SystemExit(f"invalid fixture manifest: {expected}")
    observed = {
        p.relative_to(source).as_posix()
        for p in source.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    if observed != set(expected):
        raise SystemExit(f"fixture identity mismatch: {observed} != {set(expected)}")
    for name, digest in expected.items():
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"fixture is not a regular file: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(f"fixture bytes differ: {path}")
    print(f"PASS fixture identities and hashes: {len(expected)}")


if len(sys.argv) == 3 and sys.argv[1] == "inputs":
    verify_inputs(Path(sys.argv[2]))
    sys.exit(0)
if len(sys.argv) != 3:
    raise SystemExit("usage: variable-order-verify.py inputs SOURCE | OUT SOURCE")
out, source = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
verify_inputs(source)
spec = importlib.util.spec_from_file_location(
    "ownership", Path(__file__).with_name("rpc-ownership-verify.py")
)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load extraction verifier")
ownership = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ownership)


def rows(name):
    return ownership.tuples(json.loads((out / (name + '.json')).read_text()))
route = json.loads((out / 'routing.json').read_text())
decisions = route['decisions']
expected_totals = {'input_count': 1, 'plain_count': 1, 'markup_count': 0,
                   'markup_inconclusive_count': 0, 'uncertain_count': 0,
                   'excluded_count': 0, 'duplicate_input_count': 0}
expected_route = {'path': str(source / 'order.uc'), 'installed_path': 'order.uc',
                  'classification': 'plain', 'reason': 'ucode_extension',
                  'status': 'plain_route_selected'}
if any(route.get(k) != v for k, v in expected_totals.items()) or decisions != [expected_route]:
    raise SystemExit(f'unexpected routing: {route}')
ownership.file_identities(json.loads((out / 'extracted.json').read_text()), source, ['order.uc'])
if rows('errors'):
    raise SystemExit(f'extraction errors: {rows("errors")}')
expected_bindings = [
    [6, 13, 4, 7], [8, 13, 7, 9], [10, 11, 4, 7],
    [15, 11, 14, 17], [17, 13, 14, 17], [19, 13, 18, 9], [21, 11, 14, 17],
    [25, 13, 24, 12], [27, 11, 23, 15],
    [31, 23, 31, 10], [32, 11, 29, 19],
    [36, 32, 34, 17], [40, 11, 34, 17],
    [45, 11, 44, 7],
    [47, 34, 47, 19], [47, 63, 47, 42], [47, 77, 47, 19],
]
expected_flow = [[4, 11, 6, 13], [4, 11, 10, 11]]
for name, expected in [('bindings', expected_bindings), ('flow', expected_flow)]:
    actual_counter = collections.Counter(map(tuple, rows(name)))
    expected_counter = collections.Counter(map(tuple, expected))
    if actual_counter != expected_counter:
        raise SystemExit(f'{name} differs: missing={expected_counter-actual_counter}, extra={actual_counter-expected_counter}')
    print(f'PASS exact {name} identities: {len(expected)}')
