#!/usr/bin/env python3
"""Run the bounded namespace fs model regression in private CodeQL paths."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "ql/test/issue155-namespace-stat"


def check_routing(routing, stage, source_oracle):
    decisions = routing["decisions"]
    expected_paths = {str((stage / "usr/share/rpcd/ucode" / name if name == "luci.advanced-reboot" else stage / name).resolve()) for name in source_oracle}
    expected_counts = {"input_count": len(expected_paths), "plain_count": len(expected_paths),
                       "markup_count": 0, "markup_inconclusive_count": 0, "uncertain_count": 0,
                       "excluded_count": 0, "duplicate_input_count": 0}
    if any(routing.get(key) != value for key, value in expected_counts.items()):
        raise RuntimeError("routing summary counts differ")
    if len(decisions) != len(expected_paths) or {row["path"] for row in decisions} != expected_paths:
        raise RuntimeError("routing identities differ")
    for row in decisions:
        real = row["path"].endswith("/luci.advanced-reboot")
        expected_reason = "rpcd_raw_mode_full_path" if real else "ucode_extension"
        expected_installed = "usr/share/rpcd/ucode/luci.advanced-reboot" if real else Path(row["path"]).name
        if (row.get("classification"), row.get("reason"), row.get("status"), row.get("installed_path")) != (
                "plain", expected_reason, "plain_route_selected", expected_installed):
            raise RuntimeError(f"routing differs: {row}")


def main():
    if not __debug__:
        raise RuntimeError("run this smoke without Python -O")
    parser = argparse.ArgumentParser()
    parser.add_argument("--codeql", type=Path, default=Path(shutil.which("codeql") or "codeql"))
    parser.add_argument("--pack", type=Path, default=ROOT / "extractor-pack")
    parser.add_argument("--packages", type=Path, default=Path.home() / ".codeql/packages")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is None:
        parent = ROOT / ".codeql-database"
        parent.mkdir(exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix="issue155-namespace-", dir=parent))
    else:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
    if not args.pack.is_dir() or not args.pack.joinpath("tools").is_dir():
        raise RuntimeError("built extractor pack required")
    if not args.packages.is_dir():
        raise RuntimeError("resolved CodeQL package cache required")

    witness = FIXTURES / "luci.advanced-reboot"
    witness_bytes = witness.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(witness_bytes)).encode() + b"\0" + witness_bytes).hexdigest()
    if (hashlib.sha256(witness_bytes).hexdigest() != "b6b5562036c1f2f93ec9ea9261943a17d667d5a742c71ce128ec4859279d4b11"
            or blob != "f903b6297ea68b43398f5e091e2409f5e162edf7"):
        raise RuntimeError("pinned LuCI application witness differs")
    stage = output / "stage"
    stage.mkdir()
    for source in sorted(FIXTURES.iterdir()):
        if not source.is_file():
            continue
        target = stage / "usr/share/rpcd/ucode" / source.name if source.name == "luci.advanced-reboot" else stage / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    pack = output / "pack"
    shutil.copytree(args.pack, pack)
    cache = output / "cache"
    common = cache / "common"
    common.mkdir(parents=True)
    shutil.copytree(args.packages, common / "packages")
    (output / "home").mkdir()
    (output / "tmp").mkdir()
    (output / "config").mkdir()
    source_oracle = {
        source.name: {"sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                      "bytes": len(source.read_bytes()), "text": source.read_text()}
        for source in sorted(FIXTURES.iterdir()) if source.is_file()
    }
    (output / "oracle-before-output.json").write_text(json.dumps(source_oracle, indent=2) + "\n")
    spec = importlib.util.spec_from_file_location("namespace_check", ROOT / "scripts/issue155-namespace-check.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    (output / "expected-before-output.json").write_text(json.dumps(checker.EXPECTED, indent=2) + "\n")

    env = os.environ.copy()
    env.update({"HOME": str(output / "home"), "TMPDIR": str(output / "tmp"),
                "XDG_CACHE_HOME": str(cache), "CODEQL_CONFIG_FILE": str(output / "config/codeql-config"),
                "CODEQL_UCODE_STAGED_ROOT": str(stage)})
    cli = str(args.codeql.resolve())
    db = output / "db"
    search = f"{pack}:{ROOT / 'ql/lib'}:{ROOT / 'ql/src'}"
    commands = []

    def run(name, *argv):
        started = time.monotonic()
        result = subprocess.run([str(arg) for arg in argv], env=env, capture_output=True, text=True)
        elapsed = time.monotonic() - started
        (output / f"{name}.stdout").write_text(result.stdout)
        (output / f"{name}.stderr").write_text(result.stderr)
        commands.append({"name": name, "argv": [str(arg) for arg in argv],
                         "exit": result.returncode, "elapsed_seconds": elapsed})
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode}): {result.stderr[-1200:]}")
        return result.stdout

    run("init", cli, "database", "init", db, "--language=ucode", f"--search-path={search}",
        f"--source-root={stage}", f"--common-caches={common}")
    run("index", cli, "database", "index-files", db, "--language=ucode", "--include=**/*.uc", "--include=**/luci.advanced-reboot",
        f"--working-dir={stage}", f"--common-caches={common}", "--threads=1", "--ram=2048")
    routing_path = db / "trap/ucode/routing.json"
    routing = json.loads(routing_path.read_text())
    check_routing(routing, stage, source_oracle)
    shutil.copyfile(routing_path, output / "routing.json")
    run("finalize", cli, "database", "finalize", db, f"--common-caches={common}",
        "--threads=1", "--ram=2048")
    queries = {
        "ast": "testing/issue155-namespace-stat/NamespaceAstWitnesses.ql",
        "stat": "testing/issue155-stat/StatModel.ql",
        "namespace-stat": "testing/issue155-namespace-stat/NamespaceStatModel.ql",
        "namespace-class": "testing/issue155-namespace-stat/NamespaceStatClass.ql",
        "success": "diagnostics/SuccessfullyExtractedFiles.ql",
        "errors": "diagnostics/ExtractionErrors.ql",
    }
    for name, relative in queries.items():
        bqrs = output / f"{name}.bqrs"
        query = ROOT / "ql/src" / relative
        run(name, cli, "query", "run", query, f"--database={db}", f"--search-path={search}",
            f"--output={bqrs}", f"--common-caches={common}",
            f"--compilation-cache={cache / 'compilation'}", "--no-default-compilation-cache",
            "--threads=1", "--ram=2048")
        mode = "url,string" if name in ("success", "errors") else "id"
        decoded = run(f"decode-{name}", cli, "bqrs", "decode", "--format=json",
                      f"--entities={mode}", bqrs)
        (output / f"{name}.json").write_text(decoded)
    checker.check(output)
    print(f"namespace fs smoke artifacts: {output}")


if __name__ == "__main__":
    main()
