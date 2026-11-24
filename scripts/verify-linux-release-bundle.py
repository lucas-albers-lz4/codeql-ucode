#!/usr/bin/env python3
"""Verify extracted producer payload files against bundle-manifest.json."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pack_metadata(path: Path) -> tuple[str, str]:
    text = (path / "qlpack.yml").read_text(encoding="utf-8")
    name = re.search(r"(?m)^name:\s*([^\s#]+)\s*$", text)
    version = re.search(r"(?m)^version:\s*([^\s#]+)\s*$", text)
    if not name or not version:
        raise ValueError(f"invalid QL pack metadata: {path / 'qlpack.yml'}")
    return name.group(1), version.group(1)


def parse_relative_path(rel: str, kind: str) -> PurePosixPath:
    path = PurePosixPath(rel or "")
    if (not rel or path.is_absolute() or ".." in path.parts or "." in path.parts or
            "\\" in rel or path.as_posix() != rel):
        raise ValueError(f"invalid manifest {kind} path: {rel!r}")
    return path


def verify(root: Path) -> dict:
    root = Path(root)
    if root.is_symlink():
        raise ValueError("bundle root must not be a symlink")
    root = root.resolve(strict=True)
    manifest_path = root / "bundle-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("bundle manifest must be a regular file")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("platform") != "linux-x64":
        raise ValueError("unsupported release manifest schema or platform")
    if manifest.get("artifact_kind") != "ci-candidate" or manifest.get("source_checkout_clean") is not True:
        raise ValueError("bundle is not a clean-source CI candidate")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("producer_commit", "")):
        raise ValueError("manifest producer commit is not a full Git SHA")
    build = manifest.get("build")
    if not isinstance(build, dict):
        raise ValueError("manifest build provenance is missing")
    for field, length in (("codeql_cli_linux_zip_sha256", 64), ("cargo_lock_sha256", 64),
                          ("ql_library_lock_sha256", 64), ("ql_query_lock_sha256", 64),
                          ("built_extractor_sha256", 64), ("grammar_revision", 40)):
        if not re.fullmatch(rf"[0-9a-f]{{{length}}}", build.get(field, "")):
            raise ValueError(f"invalid build provenance digest/revision: {field}")
    for field in ("codeql_cli_version", "rustc_version", "cargo_version"):
        if not isinstance(build.get(field), str) or not build[field]:
            raise ValueError(f"missing build provenance field: {field}")
    if manifest.get("codeql_cli_included") is not False:
        raise ValueError("producer bundle must declare CodeQL CLI as separately pinned")
    if manifest.get("bundle_root_mode") != 0o755 or manifest.get("manifest_file_mode") != 0o644:
        raise ValueError("unsupported bundle root/manifest modes")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("manifest files must be a list")
    dir_entries = manifest.get("directories")
    if not isinstance(dir_entries, list):
        raise ValueError("manifest directories must be a list")
    expected: dict[str, dict] = {}
    for item in entries:
        rel = item.get("path")
        path = parse_relative_path(rel, "file")
        if (path.parts[0] not in {"extractor-pack", "ql"} and rel != ".codeqlmanifest.json") or rel in expected:
            raise ValueError(f"invalid or duplicate manifest path: {rel!r}")
        if (not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) or
                not isinstance(item.get("bytes"), int) or item["bytes"] < 0):
            raise ValueError(f"invalid file digest/size in manifest: {rel}")
        if item.get("mode") not in (0o644, 0o755) or item.get("executable") != (item["mode"] == 0o755):
            raise ValueError(f"unsupported payload file mode: {rel}")
        expected[rel] = item
    observed = set()
    expected_dirs = set()
    for item in dir_entries:
        rel = item.get("path")
        path = parse_relative_path(rel, "directory")
        if path.parts[0] not in {"extractor-pack", "ql"} or rel in expected_dirs or rel in expected:
            raise ValueError(f"invalid or duplicate manifest directory: {rel!r}")
        if item.get("mode") != 0o755:
            raise ValueError(f"unsupported payload directory mode: {rel}")
        expected_dirs.add(rel)
    required_files = {
        ".codeqlmanifest.json",
        "extractor-pack/codeql-extractor.yml", "extractor-pack/tools/linux64/extractor", "ql/lib/qlpack.yml",
        "ql/lib/codeql-pack.lock.yml", "ql/src/qlpack.yml",
        "ql/src/codeql-pack.lock.yml", "ql/src/codeql-suites/code-scanning.qls",
    }
    if not required_files.issubset(expected):
        raise ValueError(f"required producer pack files missing: {sorted(required_files-set(expected))}")
    if expected["extractor-pack/tools/linux64/extractor"]["mode"] != 0o755:
        raise ValueError("Linux extractor is not executable")
    extractor_config = (root / "extractor-pack/codeql-extractor.yml").read_text(encoding="utf-8")
    if not re.search(r"(?m)^name:\s*ucode\s*$", extractor_config):
        raise ValueError("extractor pack configuration is not for ucode")
    actual_root_children = {p.name for p in root.iterdir()}
    if actual_root_children != {".codeqlmanifest.json", "bundle-manifest.json", "extractor-pack", "ql"}:
        raise ValueError(f"unexpected bundle-root members: {sorted(actual_root_children)}")
    workspace = json.loads((root / ".codeqlmanifest.json").read_text(encoding="utf-8"))
    if workspace.get("provide") != ["ql/*/qlpack.yml"]:
        raise ValueError("CodeQL workspace manifest does not provide the bundled QL packs")
    workspace_rel = ".codeqlmanifest.json"
    workspace_item = expected[workspace_rel]
    workspace_file = root / workspace_rel
    if (workspace_file.is_symlink() or not workspace_file.is_file() or
            workspace_file.stat().st_size != workspace_item["bytes"] or
            digest(workspace_file) != workspace_item["sha256"] or
            workspace_file.stat().st_mode & 0o777 != workspace_item["mode"]):
        raise ValueError("CodeQL workspace manifest does not match its payload receipt")
    observed.add(workspace_rel)
    ql_root = root / "ql"
    if ql_root.is_symlink() or not ql_root.is_dir() or {p.name for p in ql_root.iterdir()} != {"lib", "src"}:
        raise ValueError("QL pack root must contain exactly lib/ and src/")
    if ql_root.stat().st_mode & 0o777 != 0o755 or "ql" not in expected_dirs:
        raise ValueError("QL root directory mode or manifest entry mismatch")
    observed_dirs = set()
    observed_dirs.add("ql")
    for base in (root / "extractor-pack", root / "ql/lib", root / "ql/src"):
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"missing/invalid payload directory: {base}")
        base_rel = base.relative_to(root).as_posix()
        if base_rel not in expected_dirs or base.stat().st_mode & 0o777 != 0o755:
            raise ValueError(f"payload root directory mode/manifest mismatch: {base_rel}")
        observed_dirs.add(base_rel)
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"unexpected symlink in bundle: {path}")
            if not path.is_file():
                if path.is_dir():
                    rel = path.relative_to(root).as_posix()
                    if rel not in expected_dirs:
                        raise ValueError(f"unmanifested payload directory: {rel}")
                    observed_dirs.add(rel)
                    if path.stat().st_mode & 0o777 != 0o755:
                        raise ValueError(f"payload directory mode mismatch: {rel}")
                continue
            rel = path.relative_to(root).as_posix()
            item = expected.get(rel)
            if item is None:
                raise ValueError(f"unmanifested payload file: {rel}")
            observed.add(rel)
            if path.stat().st_size != item.get("bytes") or digest(path) != item.get("sha256"):
                raise ValueError(f"payload digest/size mismatch: {rel}")
            if path.stat().st_mode & 0o777 != item.get("mode"):
                raise ValueError(f"payload mode mismatch: {rel}")
            if bool(path.stat().st_mode & 0o111) != bool(item.get("executable")):
                raise ValueError(f"payload executable mode mismatch: {rel}")
    missing = set(expected) - observed
    if missing:
        raise ValueError(f"manifest payload file(s) missing: {sorted(missing)}")
    if observed_dirs != expected_dirs:
        raise ValueError(f"manifest directory set mismatch: missing={sorted(expected_dirs-observed_dirs)}")
    if root.stat().st_mode & 0o777 != manifest.get("bundle_root_mode"):
        raise ValueError("bundle root directory mode mismatch")
    if manifest_path.stat().st_mode & 0o777 != manifest.get("manifest_file_mode"):
        raise ValueError("manifest file mode mismatch")
    file_hashes = {rel: item["sha256"] for rel, item in expected.items()}
    if build["built_extractor_sha256"] != file_hashes["extractor-pack/tools/linux64/extractor"]:
        raise ValueError("redundant extractor digest does not match payload entry")
    if build["ql_library_lock_sha256"] != file_hashes["ql/lib/codeql-pack.lock.yml"]:
        raise ValueError("redundant library lock digest does not match payload entry")
    if build["ql_query_lock_sha256"] != file_hashes["ql/src/codeql-pack.lock.yml"]:
        raise ValueError("redundant query lock digest does not match payload entry")
    packs = manifest.get("packs")
    if not isinstance(packs, dict) or packs.get("extractor") != {"path": "extractor-pack", "language": "ucode"}:
        raise ValueError("invalid extractor pack identity")
    lib_name, lib_version = pack_metadata(root / "ql/lib")
    query_name, query_version = pack_metadata(root / "ql/src")
    if packs.get("library") != {"path": "ql/lib", "name": lib_name, "version": lib_version}:
        raise ValueError("library pack name/version differs from the manifest")
    suite = packs.get("queries", {})
    if not isinstance(suite, dict):
        raise ValueError("query pack identity is missing")
    suite_path = parse_relative_path(suite.get("default_suite", ""), "default suite")
    suite_rel = "ql/src/" + suite_path.as_posix()
    if suite.get("path") != "ql/src" or suite.get("name") != query_name or suite.get("version") != query_version:
        raise ValueError("query pack name/version differs from the manifest")
    qlpack_suite = re.search(r"(?m)^defaultSuiteFile:\s*([^\s#]+)\s*$",
                             (root / "ql/src/qlpack.yml").read_text(encoding="utf-8"))
    if not qlpack_suite or qlpack_suite.group(1) != suite["default_suite"]:
        raise ValueError("default suite path differs from query pack metadata")
    if file_hashes.get(suite_rel) != suite.get("default_suite_sha256"):
        raise ValueError("default suite digest differs from the manifest file table")
    query_files = {rel.removeprefix("ql/src/"): item["sha256"] for rel, item in expected.items()
                   if rel.startswith("ql/src/") and rel.endswith(".ql")}
    if query_files != suite.get("query_files"):
        raise ValueError("QL query digest map does not match bundled query files")
    return {"status": "verified", "producer_commit": manifest["producer_commit"],
            "query_pack": manifest["packs"]["queries"],
            "library_pack": manifest["packs"]["library"], "file_count": len(observed)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_root", type=Path, nargs="?",
                        help="extracted codeql-ucode-linux directory")
    parser.add_argument("--archive", type=Path, help="verify and safely extract a pinned tar.gz")
    parser.add_argument("--expected-sha256", help="required when --archive is used")
    parser.add_argument("--output-dir", type=Path, help="new extraction parent for --archive")
    args = parser.parse_args()
    if args.archive:
        if args.bundle_root or not args.expected_sha256 or not args.output_dir:
            parser.error("--archive requires --expected-sha256 and --output-dir, and no bundle_root")
        archive_path = args.archive.resolve(strict=True)
        if not __import__("re").fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
            parser.error("--expected-sha256 must be 64 lowercase hex characters")
        if digest(archive_path) != args.expected_sha256:
            raise ValueError("archive SHA-256 does not match the pinned digest")
        output = args.output_dir.resolve()
        if output.exists():
            raise FileExistsError(f"extraction directory already exists: {output}")
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if not members:
                raise ValueError("empty archive")
            validated = []
            seen = set()
            for member in members:
                name = member.name
                rel = PurePosixPath(name)
                if ("\\" in name or rel.is_absolute() or ".." in rel.parts or
                        "." in rel.parts or not rel.parts or rel.parts[0] != "codeql-ucode-linux"):
                    raise ValueError(f"unsafe archive member path: {name!r}")
                normalized = rel.as_posix().rstrip("/")
                if normalized in seen:
                    raise ValueError(f"duplicate archive member: {normalized}")
                seen.add(normalized)
                if not (member.isdir() or member.isreg()):
                    raise ValueError(f"unsupported archive member type: {name!r}")
                validated.append((member, rel))
            manifest_member = next((member for member in members
                                    if member.name == "codeql-ucode-linux/bundle-manifest.json"), None)
            if manifest_member is None or not manifest_member.isreg():
                raise ValueError("archive is missing its regular bundle manifest")
            root_member = next((member for member in members if member.name == "codeql-ucode-linux"), None)
            if root_member is None or not root_member.isdir():
                raise ValueError("archive root member must be a directory")
            manifest_stream = archive.extractfile(manifest_member)
            if manifest_stream is None:
                raise ValueError("cannot read archive manifest")
            archived_manifest = json.load(manifest_stream)
            expected_names = {"codeql-ucode-linux", "codeql-ucode-linux/bundle-manifest.json"}
            expected_names.update("codeql-ucode-linux/" + item["path"]
                                  for item in archived_manifest.get("files", []))
            expected_names.update("codeql-ucode-linux/" + item["path"]
                                  for item in archived_manifest.get("directories", []))
            if seen != expected_names:
                raise ValueError(f"archive member set mismatch: extra={sorted(seen-expected_names)}, "
                                 f"missing={sorted(expected_names-seen)}")
            if root_member.mode & 0o777 != archived_manifest.get("bundle_root_mode"):
                raise ValueError("archive root directory mode mismatch")
            if manifest_member.mode & 0o777 != archived_manifest.get("manifest_file_mode"):
                raise ValueError("archive manifest file mode mismatch")
            for member, rel in validated:
                if rel.parts[-1] == "bundle-manifest.json" or len(rel.parts) == 1:
                    continue
                rel_payload = PurePosixPath(*rel.parts[1:]).as_posix()
                if member.isdir():
                    table = {item["path"]: item["mode"] for item in archived_manifest.get("directories", [])}
                else:
                    table = {item["path"]: item["mode"] for item in archived_manifest.get("files", [])}
                if rel_payload not in table or (member.mode & 0o777) != table[rel_payload]:
                    raise ValueError(f"archive payload mode mismatch: {member.name}")
            output.mkdir(parents=True)
            for member, rel in validated:
                target = output.joinpath(*rel.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read archive member: {member.name}")
                with stream, target.open("xb") as destination:
                    destination.write(stream.read())
                target.chmod(member.mode & 0o777)
        result = verify(output / "codeql-ucode-linux")
    else:
        if args.expected_sha256 or args.output_dir or not args.bundle_root:
            parser.error("provide bundle_root, or use all three archive options")
        result = verify(args.bundle_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
