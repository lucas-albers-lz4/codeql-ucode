#!/usr/bin/env python3
"""Check source-derived exact bindings, local flow, SSA, and extraction identity."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_FIXTURE = "23e858dcee2b2b8541c41c685c70219773d634b8bc0074bfe9ec6f6b0a0843b5"
EXPECTED_BINDINGS = Counter({
    ("scope.uc", 5, 11, 4, 7): 1,
    ("scope.uc", 8, 15, 4, 7): 1,
    ("scope.uc", 10, 15, 9, 11): 1,
    ("scope.uc", 14, 19, 13, 15): 1,
    ("scope.uc", 17, 15, 9, 11): 1,
    ("scope.uc", 20, 15, 9, 11): 1,
    ("scope.uc", 24, 11, 4, 7): 1,
    ("scope.uc", 28, 40, 28, 19): 1,
    ("scope.uc", 31, 11, 26, 7): 1,
    ("scope.uc", 33, 41, 33, 19): 1,
    ("scope.uc", 36, 11, 26, 7): 1,
    ("scope.uc", 44, 17, 43, 13): 1,
    ("scope.uc", 46, 15, 41, 11): 1,
    ("scope.uc", 50, 11, 38, 7): 1,
    ("scope.uc", 56, 23, 56, 16): 1,
    ("scope.uc", 56, 30, 56, 16): 1,
    ("scope.uc", 56, 43, 56, 16): 1,
    ("scope.uc", 57, 15, 55, 11): 1,
    ("scope.uc", 61, 11, 52, 7): 1,
})
EXPECTED_FLOW = Counter({
    (4, 11, 5, 11): 1,
    (4, 11, 8, 15): 1,
    (4, 11, 24, 11): 1,
})
EXPECTED_SSA = Counter({
    ("value", 1, 18, 1, 33): 1,
    ("k", 3, 16, 6, 11): 1,
    ("k", 3, 16, 11, 15): 1,
    ("k", 3, 16, 27, 11): 1,
    ("k", 3, 16, 32, 11): 1,
    ("k", 3, 16, 39, 11): 1,
    ("k", 3, 16, 53, 11): 1,
    ("x", 4, 7, 5, 11): 1,
    ("x", 4, 7, 8, 15): 1,
    ("x", 4, 7, 24, 11): 1,
    ("x", 9, 11, 10, 15): 1,
    ("x", 9, 11, 17, 15): 1,
    ("x", 13, 15, 14, 19): 1,
    ("y", 26, 7, 31, 11): 1,
    ("y", 26, 7, 36, 11): 1,
    ("y", 28, 19, 28, 40): 1,
    ("y", 33, 19, 33, 41): 1,
    ("q", 38, 7, 50, 11): 1,
    ("q", 41, 11, 46, 15): 1,
    ("q", 43, 13, 44, 17): 1,
    ("i", 52, 7, 61, 11): 1,
    ("i", 55, 11, 57, 15): 1,
    ("i", 56, 16, 56, 23): 1,
    ("i", 56, 16, 56, 30): 1,
    ("i", 56, 16, 56, 43): 1,
    ("i", 56, 30, 56, 23): 1,
    ("i", 56, 30, 56, 30): 1,
    ("i", 56, 30, 56, 43): 1,
})


def decode_rows(out, name):
    result = json.loads((out / f"{name}.json").read_text())
    return Counter(tuple(row) for row in result["#select"]["tuples"])


def assert_equal(name, expected, actual):
    if actual != expected:
        raise SystemExit(
            f"{name} identities differ: missing={expected-actual}, extra={actual-expected}"
        )


def main(out):
    src = (out / "src" / "scope.uc").resolve(strict=True)
    if src.is_symlink() or hashlib.sha256(src.read_bytes()).hexdigest() != EXPECTED_FIXTURE:
        raise SystemExit(f"fixture identity/hash mismatch: {src}")
    routing = json.loads((out / "routing.json").read_text())
    if (routing.get("input_count"), routing.get("plain_count"),
        routing.get("excluded_count"), len(routing.get("decisions", []))) != (1, 1, 0, 1):
        raise SystemExit(f"unexpected routing totals: {routing}")
    decision = routing["decisions"][0]
    if (decision.get("path"), decision.get("installed_path"), decision.get("classification"),
        decision.get("reason"), decision.get("status")) != (
            str(src), str(src), "plain", "ucode_extension", "plain_route_selected"):
        raise SystemExit(f"unexpected routed identity: {decision}")
    extracted = json.loads((out / "extracted.json").read_text())["#select"]["tuples"]
    if len(extracted) != 1 or extracted[0][0]["url"]["uri"] != src.as_uri():
        raise SystemExit(f"unexpected successful-file identity: {extracted}")
    errors = json.loads((out / "errors.json").read_text())["#select"]["tuples"]
    if errors:
        raise SystemExit(f"extraction errors: {errors}")

    assert_equal("source-first bindings", EXPECTED_BINDINGS, decode_rows(out, "bindings"))
    assert_equal("outer-source local flow", EXPECTED_FLOW, decode_rows(out, "flow"))
    assert_equal("SSA definition/read identities", EXPECTED_SSA, decode_rows(out, "ssa"))
    print(f"PASS exact switch binding identities: {sum(EXPECTED_BINDINGS.values())}")
    print(f"PASS exact switch local-flow identities: {sum(EXPECTED_FLOW.values())}")
    print(f"PASS exact SSA identities: {sum(EXPECTED_SSA.values())}")
    print("PASS one clean, identity-matched extraction")

if len(sys.argv) != 2:
    raise SystemExit("usage: switch-scope-verify.py OUTPUT")
main(Path(sys.argv[1]))
