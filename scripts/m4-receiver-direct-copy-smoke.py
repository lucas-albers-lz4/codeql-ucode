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
EXPECTED_FILES = ["direct-copy-controls.uc"]

# Complete source declaration, direct-copy declaration, receiver, and call
# spans. Every expected row is enumerated from this checked-in fixture.
EXPECTED = [
    ((4, 7, 4, 35), (4, 12, 4, 35), (5, 7, 5, 16), (6, 3, 6, 7), (6, 3, 6, 22), "one direct copy to direct receiver"),
    ((24, 7, 24, 35), (24, 12, 24, 35), (25, 7, 25, 16), (28, 3, 28, 7), (28, 3, 28, 26), "one direct copy to direct receiver"),
    ((38, 7, 38, 35), (38, 12, 38, 35), (39, 7, 39, 16), (42, 3, 42, 7), (42, 3, 42, 31), "one direct copy to direct receiver"),
]
EXPECTED_CALLS = [
    ((4, 12, 4, 35), "popen"),
    ((6, 3, 6, 22), "MemberExpression"),
    ((8, 3, 8, 15), "MemberExpression"),
    ((12, 12, 12, 35), "popen"),
    ((15, 3, 15, 21), "MemberExpression"),
    ((19, 12, 19, 35), "popen"),
    ((20, 3, 20, 12), "MemberExpression"),
    ((24, 12, 24, 35), "popen"),
    ((26, 27, 26, 46), "MemberExpression"),
    ((27, 3, 27, 14), "inner"),
    ((28, 3, 28, 26), "MemberExpression"),
    ((32, 3, 32, 25), "MemberExpression"),
    ((34, 3, 34, 15), "MemberExpression"),
    ((38, 12, 38, 35), "popen"),
    ((40, 3, 40, 35), "SubscriptExpression"),
    ((41, 3, 41, 33), "SubscriptExpression"),
    ((42, 3, 42, 31), "MemberExpression"),
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
    require(routing["input_count"] == 1 and routing["plain_count"] == 1 and
            routing["markup_count"] == 0 and routing["uncertain_count"] == 0 and
            len(routing["decisions"]) == 1 and
            routing["decisions"][0]["status"] == "plain_route_selected" and
            Path(routing["decisions"][0]["path"]).name == FIXTURE.name,
            f"unexpected routing receipt: {routing}")
    run(codeql, ["database", "finalize", db])
    files = query(codeql, db, search, work, ROOT / "ql/src/diagnostics/SuccessfullyExtractedFiles.ql", "files")
    actual_files = [decode_entity(row[0], source)[0] for row in files]
    require(collections.Counter(actual_files) == collections.Counter(EXPECTED_FILES),
            f"successful-file identity mismatch: {actual_files}")
    errors = query(codeql, db, search, work, ROOT / "ql/src/diagnostics/ExtractionErrors.ql", "errors")
    require(not errors, f"extraction errors: {errors}")
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
    print(f"PASS exact selected files={len(actual_files)}, extraction errors=0, "
          f"extracted call controls={len(actual_calls)}, exact direct-copy rows={len(actual)}")


if __name__ == "__main__":
    main()
