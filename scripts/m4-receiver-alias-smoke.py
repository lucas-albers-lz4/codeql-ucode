#!/usr/bin/env python3
"""Fresh extractor gate and exact witness oracle for receiver alias controls."""
import collections
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "ql/test/receiver-provenance/alias-transfer-controls.uc"
QUERY = ROOT / "ql/src/m4/ReceiverAliasFlow.ql"
EXPECTED_FILES = ["alias-transfer-controls.uc"]

# Complete source/declaration, receiver-read, call spans, and query label.
EXPECTED = [
    ((4, 7, 4, 35), (7, 3, 7, 7), (7, 3, 7, 19), "fd -> alias:read@7"),
    ((4, 7, 4, 35), (8, 3, 8, 7), (8, 3, 8, 15), "fd -> alias:close@8"),
    ((5, 7, 5, 16), (7, 3, 7, 7), (7, 3, 7, 19), "alias -> alias:read@7"),
    ((5, 7, 5, 16), (8, 3, 8, 7), (8, 3, 8, 15), "alias -> alias:close@8"),
    ((12, 7, 12, 35), (13, 3, 13, 4), (13, 3, 13, 16), "fd -> fd:read@13"),
    ((12, 7, 12, 35), (14, 3, 14, 4), (14, 3, 14, 12), "fd -> fd:close@14"),
    ((18, 7, 18, 19), (19, 3, 19, 7), (19, 3, 19, 19), "alias -> alias:read@19"),
    ((18, 7, 18, 19), (20, 3, 20, 7), (20, 3, 20, 15), "alias -> alias:close@20"),
    ((26, 3, 26, 15), (27, 3, 27, 7), (27, 3, 27, 19), "alias -> alias:read@27"),
    ((26, 3, 26, 15), (28, 3, 28, 7), (28, 3, 28, 15), "alias -> alias:close@28"),
    ((32, 7, 32, 35), (34, 3, 34, 7), (34, 3, 34, 19), "fd -> alias:read@34"),
    ((33, 7, 33, 16), (34, 3, 34, 7), (34, 3, 34, 19), "alias -> alias:read@34"),
    ((35, 3, 35, 15), (36, 3, 36, 7), (36, 3, 36, 15), "alias -> alias:close@36"),
    ((17, 30, 17, 34), (19, 3, 19, 7), (19, 3, 19, 19), "other -> alias:read@19"),
    ((17, 30, 17, 34), (20, 3, 20, 7), (20, 3, 20, 15), "other -> alias:close@20"),
    ((23, 32, 23, 36), (27, 3, 27, 7), (27, 3, 27, 19), "other -> alias:read@27"),
    ((23, 32, 23, 36), (28, 3, 28, 7), (28, 3, 28, 15), "other -> alias:close@28"),
    ((31, 31, 31, 35), (36, 3, 36, 7), (36, 3, 36, 15), "other -> alias:close@36"),
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
    require(FIXTURE.is_file() and QUERY.is_file(), "fixture or query missing")
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
    tuples = query(codeql, db, search, work, QUERY, "receiver-alias")
    actual = []
    for row in tuples:
        entities = [decode_entity(entity, source) for entity in row[:3]]
        require(all(name == FIXTURE.name for name, _ in entities), f"wrong file identity: {entities}")
        actual.append(tuple(coords for _, coords in entities) + (row[3],))
    expected = EXPECTED
    require(collections.Counter(actual) == collections.Counter(expected),
            f"exact receiver witnesses mismatch: missing={collections.Counter(expected)-collections.Counter(actual)} "
            f"extra={collections.Counter(actual)-collections.Counter(expected)}")
    print(f"PASS exact selected files={len(actual_files)}, extraction errors=0, exact receiver rows={len(actual)}")


if __name__ == "__main__":
    main()
