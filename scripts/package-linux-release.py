#!/usr/bin/env python3
"""Create a deterministic Linux producer bundle after the R2 build gate.

The CodeQL CLI is intentionally not copied into the bundle. Downstream pins and
verifies the CLI archive separately, then uses this bundle as its CodeQL search
path and extractor search path.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile


PAYLOADS = ("extractor-pack", "ql/lib", "ql/src", "runner")
CONTROL_FILES = (".codeqlmanifest.json",)
SCHEMA_VERSION = 1


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def metadata(pack: Path) -> tuple[str, str]:
    text = (pack / "qlpack.yml").read_text(encoding="utf-8")
    name = re.search(r"(?m)^name:\s*([^\s#]+)\s*$", text)
    version = re.search(r"(?m)^version:\s*([^\s#]+)\s*$", text)
    if not name or not version:
        raise ValueError(f"missing pack name/version in {pack / 'qlpack.yml'}")
    return name.group(1), version.group(1)


def tree_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in {".codeql", "__pycache__"} for part in rel.parts) or path.suffix in {".qlx", ".pyc"}:
            continue
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed in release payload: {path}")
        if path.is_file():
            files.append(path)
    return files


def copy_payload(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    for original in tree_files(source):
        target = destination / original.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    for directory in sorted((p for p in destination.rglob("*") if p.is_dir()), reverse=True):
        directory.chmod(0o755)
    destination.chmod(0o755)


def create_bundle(source: Path, output: Path, producer_commit: str,
                  codeql_version: str, rustc: str, cargo: str,
                  grammar_revision: str, codeql_archive_sha256: str,
                  source_clean: bool, release_tag: str | None = None,
                  grammar_patch_sha256: str | None = None,
                  grammar_generated_files_sha256: str | None = None) -> dict:
    source = source.resolve(strict=True)
    output = output.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", producer_commit):
        raise ValueError("producer commit must be a full 40-character Git SHA")
    if not codeql_version or not rustc or not cargo or not grammar_revision:
        raise ValueError("CodeQL, Rust, Cargo and grammar versions are required")
    if not re.fullmatch(r"[0-9a-f]{64}", codeql_archive_sha256):
        raise ValueError("CodeQL CLI archive SHA-256 must be a full lowercase digest")
    if not grammar_patch_sha256 or not re.fullmatch(r"[0-9a-f]{64}", grammar_patch_sha256):
        raise ValueError("grammar patch SHA-256 must be a full lowercase digest")
    if not grammar_generated_files_sha256 or not re.fullmatch(r"[0-9a-f]{64}", grammar_generated_files_sha256):
        raise ValueError("generated grammar files SHA-256 must be a full lowercase digest")
    if not source_clean:
        raise ValueError("release bundle requires a clean producer source checkout")
    if release_tag is not None and not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", release_tag):
        raise ValueError("release tag must be a versioned vMAJOR.MINOR.PATCH tag")
    for rel in PAYLOADS:
        p = source / rel
        if not p.is_dir():
            raise ValueError(f"missing required payload directory: {p}")
        if p.is_symlink():
            raise ValueError(f"payload roots must not be symlinks: {p}")
        tree_files(p)  # reject symlinks before copytree could dereference them
    for rel in CONTROL_FILES:
        if not (source / rel).is_file() or (source / rel).is_symlink():
            raise ValueError(f"missing required CodeQL workspace control file: {rel}")
    extractor = source / "extractor-pack/tools/linux64/extractor"
    if not extractor.is_file() or not os.access(extractor, os.X_OK):
        raise ValueError(f"missing executable Linux extractor: {extractor}")
    src_pack = source / "ql/src"
    lib_pack = source / "ql/lib"
    query_pack_name, query_pack_version = metadata(src_pack)
    lib_pack_name, lib_pack_version = metadata(lib_pack)
    suite = src_pack / "codeql-suites/code-scanning.qls"
    if not suite.is_file():
        raise ValueError(f"missing default code-scanning suite: {suite}")
    for lock in (src_pack / "codeql-pack.lock.yml", lib_pack / "codeql-pack.lock.yml"):
        if not lock.is_file():
            raise ValueError(f"missing CodeQL pack lock: {lock}")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    with tempfile.TemporaryDirectory(prefix="ucode-release-bundle-") as temp_text:
        temp = Path(temp_text)
        bundle = temp / "codeql-ucode-linux"
        bundle.mkdir()
        for rel in PAYLOADS:
            copy_payload(source / rel, bundle / rel)
        for rel in CONTROL_FILES:
            shutil.copy2(source / rel, bundle / rel)

        entries = []
        directories = []
        for path in sorted(p for p in bundle.rglob("*") if p.is_dir()):
            path.chmod(0o755)
            directories.append({"path": path.relative_to(bundle).as_posix(), "mode": 0o755})
        for rel in PAYLOADS:
            for path in tree_files(bundle / rel):
                entries.append({
                    "path": path.relative_to(bundle).as_posix(),
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                    "mode": path.stat().st_mode & 0o777,
                    "executable": bool(path.stat().st_mode & 0o111),
                })
        for rel in CONTROL_FILES:
            path = bundle / rel
            entries.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size,
                            "mode": path.stat().st_mode & 0o777,
                            "executable": bool(path.stat().st_mode & 0o111)})
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": "versioned-release" if release_tag else "ci-candidate",
            "platform": "linux-x64",
            "bundle_root_mode": 0o755,
            "manifest_file_mode": 0o644,
            "producer_commit": producer_commit,
            "release_tag": release_tag,
            "source_checkout_clean": source_clean,
            "build": {
                "codeql_cli_version": codeql_version,
                "codeql_cli_linux_zip_sha256": codeql_archive_sha256,
                "rustc_version": rustc,
                "cargo_version": cargo,
                "grammar_revision": grammar_revision,
                "grammar_patch_sha256": grammar_patch_sha256,
                "grammar_generated_files_sha256": grammar_generated_files_sha256,
                "cargo_lock_sha256": sha256(source / "Cargo.lock"),
                "ql_library_lock_sha256": sha256(lib_pack / "codeql-pack.lock.yml"),
                "ql_query_lock_sha256": sha256(src_pack / "codeql-pack.lock.yml"),
                "built_extractor_sha256": sha256(extractor),
                "reproducibility": "deterministic archive; native extractor rebuild identity is recorded, not asserted byte-reproducible",
            },
            "packs": {
                "extractor": {"path": "extractor-pack", "language": "ucode"},
                "library": {"path": "ql/lib", "name": lib_pack_name, "version": lib_pack_version},
                "queries": {"path": "ql/src", "name": query_pack_name, "version": query_pack_version,
                            "default_suite": "codeql-suites/code-scanning.qls",
                            "default_suite_sha256": sha256(suite),
                            "query_files": {p.relative_to(src_pack).as_posix(): sha256(p)
                                            for p in tree_files(src_pack) if p.suffix == ".ql"}},
            },
            "codeql_cli_included": False,
            "directories": sorted(directories, key=lambda item: item["path"]),
            "files": entries,
        }
        manifest_path = bundle / "bundle-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_path.chmod(0o644)
        bundle.chmod(0o755)
        with output.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    archive_paths = [bundle, *bundle.rglob("*")]
                    for path in sorted(archive_paths):
                        if path.is_symlink():
                            raise ValueError(f"symlinks appeared in bundle payload: {path}")
                        if path.is_dir() and any(part in {".codeql", "__pycache__"} for part in path.parts):
                            continue
                        if path.is_file() and (path.suffix in {".qlx", ".pyc"} or
                                any(part in {".codeql", "__pycache__"} for part in path.parts)):
                            continue
                        rel = Path("codeql-ucode-linux") / path.relative_to(bundle)
                        info = archive.gettarinfo(str(path), arcname=rel.as_posix())
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mtime = 0
                        info.mode = 0o755 if path.is_dir() else path.stat().st_mode & 0o777
                        if path.is_file():
                            with path.open("rb") as stream:
                                archive.addfile(info, stream)
                        else:
                            archive.addfile(info)
    return {"archive": str(output), "archive_sha256": sha256(output), "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="built, isolated producer tree")
    parser.add_argument("--output", type=Path, required=True, help="new .tar.gz output path")
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--codeql-version", required=True)
    parser.add_argument("--rustc-version", required=True)
    parser.add_argument("--cargo-version", required=True)
    parser.add_argument("--grammar-revision", required=True)
    parser.add_argument("--grammar-patch-sha256", required=True)
    parser.add_argument("--grammar-generated-files-sha256", required=True)
    parser.add_argument("--codeql-archive-sha256", required=True)
    parser.add_argument("--source-clean", action="store_true",
                        help="assert that the release gate verified a clean source checkout")
    parser.add_argument("--release-tag", help="versioned release tag; omit for a CI candidate")
    args = parser.parse_args()
    result = create_bundle(args.source, args.output, args.producer_commit,
                           args.codeql_version, args.rustc_version,
                           args.cargo_version, args.grammar_revision,
                           args.codeql_archive_sha256, args.source_clean, args.release_tag,
                           args.grammar_patch_sha256, args.grammar_generated_files_sha256)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
