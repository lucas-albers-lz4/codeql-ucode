#!/usr/bin/env python3
"""Exact source-identity oracle for the experimental rest-value smoke."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
DIGEST = "11224c4f8f0c9383b878d3395602af3e1c93dbfe907f58b020f0c29c58b14c87"
INVENTORY = [
    ("formal", "value", 1, 19, 0), ("formal", "xs", 2, 20, 0),
    ("formal", "head", 3, 18, 0), ("formal", "tail", 3, 27, 1),
    ("call", "ordinary", 4, 1, -1), ("call", "gather", 5, 1, -1),
    ("call", "gather", 6, 1, -1), ("call", "gather", 7, 1, -1),
    ("call", "gather2", 8, 1, -1), ("call", "gather2", 9, 1, -1),
    ("call", "gather2", 10, 1, -1),
    ("argument", "ordinary", 4, 10, 0),
    ("argument", "gather", 6, 8, 0),
    ("argument", "gather", 7, 8, 0), ("argument", "gather", 7, 13, 1),
    ("argument", "gather2", 8, 9, 0),
    ("argument", "gather2", 9, 9, 0), ("argument", "gather2", 9, 20, 1),
    ("argument", "gather2", 10, 9, 0), ("argument", "gather2", 10, 20, 1),
    ("argument", "gather2", 10, 25, 2),
]
EDGES = [
    ("ordinary", 4, 0, 4, 10, "value", 1, 19),
    ("gather2", 8, 0, 8, 9, "head", 3, 18),
    ("gather2", 9, 0, 9, 9, "head", 3, 18),
    ("gather2", 10, 0, 10, 9, "head", 3, 18),
]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def exact(name, actual, expected):
    got = collections.Counter(map(tuple, actual))
    want = collections.Counter(expected)
    require(got == want, f"{name}: missing={want - got}, extra={got - want}")


def inputs(source):
    require(not source.is_symlink(), "source root is a symlink")
    source = source.resolve(strict=True)
    require({p.name for p in source.iterdir()} == {"rest.uc"}, "unexpected fixture files")
    file = source / "rest.uc"
    require(not file.is_symlink() and file.is_file(), "fixture is not a regular file")
    require(hashlib.sha256(file.read_bytes()).hexdigest() == DIGEST, "fixture bytes changed")
    return source


def verify(out, source):
    source = inputs(source)
    spec = importlib.util.spec_from_file_location("ownership", ROOT / "scripts/rpc-ownership-verify.py")
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load extraction verifier")
    ownership = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ownership)
    def data(name):
        return json.loads((out / (name + ".json")).read_text())
    route = data("routing")
    totals = {"input_count": 1, "plain_count": 1, "markup_count": 0,
              "markup_inconclusive_count": 0, "uncertain_count": 0,
              "excluded_count": 0, "duplicate_input_count": 0}
    require(all(route.get(k) == v for k, v in totals.items()), f"routing totals: {route}")
    decisions = [(d.get("path"), d.get("installed_path"), d.get("classification"),
                  d.get("reason"), d.get("status")) for d in route["decisions"]]
    exact("routing", decisions, [(str(source / "rest.uc"), "rest.uc", "plain", "ucode_extension", "plain_route_selected")])
    ownership.file_identities(data("extracted"), source, ["rest.uc"])
    require(not ownership.tuples(data("errors")), "extraction errors")
    exact("call/formal inventory", ownership.tuples(data("inventory")), INVENTORY)
    exact("argument/formal value edges", ownership.tuples(data("edges")), EDGES)
    print("PASS exact call/formal inventory and argument/formal value identities")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "inputs":
        inputs(Path(sys.argv[2]))
        print("PASS fixture bytes")
    elif len(sys.argv) == 4 and sys.argv[1] == "results":
        verify(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit("usage: rest-value-verify.py inputs SOURCE | results OUT SOURCE")
