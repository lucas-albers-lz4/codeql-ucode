#!/usr/bin/env python3
"""Exact identity oracle for the RPC ownership controls (test-only)."""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "ql/test/rpc-ownership"
MANIFEST = json.loads((CORPUS / "manifest.json").read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def input_oracle(source: Path) -> dict[str, Path]:
    require(not source.is_symlink(), f"source root must not be a symlink: {source}")
    source = source.resolve(strict=True)
    require(source.is_dir(), f"invalid source root: {source}")
    expected = {item["path"] for item in MANIFEST["files"].values()}
    observed = {p.relative_to(source).as_posix() for p in source.rglob("*") if (p.is_file() or p.is_symlink()) and p.name != "manifest.json"}
    require(observed == expected, f"selected file identity mismatch: missing={sorted(expected-observed)} extra={sorted(observed-expected)}")
    paths = {}
    for name, item in MANIFEST["files"].items():
        path = source / item["path"]
        require(not path.is_symlink() and path.is_file(), f"fixture must be a regular file: {path}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], f"fixture bytes changed: {path}")
        paths[name] = path
    return paths


def tuples(result: Any) -> list[list[Any]]:
    require(isinstance(result, dict) and isinstance(result.get("#select"), dict), "expected decoded #select BQRS JSON")
    rows = result["#select"].get("tuples")
    require(isinstance(rows, list) and all(isinstance(row, list) for row in rows), "invalid decoded tuple schema")
    return rows


def entity(cell: object, source: Path) -> dict[str, object]:
    require(isinstance(cell, dict) and set(cell) == {"label", "url"} and isinstance(cell["url"], dict), f"expected entity cell: {cell!r}")
    url = cell["url"]
    keys = {"uri", "startLine", "startColumn", "endLine", "endColumn"}
    require(set(url) == keys, f"invalid entity URL fields: {url}")
    parsed = urlsplit(url["uri"])
    require(parsed.scheme == "file" and parsed.netloc == "" and not parsed.query and not parsed.fragment, f"invalid file URI: {url['uri']}")
    require(not re.search(r"%(?![0-9a-fA-F]{2})", parsed.path), f"invalid percent escape in {url['uri']}")
    path = Path(unquote(parsed.path, errors="strict"))
    require(path.is_absolute() and ".." not in path.parts, f"invalid entity path: {path}")
    try:
        rel = path.relative_to(source)
    except ValueError as error:
        raise SystemExit(f"entity outside exact source root: {url['uri']}") from error
    coords = [url[k] for k in ("startLine", "startColumn", "endLine", "endColumn")]
    require(all(type(n) is int and n > 0 for n in coords), f"invalid full span: {coords}")
    return {"label": cell["label"], "path": rel.as_posix(), "span": coords}


def file_identities(result: Any, source: Path) -> list[str]:
    """Decode diagnostic File entities by canonical full URI, not basename."""
    identities = []
    for row in tuples(result):
        require(len(row) == 2 and isinstance(row[0], dict) and row[0].get("label") == "File", f"invalid extracted-file row: {row!r}")
        url = row[0].get("url")
        require(isinstance(url, dict) and set(url) == {"uri"}, f"invalid File URL: {url!r}")
        parsed = urlsplit(url["uri"])
        require(parsed.scheme == "file" and parsed.netloc == "" and not parsed.query and not parsed.fragment, f"invalid file URI: {url['uri']}")
        require(not re.search(r"%(?![0-9a-fA-F]{2})", parsed.path), f"invalid percent escape in {url['uri']}")
        path = Path(unquote(parsed.path, errors="strict"))
        try:
            identities.append(path.relative_to(source).as_posix())
        except ValueError as error:
            raise SystemExit(f"diagnostic File outside source root: {url['uri']}") from error
    return identities


def normalized(rows: list[list[Any]], source: Path) -> list[list[Any]]:
    result = []
    for row in rows:
        result.append([entity(c, source) if isinstance(c, dict) else c for c in row])
    return result


def identity(name: str, role: str) -> dict[str, object]:
    rel = MANIFEST["files"][name]["path"]
    return {"label": "MemberExpression" if role in ("outer", "inner") else "CallExpression",
            "path": rel, "span": MANIFEST["entities"][name][role]}


def exact_counter(rows: list[list[object]], expected: list[list[object]], name: str) -> None:
    got = collections.Counter(json.dumps(r, sort_keys=True) for r in rows)
    want = collections.Counter(json.dumps(r, sort_keys=True) for r in expected)
    require(got == want, f"{name} exact full-entity rows differ: missing={want-got} extra={got-want}")


def verify(source: Path, results: Path) -> None:
    input_oracle(source)
    source = source.resolve(strict=True)
    # Fixture eligibility is independent of sameRpcMethod and taint relations.
    eligibility = normalized(tuples(json.loads((results / "RpcOwnershipControlsTest.json").read_text())), source)
    want_eligibility = []
    for fixture, method_rows in MANIFEST["eligibility"].items():
        for method, roles in method_rows.items():
            for role in roles:
                want_eligibility.append([identity(fixture, role), "request-args" if role in ("outer", "inner") else "fs-popen", method])
    exact_counter(eligibility, want_eligibility, "eligibility inventory")

    for query, symbolic in MANIFEST["expected"].items():
        actual = normalized(tuples(json.loads((results / f"{query}.json").read_text())), source)
        expected = []
        for src_name, src_role, message, sink_name, sink_role, sink_name_string in symbolic:
            expected.append([identity(src_name, src_role), message, identity(sink_name, sink_role), sink_name_string])
        exact_counter(actual, expected, query)
    print("PASS exact ownership baseline: 12 eligible entities and positive-only query rows")


def verify_mutant(source: Path, results: Path) -> None:
    """Require the real independent-owner mutation's predicted extra entities."""
    with tempfile.TemporaryDirectory(prefix="rpc-ownership-mutant-oracle-") as temp:
        red_dir = Path(temp)
        shutil.copyfile(results / "RpcOwnershipControlsTest.json", red_dir / "RpcOwnershipControlsTest.json")
        for query, _ in MANIFEST["expected"].items():
            shutil.copyfile(results / f"mutant-{query}.json", red_dir / f"{query}.json")
        try:
            verify(source, red_dir)
        except SystemExit:
            pass
        else:
            raise SystemExit("positive-only baseline verifier accepted the actual owner mutant")
    print("PASS baseline verifier rejects the actual independent-owner mutation")

    expected = {name: rows for name, rows in MANIFEST["expected"].items()}
    request = [list(row) for row in expected["RequestArgsExec.ql"]]
    request.extend([
        ["cross-source", "outer", "probe request.args reaches popen", "cross-sink", "sink", "popen"],
        ["same-file", "outer", "sinkOnly request.args reaches popen", "same-file", "sink", "popen"],
    ])
    local = [list(row) for row in expected["LocalTaint.ql"]]
    for source_role in ("outer", "inner"):
        local.extend([
            ["cross-source", source_role, "request.args reaches popen in luci", "cross-sink", "sink", "popen"],
            ["same-file", source_role, "request.args reaches popen in luci", "same-file", "sink", "popen"],
        ])
    for query, symbolic in (("RequestArgsExec.ql", request), ("LocalTaint.ql", local)):
        actual = normalized(tuples(json.loads((results / f"mutant-{query}.json").read_text())), source)
        rows = [[identity(a, b), message, identity(c, d), sink]
                for a, b, message, c, d, sink in symbolic]
        exact_counter(actual, rows, f"actual owner mutation {query}")
    print("PASS actual independent-owner mutation: exact cross-file and same-file extra rows")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: rpc-ownership-verify.py SOURCE_ROOT DECODED_JSON_DIR")
    verify(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
