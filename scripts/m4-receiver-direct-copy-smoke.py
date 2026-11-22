#!/usr/bin/env python3
"""Fresh extraction gate and exact oracle for direct receiver-copy controls."""
import collections
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "ql/test/receiver-provenance/direct-copy-controls.uc"
QUERY = ROOT / "ql/src/m4/ReceiverDirectCopy.ql"
CALL_INVENTORY = ROOT / "ql/src/m4/ReceiverDirectCopyCallInventory.ql"

# Complete source declaration, direct-copy declaration, receiver, and call
# spans. Every expected row is enumerated from this checked-in fixture.
EXPECTED = [
    ((4, 7, 4, 35), (4, 12, 4, 35), (5, 7, 5, 16), (6, 3, 6, 7), (6, 3, 6, 22), "one direct copy may reach direct receiver"),
    ((19, 7, 19, 35), (19, 12, 19, 35), (20, 7, 20, 16), (21, 3, 21, 7), (21, 3, 21, 15), "one direct copy may reach direct receiver"),
    ((25, 7, 25, 35), (25, 12, 25, 35), (26, 7, 26, 16), (29, 3, 29, 7), (29, 3, 29, 28), "one direct copy may reach direct receiver"),
    ((52, 7, 52, 35), (52, 12, 52, 35), (53, 7, 53, 16), (56, 3, 56, 7), (56, 3, 56, 26), "one direct copy may reach direct receiver"),
    ((66, 7, 66, 35), (66, 12, 66, 35), (67, 7, 67, 16), (70, 3, 70, 7), (70, 3, 70, 31), "one direct copy may reach direct receiver"),
]
EXPECTED_CALLS = [
    ((4, 12, 4, 35), "popen"),
    ((6, 3, 6, 22), "MemberExpression"),
    ((8, 3, 8, 15), "MemberExpression"),
    ((12, 12, 12, 35), "popen"),
    ((15, 3, 15, 21), "MemberExpression"),
    ((19, 12, 19, 35), "popen"),
    ((21, 3, 21, 15), "MemberExpression"),
    ((25, 12, 25, 35), "popen"),
    ((29, 3, 29, 28), "MemberExpression"),
    ((33, 12, 33, 35), "popen"),
    ((36, 3, 36, 27), "MemberExpression"),
    ((40, 12, 40, 35), "popen"),
    ((43, 3, 43, 28), "MemberExpression"),
    ((47, 12, 47, 35), "popen"),
    ((48, 3, 48, 12), "MemberExpression"),
    ((52, 12, 52, 35), "popen"),
    ((54, 27, 54, 46), "MemberExpression"),
    ((55, 3, 55, 14), "inner"),
    ((56, 3, 56, 26), "MemberExpression"),
    ((60, 3, 60, 25), "MemberExpression"),
    ((62, 3, 62, 15), "MemberExpression"),
    ((66, 12, 66, 35), "popen"),
    ((68, 3, 68, 35), "SubscriptExpression"),
    ((69, 3, 69, 33), "SubscriptExpression"),
    ((70, 3, 70, 31), "MemberExpression"),
]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def decode_entity(entity, source_root):
    uri = urlsplit(entity["url"]["uri"])
    require(uri.scheme == "file" and not uri.netloc, f"bad entity URI: {uri}")
    path = Path(unquote(uri.path, errors="strict"))
    name = path.relative_to(source_root).as_posix()
    coords = tuple(entity["url"][k] for k in ("startLine", "startColumn", "endLine", "endColumn"))
    return name, coords


