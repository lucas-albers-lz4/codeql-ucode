#!/usr/bin/env python3
"""Run the exact Models fs.popen attribution and consumer regression gates."""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CODEQL = shutil.which("codeql")
assert CODEQL is not None, "codeql CLI must be on PATH"
PACK = ROOT / "extractor-pack"
QLPATH = os.pathsep.join((str(PACK), str(ROOT / "ql/lib"), str(ROOT / "ql/src")))
CORPUS = ROOT / "ql/test/models-fs-popen-controls"
EFFECTS = ROOT / "ql/test/effect-controls/getblock"
DB = ROOT / ".codeql-database/m4-models-fs-popen"
EXPECTED_CALLS = json.loads((CORPUS / "proposed-targets.json").read_text())["targets"]
RAW_MANIFEST = json.loads((CORPUS / "raw-entity-manifest.json").read_text())
INPUTS = json.loads((CORPUS / "final-input-manifest.json").read_text())
BASELINE = json.loads((CORPUS / "pinned-production-baseline.json").read_text())
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
    result = command([CODEQL, "bqrs", "decode", f"--format={fmt}", bqrs])
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


def projected(value: object) -> object:
    if isinstance(value, dict):
        if "entity" in value and "label" in value:
            return {"label": value["label"]}
        return {key: projected(item) for key, item in value.items()}
    if isinstance(value, list):
        return [projected(item) for item in value]
    return value


def expected_consumer_projection(rows: list[list[object]]) -> list[list[object]]:
    return [[projected(cell) for cell in row] for row in rows]


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
    require(len(indexed) == 83 and len(support) == 8 and indexed.isdisjoint(support), "unexpected committed fixture manifest shape")

    shutil.rmtree(DB, ignore_errors=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    command([CODEQL, "database", "init", DB, "--language=ucode", f"--search-path={PACK}", f"--source-root={source}"])
    command([CODEQL, "database", "index-files", "--language=ucode", "--include=**/*.uc", "--include=**/rpcd/ucode/luci", f"--working-dir={source}", DB])

    routing_path = DB / "trap/ucode/routing.json"
    require(routing_path.is_file(), "missing live extractor routing diagnostics")
    routing = json.loads(routing_path.read_text())
    decisions = routing["decisions"]
    routed = [Path(item["path"]).relative_to(source).as_posix() for item in decisions]
    require((routing["input_count"], routing["plain_count"], routing["excluded_count"], routing["duplicate_input_count"]) == (83, 83, 0, 0), f"unexpected routing counters: {routing}")
    require(len(set(routed)) == 83 and set(routed) == indexed, "routing decisions do not exactly match indexed input manifest")
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
    require(sum(status == "ok" for status in observed_files.values()) == 82, "expected exactly 82 successful extractions")

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
    require(len(raw) == 529, f"expected 529 raw call entities, got {len(raw)}")
    require(collections.Counter(raw) == collections.Counter(tuple(row) for row in RAW_MANIFEST), "raw call identities differ from frozen full-span inventory")
    expected_targets = {tuple(row) for row in EXPECTED_CALLS}
    require(classified == expected_targets, f"NamedFsPopenCall exact-target mismatch: missing={sorted(expected_targets-classified)} extra={sorted(classified-expected_targets)}")
    require(any(row[0] == "malformed.uc" and row[5] == "popen" for row in raw), "malformed recovered prefix call is absent from actual query output")
    require(not (OBSERVATIONS & {name for name, status in observed_files.items() if status == "error"}), "synthetic observation unexpectedly failed extraction")

    named = tuples(run_query(ROOT / "ql/src/m3/NamedFsPopen.ql", DB, out, "named-fs-popen"))
    require(len(named) == len(expected_targets) and all(row[0] == {"label": "CallExpression"} for row in named), "actual NamedFsPopen query does not select exactly 21 call entities")

    consumers = {
        "local-taint": ROOT / "ql/src/m3/LocalTaint.ql",
        "request-args": ROOT / "ql/src/m4/RequestArgsExec.ql",
        "shell-injection": ROOT / "ql/src/m4/ShellInjection.ql",
    }
    for key, query in consumers.items():
        actual = tuples(run_query(query, DB, out, key))
        expected = expected_consumer_projection(BASELINE[key])
        require(collections.Counter(map(json.dumps, actual)) == collections.Counter(map(json.dumps, expected)), f"{key} consumer rows changed or include synthetic observations: got={len(actual)} expected={len(expected)}")
        require(not any(any(path in json.dumps(row) for path in OBSERVATIONS) for row in actual), f"{key} contains a synthetic observation row")
        print(f"PASS {key}: {len(actual)} pinned rows; no observation_* rows")

    # Fault controls use the same exact target/type oracle against real BQRS.
    def expect_rejected(query: Path, name: str) -> None:
        candidate = tuples(run_query(query, DB, out, name))
        if len(candidate) == len(expected_targets) and all(row and row[0] == {"label": "CallExpression"} for row in candidate):
            raise SystemExit(f"{name} mutation unexpectedly passed candidate identity oracle")
        print(f"PASS {name}: actual query output rejected by exact candidate oracle")

    expect_rejected(ROOT / "ql/src/extractor-smoke/ModelsFsPopenNoTargets.ql", "models-no-targets")
    expect_rejected(ROOT / "ql/src/extractor-smoke/ModelsFsPopenWrongEntity.ql", "models-wrong-entity")

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
        '''  exists(UCODE::ImportStatement imp |
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
            ("negative-member", 4, 5, 47),
        )
    }
    require(mutant_ids - expected == bad, f"legacy effect predicate produced unexpected mutation rows: {mutant_ids-expected}")
    print("PASS effect-query rollback: old import-only predicate adds exact formal/local/member/escape rows")


def main() -> None:

    require((PACK / "tools/linux64/extractor").is_file(), "extractor-pack is missing; run scripts/create-extractor-pack.sh first")
    temp_parent = Path(os.environ.get("CODEQL_UCODE_SMOKE_TMPDIR", tempfile.gettempdir()))
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="models-fs-popen-", dir=temp_parent) as temp:
        temp_root = Path(temp)
        run_model_database(temp_root)
        run_effect_database(temp_root)
    print("PASS Models fs.popen exact attribution, consumer baselines, and rollback mutations")


if __name__ == "__main__":
    main()
