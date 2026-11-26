#!/usr/bin/env python3
"""Stage source-pinned Ucode candidates from actual OpenWrt IPK member bytes."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(name: str) -> str:
    name = name.removeprefix("./")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name or path.as_posix() != name:
        raise ValueError(f"unsafe archive member: {name!r}")
    return name


def candidate(path: str, data: bytes) -> bool:
    suffix = PurePosixPath(path).suffix
    if suffix in {".uc", ".ucode", ".ut"} or path.startswith("usr/share/rpcd/ucode/"):
        return True
    first = data.split(b"\n", 1)[0].decode("utf-8", "replace")
    if not first.startswith("#!"):
        return False
    words = first[2:].split()
    if not words:
        return False
    interpreter = words[0]
    if interpreter.rsplit("/", 1)[-1] == "ucode":
        return True
    if interpreter in {"/usr/bin/env", "/bin/env"}:
        command = words[2] if len(words) > 2 and words[1] == "-S" else (words[1] if len(words) > 1 else "")
        return command.strip("'\"") == "ucode"
    return False


def stage(ipk: Path, expected_sha256: str, oracle_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"stage already exists: {output}")
    raw = ipk.read_bytes()
    if digest(raw) != expected_sha256:
        raise ValueError("IPK digest differs from independent pin")
    oracle = json.loads(oracle_path.read_text())
    if oracle.get("schema") != "ucode-installed-stage-v1":
        raise ValueError("wrong stage oracle schema")
    expected = {entry["path"]: entry["sha256"] for entry in oracle["files"]}
    if len(expected) != len(oracle["files"]):
        raise ValueError("duplicate oracle path")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as package:
        data_members = [member for member in package if safe_path(member.name) == "data.tar.gz"]
        if len(data_members) != 1 or not data_members[0].isfile():
            raise ValueError("IPK lacks one regular data.tar.gz member")
        payload = package.extractfile(data_members[0]).read()
    selected: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as data_archive:
        for member in data_archive:
            name = safe_path(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                if name in expected:
                    raise ValueError(f"expected file is not a regular archive member: {name}")
                continue
            data = data_archive.extractfile(member).read()
            if not candidate(name, data):
                continue
            if name in selected:
                raise ValueError(f"duplicate candidate member: {name}")
            selected[name] = data
    if set(selected) != set(expected):
        raise ValueError(f"candidate inventory differs from oracle: missing={sorted(set(expected)-set(selected))} extra={sorted(set(selected)-set(expected))}")
    for name, data in selected.items():
        if digest(data) != expected[name]:
            raise ValueError(f"member digest mismatch: {name}")
    output.mkdir(parents=True)
    for name, data in selected.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {"schema": "ucode-ipk-stage-receipt-v1", "ipk_sha256": expected_sha256,
            "oracle_sha256": digest(oracle_path.read_bytes()),
            "files": {name: digest(data) for name, data in sorted(selected.items())}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipk", type=Path, required=True)
    parser.add_argument("--ipk-sha256", required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{64}", args.ipk_sha256) is None:
        parser.error("--ipk-sha256 must be a lowercase SHA-256")
    print(json.dumps(stage(args.ipk, args.ipk_sha256, args.oracle, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
