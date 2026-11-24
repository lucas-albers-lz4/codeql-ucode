#!/usr/bin/env python3
"""Fresh Linux release gate for the default direct-RPC rule and separate Tailscale regression.

This script is intended for an isolated GitHub Actions runner. It does not
assert package installation or runtime behavior.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODEQL_VERSION = "2.27.4"
CODEQL_ZIP_SHA256 = "393bf92b66596141ec93baf9b483f4a350f3749916c922fed0dd63c67706047"
GRAMMAR_REV = "4a243af329fae2f4ff01e0fc80133cbab8314600"
CARGO_LOCK_SHA256 = "20678c3cbb29632a9369bdb3c735af9ee63c9443879db38847fbda9813aa0a77"
QL_LOCK_SHA256 = "bce2891940f09fcac3337b250707047ba9fd06d307abdbc7cb42c2ed193751a3"
DIRECT_QUERY_SHA256 = "a071facd947a65d3eb48906070cf17ad53d2bd62b54116991437f77fef5e52d8"
DEFAULT_SUITE_SHA256 = "6d343f93e37c309b8461da9fafcf67d089737980d7ac42a5409e75df3bd442e5"
TAILSCALE_MANIFEST_SHA256 = "b1a538d03d60e356ae94cf374a2bfdc9338d81068b9e0a7233ac3bcbf89ac114"
TAILSCALE_QUERY_SHA256 = "136ec48e2f38c0da03d3dd975fcccae348997dbb6e6ec4a014444c42b6e09bfc"
DIRECT_RULE_ID = "ucode/m4/direct-rpc-shell-word"
LUCI_URL = "https://github.com/openwrt/luci.git"
OPENVPN_PARENT = "b45584b4e6068b9b096872dd02494a048d869c36"
OPENVPN_FIXED = "e4ff45ecbc6ad212951815c8c99b2749fbd7de6b"
SWCONFIG_REV = "b2e0be4b46ec0fd43394c081fa7c50657af14011"
OPENVPN_PATH = "protocols/luci-proto-openvpn/root/usr/share/rpcd/ucode/luci.openvpn.uc"
SWCONFIG_PATH = "modules/luci-base/root/usr/share/rpcd/ucode/luci"
SWCONFIG_BLOB = "64caf75c08bc0fa54520a0ef262dfd6f339dc89e"
REAL_INPUTS = {
    "openvpn-parent": {"revision": OPENVPN_PARENT, "path": OPENVPN_PATH,
        "sha256": "051c8162f826683333e11264615806df5ab08415676c0bd098921cb1b05af991",
        "blob": "da389170328212f8f0a3b7bea42be11d42bd0c38", "rule_count": 1,
        "location": ("usr/share/rpcd/ucode/luci.openvpn.uc", 71, 115, 132)},
    "openvpn-fixed": {"revision": OPENVPN_FIXED, "path": OPENVPN_PATH,
        "sha256": "6593792678951fd500c2b090d17d9e500a05a642cfb996ee02c1649473152410",
        "blob": "eb3b418f855d24ae0a34d5d09a289b9342098129", "rule_count": 0},
    "luci-swconfig": {"revision": SWCONFIG_REV, "path": SWCONFIG_PATH,
        "sha256": "6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e",
        "blob": SWCONFIG_BLOB, "rule_count": 0},
}


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tailscale_file_expectation(manifest: dict, case: str, rel: str) -> dict:
    """Look up a case-relative file in the source-first manifest's files map."""
    key = f"{case}/{rel}"
    try:
        return manifest["files"][key]
    except KeyError as exc:
        raise RuntimeError(f"Tailscale file expectation is missing: {key}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def invalidating_codeql_warnings(stderr: str) -> list[str]:
    warnings = [line for line in stderr.splitlines()
                if re.search(r"\bWARNING:", line, re.IGNORECASE)]
    # This CLI warning concerns performance, not interpretation of results.
    return [line for line in warnings if not re.search(
        r"WARNING: Not caching stages during query-loading, since max heap size is only \d+ MB\.",
        line)]


class Runner:
    def __init__(self, run: pathlib.Path, codeql: pathlib.Path):
        self.run = run
        self.codeql = codeql
        self.commands: list[dict] = []
        self.home = run / "home"
        self.tmp = run / "tmp"
        self.cache = run / "cache"
        self.out = run / "out"
        for p in (self.home, self.tmp, self.cache, self.out):
            p.mkdir(parents=True, exist_ok=True)

    def env(self, **overrides: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update({"HOME": str(self.home), "TMPDIR": str(self.tmp),
                    "CARGO_HOME": str(self.cache / "cargo"),
                    "RUSTUP_HOME": str(self.run.parent / (self.run.name + "-rustup")),
                    "RUSTUP_TOOLCHAIN": "1.100.0",
                    "PATH": f"{self.codeql.parent}:{env.get('PATH', '')}"})
        env.update(overrides)
        return env

    def call(self, label: str, argv: list[str | pathlib.Path], *, cwd: pathlib.Path = ROOT,
             env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess:
        argv = [str(x) for x in argv]
        phase_dir = self.out / "commands"
        phase_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label)
        stdout_path, stderr_path, time_path = (phase_dir / f"{safe}.{s}" for s in ("stdout", "stderr", "time"))
        start = time.monotonic()
        with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
            timed = subprocess.run(["/usr/bin/time", "-v", "-o", str(time_path), *argv],
                                   cwd=cwd, env=env or self.env(), text=True,
                                   stdout=stdout, stderr=stderr, check=False)
        wall = round(time.monotonic() - start, 3)
        time_text = time_path.read_text(errors="replace") if time_path.exists() else ""
        match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", time_text)
        row = {"label": label, "argv": argv, "cwd": str(cwd), "exit": timed.returncode,
               "wall_seconds": wall, "peak_rss_bytes": int(match.group(1)) * 1024 if match else None,
               "stdout": str(stdout_path.relative_to(self.run)),
               "stderr": str(stderr_path.relative_to(self.run)),
               "time": str(time_path.relative_to(self.run))}
        self.commands.append(row)
        (self.run / "commands.json").write_text(json.dumps(self.commands, indent=2) + "\n")
        if check and timed.returncode:
            raise RuntimeError(f"{label} exited {timed.returncode}; see {stderr_path}")
        return timed

    def codeql_call(self, label: str, args: list[str | pathlib.Path], *,
                    env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        result = self.call(label, [self.codeql, *args], env=env)
        if args and args[0] in ("query", "database", "resolve"):
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label)
            stderr_path = self.out / "commands" / f"{safe}.stderr"
            invalidating = invalidating_codeql_warnings(stderr_path.read_text(errors="replace"))
            require(not invalidating,
                    f"{label} emitted CodeQL warnings requiring review: {invalidating}; see {stderr_path}")
        return result


def git_call(runner: Runner, label: str, repo: pathlib.Path, *args: str) -> str:
    result = runner.call(label, ["git", "-C", repo, *args])
    return result.stdout if result.stdout else (runner.out / "commands" /
        (re.sub(r"[^A-Za-z0-9_.-]+", "-", label) + ".stdout")).read_text()


def git_output(runner: Runner, label: str, repo: pathlib.Path, *args: str) -> str:
    git_call(runner, label, repo, *args)
    return (runner.out / "commands" / (re.sub(r"[^A-Za-z0-9_.-]+", "-", label) + ".stdout")).read_text().strip()


def source_checkouts(runner: Runner, run: pathlib.Path) -> dict[str, pathlib.Path]:
    repo = run / "sources" / "luci.git"
    repo.parent.mkdir(parents=True, exist_ok=True)
    runner.call("luci-source-init", ["git", "init", "--bare", repo])
    runner.call("luci-source-remote", ["git", "--git-dir", repo, "remote", "add", "origin", LUCI_URL])
    revisions = {
        "openvpn-parent": OPENVPN_PARENT, "openvpn-fixed": OPENVPN_FIXED,
        "luci-swconfig": SWCONFIG_REV,
        "tailscale-parent": "46cd82328dfb7fbb15961c63f9e674a41cef2500",
        "tailscale-fixed": "507ab5e45c304543d4111af9a331db0f03be6bcb",
    }
    checkouts = {}
    for name, revision in revisions.items():
        runner.call(f"fetch-{name}", ["git", "--git-dir", repo, "fetch", "--depth=1", "origin", revision])
        path = run / "sources" / name
        runner.call(f"checkout-{name}", ["git", "--git-dir", repo, "worktree", "add", "--detach", path, revision])
        got = git_output(runner, f"verify-{name}-head", path, "rev-parse", "HEAD")
        status = git_output(runner, f"verify-{name}-status", path, "status", "--porcelain=v1")
        require(got == revision and not status, f"source checkout mismatch or dirty: {name} {got} {status}")
        checkouts[name] = path
    return checkouts


def copy_source(r: Runner, repo: pathlib.Path, revision: str, path: str, target: pathlib.Path,
                expected_sha: str, expected_blob: str | None = None, label: str = "source") -> dict:
    source = repo / path
    require(source.is_file(), f"missing source {source}")
    source_sha = digest(source)
    blob = git_output(r, f"{label}-git-blob", repo, "rev-parse", f"{revision}:{path}")
    require(source_sha == expected_sha, f"source hash mismatch for {path}: {source_sha}")
    if expected_blob:
        require(blob == expected_blob, f"source Git blob mismatch for {path}: {blob}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    require(digest(target) == source_sha, f"stage hash mismatch for {target}")
    return {"revision": revision, "source_path": path, "git_blob": blob,
            "source_sha256": source_sha, "stage_path": str(target),
            "stage_sha256": digest(target), "bytes": target.stat().st_size}


def run_query(r: Runner, build: pathlib.Path, db: pathlib.Path, case: str, name: str,
              query: pathlib.Path, fmt: str = "json") -> list:
    common = r.cache / "codeql-common" / case
    comp = r.cache / "codeql-compile" / case
    common.mkdir(parents=True, exist_ok=True)
    comp.mkdir(parents=True, exist_ok=True)
    output = r.out / case / f"{name}.bqrs"
    output.parent.mkdir(parents=True, exist_ok=True)
    search_path = ":".join(map(str, [build / "extractor-pack", build / "ql/lib", build / "ql/src"]))
    r.codeql_call(f"{case}-{name}-query", ["query", "run", query, f"--database={db}",
        f"--search-path={search_path}", f"--common-caches={common}",
        f"--compilation-cache={comp}", "--no-default-compilation-cache",
        f"--output={output}", "--threads=1", "--ram=2048"])
    decoded = r.codeql_call(f"{case}-{name}-decode", ["bqrs", "decode", f"--format={fmt}",
        *( ["--entities=url,string"] if fmt == "json" else []), output])
    decoded_path = r.out / case / f"{name}.{fmt}"
    decoded_path.write_text((r.out / "commands" /
        (f"{case}-{name}-decode.stdout")).read_text())
    if fmt == "json":
        return json.loads(decoded_path.read_text())["#select"]["tuples"]
    return []


def checked_file_identities(rows: list, stage: pathlib.Path, expected_rel: list[str], case: str) -> None:
    actual = collections.Counter()
    for row in rows:
        entity = row[0]
        uri = entity.get("url", {}).get("uri")
        require(uri is not None, f"{case}: missing file URL in successful-file row {row}")
        parsed = urlsplit(uri)
        require(parsed.scheme == "file" and not parsed.netloc, f"{case}: unexpected file URI {uri}")
        path = pathlib.Path(unquote(parsed.path)).resolve()
        actual[path.relative_to(stage.resolve()).as_posix()] += 1
    want = collections.Counter(expected_rel)
    require(actual == want, f"{case}: successful-file multiset mismatch; got={actual}, want={want}")


def check_route(db: pathlib.Path, stage: pathlib.Path, rels: list[str], case: str) -> dict:
    path = db / "trap/ucode/routing.json"
    require(path.is_file(), f"{case}: extractor route receipt missing")
    receipt = json.loads(path.read_text())
    expected = [{"path": str((stage / rel).resolve()), "installed_path": rel,
        "classification": "plain", "reason": "rpcd_raw_mode_full_path",
        "status": "plain_route_selected"} for rel in sorted(rels)]
    decisions = sorted(receipt.get("decisions", []), key=lambda row: row.get("installed_path", ""))
    require(receipt.get("input_count") == len(rels) and receipt.get("plain_count") == len(rels) and
            receipt.get("excluded_count") == 0 and receipt.get("uncertain_count") == 0 and
            receipt.get("markup_count") == 0 and receipt.get("duplicate_input_count") == 0 and
            decisions == expected, f"{case}: route mismatch {receipt}")
    return receipt


def make_database(r: Runner, build: pathlib.Path, case: str, stage: pathlib.Path,
                  relative_files: list[str]) -> pathlib.Path:
    db = r.run / "db" / case
    db.parent.mkdir(parents=True, exist_ok=True)
    pack = build / "extractor-pack"
    common = r.cache / "database-common" / case
    common.mkdir(parents=True, exist_ok=True)
    env = r.env(CODEQL_UCODE_STAGED_ROOT=str(stage))
    r.codeql_call(f"{case}-database-init", ["database", "init", db, "--language=ucode",
        f"--search-path={pack}", f"--common-caches={common}", f"--source-root={stage}"], env=env)
    r.codeql_call(f"{case}-database-index", ["database", "index-files", "--language=ucode",
        "--include=**/rpcd/ucode/*", f"--working-dir={stage}",
        f"--common-caches={common}", db], env=env)
    route = check_route(db, stage, relative_files, case)
    r.codeql_call(f"{case}-database-finalize", ["database", "finalize", db,
        f"--common-caches={common}"], env=env)
    q_success = run_query(r, build, db, case, "success", build / "ql/src/diagnostics/SuccessfullyExtractedFiles.ql")
    q_errors = run_query(r, build, db, case, "errors", build / "ql/src/diagnostics/ExtractionErrors.ql")
    checked_file_identities(q_success, stage, relative_files, case)
    require(q_errors == [], f"{case}: extraction errors present: {q_errors}")
    return db


def check_sarif(path: pathlib.Path, case: str, expected_count: int,
                expected_location: tuple | None = None, expected_rule_id: str = DIRECT_RULE_ID) -> dict:
    sarif = json.loads(path.read_text())
    require(sarif.get("version") == "2.1.0" and len(sarif.get("runs", [])) == 1,
            f"{case}: malformed SARIF envelope")
    run = sarif["runs"][0]
    rules = run["tool"]["driver"].get("rules", [])
    require([r["id"] for r in rules] == [expected_rule_id], f"{case}: rule descriptor mismatch {[r['id'] for r in rules]}")
    results = run.get("results", [])
    require(len(results) == expected_count, f"{case}: expected {expected_count} results, got {len(results)}")
    if expected_location:
        require(expected_count == 1, "exact location check requires one result")
        result = results[0]
        require(result.get("ruleId") == expected_rule_id, f"{case}: unexpected result rule ID")
        phys = result["locations"][0]["physicalLocation"]
        loc = (phys["artifactLocation"]["uri"], phys["region"]["startLine"],
               phys["region"]["startColumn"], phys["region"]["endColumn"])
        require(loc == expected_location, f"{case}: exact SARIF location mismatch {loc}")
    return {"rule_ids": [r["id"] for r in rules], "result_count": len(results),
            "results": results, "sha256": digest(path)}


def build_extractor(r: Runner, producer_copy: pathlib.Path) -> dict:
    cargo_lock = producer_copy / "Cargo.lock"
    lib_lock = producer_copy / "ql/lib/codeql-pack.lock.yml"
    src_lock = producer_copy / "ql/src/codeql-pack.lock.yml"
    require(digest(cargo_lock) == CARGO_LOCK_SHA256, "Cargo.lock pin changed")
    require(digest(lib_lock) == QL_LOCK_SHA256 and digest(src_lock) == QL_LOCK_SHA256,
            "CodeQL pack lock pin changed")
    rustc_result = r.call("rustc-version", ["rustc", "--version"])
    require(rustc_result.returncode == 0, "rustc is unavailable")
    rustc_line = (r.out / "commands/rustc-version.stdout").read_text().strip()
    require(rustc_line.startswith("rustc 1.100.0"), f"unexpected rustc toolchain {rustc_line}")
    r.call("cargo-version", ["cargo", "--version"])
    cargo_line = (r.out / "commands/cargo-version.stdout").read_text().strip()
    grammar = producer_copy / "extractor/tree-sitter"
    r.call("clone-pinned-grammar", ["bash", "scripts/clone-grammar.sh"], cwd=producer_copy)
    grammar_head = git_output(r, "grammar-revision", grammar, "rev-parse", "HEAD")
    require(grammar_head == GRAMMAR_REV, f"grammar pin mismatch: {grammar_head}")
    grammar_status = git_output(r, "grammar-post-bootstrap-status", grammar, "status", "--porcelain=v1")
    require(grammar_status.splitlines() == [" M Cargo.toml"],
            f"unexpected pinned grammar working-tree transformation: {grammar_status!r}")
    grammar_manifest = grammar / "Cargo.toml"
    r.call("grammar-upstream-cargo-toml", ["git", "-C", grammar, "show", f"{GRAMMAR_REV}:Cargo.toml"])
    grammar_raw = (r.out / "commands/grammar-upstream-cargo-toml.stdout").read_bytes()
    transformed = grammar_raw.replace(b'tree-sitter = "0.27.1"', b'tree-sitter = "=0.26.8"')
    require(grammar_raw.count(b'tree-sitter = "0.27.1"') == 1 and
            grammar_manifest.read_bytes() == transformed,
            "pinned grammar dev-dependency transformation differs from clone-grammar.sh")
    grammar_build_sha = digest(grammar_manifest)
    r.call("create-extractor-pack", ["bash", "scripts/create-extractor-pack.sh"], cwd=producer_copy)
    require(digest(cargo_lock) == CARGO_LOCK_SHA256, "Cargo.lock changed during unlocked pack build")
    require(digest(lib_lock) == QL_LOCK_SHA256 and digest(src_lock) == QL_LOCK_SHA256,
            "CodeQL pack locks changed during pack build")
    pack = producer_copy / "extractor-pack"
    extractor = pack / "tools/linux64/extractor"
    require(extractor.is_file() and os.access(extractor, os.X_OK), "Linux extractor pack missing executable")
    r.codeql_call("install-lib-qlpack", ["pack", "install", producer_copy / "ql/lib"])
    r.codeql_call("install-src-qlpack", ["pack", "install", producer_copy / "ql/src"])
    require(digest(lib_lock) == QL_LOCK_SHA256 and digest(src_lock) == QL_LOCK_SHA256,
            "CodeQL pack lock files changed during dependency install")
    files = []
    for p in sorted(pack.rglob("*")):
        if p.is_file():
            files.append({"path": p.relative_to(producer_copy).as_posix(), "sha256": digest(p), "bytes": p.stat().st_size})
    return {"rustc": rustc_line, "cargo": cargo_line, "cargo_lock_sha256_before_after": CARGO_LOCK_SHA256,
            "ql_lock_sha256_before_after": QL_LOCK_SHA256, "grammar_revision": grammar_head,
            "grammar_worktree_status_after_pinned_dev_dependency_adjustment": grammar_status,
            "grammar_cargo_toml_upstream_sha256": hashlib.sha256(grammar_raw).hexdigest(),
            "grammar_cargo_toml_transformed_sha256": grammar_build_sha,
            "grammar_transformation": 'tree-sitter = "0.27.1" to tree-sitter = "=0.26.8" (one exact replacement)',
            "extractor_sha256": digest(extractor), "pack_files": files}


def run_default_cases(r: Runner, build: pathlib.Path, sources: dict[str, pathlib.Path]) -> dict:
    query = build / "ql/src/m4/DirectRpcShellWord.ql"
    suite = build / "ql/src/codeql-suites/code-scanning.qls"
    require(digest(query) == DIRECT_QUERY_SHA256, "direct rule bytes differ from reviewed pin")
    require(digest(suite) == DEFAULT_SUITE_SHA256, "code-scanning suite bytes differ from reviewed pin")
    sp = ":".join(map(str, [build / "extractor-pack", build / "ql/lib", build / "ql/src"]))
    r.codeql_call("resolve-default-suite", ["resolve", "queries", "--format=json",
        suite, f"--search-path={sp}"])
    resolved_path = r.out / "resolved-default-suite.json"
    resolved_path.write_text((r.out / "commands/resolve-default-suite.stdout").read_text())
    resolved = json.loads(resolved_path.read_text())
    names = sorted(pathlib.Path(q).name for q in resolved)
    require(names == ["DirectRpcShellWord.ql", "ExtractionErrors.ql", "SuccessfullyExtractedFiles.ql"],
            f"unexpected default suite contents: {names}")
    cases = {}
    source_records = {}
    for case in ("openvpn-parent", "openvpn-fixed", "luci-swconfig"):
        info = REAL_INPUTS[case]
        source_root = sources[case]
        # Use the package's proposed installed-style relative path as the stage identity.
        installed_rel = "usr/share/rpcd/ucode/" + pathlib.PurePosixPath(info["path"]).name
        staged_path = r.run / "stage" / case / installed_rel
        # Copy the exact pinned source bytes to the proposed installed-style path.
        source_records[case] = copy_source(r, source_root, info["revision"], info["path"], staged_path,
            info["sha256"], info["blob"] or None, case)
        stage = r.run / "stage" / case
        db = make_database(r, build, case, stage, [installed_rel])
        sarif_path = r.out / case / "default-suite.sarif"
        common = r.cache / "codeql-common" / case
        comp = r.cache / "codeql-compile" / case
        r.codeql_call(f"{case}-default-suite-analyze", ["database", "analyze", db, suite,
            "--format=sarifv2.1.0", f"--output={sarif_path}", f"--search-path={sp}",
            f"--common-caches={common}", f"--compilation-cache={comp}",
            "--no-default-compilation-cache", "--threads=1", "--ram=2048"])
        expected_loc = info.get("location")
        sarif_summary = check_sarif(sarif_path, case, info["rule_count"], expected_loc)
        cases[case] = {"source": source_records[case], "selected": [installed_rel],
            "successful_multiset": {installed_rel: 1}, "extraction_errors": 0,
            "route_sha256": digest(db / "trap/ucode/routing.json"), "sarif": sarif_summary}
    return {"resolved_queries": names, "cases": cases,
            "resolved_suite_sha256": digest(resolved_path)}


def run_tailscale_regression(r: Runner, build: pathlib.Path, sources: dict[str, pathlib.Path]) -> dict:
    base = build / "ql/test/tailscale-nested-shell"
    manifest_path = base / "expected.json"
    require(digest(manifest_path) == TAILSCALE_MANIFEST_SHA256,
            "Tailscale expected.json differs from reviewed source-first pin")
    require(digest(build / "ql/src/m4/TailscaleNestedShell.ql") == TAILSCALE_QUERY_SHA256,
            "Tailscale explicit regression query differs from reviewed pin")
    expected = json.loads(manifest_path.read_text())
    require(expected["historical_parent"] == "46cd82328dfb7fbb15961c63f9e674a41cef2500" and
            expected["historical_fix"] == "507ab5e45c304543d4111af9a331db0f03be6bcb",
            "Tailscale historical manifest pins changed")
    source_map = {"parent": sources["tailscale-parent"], "fixed": sources["tailscale-fixed"]}
    for name in ("parent", "fixed"):
        item = tailscale_file_expectation(expected, name, "usr/share/rpcd/ucode/tailscale.uc")
        source_path = "applications/luci-app-tailscale-community/root/usr/share/rpcd/ucode/tailscale.uc"
        require(digest(source_map[name] / source_path) == item["sha256"], f"Tailscale {name} source hash mismatch")
    cases = {}
    query = build / "ql/src/m4/TailscaleNestedShell.ql"
    for case in ("parent", "fixed", "controls"):
        stage = r.run / "stage/tailscale" / case
        selected = []
        file_identities = []
        for rel, info in expected["files"].items():
            if not rel.startswith(case + "/"):
                continue
            stage_rel = rel[len(case) + 1:]
            dest = stage / stage_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if case in ("parent", "fixed"):
                source_path = "applications/luci-app-tailscale-community/root/" + stage_rel
                shutil.copyfile(source_map[case] / source_path, dest)
            else:
                fixture = base / rel
                shutil.copyfile(fixture, dest)
            observed_sha = digest(dest)
            require(observed_sha == info["sha256"], f"Tailscale fixture/source hash mismatch: {rel}")
            blob = None
            if case in ("parent", "fixed"):
                blob = git_output(r, f"tailscale-{case}-{pathlib.Path(stage_rel).stem}-git-blob",
                    source_map[case], "rev-parse",
                    f"{expected['historical_parent'] if case == 'parent' else expected['historical_fix']}:{source_path}")
            file_identities.append({"manifest_path": rel, "stage_path": str(dest),
                                    "sha256": observed_sha, "git_blob": blob})
            selected.append(stage_rel)
        db = make_database(r, build, f"tailscale-{case}", stage, sorted(selected))
        sarif_path = r.out / f"tailscale-{case}" / "candidate.sarif"
        common = r.cache / "codeql-common" / f"tailscale-{case}"
        comp = r.cache / "codeql-compile" / f"tailscale-{case}"
        sp = ":".join(map(str, [build / "extractor-pack", build / "ql/lib", build / "ql/src"]))
        r.codeql_call(f"tailscale-{case}-explicit-analyze", ["database", "analyze", db, query,
            "--format=sarifv2.1.0", f"--output={sarif_path}", f"--search-path={sp}",
            f"--common-caches={common}", f"--compilation-cache={comp}",
            "--no-default-compilation-cache", "--threads=1", "--ram=2048"])
        wanted = []
        for rel in selected:
            info = tailscale_file_expectation(expected, case, rel)
            for span in info.get("candidate_sinks", []):
                m = re.fullmatch(r"(\d+):(\d+)-(\d+)", span)
                require(m is not None, f"bad Tailscale candidate span {span}")
                line, start_col, end_inclusive = map(int, m.groups())
                wanted.append((rel, line, start_col, end_inclusive + 1))
        # SARIF for this explicit testing query is validated independently of the default suite.
        sarif = json.loads(sarif_path.read_text())
        sr = sarif["runs"][0]
        require([x["id"] for x in sr["tool"]["driver"].get("rules", [])] ==
                ["ucode/m4/tailscale-nested-shell-candidate"], "Tailscale rule ID mismatch")
        actual = []
        for result in sr.get("results", []):
            phys = result["locations"][0]["physicalLocation"]
            region = phys["region"]
            actual.append((phys["artifactLocation"]["uri"], region["startLine"],
                           region["startColumn"], region["endColumn"]))
        require(collections.Counter(actual) == collections.Counter(wanted),
                f"Tailscale {case} SARIF locations differ: {actual} != {wanted}")
        cases[case] = {"selected": sorted(selected), "files": file_identities,
                       "expected_candidate_locations": wanted,
                       "observed_candidate_locations": actual, "sarif_sha256": digest(sarif_path),
                       "candidate_count": len(actual)}
    return {"explicit_testing_query": "TailscaleNestedShell.ql", "manifest_sha256": digest(manifest_path),
            "cases": cases, "separate_from_default_suite": True}


def main() -> int:
    codeql_text = os.environ.get("CODEQL_BIN")
    run_text = os.environ.get("DIRECT_RPC_RUN_DIR")
    require(codeql_text and run_text, "CODEQL_BIN and DIRECT_RPC_RUN_DIR are required")
    codeql = pathlib.Path(codeql_text).resolve()
    run = pathlib.Path(run_text).resolve()
    require(codeql.is_file() and os.access(codeql, os.X_OK), f"CodeQL CLI not executable: {codeql}")
    codeql_zip = codeql.parent.parent.parent / "download/codeql-linux64.zip"
    require(codeql_zip.is_file() and digest(codeql_zip) == CODEQL_ZIP_SHA256,
            "CodeQL CLI archive is missing or does not match the pinned SHA-256")
    require(not run.exists(), f"run path already exists: {run}")
    run.mkdir(parents=True)
    runner = Runner(run, codeql)
    mem_available = None
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            mem_available = int(line.split()[1]) * 1024
            break
    resources = {"cpu_count": os.cpu_count(), "disk_free_bytes": shutil.disk_usage(run).free,
        "memory_available_bytes": mem_available}
    require(resources["cpu_count"] and resources["cpu_count"] >= 2, f"insufficient CPU capacity: {resources}")
    require(resources["disk_free_bytes"] >= 8 * 1024**3, f"less than 8 GiB disk free before build: {resources}")
    require(mem_available is not None and mem_available >= 4 * 1024**3,
            f"less than 4 GiB available memory before build: {resources}")
    preflight = {"status": "preflight passed before source fetch/build/extraction",
        "run_directory": str(run), "home": str(runner.home), "tmp": str(runner.tmp),
        "cache": str(runner.cache), "rustup_home": os.environ.get("RUSTUP_HOME"),
        "codeql_zip_sha256": digest(codeql_zip), "codeql_version_expected": CODEQL_VERSION,
        "resources_before_run": resources}
    (run / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    runner.codeql_call("codeql-version", ["version"])
    version_line = (run / "out/commands/codeql-version.stdout").read_text().splitlines()[0]
    require(version_line.endswith(CODEQL_VERSION + "."), f"CodeQL version mismatch: {version_line}")
    require(pathlib.Path("/usr/bin/time").is_file(), "GNU time is required for peak RSS recording")
    require(sys.platform == "linux", "this release-gate runner is Linux-only")
    require(os.environ.get("RUSTUP_TOOLCHAIN") == "1.100.0", "workflow must pin RUSTUP_TOOLCHAIN=1.100.0")
    producer_sha = git_output(runner, "producer-head", ROOT, "rev-parse", "HEAD")
    producer_status = git_output(runner, "producer-status", ROOT, "status", "--porcelain=v1")
    require(not producer_status, f"producer checkout must be clean: {producer_status}")
    build = run / "producer-build"
    build.mkdir()
    archive_path = run / "producer-source.tar"
    runner.call("archive-producer-source", ["git", "-C", ROOT, "archive", "--format=tar",
        f"--output={archive_path}", "HEAD"])
    runner.call("extract-producer-archive", ["tar", "-xf", archive_path, "-C", build])
    upstream = source_checkouts(runner, run)
    swconfig_blob = git_output(runner, "luci-swconfig-pinned-blob", upstream["luci-swconfig"],
                               "rev-parse", f"{SWCONFIG_REV}:{SWCONFIG_PATH}")
    require(swconfig_blob == SWCONFIG_BLOB, f"swconfig Git blob pin mismatch: {swconfig_blob}")
    expected_rustup_home = run.parent / (run.name + "-rustup")
    require(pathlib.Path(os.environ.get("RUSTUP_HOME", "")).resolve() == expected_rustup_home.resolve(),
            "workflow must set RUSTUP_HOME to this run's dedicated rustup directory")
    # Pre-extraction source oracle: hash, blob and exact source path are frozen before any query output.
    source_oracle = {"direct_rpc_cases": {name: {"revision": info["revision"], "path": info["path"],
        "git_blob": info["blob"], "sha256": info["sha256"], "expected_rule_count": info["rule_count"],
        "expected_location": info.get("location")} for name, info in REAL_INPUTS.items()}}
    tailscale_manifest = build / "ql/test/tailscale-nested-shell/expected.json"
    require(digest(tailscale_manifest) == TAILSCALE_MANIFEST_SHA256,
            "Tailscale expected.json differs from reviewed source-first pin")
    require(digest(build / "ql/src/m4/TailscaleNestedShell.ql") == TAILSCALE_QUERY_SHA256,
            "Tailscale explicit query differs from reviewed pin")
    source_oracle["tailscale_explicit_regression"] = {
        "manifest_sha256": digest(tailscale_manifest),
        "expectations": json.loads(tailscale_manifest.read_text())}
    (run / "source-oracle.json").write_text(json.dumps(source_oracle, indent=2) + "\n")
    preflight.update({"producer_commit": producer_sha, "producer_dirty_before_run": False,
        "producer_archive_sha256": digest(archive_path), "luci_repo_url": LUCI_URL,
        "upstream_checkouts": {
            key: {"commit": REAL_INPUTS[key]["revision"] if key in REAL_INPUTS else
                  ("46cd82328dfb7fbb15961c63f9e674a41cef2500" if key == "tailscale-parent" else "507ab5e45c304543d4111af9a331db0f03be6bcb"),
                  "dirty": False} for key in upstream},
        "codeql_version": version_line, "rustup_home": str(pathlib.Path(os.environ["RUSTUP_HOME"]).resolve()),
        "cargo_lock_sha256": digest(build / "Cargo.lock"),
        "ql_lib_lock_sha256": digest(build / "ql/lib/codeql-pack.lock.yml"),
        "ql_src_lock_sha256": digest(build / "ql/src/codeql-pack.lock.yml"),
        "grammar_revision": GRAMMAR_REV,
        "source_oracle_sha256": digest(run / "source-oracle.json"),
        "direct_query_sha256": digest(build / "ql/src/m4/DirectRpcShellWord.ql"),
        "default_suite_sha256": digest(build / "ql/src/codeql-suites/code-scanning.qls"),
        "tailscale_query_sha256": digest(build / "ql/src/m4/TailscaleNestedShell.ql"),
        "tailscale_manifest_sha256": digest(build / "ql/test/tailscale-nested-shell/expected.json")})
    (run / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    build_info = build_extractor(runner, build)
    preflight["build"] = build_info
    (run / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    default = run_default_cases(runner, build, upstream)
    tailscale = run_tailscale_regression(runner, build, upstream)
    summary = {"producer_commit": producer_sha, "codeql_version": version_line,
        "source_oracle_sha256": digest(run / "source-oracle.json"),
        "default_suite": default, "tailscale_explicit_regression": tailscale,
        "commands": runner.commands, "command_count": len(runner.commands)}
    bundle_path = run / "artifact/codeql-ucode-linux.tar.gz"
    runner.call("package-linux-release-candidate", ["python3", build / "scripts/package-linux-release.py",
        f"--source={build}", f"--output={bundle_path}", f"--producer-commit={producer_sha}",
        f"--codeql-version={version_line}", f"--rustc-version={build_info['rustc']}",
        f"--cargo-version={build_info['cargo']}", f"--grammar-revision={GRAMMAR_REV}",
        f"--codeql-archive-sha256={CODEQL_ZIP_SHA256}", "--source-clean"], cwd=build)
    bundle_record = json.loads((run / "out/commands/package-linux-release-candidate.stdout").read_text())
    extracted_parent = run / "verified-bundle"
    verifier = build / "scripts/verify-linux-release-bundle.py"
    runner.call("verify-and-extract-linux-release-candidate", ["python3", verifier,
        f"--archive={bundle_path}", f"--expected-sha256={bundle_record['archive_sha256']}",
        f"--output-dir={extracted_parent}"])
    verifier_record = json.loads((run / "out/commands/verify-and-extract-linux-release-candidate.stdout").read_text())
    extracted_bundle = extracted_parent / "codeql-ucode-linux"
    extracted_lib = extracted_bundle / "ql/lib"
    extracted_src = extracted_bundle / "ql/src"
    runner.codeql_call("install-candidate-lib-dependencies", ["pack", "install", extracted_lib])
    runner.codeql_call("install-candidate-query-dependencies", ["pack", "install", extracted_src])
    require(digest(extracted_lib / "codeql-pack.lock.yml") == QL_LOCK_SHA256 and
            digest(extracted_src / "codeql-pack.lock.yml") == QL_LOCK_SHA256,
            "candidate dependency bootstrap changed a QL lock")
    extracted_suite = extracted_src / "codeql-suites/code-scanning.qls"
    extracted_search_path = ":".join(map(str, [extracted_bundle / "extractor-pack",
        extracted_lib, extracted_src]))
    runner.codeql_call("resolve-candidate-default-suite", ["resolve", "queries", "--format=json",
        extracted_suite, f"--search-path={extracted_search_path}"])
    extracted_resolved = json.loads((run / "out/commands/resolve-candidate-default-suite.stdout").read_text())
    extracted_names = sorted(pathlib.Path(query).name for query in extracted_resolved)
    require(extracted_names == ["DirectRpcShellWord.ql", "ExtractionErrors.ql",
                                "SuccessfullyExtractedFiles.ql"],
            f"candidate bundle default suite mismatch: {extracted_names}")
    for query in extracted_resolved:
        try:
            pathlib.Path(query).resolve().relative_to(extracted_src.resolve())
        except ValueError as exc:
            raise RuntimeError(f"candidate suite resolved outside bundled query pack: {query}") from exc
    summary["release_bundle_candidate"] = {
        "path": "artifact/codeql-ucode-linux.tar.gz",
        "archive_sha256": bundle_record["archive_sha256"],
        "manifest": bundle_record["manifest"],
        "verification": verifier_record,
        "dependency_bootstrap": {
            "commands": ["codeql pack install ql/lib", "codeql pack install ql/src"],
            "cache_scope": "run-owned HOME and extracted candidate tree",
            "lock_digests_after_install": {
                "ql/lib/codeql-pack.lock.yml": digest(extracted_lib / "codeql-pack.lock.yml"),
                "ql/src/codeql-pack.lock.yml": digest(extracted_src / "codeql-pack.lock.yml")},
            "network_access": "not separately instrumented; missing locked dependencies may be downloaded"},
        "resolved_default_suite": {"query_names": extracted_names,
            "suite_sha256": digest(extracted_suite),
            "query_pack_lock_sha256": digest(extracted_src / "codeql-pack.lock.yml"),
            "library_pack_lock_sha256": digest(extracted_lib / "codeql-pack.lock.yml"),
            "resolved_query_paths": [str(pathlib.Path(query).resolve().relative_to(extracted_src.resolve()))
                                     for query in extracted_resolved]}}
    summary["commands"] = runner.commands
    summary["command_count"] = len(runner.commands)
    (run / "receipt.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # artifacts survive failures for review
        print(f"direct-rpc release gate failed: {exc}", file=sys.stderr)
        raise
