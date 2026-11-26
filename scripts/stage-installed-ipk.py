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

MAX_IPK_BYTES = 4 * 1024 * 1024
MAX_DATA_TAR_BYTES = 4 * 1024 * 1024
MAX_MEMBER_BYTES = 2 * 1024 * 1024
MAX_TOTAL_REGULAR_BYTES = 16 * 1024 * 1024
MAX_MEMBERS = 512


def read_limited(stream, limit: int, label: str) -> bytes:
    data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"{label} exceeds byte budget")
    return data


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
    if first.startswith("#!"):
        words = first[2:].split()
        if words:
            interpreter = words[0]
            if interpreter.rsplit("/", 1)[-1] == "ucode":
                return True
            if interpreter in {"/usr/bin/env", "/bin/env"} and len(words) > 1:
                command = words[2] if words[1] == "-S" and len(words) > 2 else words[1]
                command = command.removeprefix("-S").strip("'\"")
                command_words = command.split()
                if command_words and command_words[0].rsplit("/", 1)[-1] == "ucode":
                    return True
    if any(line.lstrip().startswith(("{%", "{{", "{#"))
           for line in data.decode("utf-8", "replace").splitlines()):
        return True
    return path.startswith("usr/share/ucode/")


def stage(ipk: Path, expected_sha256: str, oracle_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"stage already exists: {output}")
    if ipk.stat().st_size > MAX_IPK_BYTES:
        raise ValueError("IPK exceeds byte budget")
    with ipk.open("rb") as stream:
        raw = read_limited(stream, MAX_IPK_BYTES, "IPK")
    if digest(raw) != expected_sha256:
        raise ValueError("IPK digest differs from independent pin")
    oracle = json.loads(oracle_path.read_text())
    if oracle.get("schema") != "ucode-installed-stage-v1":
        raise ValueError("wrong stage oracle schema")
    expected = {entry["path"]: entry["sha256"] for entry in oracle["files"]}
    expected_selected = {entry["path"] for entry in oracle["files"]
                         if entry["route"]["classification"] != "excluded"}
    if len(expected) != len(oracle["files"]):
        raise ValueError("duplicate oracle path")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as package:
        outer_members = []
        for member in package:
            if len(outer_members) >= MAX_MEMBERS:
                raise ValueError("IPK exceeds member budget")
            outer_members.append(member)
        data_members = [member for member in outer_members if safe_path(member.name) == "data.tar.gz"]
        if len(data_members) != 1 or not data_members[0].isfile():
            raise ValueError("IPK lacks one regular data.tar.gz member")
        if data_members[0].size > MAX_DATA_TAR_BYTES:
            raise ValueError("data.tar.gz exceeds byte budget")
        payload = read_limited(package.extractfile(data_members[0]), MAX_DATA_TAR_BYTES, "data.tar.gz")
    staged: dict[str, bytes] = {}
    selected: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as data_archive:
        seen_members: set[str] = set()
        regular_bytes = 0
        for member in data_archive:
            if len(seen_members) >= MAX_MEMBERS:
                raise ValueError("data archive exceeds member budget")
            name = safe_path(member.name)
            if name in seen_members:
                raise ValueError(f"duplicate data archive member: {name}")
            seen_members.add(name)
            if member.isdir():
                continue
            if not member.isfile():
                if name in expected:
                    raise ValueError(f"expected file is not a regular archive member: {name}")
                continue
            if member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"member exceeds byte budget: {name}")
            regular_bytes += member.size
            if regular_bytes > MAX_TOTAL_REGULAR_BYTES:
                raise ValueError("regular members exceed total byte budget")
            data = read_limited(data_archive.extractfile(member), MAX_MEMBER_BYTES, name)
            if name in staged:
                raise ValueError(f"duplicate regular member: {name}")
            staged[name] = data
            if candidate(name, data):
                selected.add(name)
    if set(staged) != set(expected):
        raise ValueError(f"regular-member inventory differs from oracle: missing={sorted(set(expected)-set(staged))} extra={sorted(set(staged)-set(expected))}")
    if selected != expected_selected:
        raise ValueError(f"selected-member inventory differs from oracle: missing={sorted(expected_selected-selected)} extra={sorted(selected-expected_selected)}")
    for name, data in staged.items():
        if digest(data) != expected[name]:
            raise ValueError(f"member digest mismatch: {name}")
    output.mkdir(parents=True)
    for name, data in staged.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {"schema": "ucode-ipk-stage-receipt-v1", "ipk_sha256": expected_sha256,
            "oracle_sha256": digest(oracle_path.read_bytes()),
            "files": {name: digest(data) for name, data in sorted(staged.items())},
            "selected": sorted(selected), "excluded": sorted(set(staged) - selected)}


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
