#!/usr/bin/env python3
"""Fetch one pinned Actions artifact ZIP and extract only its pinned IPK."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import stat
import subprocess
import sys
import tempfile
import time
import zipfile


MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_IPK_BYTES = 4 * 1024 * 1024
MAX_MEMBERS = 128
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
REPO = "lucas-albers-lz4/codeql-openwrt"


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def gh_bytes(endpoint: str, limit: int, destination: Path | None = None) -> tuple[bytes, str, int]:
    """Stream gh stdout with a live limit; never retain or display raw stderr."""
    need(bool(os.environ.get("GH_TOKEN")), "GH_TOKEN is required")
    with tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(["gh", "api", "-H", "Accept: application/vnd.github+json", endpoint],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=stderr,
                                   env={**os.environ, "GH_PROMPT_DISABLED": "1"})
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 300
        total = 0
        h = hashlib.sha256()
        pieces: list[bytes] = []
        output = None
        try:
            if destination is not None:
                output = destination.open("xb")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                need(remaining > 0, "GitHub artifact request timed out")
                for key, _ in selector.select(min(remaining, 1.0)):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    total += len(block)
                    need(total <= limit, "GitHub artifact response exceeds byte budget")
                    h.update(block)
                    if output is None:
                        pieces.append(block)
                    else:
                        output.write(block)
            remaining = deadline - time.monotonic()
            need(remaining > 0, "GitHub artifact request timed out")
            status = process.wait(timeout=remaining)
            need(status == 0, f"GitHub artifact request failed with status {status}")
            if output is not None:
                output.flush()
                os.fsync(output.fileno())
        except (Exception, subprocess.TimeoutExpired) as error:
            if process.poll() is None:
                process.kill()
            process.wait()
            if destination is not None:
                destination.unlink(missing_ok=True)
            if isinstance(error, subprocess.TimeoutExpired):
                raise ValueError("GitHub artifact request timed out") from error
            raise
        finally:
            selector.close()
            if output is not None:
                output.close()
            if not process.stdout.closed:
                process.stdout.close()
    return b"".join(pieces), h.hexdigest(), total


def check_metadata(data: bytes, *, artifact_id: int, run_id: int, name: str,
                   zip_sha256: str) -> None:
    record = json.loads(data)
    need(record.get("id") == artifact_id and record.get("name") == name and
         record.get("expired") is False, "artifact ID, name or retention state differs from pin")
    workflow = record.get("workflow_run")
    need(isinstance(workflow, dict) and workflow.get("id") == run_id,
         "artifact workflow run differs from pin")
    size = record.get("size_in_bytes")
    need(type(size) is int and 0 < size <= MAX_ZIP_BYTES,
         "artifact reported ZIP size exceeds byte budget")
    api_digest = record.get("digest")
    if api_digest is not None:
        need(api_digest == f"sha256:{zip_sha256}", "artifact API digest differs from reviewed ZIP pin")


def check_zip(archive: zipfile.ZipFile, ipk_name: str) -> zipfile.ZipInfo:
    members = archive.infolist()
    need(0 < len(members) <= MAX_MEMBERS, "artifact ZIP member count exceeds budget")
    seen: set[str] = set()
    total = 0
    selected = []
    for member in members:
        name = member.filename
        path = PurePosixPath(name)
        need(bool(name) and not path.is_absolute() and path.as_posix() == name and
             "\\" not in name and "\x00" not in name and
             all(part not in {"", ".", ".."} for part in name.split("/")),
             "artifact ZIP contains unsafe member path")
        need(name not in seen, "artifact ZIP contains duplicate member")
        seen.add(name)
        mode = (member.external_attr >> 16) & 0xffff
        need(stat.S_IFMT(mode) in {0, stat.S_IFREG} and not member.is_dir(),
             "artifact ZIP contains link, directory or special member")
        need(not member.flag_bits & 1 and member.compress_type in
             {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED},
             "artifact ZIP contains encrypted or unsupported member")
        need(0 <= member.file_size <= MAX_MEMBER_BYTES and
             0 <= member.compress_size <= MAX_ZIP_BYTES,
             "artifact ZIP member size exceeds budget")
        total += member.file_size
        need(total <= MAX_TOTAL_BYTES, "artifact ZIP declared size exceeds budget")
        if name == ipk_name:
            selected.append(member)
    need(len(selected) == 1, "artifact ZIP must contain the named IPK exactly once")
    need(0 < selected[0].file_size <= MAX_IPK_BYTES, "pinned IPK exceeds byte budget")
    return selected[0]


def extract_ipk(zip_path: Path, ipk_name: str, expected_sha256: str, target: Path) -> dict:
    need(not target.exists() and not target.is_symlink(), "IPK output already exists")
    with zipfile.ZipFile(zip_path) as archive:
        member = check_zip(archive, ipk_name)
        h = hashlib.sha256()
        total = 0
        try:
            with target.open("xb") as output, archive.open(member) as source:
                while block := source.read(65536):
                    total += len(block)
                    need(total <= member.file_size and total <= MAX_IPK_BYTES,
                         "IPK expands beyond declared or allowed size")
                    h.update(block)
                    output.write(block)
            need(total == member.file_size and h.hexdigest() == expected_sha256,
                 "IPK size or SHA-256 differs from independent pin")
        except Exception:
            target.unlink(missing_ok=True)
            raise
    return {"ipk_sha256": h.hexdigest(), "ipk_bytes": total, "member_name": ipk_name}


def fetch(args: argparse.Namespace) -> dict:
    need(args.artifact_id > 0 and args.run_id > 0 and
         HEX64.fullmatch(args.zip_sha256) is not None and
         HEX64.fullmatch(args.ipk_sha256) is not None,
         "invalid artifact identity or digest pin")
    need(PurePosixPath(args.ipk_name).name == args.ipk_name and args.ipk_name.endswith(".ipk"),
         "IPK name must be a simple .ipk filename")
    output = args.output.absolute()
    need(not output.exists() and not output.is_symlink(), "artifact output already exists")
    need(output.parent.is_dir() and not output.parent.is_symlink(), "artifact parent is not a real directory")
    started = time.monotonic()
    metadata, _, _ = gh_bytes(f"/repos/{REPO}/actions/artifacts/{args.artifact_id}", MAX_METADATA_BYTES)
    check_metadata(metadata, artifact_id=args.artifact_id, run_id=args.run_id,
                   name=args.artifact_name, zip_sha256=args.zip_sha256)
    metadata_seconds = round(time.monotonic() - started, 3)
    output.mkdir(mode=0o700)
    zip_path = output / "artifact.zip"
    started = time.monotonic()
    _, observed_sha, size = gh_bytes(f"/repos/{REPO}/actions/artifacts/{args.artifact_id}/zip",
                                     MAX_ZIP_BYTES, zip_path)
    need(observed_sha == args.zip_sha256 and sha256(zip_path) == args.zip_sha256,
         "downloaded artifact ZIP differs from reviewed SHA-256 pin")
    download_seconds = round(time.monotonic() - started, 3)
    started = time.monotonic()
    ipk = extract_ipk(zip_path, args.ipk_name, args.ipk_sha256, output / args.ipk_name)
    extraction_seconds = round(time.monotonic() - started, 3)
    return {"schema": "r25-pinned-artifact-v1", "repository": REPO,
            "run_id": args.run_id, "artifact_id": args.artifact_id,
            "artifact_name": args.artifact_name, "zip_sha256": observed_sha,
            "zip_bytes": size, "metadata_seconds": metadata_seconds,
            "download_seconds": download_seconds,
            "extraction_seconds": extraction_seconds, **ipk}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--zip-sha256", required=True)
    parser.add_argument("--ipk-name", required=True)
    parser.add_argument("--ipk-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(fetch(args), indent=2, sort_keys=True))
    except Exception as error:
        print(f"pinned artifact download failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
