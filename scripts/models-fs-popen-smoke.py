#!/usr/bin/env python3
"""Run the exact Models fs.popen attribution and consumer regression gates."""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import platform
import sys
import tempfile
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CODEQL = shutil.which("codeql")
PACK = ROOT / "extractor-pack"
QLPATH = os.pathsep.join((str(PACK), str(ROOT / "ql/lib"), str(ROOT / "ql/src")))
CORPUS = ROOT / "ql/test/models-fs-popen-controls"
EFFECTS = ROOT / "ql/test/effect-controls/getblock"
DB = ROOT / ".codeql-database/m4-models-fs-popen"
EXPECTED_CALLS = json.loads((CORPUS / "proposed-targets.json").read_text())["targets"]
RAW_MANIFEST = json.loads((CORPUS / "raw-entity-manifest.json").read_text())
INPUTS = json.loads((CORPUS / "final-input-manifest.json").read_text())
BASELINE_BYTES = (CORPUS / "pinned-production-baseline.json").read_bytes()
BASELINE_DIGEST = "ace8f6ff871c3261992c9088d4065c2fdf9e5e77d391f34447fb5ebb254fa4ac"
BASELINE = json.loads(BASELINE_BYTES)
OBSERVATIONS = {
    "observation_formal/usr/share/rpcd/ucode/luci",
    "observation_lexical/usr/share/rpcd/ucode/luci",
    "observation_wrong_module/usr/share/rpcd/ucode/luci",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def command(args: list[str | Path], *, cwd: Path = ROOT, expect: int = 0) -> subprocess.CompletedProcess[str]:
    argv = [str(x) for x in args]
    result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != expect:
        raise SystemExit(f"command exit {result.returncode} (expected {expect}): {' '.join(argv)}\n{result.stdout[-5000:]}")
    return result


def decode(bqrs: Path, fmt: str) -> Any:
    args = [CODEQL, "bqrs", "decode", f"--format={fmt}"]
    if fmt == "json":
        args.append("--entities=url,string")
    result = command([*args, bqrs])
    if fmt == "json":
        return json.loads(result.stdout)
    return list(csv.reader(result.stdout.splitlines()))


def run_query(query: Path, database: Path, output_dir: Path, name: str, *, search_path: str = QLPATH) -> object:
    bqrs = output_dir / f"{name}.bqrs"
    command([CODEQL, "query", "run", query, f"--database={database}", f"--search-path={search_path}", f"--output={bqrs}"])
    return decode(bqrs, "json")


def tuples(result: Any) -> list[list[Any]]:
    require(isinstance(result, dict) and "#select" in result, "expected a #select BQRS result")
    return result["#select"]["tuples"]


def normalize_rows(rows: list[list[Any]], source: Path) -> list[list[Any]]:
    """Normalize only decoded entity cells, never ordinary domain strings."""
    def normalize(cell: Any) -> Any:
        if not isinstance(cell, dict):
            return cell
        require(set(cell) == {"label", "url"} and isinstance(cell["url"], dict), f"invalid entity: {cell}")
        url = cell["url"]
        require(set(url) == {"uri", "startLine", "startColumn", "endLine", "endColumn"}, f"invalid entity URL: {url}")
        parsed = urlsplit(url["uri"])
        require(parsed.scheme == "file" and not parsed.netloc and not parsed.query and not parsed.fragment, f"invalid entity URI: {url['uri']}")
        require(not re.search(r"%(?![0-9a-fA-F]{2})", parsed.path), f"invalid URI escape: {url['uri']}")
        try:
            decoded_path = unquote(parsed.path, errors="strict")
            require("\x00" not in decoded_path, f"invalid entity path: {url['uri']}")
            path = Path(decoded_path)
            require(path.is_absolute() and ".." not in path.parts, f"invalid entity path: {path}")
            relative = path.relative_to(source)
        except (ValueError, UnicodeError) as error:
            raise SystemExit(f"entity outside staged source root: {url['uri']}: {error}") from error
        coords = [url[k] for k in ("startLine", "startColumn", "endLine", "endColumn")]
        require(all(type(n) is int and n > 0 for n in coords) and tuple(coords[:2]) <= tuple(coords[2:]), f"invalid entity span: {url}")
        return {"label": cell["label"], "entity": [relative.as_posix(), *coords]}
    return [[normalize(cell) for cell in row] for row in rows]


def row_counter(rows: list[list[Any]]) -> collections.Counter[str]:
    return collections.Counter(json.dumps(row, sort_keys=True) for row in rows)


def named_oracle(rows: list[list[Any]], expected: set[tuple[Any, ...]]) -> None:
    require(all(len(row) >= 1 and isinstance(row[0], dict) and row[0].get("label") == "CallExpression" and "entity" in row[0] for row in rows), "NamedFsPopen returned a non-call entity")
    observed = collections.Counter(tuple(row[0]["entity"]) for row in rows)
    require(observed == collections.Counter(expected), f"NamedFsPopen exact entity mismatch: missing={collections.Counter(expected)-observed} extra={observed-collections.Counter(expected)}")


def consumer_oracle(key: str, actual: list[list[Any]], expected: list[list[Any]]) -> None:
    require(row_counter(actual) == row_counter(expected), f"{key} exact consumer rows changed: missing={row_counter(expected)-row_counter(actual)} extra={row_counter(actual)-row_counter(expected)}")


def identity_fault_controls(temp_root: Path, source: Path, out: Path,
                            expected_targets: set[tuple[Any, ...]], consumers: dict[str, Path]) -> None:
    """Run Sol's count-preserving faults as actual queries, through the same oracles."""
    pack = temp_root / "identity-fault-pack"
    (pack / "ql").mkdir(parents=True)
    shutil.copyfile(ROOT / ".codeqlmanifest.json", pack / ".codeqlmanifest.json")
    shutil.copytree(ROOT / "ql/lib", pack / "ql/lib")
    shutil.copytree(ROOT / "ql/src", pack / "ql/src")
    search = os.pathsep.join((str(PACK), str(pack / "ql/lib"), str(pack / "ql/src")))

    def replace_once(text: str, old: str, new: str) -> str:
        require(text.count(old) == 1, f"cannot isolate fault insertion: {old}")
        return text.replace(old, new, 1)

    def query_rows(text: str, name: str) -> list[list[Any]]:
        query = pack / "ql/src/extractor-smoke" / f"{name}.ql"
        query.write_text(text)
        return normalize_rows(tuples(run_query(query, DB, out, name, search_path=search)), source)

    named_text = (ROOT / "ql/src/m3/NamedFsPopen.ql").read_text()
    helper = '''
UCODE::CallExpression reportedCall(NamedFsPopenCall original) {
  if original.getLocation().getFile().getRelativePath() = "direct.uc" then
    result.getLocation().getFile().getRelativePath() = "issue_formal.uc" and
    result.getLocation().getStartLine() = 2 and result.getLocation().getStartColumn() = 32
  else result = original
}
'''
    named_text = replace_once(named_text, "from NamedFsPopenCall c", helper + "\nfrom NamedFsPopenCall c")
    named_text = replace_once(named_text, "select c,", "select reportedCall(c),")
    rows = query_rows(named_text, "fault-named-same-type")
    actual_ids = collections.Counter(tuple(row[0]["entity"]) for row in rows)
    require(len(rows) == len(expected_targets) and all(row[0]["label"] == "CallExpression" for row in rows) and
            actual_ids - collections.Counter(expected_targets) == collections.Counter({("issue_formal.uc", 2, 32, 2, 46): 1}) and
            collections.Counter(expected_targets) - actual_ids == collections.Counter({("direct.uc", 3, 17, 3, 35): 1}), "named mutation did not exercise Sol's exact same-type substitution")
    try:
        named_oracle(rows, expected_targets)
    except SystemExit:
        print("PASS same-type wrong-call query rejected by exact NamedFsPopen oracle")
    else:
        raise SystemExit("same-type wrong-call query unexpectedly passed")

    source_helper = '''
UCODE::AstNode reportedSource(RequestArgsAccess original) {
  if original.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
     original.getLocation().getStartLine() = 108 and original.getLocation().getEndColumn() = 43 then
    result.(RequestArgsAccess).getLocation().getFile().getRelativePath() = "SOURCE_PATH" and
    result.getLocation().getStartLine() = SOURCE_LINE and result.getLocation().getStartColumn() = SOURCE_COL and
    result.getLocation().getEndColumn() = SOURCE_END
  else result = original
}
'''
    sink_helper = '''
UCODE::CallExpression reportedSink(RequestArgsAccess src, NamedCall original) {
  if src.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
     src.getLocation().getStartLine() = 108 and src.getLocation().getEndColumn() = 43 then
    result.getLocation().getFile().getRelativePath() = "SINK_PATH" and
    result.getLocation().getStartLine() = SINK_LINE and result.getLocation().getStartColumn() = SINK_COL
  else result = original
}
'''
    pinned = "usr/share/rpcd/ucode/luci"
    for key, original in consumers.items():
        for mode in ("synthetic-pair", "pinned-pair", "pinned-source", "pinned-sink"):
            synthetic = mode == "synthetic-pair"
            use_source = mode != "pinned-sink"
            use_sink = mode != "pinned-source"
            source_id = ("observation_formal/usr/share/rpcd/ucode/luci", 5, 18, 5, 37) if synthetic else (pinned, 343, 49, 343, 67)
            sink_id = ("issue_formal.uc", 2, 32, 2, 46) if synthetic else (pinned, 26, 12, 26, 75)
            text = original.read_text()
            helpers = ""
            if use_source:
                h = source_helper
                for old, new in (("SOURCE_PATH", source_id[0]), ("SOURCE_LINE", str(source_id[1])), ("SOURCE_COL", str(source_id[2])), ("SOURCE_END", str(source_id[4]))):
                    h = h.replace(old, new)
                helpers += h
                text = replace_once(text, "select src,", "select reportedSource(src),")
            if use_sink:
                h = sink_helper
                for old, new in (("SINK_PATH", sink_id[0]), ("SINK_LINE", str(sink_id[1])), ("SINK_COL", str(sink_id[2]))):
                    h = h.replace(old, new)
                helpers += h
                text, count = re.subn(r"\bsink, sink.getName\(\)", "reportedSink(src, sink), sink.getName()", text)
                require(count == 1, f"cannot isolate sink selection in {original}")
            text = replace_once(text, "from RequestArgsAccess src,", helpers + "\nfrom RequestArgsAccess src,")
            rows = query_rows(text, f"fault-{key}-{mode}")
            expected = BASELINE[key]
            missing, extra = row_counter(expected) - row_counter(rows), row_counter(rows) - row_counter(expected)
            require(len(rows) == len(expected) and sum(missing.values()) == sum(extra.values()) == 1, f"{key} {mode}: fault did not change exactly one row")
            before, after = json.loads(next(iter(missing))), json.loads(next(iter(extra)))
            require(tuple(before[0]["entity"]) == (pinned, 108, 22, 108, 43) and
                    tuple(before[2]["entity"]) == (pinned, 111, 5, 111, 118), f"{key} {mode}: original Sol row not selected")
            require(all(before[i] == after[i] for i in range(len(before)) if i not in (0, 2)), f"{key} {mode}: scalar changed")
            for i, changed, target in ((0, use_source, source_id), (2, use_sink, sink_id)):
                require(before[i]["label"] == after[i]["label"] and
                        (tuple(after[i]["entity"]) == target if changed else before[i] == after[i]), f"{key} {mode}: wrong fault entity at column {i}")
            try:
                consumer_oracle(key, rows, expected)
            except SystemExit:
                print(f"PASS {key} {mode}: actual count-preserving query rejected by exact consumer oracle")
            else:
                raise SystemExit(f"{key} {mode}: wrong entities unexpectedly accepted")


def run_model_database(temp_root: Path) -> None:
    source = temp_root / "source/ql/test/extractor-smoke"
    for entry in INPUTS:
        src = CORPUS / entry["file"]
        dst = source / entry["file"]
        require(hashlib.sha256(src.read_bytes()).hexdigest() == entry["sha256"], f"committed input hash mismatch: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        require(hashlib.sha256(dst.read_bytes()).hexdigest() == entry["sha256"], f"staged input hash mismatch: {dst}")

    indexed = {entry["file"] for entry in INPUTS if entry["role"] == "indexed"}
    support = {entry["file"] for entry in INPUTS if entry["role"] == "runtime-module-support"}
    require(len(indexed) == 84 and len(support) == 8 and indexed.isdisjoint(support), "unexpected committed fixture manifest shape")

    shutil.rmtree(DB, ignore_errors=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    command([CODEQL, "database", "init", DB, "--language=ucode", f"--search-path={PACK}", f"--source-root={source}"])
    command([CODEQL, "database", "index-files", "--language=ucode", "--include=**/*.uc", "--include=**/rpcd/ucode/luci", f"--working-dir={source}", DB])

    routing_path = DB / "trap/ucode/routing.json"
    require(routing_path.is_file(), "missing live extractor routing diagnostics")
    routing = json.loads(routing_path.read_text())
    decisions = routing["decisions"]
    routed = [Path(item["path"]).relative_to(source).as_posix() for item in decisions]
    require((routing["input_count"], routing["plain_count"], routing["excluded_count"], routing["duplicate_input_count"]) == (84, 84, 0, 0), f"unexpected routing counters: {routing}")
    require(len(set(routed)) == 84 and set(routed) == indexed, "routing decisions do not exactly match indexed input manifest")
    require(all(item["classification"] == "plain" and item["status"] == "plain_route_selected" for item in decisions), "unexpected or failed extractor route")

    command([CODEQL, "database", "finalize", DB])
    out = DB / "models-fs-popen-evidence"
    out.mkdir()

    run_query(ROOT / "ql/src/extractor-smoke/ModelsFsPopenFileInventory.ql", DB, out, "file-inventory")
    file_rows = decode(out / "file-inventory.bqrs", "csv")
    require(file_rows, "empty extracted-file inventory")
    observed_files = {row[0]: row[1] for row in file_rows[1:]}
    expected_errors = {"malformed.uc"}
    require(set(observed_files) == indexed, f"extracted file set mismatch: missing={sorted(indexed-set(observed_files))} extra={sorted(set(observed_files)-indexed)}")
    require({name for name, status in observed_files.items() if status == "error"} == expected_errors, f"unexpected extracted-file errors: {observed_files}")
    require(sum(status == "ok" for status in observed_files.values()) == 83, "expected exactly 83 successful extractions")

    raw_query = ROOT / "ql/src/extractor-smoke/ModelsFsPopenRawCalls.ql"
    raw_bqrs = out / "raw-calls.bqrs"
    command([CODEQL, "query", "run", raw_query, f"--database={DB}", f"--search-path={QLPATH}", f"--output={raw_bqrs}"])
    rows = decode(raw_bqrs, "csv")
    raw = []
    classified = set()
    for row in rows[1:]:
        # RawCalls selects c, callee, classification, path, and full inclusive span.
        _, callee, classification, path, sl, sc, el, ec = row
        identity = (path, int(sl), int(sc), int(el), int(ec))
        raw.append((*identity, callee))
        if classification == "named-fs-popen":
            classified.add(identity)
    require(len(raw) == 530, f"expected 530 raw call entities, got {len(raw)}")
    require(collections.Counter(raw) == collections.Counter(tuple(row) for row in RAW_MANIFEST), "raw call identities differ from frozen full-span inventory")
    expected_targets = {tuple(row) for row in EXPECTED_CALLS}
    require(classified == expected_targets, f"NamedFsPopenCall exact-target mismatch: missing={sorted(expected_targets-classified)} extra={sorted(classified-expected_targets)}")
    require(("arrow_unshadowed.uc", 2, 15, 2, 33) in classified, "unshadowed expression-bodied arrow target missing")
    print("PASS unshadowed expression-bodied arrow: exact target arrow_unshadowed.uc:2:15-2:33")
    require(any(row[0] == "malformed.uc" and row[5] == "popen" for row in raw), "malformed recovered prefix call is absent from actual query output")
    require(not (OBSERVATIONS & {name for name, status in observed_files.items() if status == "error"}), "synthetic observation unexpectedly failed extraction")

    named = normalize_rows(tuples(run_query(ROOT / "ql/src/m3/NamedFsPopen.ql", DB, out, "named-fs-popen")), source)
    named_oracle(named, expected_targets)

    consumers = {
        "local-taint": ROOT / "ql/src/m3/LocalTaint.ql",
        "request-args": ROOT / "ql/src/m4/RequestArgsExec.ql",
        "shell-injection": ROOT / "ql/src/m4/ShellInjection.ql",
    }
    for key, query in consumers.items():
        actual = normalize_rows(tuples(run_query(query, DB, out, key)), source)
        consumer_oracle(key, actual, BASELINE[key])
        require(not any(cell["entity"][0] in OBSERVATIONS for row in actual for cell in row if isinstance(cell, dict)), f"{key} contains a synthetic observation entity")
        print(f"PASS {key}: {len(actual)} pinned rows; no observation_* rows")

    # Fault controls use the same exact target/type oracle against real BQRS.
    def expect_rejected(query: Path, name: str) -> None:
        candidate = normalize_rows(tuples(run_query(query, DB, out, name)), source)
        try:
            named_oracle(candidate, expected_targets)
        except SystemExit:
            pass
        else:
            raise SystemExit(f"{name} mutation unexpectedly passed exact candidate oracle")
        print(f"PASS {name}: actual query output rejected by exact candidate oracle")

    expect_rejected(ROOT / "ql/src/extractor-smoke/ModelsFsPopenNoTargets.ql", "models-no-targets")
    expect_rejected(ROOT / "ql/src/extractor-smoke/ModelsFsPopenWrongEntity.ql", "models-wrong-entity")
    identity_fault_controls(temp_root, source, out, expected_targets, consumers)

    # Revert only the Models constructor to its pre-fix same-file import matcher.
    mutant = temp_root / "legacy-pack"
    (mutant / "ql").mkdir(parents=True)
    shutil.copyfile(ROOT / ".codeqlmanifest.json", mutant / ".codeqlmanifest.json")
    shutil.copytree(ROOT / "ql/lib", mutant / "ql/lib")
    shutil.copytree(ROOT / "ql/src", mutant / "ql/src")
    models = mutant / "ql/lib/codeql/ucode/m3/Models.qll"
    source_text = models.read_text()
    fixed = 'this.getName() = "popen" and\n    sourceDeclaredFsCall(this, "popen")'
    legacy = '''this.getName() = "popen" and
    exists(UCODE::ImportStatement imp |
      imp.getLocation().getFile() = this.getLocation().getFile() and
      namedImport(imp, "fs", "popen")
    )'''
    require(source_text.count(fixed) == 1, "cannot isolate Models-only legacy matcher mutation")
    models.write_text(source_text.replace(fixed, legacy))
    mutant_path = os.pathsep.join((str(PACK), str(mutant / "ql/lib"), str(mutant / "ql/src")))
    mutant_raw_bqrs = out / "legacy-models-raw-calls.bqrs"
    command([CODEQL, "query", "run", mutant / "ql/src/extractor-smoke/ModelsFsPopenRawCalls.ql", f"--database={DB}", f"--search-path={mutant_path}", f"--output={mutant_raw_bqrs}"])
    mutant_raw = decode(mutant_raw_bqrs, "csv")
    mutant_targets = set()
    for row in mutant_raw[1:]:
        if row[2] == "named-fs-popen":
            mutant_targets.add((row[3], int(row[4]), int(row[5]), int(row[6]), int(row[7])))
    wrong_cases = {
        ("issue_formal.uc", 2, 32, 2, 46),
        ("issue_local.uc", 2, 55, 2, 69),
        ("issue_wrong_module.uc", 2, 7, 2, 21),
    }
    require(wrong_cases <= mutant_targets, f"legacy matcher did not reintroduce all three issue examples: {sorted(wrong_cases-mutant_targets)}")
    require(mutant_targets != expected_targets, "Models-only legacy rollback unexpectedly passed exact target oracle")
    mutant_consumer = tuples(run_query(mutant / "ql/src/m3/LocalTaint.ql", DB, out, "legacy-models-local-taint", search_path=mutant_path))
    require(len(mutant_consumer) > len(BASELINE["local-taint"]), "legacy matcher rollback did not reintroduce consumer rows")
    print(f"PASS Models-only legacy rollback: {len(mutant_targets)} target identities (including formal/local/escape regressions) and {len(mutant_consumer)} LocalTaint rows rejected")


def run_effect_database(temp_root: Path) -> None:
    # Keep this outside the explicit ql/test/extractor-smoke fixture root so
    # the extractor maps modules/<name>/root/ to its installed package path.
    source = temp_root / "effect-source"
    fixture = ROOT / "ql/test/extractor-smoke/usr/share/rpcd/ucode/luci"
    expected_pin = "6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e"
    require(hashlib.sha256(fixture.read_bytes()).hexdigest() == expected_pin, "pinned LuCI source hash mismatch")

    cases = {
        "real": fixture,
        "positive": EFFECTS / "positive/usr/share/rpcd/ucode/luci",
        "negative-method": EFFECTS / "negative-method/usr/share/rpcd/ucode/luci",
        "negative-command": EFFECTS / "negative-command/usr/share/rpcd/ucode/luci",
        "negative-member": EFFECTS / "negative-member/usr/share/rpcd/ucode/luci",
        "negative-import": EFFECTS / "negative-import/usr/share/rpcd/ucode/luci",
        "negative-formal-shadow": EFFECTS / "negative-formal-shadow/usr/share/rpcd/ucode/luci",
        "negative-local-shadow": EFFECTS / "negative-local-shadow/usr/share/rpcd/ucode/luci",
        "negative-escaped-module": EFFECTS / "negative-escaped-module/usr/share/rpcd/ucode/luci",
    }
    for case, path in cases.items():
        dst = source / "modules" / case / "root/usr/share/rpcd/ucode/luci"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dst)

    db = ROOT / ".codeql-database/m4-models-fs-popen-effect-controls"
    shutil.rmtree(db, ignore_errors=True)
    command([CODEQL, "database", "init", db, "--language=ucode", f"--search-path={PACK}", f"--source-root={source}"])
    command([CODEQL, "database", "index-files", "--language=ucode", "--include=**/rpcd/ucode/luci", f"--working-dir={source}", db])
    routing = json.loads((db / "trap/ucode/routing.json").read_text())
    require((routing["input_count"], routing["plain_count"], routing["excluded_count"], routing["duplicate_input_count"]) == (9, 9, 0, 0), f"effect control routing mismatch: {routing}")
    command([CODEQL, "database", "finalize", db])
    out = db / "effect-evidence"
    out.mkdir()

    # Routing alone does not prove extraction succeeded. Gate this database
    # independently before consuming any semantic results.
    for diagnostic in ("SuccessfullyExtractedFiles", "ExtractionErrors"):
        result = run_query(ROOT / "ql/src/diagnostics" / f"{diagnostic}.ql", db, out, diagnostic)
        (out / f"{diagnostic}.json").write_text(json.dumps(result))
    selected = [source / "modules" / case / "root/usr/share/rpcd/ucode/luci" for case in cases]
    verdict = subprocess.run([sys.executable, "-B", ROOT / "scripts/m4-smoke-diagnostics.py",
                             out / "SuccessfullyExtractedFiles.json", out / "ExtractionErrors.json", *selected],
                            cwd=ROOT, text=True, capture_output=True)
    require(verdict.returncode == 0, f"effect control extraction rejected: {verdict.stderr}")

    # Confirm the matching raw call entities exist, including all discriminating negatives.
    run_query(ROOT / "ql/src/extractor-smoke/ModelsFsPopenRawCalls.ql", db, out, "raw-effect-calls")
    raw_csv = decode(out / "raw-effect-calls.bqrs", "csv")
    raw_calls = collections.defaultdict(list)
    for row in raw_csv[1:]:
        if row[1] == "popen":
            raw_calls[row[3]].append((int(row[4]), int(row[5]), int(row[6]), int(row[7])))
    for case, expected_line in (("negative-formal-shadow", 4), ("negative-local-shadow", 5), ("negative-escaped-module", 4)):
        rel = f"modules/{case}/root/usr/share/rpcd/ucode/luci"
        lines = (source / rel).read_text().splitlines()
        call = lines[expected_line - 1]
        start = call.index("popen(") + 1
        span = (expected_line, start, expected_line, start + len("popen('/sbin/block info 2>/dev/null')") - 1)
        require(raw_calls.get(rel) == [span], f"expected exact raw popen entity absent/ambiguous for {rel}: {raw_calls.get(rel)} != {[span]}")

    query = ROOT / "ql/src/m4/GetBlockDevicesEffectTable.ql"
    run_query(query, db, out, "effect-table")
    actual = decode(out / "effect-table.bqrs", "csv")
    fields, result_rows = actual[0], actual[1:]
    expected_fields = ["observation_kind", "method", "sink_kind", "command", "source_path", "start_line", "start_column", "end_line", "end_column"]
    require(fields == expected_fields, f"effect table schema changed: {fields}")
    def effect_identity(row: list[str]) -> tuple[object, ...]:
        return (row[4], int(row[5]), int(row[6]), int(row[7]), int(row[8]))
    expected = {
        ("modules/real/root/usr/share/rpcd/ucode/luci", 481, 18, 481, 54),
        ("modules/positive/root/usr/share/rpcd/ucode/luci", 4, 5, 4, 41),
    }
    actual_ids = {effect_identity(row) for row in result_rows}
    def effect_oracle(identities: set[tuple[object, ...]]) -> None:
        require(identities == expected, f"effect exact-row oracle mismatch: missing={sorted(expected-identities)} extra={sorted(identities-expected)}")

    effect_oracle(actual_ids)
    print("PASS effect table: existing real and positive entities preserved; exact shadow/escape calls are absent")

    # Restore only the old import-only condition, then run the unchanged table oracle.
    legacy_pack = temp_root / "legacy-effect"
    (legacy_pack / "ql").mkdir(parents=True)
    shutil.copyfile(ROOT / ".codeqlmanifest.json", legacy_pack / ".codeqlmanifest.json")
    shutil.copytree(ROOT / "ql/lib", legacy_pack / "ql/lib")
    shutil.copytree(ROOT / "ql/src", legacy_pack / "ql/src")
    mutated = legacy_pack / "ql/src/m4/GetBlockDevicesEffectTable.ql"
    query = ROOT / "ql/src/m4/GetBlockDevicesEffectTable.ql"
    old = query.read_text().replace(
        '  c instanceof NamedFsPopenCall and',
        '''  c.getFunction().(UCODE::Identifier).getValue() = "popen" and
  exists(UCODE::ImportStatement imp |
    imp.getLocation().getFile() = c.getLocation().getFile() and
    namedImport(imp, "fs", "popen")
  ) and''',
    )
    require(old != query.read_text(), "cannot isolate legacy effect-query predicate mutation")
    mutated.write_text(old)
    effect_mutant_path = os.pathsep.join((str(PACK), str(legacy_pack / "ql/lib"), str(legacy_pack / "ql/src")))
    run_query(mutated, db, out, "legacy-effect-table", search_path=effect_mutant_path)
    mutant_rows = decode(out / "legacy-effect-table.bqrs", "csv")
    mutant_ids = {effect_identity(row) for row in mutant_rows[1:]}
    try:
        effect_oracle(mutant_ids)
    except SystemExit as expected_failure:
        print(f"PASS unchanged effect-row oracle rejects old predicate: {expected_failure}")
    else:
        raise SystemExit("unchanged effect-row oracle unexpectedly accepted old predicate")
    bad = {
        (f"modules/{case}/root/usr/share/rpcd/ucode/luci", line, start, line, end)
        for case, line, start, end in (
            ("negative-formal-shadow", 4, 5, 41),
            ("negative-local-shadow", 5, 5, 41),
            ("negative-escaped-module", 4, 5, 41),
        )
    }
    require(mutant_ids - expected == bad, f"legacy effect predicate produced unexpected mutation rows: {mutant_ids-expected}")
    print("PASS effect-query rollback: old import-only predicate adds exact formal/local/escape rows")


def main() -> None:

    require(CODEQL is not None, "codeql CLI must be on PATH")
    require(hashlib.sha256(BASELINE_BYTES).hexdigest() == BASELINE_DIGEST, "pinned consumer baseline digest mismatch")
    system = {"Linux": "linux64", "Darwin": "osx64"}.get(platform.system())
    require(system is not None, f"unsupported OS: {platform.system()}")
    require((PACK / "tools" / system / "extractor").is_file(), "extractor-pack is missing; run scripts/create-extractor-pack.sh first")
    temp_parent = Path(os.environ.get("CODEQL_UCODE_SMOKE_TMPDIR", tempfile.gettempdir())).resolve()
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="models-fs-popen-", dir=temp_parent) as temp:
        temp_root = Path(temp)
        run_model_database(temp_root)
        run_effect_database(temp_root)
    print("PASS Models fs.popen exact attribution, consumer baselines, and rollback mutations")


if __name__ == "__main__":
    main()
