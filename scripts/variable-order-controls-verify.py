#!/usr/bin/env python3
"""Source-pinned, exact-identity oracle for declaration-order controls."""

import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "ql/test/variable-order-controls.json").read_text())


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def inputs(source):
    source = source.resolve(strict=True)
    expected = MANIFEST["files"]
    observed = {p.name for p in source.iterdir() if p.is_file() or p.is_symlink()}
    require(
        observed == set(expected),
        f"fixture identity mismatch: {observed} != {set(expected)}",
    )
    for name, digest in expected.items():
        path = source / name
        require(
            not path.is_symlink() and path.is_file(),
            f"fixture is not a regular file: {path}",
        )
        require(
            hashlib.sha256(path.read_bytes()).hexdigest() == digest,
            f"fixture bytes differ: {path}",
        )
    print(f"PASS fixture identities and hashes: {len(expected)}")


def verify(out, source):
    source = source.resolve(strict=True)
    inputs(source)
    spec = importlib.util.spec_from_file_location(
        "ownership", ROOT / "scripts/rpc-ownership-verify.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load extraction verifier")
    ownership = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ownership)

    def rows(name):
        return ownership.tuples(json.loads((out / (name + ".json")).read_text()))

    names = MANIFEST["files"]
    route = json.loads((out / "routing.json").read_text())
    totals = {
        "input_count": len(names),
        "plain_count": len(names),
        "markup_count": 0,
        "markup_inconclusive_count": 0,
        "uncertain_count": 0,
        "excluded_count": 0,
        "duplicate_input_count": 0,
    }
    require(
        all(route.get(k) == v for k, v in totals.items()),
        f"routing totals differ: {route}",
    )
    expected_routes = collections.Counter(
        (str(source / n), n, "plain", "ucode_extension", "plain_route_selected")
        for n in names
    )
    actual_routes = collections.Counter(
        (
            d.get("path"),
            d.get("installed_path"),
            d.get("classification"),
            d.get("reason"),
            d.get("status"),
        )
        for d in route["decisions"]
    )
    require(
        actual_routes == expected_routes,
        f"routing identities differ: {actual_routes} != {expected_routes}",
    )
    ownership.file_identities(
        json.loads((out / "extracted.json").read_text()), source, list(names)
    )
    require(not rows("errors"), f"extraction errors: {rows('errors')}")
    actual = collections.Counter(map(tuple, rows("bindings")))
    wanted = collections.Counter(map(tuple, MANIFEST["rows"]))
    require(
        actual == wanted,
        f"bindings differ: missing={wanted - actual}, extra={actual - wanted}",
    )
    print(
        f"PASS exact binding identities: {sum(wanted.values())}; fixtures: {len(names)}"
    )


if sys.argv[1] == "inputs":
    inputs(Path(sys.argv[2]))
elif sys.argv[1] == "results":
    verify(Path(sys.argv[2]), Path(sys.argv[3]))
else:
    raise SystemExit(
        "usage: variable-order-controls-verify.py inputs SOURCE | results OUT SOURCE"
    )
