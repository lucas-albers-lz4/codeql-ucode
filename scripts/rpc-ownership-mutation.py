#!/usr/bin/env python3
"""Replay the audited sameRpcMethod independent-owner mutation on one DB."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "ql/lib/codeql/ucode/m3/Models.qll"
ORIGINAL = "exists(UCODE::FunctionExpression fn | fn = rpcCallFn(_) and a.getParent*() = fn and b.getParent*() = fn)"
MUTANT = "exists(UCODE::FunctionExpression fa, UCODE::FunctionExpression fb | fa = rpcCallFn(_) and fb = rpcCallFn(_) and a.getParent*() = fa and b.getParent*() = fb)"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: rpc-ownership-mutation.py DATABASE SOURCE_ROOT OUTPUT_DIR")
    database, source, output = map(Path, sys.argv[1:])
    codeql = shutil.which("codeql")
    if codeql is None:
        raise SystemExit("codeql CLI must be on PATH")
    require(database.is_dir() and source.is_dir() and output.is_dir(), "database, source, and output directory must exist")
    text = MODELS.read_text()
    require(text.count(ORIGINAL) == 1, "sameRpcMethod owner guard not unique; refusing mutation")
    temp = output / "rpc-ownership-mutant-pack"
    shutil.rmtree(temp, ignore_errors=True)
    (temp / "ql").mkdir(parents=True)
    shutil.copyfile(ROOT / ".codeqlmanifest.json", temp / ".codeqlmanifest.json")
    shutil.copytree(ROOT / "ql/lib", temp / "ql/lib")
    shutil.copytree(ROOT / "ql/src", temp / "ql/src")
    mutated = temp / "ql/lib/codeql/ucode/m3/Models.qll"
    mutated.write_text(text.replace(ORIGINAL, MUTANT, 1))
    search_path = os.pathsep.join((str(ROOT / "extractor-pack"), str(temp / "ql/lib"), str(temp / "ql/src")))
    for query, name in (("m4/RequestArgsExec.ql", "RequestArgsExec.ql"), ("m3/LocalTaint.ql", "LocalTaint.ql")):
        bqrs = output / f"mutant-{name}.bqrs"
        command = [codeql, "query", "run", str(temp / "ql/src" / query), f"--database={database}",
                   f"--search-path={search_path}", "--threads=1", "--ram=2048", f"--output={bqrs}"]
        completed = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if completed.returncode:
            raise SystemExit(f"mutation query failed (not semantic red proof): {' '.join(command)}\n{completed.stdout[-6000:]}")
        decoded = subprocess.run([codeql, "bqrs", "decode", "--format=json", "--entities=url,string", str(bqrs)],
                                 cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if decoded.returncode:
            raise SystemExit(f"mutation decode failed: {decoded.stdout[-6000:]}")
        (output / f"mutant-{name}.json").write_text(decoded.stdout)
    spec = importlib.util.spec_from_file_location("rpc_ownership_verify", ROOT / "scripts/rpc-ownership-verify.py")
    if spec is None or spec.loader is None:
        raise SystemExit("could not load the exact-entity verifier")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    verifier.verify_mutant(source, output)


if __name__ == "__main__":
    main()
