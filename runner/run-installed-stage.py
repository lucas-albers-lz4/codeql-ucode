#!/usr/bin/env python3
"""Run the bundled ucode producer on a pinned, installation-shaped stage."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(value: str) -> Path:
    require(isinstance(value, str) and value != "" and "\\" not in value,
            f"invalid stage path: {value!r}")
    posix = PurePosixPath(value)
    require(not posix.is_absolute() and posix.as_posix() == value and
            all(part not in {".", ".."} for part in posix.parts),
            f"invalid stage path: {value!r}")
    return Path(*posix.parts)


def load_oracle(path: Path, stage: Path) -> dict:
    oracle = json.loads(path.read_text(encoding="utf-8"))
    require(oracle.get("schema") == "ucode-installed-stage-v1", "unknown stage oracle schema")
    entries = oracle.get("files")
    require(isinstance(entries, list) and entries, "stage oracle needs files")
    actual = set()
    for source in stage.rglob("*"):
        require(not source.is_symlink(), f"stage symlink is unsupported: {source}")
        require(source.is_dir() or source.is_file(), f"special stage file is unsupported: {source}")
        if source.is_file():
            actual.add(source.relative_to(stage).as_posix())
    seen: set[str] = set()
    for entry in entries:
        require(isinstance(entry, dict), "invalid stage entry")
        rel = entry.get("path")
        parsed = relative_path(rel)
        require(rel not in seen, f"duplicate stage path: {rel}")
        seen.add(rel)
        require(re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")) is not None,
                f"invalid stage digest: {rel}")
        require(type(entry.get("expect_success")) is bool, f"missing success expectation: {rel}")
        route = entry.get("route")
        require(isinstance(route, dict) and set(route) ==
                {"classification", "reason", "status", "inconclusive_reason"},
                f"incomplete route expectation: {rel}")
        require(all(v is None or isinstance(v, str) for v in route.values()),
                f"invalid route expectation: {rel}")
        source = stage / parsed
        require(source.is_file() and not source.is_symlink(), f"missing regular stage file: {rel}")
        require(sha256(source) == entry["sha256"], f"stage digest mismatch: {rel}")
    require(actual == seen, f"stage file inventory mismatch: missing={sorted(seen-actual)} extra={sorted(actual-seen)}")
    return oracle


def verify_bundle(bundle: Path, manifest: dict) -> None:
    files = manifest.get("files")
    require(isinstance(files, list), "bundle file manifest missing")
    expected: set[str] = set()
    for entry in files:
        rel = entry.get("path")
        target = bundle / relative_path(rel)
        require(rel not in expected and target.is_file() and not target.is_symlink(),
                f"missing or duplicate bundle member: {rel}")
        expected.add(rel)
        require(sha256(target) == entry.get("sha256") and
                target.stat().st_size == entry.get("bytes") and
                target.stat().st_mode & 0o777 == entry.get("mode"),
                f"bundle member differs from manifest: {rel}")
    expected.add("bundle-manifest.json")
    actual: set[str] = set()
    for target in bundle.rglob("*"):
        require(not target.is_symlink(), f"bundle symlink is unsupported: {target}")
        require(target.is_file() or target.is_dir(), f"bundle special member is unsupported: {target}")
        if target.is_file():
            actual.add(target.relative_to(bundle).as_posix())
    require(actual == expected, f"bundle membership mismatch: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")


def file_uri_relative(uri: str, stage: Path) -> str:
    parsed = urlsplit(uri)
    require(parsed.scheme == "file" and parsed.netloc in {"", "localhost"}, f"unexpected file URI: {uri}")
    path = Path(unquote(parsed.path)).resolve(strict=True)
    try:
        return path.relative_to(stage).as_posix()
    except ValueError as error:
        raise ValueError(f"file URI is outside stage: {uri}") from error


class Run:
    def __init__(self, root: Path, codeql: Path, bundle: Path, stage: Path):
        require(not root.exists(), f"run output already exists: {root}")
        root.mkdir(parents=True)
        self.root, self.codeql, self.stage = root, codeql, stage
        self.bundle = root / "bundle"
        shutil.copytree(bundle, self.bundle)
        for name in ("home", "tmp", "cache", "output"):
            (root / name).mkdir()
        self.commands: list[dict] = []

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(HOME=str(self.root / "home"), TMPDIR=str(self.root / "tmp"),
                   CODEQL_UCODE_STAGED_ROOT=str(self.stage))
        return env

    def call(self, label: str, args: list[str | Path], *, capture: bool = False) -> str:
        argv = [str(a) for a in args]
        start = time.monotonic()
        timed = sys.platform == "linux" and Path("/usr/bin/time").is_file()
        time_file = self.root / "output" / f"{label}.time"
        command = ["/usr/bin/time", "-v", "-o", str(time_file), *argv] if timed else argv
        result = subprocess.run(command, cwd=self.bundle, env=self.env(),
                                capture_output=True, text=True, check=False)
        record = {"label": label, "argv": argv, "exit_status": result.returncode,
                  "elapsed_seconds": round(time.monotonic() - start, 3),
                  "stdout": f"output/{label}.stdout", "stderr": f"output/{label}.stderr"}
        if timed:
            match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", time_file.read_text())
            record["peak_rss_kb"] = int(match.group(1)) if match else None
            record["time_report"] = f"output/{label}.time"
        else:
            record["peak_rss_kb"] = None
        (self.root / record["stdout"]).write_text(result.stdout)
        (self.root / record["stderr"]).write_text(result.stderr)
        self.commands.append(record)
        require(result.returncode == 0, f"{label} failed with status {result.returncode}")
        invalid = [line for line in result.stderr.splitlines() if "WARNING:" in line and
                   not re.search(r"Not caching stages during query-loading, since max heap size is only \d+ MB", line)]
        require(not invalid, f"{label} emitted CodeQL warnings: {invalid}")
        return result.stdout if capture else ""

    def codeql_call(self, label: str, *args: str | Path, capture: bool = False) -> str:
        return self.call(label, [self.codeql, *args], capture=capture)


def check_route(path: Path, stage: Path, oracle: dict) -> dict:
    receipt = json.loads(path.read_text())
    actual = receipt.get("decisions")
    require(isinstance(actual, list), "routing decisions missing")
    expected = {e["path"]: e for e in oracle["files"]}
    require(receipt.get("input_count") == len(expected) and
            receipt.get("duplicate_input_count") == 0 and len(actual) == len(expected),
            "routing count or duplicate mismatch")
    observed = Counter()
    for decision in actual:
        rel = decision.get("installed_path")
        require(rel in expected, f"unexpected routed file: {rel}")
        observed[rel] += 1
        require(decision.get("path") == str(stage / relative_path(rel)),
                f"route source identity mismatch: {rel}")
        for key, value in expected[rel]["route"].items():
            require(decision.get(key) == value, f"route {key} mismatch: {rel}")
    require(observed == Counter(expected.keys()), f"route multiset mismatch: {observed}")
    return receipt


def query_rows(run: Run, database: Path, name: str, query: Path, search_path: str) -> list:
    bqrs = run.root / "output" / f"{name}.bqrs"
    common = run.root / "cache" / "queries"
    common.mkdir(exist_ok=True)
    compile_cache = run.root / "cache" / "compile"
    compile_cache.mkdir(exist_ok=True)
    run.codeql_call(f"{name}-query", "query", "run", query, f"--database={database}",
                    f"--search-path={search_path}", f"--common-caches={common}",
                    f"--compilation-cache={compile_cache}", "--no-default-compilation-cache",
                    f"--output={bqrs}", "--threads=1", "--ram=2048")
    decoded = run.codeql_call(f"{name}-decode", "bqrs", "decode", "--format=json",
                              "--entities=url,string", bqrs, capture=True)
    (run.root / "output" / f"{name}.json").write_text(decoded)
    return json.loads(decoded)["#select"]["tuples"]


def check_sarif(path: Path, stage: Path) -> dict:
    sarif = json.loads(path.read_text())
    require(sarif.get("version") == "2.1.0" and len(sarif.get("runs", [])) == 1,
            "invalid SARIF envelope")
    run = sarif["runs"][0]
    rules = run.get("tool", {}).get("driver", {}).get("rules")
    require(isinstance(rules, list),
            "SARIF rule descriptors missing")
    rule_ids = [rule.get("id") for rule in rules]
    require(all(isinstance(rule_id, str) and rule_id for rule_id in rule_ids) and
            len(set(rule_ids)) == len(rule_ids), "SARIF rule descriptors invalid")
    results = run.get("results")
    require(isinstance(results, list), "SARIF results missing")
    for result in results:
        require(result.get("ruleId") in rule_ids and isinstance(result.get("locations"), list) and
                result["locations"],
                "SARIF result lacks rule or location")
        for loc in result["locations"]:
            physical = loc["physicalLocation"]
            uri = physical["artifactLocation"]["uri"]
            require(isinstance(uri, str), "SARIF location URI missing")
            if uri.startswith("file:"):
                file_uri_relative(uri, stage)
            else:
                rel = relative_path(uri)
                require((stage / rel).is_file(), f"SARIF location outside staged files: {uri}")
            region = physical["region"]
            require(type(region.get("startLine")) is int and region["startLine"] > 0,
                    "SARIF result has invalid range")
    return {"sha256": sha256(path), "rule_ids": sorted(rule_ids),
            "result_count": len(results)}


def execute(args: argparse.Namespace) -> dict:
    bundle = args.bundle.resolve(strict=True)
    stage = args.stage.resolve(strict=True)
    codeql = args.codeql.resolve(strict=True)
    require(bundle.is_dir() and stage.is_dir() and codeql.is_file(), "bundle, stage or CLI missing")
    oracle = load_oracle(args.oracle, stage)  # independent source expectation precedes output
    manifest = json.loads((bundle / "bundle-manifest.json").read_text())
    require(manifest.get("schema_version") == 1 and manifest.get("source_checkout_clean") is True,
            "unverified bundle manifest")
    require(args.bundle_sha256 == sha256(bundle / "bundle-manifest.json"),
            "bundle manifest digest does not match consumer pin")
    verify_bundle(bundle, manifest)
    run = Run(args.output.resolve(), codeql, bundle, stage)
    try:
        version = run.codeql_call("codeql-version", "version", capture=True)
        require(manifest["build"]["codeql_cli_version"] in version, "CodeQL version mismatch")
        locks = {rel: sha256(run.bundle / rel) for rel in
                 ("ql/lib/codeql-pack.lock.yml", "ql/src/codeql-pack.lock.yml")}
        for pack in ("ql/lib", "ql/src"):
            run.codeql_call(f"install-{pack.replace('/', '-')}", "pack", "install", run.bundle / pack)
        require(locks == {rel: sha256(run.bundle / rel) for rel in locks}, "QL lock changed during install")
        installed = run.root / "home/.codeql/packages"
        require(installed.is_dir(), "locked QL dependencies were not installed")
        for cache in (run.root / "cache/queries", run.root / "cache/database"):
            cache.mkdir(exist_ok=True)
            shutil.copytree(installed, cache / "packages")
        extractor = run.bundle / "extractor-pack"
        src = run.bundle / "ql/src"
        sp = ":".join(str(run.bundle / p) for p in ("extractor-pack", "ql/lib", "ql/src"))
        suite = src / "codeql-suites/code-scanning.qls"
        resolved = run.codeql_call("resolve-suite", "resolve", "queries", "--format=json",
                                   suite, f"--search-path={sp}", capture=True)
        (run.root / "output/resolved-suite.json").write_text(resolved)
        queries = sorted(Path(p).name for p in json.loads(resolved))
        require("SuccessfullyExtractedFiles.ql" in queries and "ExtractionErrors.ql" in queries,
                "default suite lacks extraction diagnostics")
        db = run.root / "database"
        common = run.root / "cache/database"
        common.mkdir(exist_ok=True)
        run.codeql_call("database-init", "database", "init", db, "--language=ucode",
                        f"--search-path={extractor}", f"--common-caches={common}",
                        f"--source-root={stage}")
        run.codeql_call("database-index", "database", "index-files", "--language=ucode",
                        "--include=**/*", f"--working-dir={stage}", f"--common-caches={common}", db)
        route_path = db / "trap/ucode/routing.json"
        route = check_route(route_path, stage, oracle)
        shutil.copy2(route_path, run.root / "output/routing.json")
        run.codeql_call("database-finalize", "database", "finalize", db,
                        f"--common-caches={common}")
        success = query_rows(run, db, "success", src / "diagnostics/SuccessfullyExtractedFiles.ql", sp)
        errors = query_rows(run, db, "errors", src / "diagnostics/ExtractionErrors.ql", sp)
        got = Counter(file_uri_relative(row[0]["url"]["uri"], stage) for row in success)
        want = Counter(e["path"] for e in oracle["files"] if e["expect_success"])
        require(got == want, f"successful-file multiset mismatch: got={got} want={want}")
        require(not errors, f"unexpected extraction errors: {errors}")
        sarif = run.root / "output/default-suite.sarif"
        query_cache = run.root / "cache/queries"
        compile_cache = run.root / "cache/compile"
        run.codeql_call("default-suite-analyze", "database", "analyze", db, suite,
                        "--format=sarifv2.1.0", f"--output={sarif}", f"--search-path={sp}",
                        f"--common-caches={query_cache}", f"--compilation-cache={compile_cache}",
                        "--no-default-compilation-cache", "--threads=1", "--ram=2048")
        sarif_summary = check_sarif(sarif, stage)
        require({e["path"]: sha256(stage / e["path"]) for e in oracle["files"]} ==
                {e["path"]: e["sha256"] for e in oracle["files"]}, "source bytes changed during run")
        return {"schema": "ucode-installed-stage-receipt-v1",
                "bundle_manifest_sha256": args.bundle_sha256,
                "producer_commit": manifest["producer_commit"], "release_tag": manifest["release_tag"],
                "codeql_version": version.strip(), "oracle_sha256": sha256(args.oracle),
                "stage_files": {e["path"]: e["sha256"] for e in oracle["files"]},
                "routing_sha256": sha256(run.root / "output/routing.json"),
                "successful_files": dict(sorted(got.items())), "extraction_errors": errors,
                "resolved_queries": queries, "resolved_suite_sha256": sha256(run.root / "output/resolved-suite.json"),
                "sarif": sarif_summary, "commands": run.commands}
    finally:
        (run.root / "commands.json").write_text(json.dumps(run.commands, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "stage", "oracle", "codeql", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--bundle-sha256", required=True,
                        help="independently pinned SHA-256 of bundle-manifest.json")
    args = parser.parse_args()
    try:
        receipt = execute(args)
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    except Exception as error:
        print(f"installed-stage run failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
