#!/usr/bin/env python3
"""Check exact CFG endpoints and the experimental local-expression-flow controls."""
import csv
import json
from pathlib import Path
import sys

FILES = ("break.uc", "break_control.uc", "controls.uc")


def span(source, filename, line, token, occurrence=0):
    text = (source / filename).read_text().splitlines()[line - 1]
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(token, start + 1)
    return (filename, line, start + 1, line, start + len(token))


def marker(source, name, token):
    lines = (source / "controls.uc").read_text().splitlines()
    matches = [i for i, s in enumerate(lines, 1) if s.endswith("// " + name)]
    if len(matches) != 1:
        raise ValueError((name, matches))
    return span(source, "controls.uc", matches[0], token)


def expected_edges(source):
    e = {}
    for name in FILES[:2]:
        e[span(source, name, 5, "break;")] = {span(source, name, 6, "safe")}
        e[span(source, name, 7, "break;")] = {span(source, name, 9, "print")}
    e[marker(source, "inner_break", "break;")] = {marker(source, "after_inner", "print")}
    e[marker(source, "outer_break", "break;")] = {marker(source, "after_switch", "print")}
    e[marker(source, "final_break", "break;")] = {marker(source, "after_switch", "print")}
    e[marker(source, "fallthrough", "print('fallthrough');")] = {marker(source, "final_break", "default: break;")}
    e[marker(source, "final_break", "default: break;")] = {marker(source, "final_break", "break;")}
    e[marker(source, "loop_continue", "continue;")] = {span(source, "controls.uc", 7, "guard")}
    e[marker(source, "switch_continue", "continue;")] = {marker(source, "continue_guard", "guard")}
    e[marker(source, "loop_break", "break;")] = {marker(source, "loop_exit", "print")}
    return e


def csv_rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def verify_edges(source, rows):
    expected = expected_edges(source)
    actual = {key: set() for key in expected}
    for row in rows:
        a = (row["sourceFile"], *(int(row[x]) for x in ("sourceLine", "sourceColumn", "sourceEndLine", "sourceEndColumn")))
        b = (row["targetFile"], *(int(row[x]) for x in ("targetLine", "targetColumn", "targetEndLine", "targetEndColumn")))
        if a in actual:
            actual[a].add(b)
    for key, targets in expected.items():
        if actual[key] != targets:
            raise ValueError(f"CFG successors for {key}: expected {targets}, got {actual[key]}")


def verify_flow(source, rows):
    got = set()
    for row in rows:
        f = row["file"]
        a = (f, *(int(row[x]) for x in ("sourceLine", "sourceColumn", "sourceEndLine", "sourceEndColumn")))
        b = (f, *(int(row[x]) for x in ("readLine", "readColumn", "readEndLine", "readEndColumn")))
        got.add((a, b))
    for name in FILES[:2]:
        pair = (span(source, name, 3, "source()"), span(source, name, 9, "x"))
        if pair in got:
            raise ValueError(f"overwritten source reached final read: {pair}")
    # Each fixture needs its own overwrite-to-read witness for a nonvacuous negative.
    # These spans are source-derived proposals, not yet confirmed by a real CodeQL run.
    for name in FILES[:2]:
        positive = (span(source, name, 6, "'safe'"), span(source, name, 9, "x"))
        if positive not in got:
            raise ValueError(f"missing positive local-expression flow: {positive}")
    positive = (span(source, "controls.uc", 3, "source()"), span(source, "controls.uc", 4, "x"))
    if positive not in got:
        raise ValueError(f"missing positive local-expression flow: {positive}")


def main(out, source):
    fixtures = Path(__file__).resolve().parent.parent / "ql/test/switch-break"
    if {p.name for p in source.iterdir()} != set(FILES):
        raise ValueError("unexpected source fixture inventory")
    for name in FILES:
        if (source / name).read_bytes() != (fixtures / name).read_bytes():
            raise ValueError(f"fixture differs: {name}")
    route = json.loads((out / "routing.json").read_text())
    expected = {"input_count": 3, "plain_count": 3, "markup_count": 0,
                "markup_inconclusive_count": 0, "uncertain_count": 0,
                "excluded_count": 0, "duplicate_input_count": 0}
    decisions = {(
        item["path"], item["installed_path"], item["classification"],
        item["reason"], item["status"]
    ) for item in route["decisions"]}
    wanted = {(str(source / name), name, "plain", "ucode_extension", "plain_route_selected")
              for name in FILES}
    if (any(route.get(key) != value for key, value in expected.items()) or
            len(route["decisions"]) != len(FILES) or decisions != wanted):
        raise ValueError(f"unexpected routing: {route}")
    extracted = csv_rows(out / "extracted.csv")
    errors = csv_rows(out / "errors.csv")
    paths = [row["f"] for row in extracted]
    if sorted(paths) != sorted(str(source / name) for name in FILES) or errors:
        raise ValueError(f"extraction diagnostics: {paths=}, {errors=}")
    verify_edges(source, csv_rows(out / "edges.csv"))
    verify_flow(source, csv_rows(out / "flow.csv"))
    print("switch-break exact CFG and local-expression-flow checks passed")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: switch-break-verify.py OUT SOURCE")
    main(Path(sys.argv[1]), Path(sys.argv[2]).resolve())
