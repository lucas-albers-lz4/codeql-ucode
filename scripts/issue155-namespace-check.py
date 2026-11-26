#!/usr/bin/env python3
"""Check exact AST and model identities for the small namespace fs probe."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "ql/test/issue155-namespace-stat"

FIXTURE_NAMES = {
    "alias-assignment.uc", "alias-write.uc", "alias.uc", "bracket-delete.uc",
    "bracket-write.uc", "changed-member.uc", "delete-member.uc", "dynamic.uc",
    "extra-argument.uc", "fixed-literal.uc", "named.uc", "no-argument.uc",
    "optional-call.uc", "optional.uc", "real-shape.uc", "reassigned.uc",
    "shadowed.uc", "spread.uc", "wrong-member.uc", "wrong-module.uc",
    "luci.advanced-reboot",
}

# Source-derived expectations for the three model members. Literal arguments
# remain model members; they are near misses for any later path-flow question.
EXPECTED = {
    "real-shape.uc": (3, "fs.stat(file_name)", "fs.stat", "file_name"),
    "fixed-literal.uc": (2, "fs.stat('/etc/ssl/certs/ca-certificates.crt')", "fs.stat", "'/etc/ssl/certs/ca-certificates.crt'"),
    "luci.advanced-reboot": (60, "fs.stat(p)", "fs.stat", "p"),
}



def tuples(directory: Path, name: str):
    return json.loads((directory / f"{name}.json").read_text())["#select"]["tuples"]


def check(directory: Path):
    if not __debug__:
        raise RuntimeError("run this checker without Python -O")
    oracle = json.loads((directory / "oracle-before-output.json").read_text())
    assert json.loads((directory / "expected-before-output.json").read_text()) == {
        path: list(witness) for path, witness in EXPECTED.items()
    }
    assert hashlib.sha256((FIXTURES / "luci.advanced-reboot").read_bytes()).hexdigest() == "b6b5562036c1f2f93ec9ea9261943a17d667d5a742c71ce128ec4859279d4b11"
    sources = sorted(p.name for p in FIXTURES.iterdir() if p.is_file())
    assert set(sources) == FIXTURE_NAMES
    assert sorted(oracle) == sources
    def staged(path):
        return directory / "stage" / ("usr/share/rpcd/ucode/" + path if path == "luci.advanced-reboot" else path)
    for path in sources:
        data = (FIXTURES / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == oracle[path]["sha256"]
        assert data.decode() == oracle[path]["text"]
        assert data == staged(path).read_bytes()
    with ZipFile(directory / "db/src.zip") as archive:
        members = archive.namelist()
        expected_members = [str(staged(path).resolve()).lstrip("/") for path in sources]
        assert Counter(members) == Counter(expected_members)
        for member in members:
            assert archive.read(member) == (FIXTURES / Path(member).name).read_bytes()
    success_rows = tuples(directory, "success")
    success = [row[0]["label"] for row in success_rows]
    expected_success = [str(staged(path).resolve()) for path in sources]
    assert Counter(success) == Counter(expected_success), success
    assert Counter(row[0]["url"]["uri"] for row in success_rows) == Counter(
        staged(path).resolve().as_uri() for path in sources
    )
    assert tuples(directory, "errors") == []

    raw = tuples(directory, "ast")
    by_id = {row[1]["id"]: row for row in raw}
    assert len(by_id) == len(raw)

    def node(path, kind, line, fragment):
        source_line = oracle[path]["text"].splitlines()[line - 1]
        assert fragment in source_line, (path, fragment)
        start = source_line.index(fragment) + 1
        matches = [row for row in raw if row[0] == path and row[2] == kind and
                   row[4:8] == [line, start, line, start + len(fragment) - 1]]
        assert len(matches) == 1, (path, kind, fragment, matches)
        return matches[0]

    def parent(row, kind):
        owner = by_id[row[8]["id"]]
        assert owner[2] == kind, (row, owner)
        return owner

    direct = tuples(directory, "stat")
    namespace = tuples(directory, "namespace-stat")
    assert [row[0] for row in direct] == ["named.uc"]
    assert Counter(row[0] for row in namespace) == Counter(EXPECTED.keys()), namespace
    class_rows = tuples(directory, "namespace-class")
    assert Counter((row[0], row[1]["id"]) for row in class_rows) == Counter(
        (row[0], row[1]["id"]) for row in namespace
    ), class_rows
    for row in namespace:
        path = row[0]
        line, call_text, callee_text, arg_text = EXPECTED[path]
        call = node(path, "CallExpression", line, call_text)
        callee = node(path, "MemberExpression", line, callee_text)
        assert parent(callee, "CallExpression")[1] == call[1]
        kind = "String" if arg_text.startswith("'") else "Identifier"
        arg = node(path, kind, line, arg_text)
        assert parent(parent(arg, "Arguments"), "CallExpression")[1] == call[1]
        assert [entity["id"] for entity in row[1:]] == [call[1]["id"], callee[1]["id"], arg[1]["id"]]
    print(f"verified {len(sources)} exact extraction identities, zero errors, "
          "three namespace stat identities and named-stat regression")



if __name__ == "__main__":
    check(Path(sys.argv[1]))
