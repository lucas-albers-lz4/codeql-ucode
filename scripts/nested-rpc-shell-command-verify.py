#!/usr/bin/env python3
"""Check a fresh, isolated nested-shell candidate run against pinned source bytes."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def tuples(path: Path) -> list:
    return json.loads(path.read_text())["#select"]["tuples"]


def verify_success_identities(rows: list, stage: Path, wanted_files: dict) -> None:
    actual = collections.Counter(row[0]["label"] for row in rows)
    expected = collections.Counter(str((stage / rel).resolve()) for rel in wanted_files)
    assert actual == expected, "successful-file identities differ"


def main() -> None:
    if not __debug__:
        raise RuntimeError("run this verifier without Python -O")
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--producer", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    run = args.run.resolve()
    producer = args.producer.resolve()
    expected = json.loads((producer / "ql/test/nested-rpc-shell-command/expected.json").read_text())
    query = producer / expected["query"]
    assert digest(query) == expected["query_sha256"], "query bytes differ"
    assert digest(run / "producer/ql/src/m4/NestedRpcShellCommand.ql") == expected["query_sha256"]
    assert digest(producer / expected["source_fixture"]) == expected["source_fixture_sha256"]

    wanted_files = {}
    for name, info in expected["files"].items():
        rel = f"usr/share/rpcd/ucode/{name}"
        assert digest(producer / "ql/test/nested-rpc-shell-command" / name) == info["sha256"]
        wanted_files[rel] = info
    for case, info in expected["historical"].items():
        rel = f"{case}/usr/share/rpcd/ucode/tailscale.uc"
        fixture = producer / "ql/test/tailscale-nested-shell" / rel
        assert digest(fixture) == info["sha256"]
        assert git_blob(fixture) == info["git_blob"], f"historical Git blob differs: {case}"
        wanted_files[rel] = info
    source_first = json.loads((run / "source-first.json").read_text())
    assert source_first["query_sha256"] == expected["query_sha256"]
    assert set(source_first["files"]) == set(wanted_files)
    for rel, info in wanted_files.items():
        assert digest(run / "stage" / rel) == info["sha256"], f"staged bytes differ: {rel}"
        assert source_first["files"][rel]["sha256"] == info["sha256"]

    verify_success_identities(tuples(run / "out/success-decode.stdout"), run / "stage", wanted_files)
    assert tuples(run / "out/errors-decode.stdout") == [], "extraction errors present"
    commands = json.loads((run / "out/commands.json").read_text())
    assert commands and all(command["exit"] == 0 for command in commands), "run command failed"

    sarif = json.loads((run / "out/candidate.sarif").read_text())
    assert sarif["version"] == "2.1.0" and len(sarif["runs"]) == 1
    one_run = sarif["runs"][0]
    rule_id = "ucode/m4/nested-rpc-shell-command-candidate"
    assert [rule["id"] for rule in one_run["tool"]["driver"]["rules"]] == [rule_id]
    wanted = []
    for rel, info in wanted_files.items():
        for span in info["candidate_sinks"]:
            line, columns = span.split(":")
            first, last_inclusive = map(int, columns.split("-"))
            wanted.append((rel, int(line), first, last_inclusive + 1))
    actual = []
    for result in one_run.get("results", []):
        assert result["ruleId"] == rule_id and len(result["locations"]) == 1
        physical = result["locations"][0]["physicalLocation"]
        region = physical["region"]
        assert region.get("endLine", region["startLine"]) == region["startLine"]
        actual.append((physical["artifactLocation"]["uri"], region["startLine"],
                       region["startColumn"], region["endColumn"]))
    assert collections.Counter(actual) == collections.Counter(wanted), "SARIF locations differ"
    print(f"verified {len(wanted_files)} extraction identities and {len(actual)} exact SARIF results")


if __name__ == "__main__":
    main()