def run(codeql, args, cwd=ROOT):
    return subprocess.run([codeql, *map(str, args)], cwd=cwd, check=True,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def query(codeql, db, search, work, path, label):
    bqrs = work / f"{label}.bqrs"
    run(codeql, ["query", "run", path, f"--database={db}", f"--search-path={search}",
                 f"--output={bqrs}", "--threads=1", "--ram=2048"])
    raw = run(codeql, ["bqrs", "decode", "--format=json", "--entities=url,string", bqrs])
    return json.loads(raw)["#select"]["tuples"]


def check_diagnostics(codeql, db, search, work, source_file):
    selected_path = source_file.resolve()
    expected_success = [{"label": str(selected_path), "url": {
        "uri": selected_path.as_uri(), "startLine": 0, "startColumn": 0,
        "endLine": 0, "endColumn": 0}}, ""]
    expected_columns = {
        "files": [{"name": "f", "kind": "Entity"}, {"kind": "String"}],
        "errors": [{"name": "error", "kind": "Entity"},
                   {"kind": "String"}, {"kind": "Integer"}],
    }
    decoded = {}
    for label, query_path in (
        ("files", ROOT / "ql/src/diagnostics/SuccessfullyExtractedFiles.ql"),
        ("errors", ROOT / "ql/src/diagnostics/ExtractionErrors.ql"),
    ):
        bqrs = work / f"diagnostics-{label}.bqrs"
        run(codeql, ["query", "run", query_path, f"--database={db}",
                     f"--search-path={search}", f"--output={bqrs}",
                     "--threads=1", "--ram=2048"])
        raw = run(codeql, ["bqrs", "decode", "--format=json", "--entities=url,string", bqrs])
        document = json.loads(raw)
        require(isinstance(document, dict) and set(document) == {"#select"},
                f"unexpected {label} diagnostic document: {document}")
        table = document["#select"]
        require(isinstance(table, dict) and set(table) == {"columns", "tuples"} and
                table["columns"] == expected_columns[label] and isinstance(table["tuples"], list),
                f"unexpected {label} diagnostic schema: {table}")
        decoded[label] = table["tuples"]
    require(decoded["files"] == [expected_success],
            f"exact successful-file identity mismatch: {decoded['files']}")
    require(not decoded["errors"], f"extraction errors: {decoded['errors']}")


def main():
    codeql = os.environ.get("CODEQL_CLI") or shutil.which("codeql")
    require(codeql, "CodeQL CLI missing; set CODEQL_CLI")
    pack = ROOT / "extractor-pack"
    require(pack.is_dir(), "extractor-pack missing; build it first")
    require(FIXTURE.is_file() and QUERY.is_file() and CALL_INVENTORY.is_file(),
            "fixture or query missing")
    work = Path(tempfile.mkdtemp(prefix="receiver-alias-smoke-")).resolve()
    print(f"evidence directory: {work}", flush=True)
    source = work / "source"
    source.mkdir()
    shutil.copyfile(FIXTURE, source / FIXTURE.name)
    db = work / "db"
    search = os.pathsep.join(map(str, [pack, ROOT / "ql/lib", ROOT / "ql/src"]))
    run(codeql, ["database", "init", db, "--language=ucode", f"--search-path={search}",
                 f"--source-root={source}"])
    run(codeql, ["database", "index-files", db, "--language=ucode", "--include=**/*.uc",
                 f"--working-dir={source}"])
    receipt = db / "trap/ucode/routing.json"
    require(receipt.is_file(), "missing pre-finalization routing receipt")
    routing = json.loads(receipt.read_text())
    (work / "routing.json").write_text(json.dumps(routing, indent=2) + "\n")
    expected_path = str((source / FIXTURE.name).resolve())
    expected_decision = {
        "path": expected_path,
        "installed_path": expected_path,
        "classification": "plain",
        "reason": "ucode_extension",
        "status": "plain_route_selected",
    }
    require(routing == {
        "input_count": 1, "plain_count": 1, "markup_count": 0,
        "markup_inconclusive_count": 0, "uncertain_count": 0,
        "excluded_count": 0, "duplicate_input_count": 0,
        "decisions": [expected_decision],
    }, f"unexpected exact routing receipt: {routing}")
    run(codeql, ["database", "finalize", db])
    check_diagnostics(codeql, db, search, work, source / FIXTURE.name)
    call_rows = query(codeql, db, search, work, CALL_INVENTORY, "call-inventory")
    actual_calls = []
    for row in call_rows:
        name, coords = decode_entity(row[0], source)
        require(name == FIXTURE.name, f"wrong call-inventory file: {name}")
        actual_calls.append((coords, row[1]))
    require(collections.Counter(actual_calls) == collections.Counter(EXPECTED_CALLS),
            f"extracted call-control inventory mismatch: missing={collections.Counter(EXPECTED_CALLS)-collections.Counter(actual_calls)} "
            f"extra={collections.Counter(actual_calls)-collections.Counter(EXPECTED_CALLS)}")
    tuples = query(codeql, db, search, work, QUERY, "receiver-direct-copy")
    actual = []
    for row in tuples:
        entities = [decode_entity(entity, source) for entity in row[:5]]
        require(all(name == FIXTURE.name for name, _ in entities), f"wrong file identity: {entities}")
        actual.append(tuple(coords for _, coords in entities) + (row[5],))
    expected = EXPECTED
    require(collections.Counter(actual) == collections.Counter(expected),
            f"exact receiver witnesses mismatch: missing={collections.Counter(expected)-collections.Counter(actual)} "
            f"extra={collections.Counter(actual)-collections.Counter(expected)}")
    print(f"PASS exact selected files=1, extraction errors=0, "
          f"extracted call controls={len(actual_calls)}, exact may-reach rows={len(actual)}")


if __name__ == "__main__":
    main()
