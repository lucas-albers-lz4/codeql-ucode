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


def file_identities(result: Any, source: Path, expected_paths: list[str], *, require_url: bool = True) -> list[str]:
    """Verify diagnostic File rows by exact canonical URL and scalar identity.

    BQRS labels for File entities are absolute paths, not the QL class name.
    Their File.getURL() positions are zero; the JSON decoder may expose those
    coordinates as fields or leave them encoded in the URI, so accept either
    representation while requiring the same zero-position source identity.
    """
    source = source.resolve()
    expected = collections.Counter(expected_paths)
    observed = []
    for row in tuples(result):
        require(len(row) == 2 and isinstance(row[0], dict), f"invalid extracted-file row: {row!r}")
        cell, message = row
        require(set(cell).issubset({"label", "url"}) and isinstance(cell.get("label"), str), f"invalid File entity cell: {cell!r}")
        require(message == "", f"SuccessfullyExtractedFiles message must be empty: {message!r}")
        url = cell.get("url")
        if url is None:
            require(not require_url, f"missing File URL in entity: {cell!r}")
            # Historical decodes without --entities=url,string carry only the
            # absolute-path label; use it solely to test compatibility with
            # that retained real output format.
            raw_path = Path(cell["label"])
        else:
            require(isinstance(url, dict) and "uri" in url, f"invalid File URL object: {url!r}")
            allowed = {"uri", "startLine", "startColumn", "endLine", "endColumn"}
            require(set(url) <= allowed and isinstance(url["uri"], str), f"invalid File URL fields: {url!r}")
            position_keys = ("startLine", "startColumn", "endLine", "endColumn")
            present = [key in url for key in position_keys]
            require(not any(present) or all(present), f"partial File URL coordinates: {url!r}")
            if all(present):
                require(all(type(url[key]) is int and url[key] == 0 for key in position_keys), f"File URL must be a zero-position identity: {url!r}")
            uri = urlsplit(url["uri"])
            require(uri.scheme == "file" and uri.netloc == "" and not uri.query and not uri.fragment, f"invalid File URI: {url['uri']!r}")
            require(not re.search(r"%(?![0-9a-fA-F]{2})", uri.path), f"invalid percent escape in {url['uri']!r}")
            uri_path = unquote(uri.path, errors="strict")
            suffix = re.search(r":(\d+):(\d+):(\d+):(\d+)$", uri_path)
            if suffix:
                coords = tuple(int(value) for value in suffix.groups())
                require(coords == (0, 0, 0, 0), f"File URL URI encodes nonzero coordinates: {url['uri']!r}")
                uri_path = uri_path[:suffix.start()]
            raw_path = Path(uri_path)
        require(raw_path.is_absolute() and ".." not in raw_path.parts, f"invalid diagnostic file path: {raw_path}")
        try:
            relative = raw_path.relative_to(source).as_posix()
        except ValueError as error:
            raise SystemExit(f"diagnostic File outside canonical source root: {raw_path}") from error
        observed.append(relative)
    actual = collections.Counter(observed)
    require(actual == expected, f"successful-extraction identities/multiplicity differ: missing={expected-actual} extra={actual-expected}")
    return observed


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
