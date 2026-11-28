#!/usr/bin/env python3
"""Fresh-database, test-only template interpolation flow experiment for ucode #155."""

from collections import Counter
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "ql/test/issue155-template-flow"
MANIFEST = FIXTURES / "manifest.json"
FLOW = ROOT / "ql/src/testing/issue155-template-flow/TemplateFlow.ql"
NO_EDGE = ROOT / "ql/src/testing/issue155-template-flow/TemplateFlowNoEdge.ql"
WITNESSES = ROOT / "ql/src/testing/issue155-template-flow/TemplateFlowWitnesses.ql"
DELETE_MUTATION = ROOT / "ql/src/testing/issue155-template-flow/TemplateFlowDeleteMutation.ql"
SUCCESS = ROOT / "ql/src/diagnostics/SuccessfullyExtractedFiles.ql"
ERRORS = ROOT / "ql/src/diagnostics/ExtractionErrors.ql"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(raw):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    return json.loads(
        raw,
        object_pairs_hook=object_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("invalid JSON number " + value)),
    )


def tree_hash(root):
    require(root.is_dir() and not root.is_symlink(), "extractor pack must be a physical directory")
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        mode = path.lstat().st_mode
        require(not stat.S_ISLNK(mode), "symlink in extractor pack: " + str(path))
        record = {"path": path.relative_to(root).as_posix(), "mode": stat.S_IMODE(mode)}
        if stat.S_ISREG(mode):
            data = path.read_bytes()
            record.update({"type": "file", "size": len(data), "sha256": digest(data)})
        elif stat.S_ISDIR(mode):
            record.update({"type": "directory", "size": None, "sha256": None})
        else:
            raise ValueError("special file in extractor pack: " + str(path))
        records.append(record)
    return digest(json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def extractor_binary(pack):
    platform_dir = {"Darwin": "osx64", "Linux": "linux64", "Windows": "win64"}.get(platform.system())
    require(platform_dir is not None, "unsupported host platform for extractor provenance")
    binary = pack / "tools" / platform_dir / "extractor"
    require(binary.is_file() and not binary.is_symlink(), "host extractor binary is missing or not physical")
    return binary


def fixture_inventory(manifest):
    actual = []
    for path in sorted(FIXTURES.rglob("*"), key=lambda item: item.relative_to(FIXTURES).as_posix()):
        mode = path.lstat().st_mode
        require(not stat.S_ISLNK(mode), "symlink in fixture tree: " + str(path))
        if path == MANIFEST:
            continue
        if stat.S_ISDIR(mode):
            continue
        require(stat.S_ISREG(mode), "special file in fixture tree: " + str(path))
        relative = path.relative_to(FIXTURES).as_posix()
        data = path.read_bytes()
        actual.append({"path": relative, "bytes": len(data), "mode": stat.S_IMODE(mode), "sha256": digest(data)})
    expected = manifest["files"]
    require(actual == expected, "fixture file inventory, mode, length, or digest differs from manifest")
    source = FIXTURES / "usr/share/rpcd/ucode/ddns.uc"
    require(digest(source.read_bytes()) == manifest["luci_source_sha256"], "pinned LuCI source bytes differ")
    return actual


def entity_location(entity):
    url = entity.get("url")
    require(isinstance(entity.get("id"), int) and isinstance(url, dict), "expected decoded CodeQL entity")
    uri = url.get("uri", "")
    require(uri.startswith("file://"), "entity does not carry a physical source URI")
    return (uri, url["startLine"], url["startColumn"], url["endLine"], url["endColumn"])


def expected_rows(manifest, source_root_uri="file:///fixture"):
    def expected_location(path, position):
        line, start, end = position
        return (source_root_uri + "/" + path, line, start, line, end)

    expected = Counter()
    for row in manifest["expected_flow_rows"]:
        for edge in row["edge_candidates"]:
            expected[(
                row["path"], expected_location(row["path"], row["source"]),
                expected_location(row["path"], row["template_argument"]), expected_location(row["path"], row["call"]),
                expected_location(row["path"], row["formal"]), expected_location(row["path"], row["import_specifier"]),
                expected_location(row["path"], edge["source"]), expected_location(row["path"], edge["substitution"]),
                row["source"][0], row["template_argument"][0], row["call"][0],
            )] += 1
    return expected


def actual_rows(result):
    select = result.get("#select")
    require(select is not None and len(select["columns"]) == 11, "flow result schema changed")
    rows = Counter()
    for row in select["tuples"]:
        require(len(row) == 11, "flow result tuple width changed")
        require(all(isinstance(row[index], dict) for index in range(1, 8)),
                "entity columns 1-7 must match source, argument, call, formal, import, edge-source, substitution roles")
        require([row[index].get("label") for index in (1, 2, 3, 4, 5, 7)] ==
                ["MemberExpression", "template string argument", "CallExpression", "request", "ImportSpecifier", "TemplateSubstitution"] and
                isinstance(row[6].get("label"), str) and row[6].get("label"),
                "entity class labels do not match the declared witness roles")
        require(all(row[index].get("url", {}).get("uri", "").endswith("/" + row[0]) for index in range(1, 8)),
                "flow witness entities do not belong to the declared source file")
        rows[(
            row[0], entity_location(row[1]), entity_location(row[2]), entity_location(row[3]),
            entity_location(row[4]), entity_location(row[5]), entity_location(row[6]),
            entity_location(row[7]), row[8], row[9], row[10],
        )] += 1
        ids = [row[index]["id"] for index in range(1, 8)]
        require(row[1]["id"] != row[2]["id"] and row[2]["id"] != row[3]["id"],
                "source, template argument and call AST identities collapsed")
        require(row[4]["id"] != row[5]["id"], "formal and import specifier identities collapsed")
        require(row[7]["id"] not in ids[:5], "template substitution identity overlaps a witness entity")
    return rows


def verify_witness_identity(flow, witnesses):
    def identities(result):
        rows = Counter()
        for row in result.get("#select", {}).get("tuples", []):
            require(len(row) == 11, "witness query schema changed")
            rows[(row[0], tuple((row[index]["id"], row[index]["label"], entity_location(row[index]))
                                for index in range(1, 8)), row[8], row[9], row[10])] += 1
        return rows

    require(identities(flow) == identities(witnesses),
            "flow entity IDs differ from independent source/ownership witness query")


class Runner:
    def __init__(self, output, cli, pack):
        self.output = output
        self.cli = cli
        self.pack = pack
        self.stage = output / "stage"
        self.db = output / "db"
        self.log_dir = output / "commands"
        self.records = []

    def run(self, label, argv, env=None):
        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        stdout_path = self.log_dir / (label + ".stdout")
        stderr_path = self.log_dir / (label + ".stderr")
        started = time.monotonic()
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            result = subprocess.run([str(arg) for arg in argv], cwd=ROOT, env=command_env,
                                    stdout=stdout, stderr=stderr, check=False)
        record = {
            "label": label,
            "argv": [str(arg) for arg in argv],
            "cwd": str(ROOT),
            "env": {key: command_env[key] for key in ("CODEQL_UCODE_STAGED_ROOT", "TMPDIR", "XDG_CACHE_HOME", "LC_ALL", "TZ") if key in command_env},
            "exit": result.returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout_sha256": digest(stdout_path.read_bytes()),
            "stderr_sha256": digest(stderr_path.read_bytes()),
        }
        self.records.append(record)
        (self.output / "commands.json").write_text(json.dumps(self.records, indent=2, sort_keys=True) + "\n")
        require(result.returncode == 0, label + " failed; see retained command output")
        return stdout_path.read_bytes().decode(errors="replace")

    def decode_query(self, label, query, result_name):
        bqrs = self.output / (label + ".bqrs")
        decoded = self.output / (label + ".json")
        search = str(self.pack) + ":" + str(ROOT / "ql/lib") + ":" + str(ROOT / "ql/src")
        self.run(label + "-run", [self.cli, "query", "run", query, "--database=" + str(self.db),
                                  "--search-path=" + search, "--output=" + str(bqrs),
                                  "--threads=1", "--ram=2048"])
        self.run(label + "-decode", [self.cli, "bqrs", "decode", "--format=json",
                                     "--entities=id,url,string", bqrs, "--output=" + str(decoded)])
        result = strict_json(decoded.read_text())
        return result

    def execute(self, manifest):
        self.log_dir.mkdir()
        self.stage.mkdir()
        for entry in manifest["files"]:
            source = FIXTURES / entry["path"]
            destination = self.stage / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            destination.write_bytes(data)
            destination.chmod(entry["mode"])
            require(digest(destination.read_bytes()) == entry["sha256"], "staged file differs: " + entry["path"])

        cache = self.output / "common-cache"
        temp = self.output / "tmp"
        cache.mkdir()
        temp.mkdir()
        safe_env = {
            "CODEQL_UCODE_STAGED_ROOT": str(self.stage),
            "TMPDIR": str(temp),
            "XDG_CACHE_HOME": str(cache),
            "LC_ALL": "C",
            "TZ": "UTC",
        }
        self.run("version", [self.cli, "version", "--format=json"], safe_env)
        version = strict_json((self.log_dir / "version.stdout").read_text())
        require(version.get("version") == "2.27.4", "expected pinned CodeQL CLI 2.27.4")

        search = str(self.pack) + ":" + str(ROOT / "ql/lib") + ":" + str(ROOT / "ql/src")
        for label, query in (("compile-flow", FLOW), ("compile-no-edge", NO_EDGE),
                             ("compile-witnesses", WITNESSES), ("compile-delete-mutation", DELETE_MUTATION),
                             ("compile-success", SUCCESS), ("compile-errors", ERRORS)):
            self.run(label, [self.cli, "query", "compile", query, "--search-path=" + search,
                             "--warnings=hide"])

        self.run("database-init", [self.cli, "database", "init", self.db, "--language=ucode",
                                   "--search-path=" + str(self.pack),
                                   "--source-root=" + str(self.stage),
                                   "--common-caches=" + str(cache / "database")], safe_env)
        self.run("database-index", [self.cli, "database", "index-files", self.db, "--language=ucode",
                                    "--include=**/*.uc", "--working-dir=" + str(self.stage)], safe_env)
        route_path = self.db / "trap/ucode/routing.json"
        route_bytes = route_path.read_bytes()
        routing = strict_json(route_bytes.decode())
        require(routing.get("input_count") == manifest["expected_indexed_count"] and
                routing.get("plain_count") == manifest["expected_indexed_count"] and
                routing.get("markup_count") == 0 and routing.get("uncertain_count") == 0 and
                routing.get("excluded_count") == 0 and routing.get("duplicate_input_count") == 0,
                "routing counts differ")
        decisions = {row["installed_path"]: row for row in routing["decisions"]}
        expected_paths = {row["path"] for row in manifest["files"] if row["path"].endswith(".uc")}
        require(set(decisions) == expected_paths, "route path inventory differs")
        require(all(row["classification"] == "plain" and row["status"] == "plain_route_selected"
                    for row in decisions.values()), "a fixture did not route as plain ucode")
        real_route = decisions["usr/share/rpcd/ucode/ddns.uc"]
        require(real_route["reason"] != "ucode_shebang", "real fixture used the wrong path alias")
        (self.output / "routing.json").write_text(json.dumps(routing, indent=2, sort_keys=True) + "\n")

        self.run("database-finalize", [self.cli, "database", "finalize", self.db], safe_env)
        successful = self.decode_query("success", SUCCESS, "success")
        errors = self.decode_query("errors", ERRORS, "errors")
        success_rows = successful["#select"]["tuples"]
        successful_paths = {row[0]["url"]["uri"] for row in success_rows}
        expected_success = {((self.stage / row["path"]).as_uri()) for row in manifest["files"]
                            if row["path"] != manifest["malformed_path"]}
        require(len(success_rows) == manifest["expected_successful_count"] and
                successful_paths == expected_success, "exact successful-file identities differ")
        error_rows = errors["#select"]["tuples"]
        require(len(error_rows) == manifest["expected_diagnostic_count"], "extraction diagnostic count differs")
        error = error_rows[0]
        expected_bad_uri = (self.stage / manifest["malformed_path"]).as_uri()
        require(error[0]["url"]["uri"] == expected_bad_uri and error[0]["url"]["startLine"] == 3 and
                error[0]["url"]["startColumn"] == 15 and error[0]["url"]["endLine"] == 3 and
                error[0]["url"]["endColumn"] == 42 and error[2] == 2,
                "malformed-input diagnostic identity or severity differs")
        require(error[0]["label"] == "A parse error occurred. Check the syntax of the file. If the file is invalid, correct the error or exclude the file from analysis.",
                "malformed-input diagnostic category differs")

        flow = self.decode_query("flow", FLOW, "flow")
        witnesses = self.decode_query("witnesses", WITNESSES, "witnesses")
        delete_mutation = self.decode_query("delete-mutation", DELETE_MUTATION, "delete-mutation")
        no_edge = self.decode_query("no-edge", NO_EDGE, "no-edge")
        verify_witness_identity(flow, witnesses)
        mutation_rows = delete_mutation.get("#select", {}).get("tuples", [])
        mutation_types = {"controls/delete-parenthesized.uc": "ParenthesizedExpression",
                          "controls/delete-subscript.uc": "SubscriptExpression"}
        require(len(mutation_rows) == 2 and
                {row[0]: row[1].get("label") for row in mutation_rows} == mutation_types and
                all(row[1].get("url", {}).get("uri", "").endswith("/" + row[0]) for row in mutation_rows),
                "typed delete mutation witnesses differ; member-only legacy guard could still match")
        require(actual_rows(flow) == expected_rows(manifest, self.stage.as_uri()),
                "positive flow and full entity-identity multiset differs")
        require(no_edge["#select"]["tuples"] == [], "edge-disabled mutation retained flow rows")
        observed_paths = {row[0] for row in flow["#select"]["tuples"]}
        expected_positive = {row["path"] for row in manifest["expected_flow_rows"]}
        require(observed_paths == expected_positive, "unexpected positive or missing expected positive")
        require(not observed_paths.intersection(manifest["expected_negative_paths"]),
                "a specified negative control produced a flow row")

        post = fixture_inventory(manifest)
        require(post == manifest["files"], "fixture inputs changed during run")
        stage_files = sorted(path.relative_to(self.stage).as_posix() for path in self.stage.rglob("*") if path.is_file())
        require(stage_files == sorted(row["path"] for row in manifest["files"]), "staged file inventory changed")
        (self.output / "provenance.json").write_text(json.dumps({
            "base": manifest["producer_base"],
            "fixture_manifest_sha256": digest(MANIFEST.read_bytes()),
            "codeql_path": str(self.cli),
            "codeql_binary_sha256": digest(self.cli.read_bytes()),
            "codeql_version": version["version"],
            "extractor_pack_path": str(self.pack),
            "extractor_pack_source_revision": os.environ["UCODE_EXTRACTOR_PACK_SOURCE_REVISION"],
            "extractor_pack_tree_sha256": tree_hash(self.pack),
            "extractor_sha256": digest(extractor_binary(self.pack).read_bytes()),
            "database_path": str(self.db),
            "source_root": str(self.stage),
            "input_inventory": post,
            "routing_sha256": digest(route_bytes),
            "successful_bqrs_sha256": digest((self.output / "success.bqrs").read_bytes()),
            "diagnostics_bqrs_sha256": digest((self.output / "errors.bqrs").read_bytes()),
            "flow_bqrs_sha256": digest((self.output / "flow.bqrs").read_bytes()),
            "witnesses_bqrs_sha256": digest((self.output / "witnesses.bqrs").read_bytes()),
            "delete_mutation_bqrs_sha256": digest((self.output / "delete-mutation.bqrs").read_bytes()),
            "no_edge_bqrs_sha256": digest((self.output / "no-edge.bqrs").read_bytes()),
            "flow_row_count": len(flow["#select"]["tuples"]),
            "no_edge_row_count": len(no_edge["#select"]["tuples"]),
            "diagnostic_count": len(error_rows),
            "limitations": [
                "testing-only local model; no production flow, runtime, reachability, sanitization, authorization, or security claim",
            ],
        }, indent=2, sort_keys=True) + "\n")
        print("template flow experiment: exact routes, diagnostics, positive/negative rows and edge mutation verified")
        print("evidence: " + str(self.output))


def main():
    manifest = strict_json(MANIFEST.read_text())
    require(manifest.get("schema") == "ucode-issue155-template-flow-v1", "fixture manifest schema differs")
    fixture_inventory(manifest)
    cli_value = os.environ.get("CODEQL")
    pack_value = os.environ.get("UCODE_EXTRACTOR_PACK")
    pack_revision = os.environ.get("UCODE_EXTRACTOR_PACK_SOURCE_REVISION")
    output_value = os.environ.get("ISSUE155_TEMPLATE_FLOW_OUT")
    require(cli_value and pack_value and pack_revision and output_value,
            "set CODEQL, UCODE_EXTRACTOR_PACK, UCODE_EXTRACTOR_PACK_SOURCE_REVISION and ISSUE155_TEMPLATE_FLOW_OUT")
    cli = Path(cli_value)
    pack = Path(pack_value)
    require(cli.is_absolute() and cli.is_file() and not cli.is_symlink(), "CODEQL must be an absolute physical executable")
    require(pack.is_absolute() and pack.is_dir() and not pack.is_symlink(), "extractor pack must be an absolute physical directory")
    require((pack / "codeql-extractor.yml").is_file(), "extractor pack descriptor is missing")
    extractor_binary(pack)
    output = Path(output_value)
    require(output.is_absolute() and not output.exists(), "output directory must be fresh and absolute")
    output.mkdir(parents=True)
    runner = Runner(output, cli, pack)
    try:
        runner.execute(manifest)
    except Exception as exc:
        (output / "failure.txt").write_text(repr(exc) + "\n")
        print("template flow experiment failed; evidence retained at " + str(output), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
