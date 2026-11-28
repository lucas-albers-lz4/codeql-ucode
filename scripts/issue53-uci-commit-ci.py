#!/usr/bin/env python3
"""Source-declared UCI commit identity smoke; no runtime or flow claim."""

from collections import Counter
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "ql/test/issue53-uci-commit"
PACK = (ROOT / "extractor-pack").resolve()
spec = importlib.util.spec_from_file_location(
    "stat_gate", ROOT / "scripts/issue155-stat-ci.py"
)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
require = common.require
oracle = common.oracle


def stage_inputs(stage):
    manifest = common.inputs.load(FIX / "source-first.json")
    entries = manifest["entries"]
    require(
        len(entries) == 31 and len({e["path"] for e in entries}) == 31,
        "fixture inventory",
    )
    for e in entries:
        path = Path(e["path"])
        require(
            not path.is_absolute()
            and ".." not in path.parts
            and "." not in path.parts
            and str(path) == e["path"]
            and (
                path.parts[:1] == ("controls",)
                and len(path.parts) == 2
                and path.suffix == ".uc"
                or e["path"] == "usr/share/rpcd/ucode/luci.adblock-fast"
            ),
            "fixture path",
        )
        require(
            e["expected"] in ("model", "model-three", "inconclusive"),
            "fixture classification",
        )
    require(
        {e["path"] for e in entries if e["expected"] == "model"}
        == {
            "controls/positive.uc",
            "controls/other-scope-write.uc",
            "controls/other-scope-member.uc",
        }
        and [e["path"] for e in entries if e["expected"] == "model-three"]
        == ["usr/share/rpcd/ucode/luci.adblock-fast"]
        and all(
            len(e["calls"]) == (3 if e["expected"] == "model-three" else 1)
            for e in entries
            if e["expected"] in ("model", "model-three")
        ),
        "positive fixture cohort",
    )
    for e in entries:
        src = FIX / e["path"]
        require(
            not src.is_symlink()
            and src.is_file()
            and src.resolve().is_relative_to(FIX.resolve()),
            "fixture source path",
        )
        data = src.read_bytes()
        require(
            len(data) == e["bytes"] and hashlib.sha256(data).hexdigest() == e["sha256"],
            "source bytes: " + e["path"],
        )

        def anchors(x):
            if isinstance(x, dict):
                if {"text", "line", "column", "end_column_exclusive", "offset"} <= set(
                    x
                ):
                    encoded = x["text"].encode()
                    lines = data.splitlines(keepends=True)
                    line = lines[x["line"] - 1]
                    line_start = sum(map(len, lines[: x["line"] - 1]))
                    require(
                        line_start + x["column"] - 1 == x["offset"],
                        "source anchor coordinate offset: " + e["path"],
                    )
                    require(
                        line[x["column"] - 1 : x["end_column_exclusive"] - 1] == encoded
                        and data[x["offset"] : x["offset"] + len(encoded)] == encoded,
                        "source anchor: " + e["path"],
                    )
                else:
                    for v in x.values():
                        anchors(v)
            elif isinstance(x, list):
                for v in x:
                    anchors(v)

        anchors(e)
        dest = stage / e["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        e["expected_route"] = {
            "classification": "plain",
            "reason": "rpcd_raw_mode_full_path"
            if e["path"].startswith("usr/")
            else "ucode_extension",
            "status": "plain_route_selected",
        }
    return entries


def verify(stage, entries, results):
    raw, edges, access = map(
        oracle.tuples, (results["raw"], results["edges"], results["access"])
    )

    def node(path, kind, a):
        return oracle.node(
            raw,
            path,
            kind,
            {
                "start": [a["line"], a["column"]],
                "end_exclusive": [a["line"], a["end_column_exclusive"]],
            },
        )

    def targets(path, source, field):
        return [
            (r[4], r[5]["id"])
            for r in edges
            if r[0] == path and r[1] == {"id": source} and r[3] == field
        ]

    expected = []
    real_variables = set()
    adjacency = []

    def parent(path, ident):
        rows = [r for r in raw if r[0] == path and r[7] == {"id": ident}]
        require(len(rows) == 1, path + ": raw parent identity")
        return rows[0][14]["id"]

    for e in entries:
        if e["expected"] not in ("model", "model-three"):
            continue
        path = e["path"]
        roles = e["roles"]
        imp = node(path, "ImportStatement", roles["import"])
        spec = node(path, "ImportSpecifier", roles["specifier"])
        decl = node(path, "VariableDeclarator", roles["declaration"])
        declname = node(path, "Identifier", roles["decl_name"])
        init = node(path, "CallExpression", roles["initializer"])
        initcallee = node(path, "Identifier", roles["init_callee"])
        source = node(path, "String", roles["import_source"])
        sourcefrag = node(path, "StringFragment", roles["import_fragment"])
        specname = node(path, "Identifier", roles["specifier_name"])
        require(
            targets(path, decl, "declarator-name") == [(-1, declname)]
            and targets(path, decl, "declarator-value") == [(-1, init)]
            and targets(path, init, "call-function") == [(-1, initcallee)],
            path + ": initializer edges",
        )
        owners = targets(path, init, "call-arguments")
        require(
            len(owners) == 1 and not targets(path, owners[0][1], "argument"),
            path + ": constructor arity",
        )
        require(
            targets(path, imp, "import-source") == [(-1, source)]
            and targets(path, source, "string-child") == [(0, sourcefrag)]
            and targets(path, spec, "import-name") == [(-1, specname)]
            and not targets(path, spec, "import-alias"),
            path + ": import identity",
        )
        clause = targets(path, imp, "import-clause")
        require(len(clause) == 1, path + ": import clause")
        named = targets(path, clause[0][1], "import-named")
        require(
            len(named) == 1
            and any(x[1] == spec for x in targets(path, named[0][1], "named-import")),
            path + ": specifier edge",
        )
        for c in e["calls"]:
            call = node(path, "CallExpression", c["call"])
            member = node(path, "MemberExpression", c["member"])
            receiver = node(path, "Identifier", c["receiver"])
            prop = node(path, "PropertyIdentifier", c["property"])
            arg = node(path, "String", c["argument"])
            argfrag = node(path, "StringFragment", c["argument_fragment"])
            require(
                targets(path, call, "call-function") == [(-1, member)]
                and targets(path, member, "member-object") == [(-1, receiver)]
                and targets(path, member, "member-property") == [(-1, prop)],
                path + ": member edges",
            )
            owner = targets(path, call, "call-arguments")
            require(
                len(owner) == 1
                and targets(path, owner[0][1], "argument") == [(0, arg)]
                and targets(path, arg, "string-child") == [(0, argfrag)],
                path + ": argument edge",
            )
            bindings = [
                r
                for r in access
                if r[0] == path and r[1] == "read" and r[3] == {"id": receiver}
            ]
            require(
                len(bindings) == 1 and bindings[0][10] == {"id": decl},
                path + ": receiver binding",
            )
            if e["expected"] == "model-three":
                real_variables.add(bindings[0][9]["id"])
            expected.append((path, call, imp, spec, decl, init, receiver, arg))
            restart_anchor = c.get("restart") or (
                e.get("restart") if e["path"] == "controls/positive.uc" else None
            )
            if restart_anchor:
                restart = node(path, "CallExpression", restart_anchor)
                first = parent(path, call)
                second = parent(path, restart)
                owner = parent(path, first)
                owner_spec = c["statement_owner"]
                require(
                    oracle.node(raw, path, owner_spec["kind"], owner_spec) == owner,
                    path + ": expected owner",
                )
                restart_name = node(path, "Identifier", c["restart_callee"])
                restart_arg = node(path, "String", c["restart_argument"])
                restart_fragment = node(path, "StringFragment", c["restart_fragment"])
                restart_args = targets(path, restart, "call-arguments")
                require(
                    targets(path, restart, "call-function") == [(-1, restart_name)]
                    and len(restart_args) == 1
                    and targets(path, restart_args[0][1], "argument")
                    == [(0, restart_arg)]
                    and targets(path, restart_arg, "string-child")
                    == [(0, restart_fragment)],
                    path + ": restart edges",
                )
                scope = e["function"]
                expected_function = oracle.node(raw, path, scope["kind"], scope)

                def enclosing(ident):
                    seen = set()
                    while ident not in seen:
                        seen.add(ident)
                        matches = [
                            r for r in raw if r[0] == path and r[7] == {"id": ident}
                        ]
                        require(len(matches) == 1, path + ": ancestry missing")
                        if matches[0][1] in (
                            "FunctionDeclaration",
                            "FunctionExpression",
                            "ArrowFunction",
                        ):
                            return ident
                        ident = matches[0][14]["id"]
                    raise ValueError(path + ": ancestry cycle")

                require(
                    enclosing(call) == expected_function
                    and enclosing(restart) == expected_function
                    and enclosing(decl) == expected_function,
                    path + ": nearest function",
                )
                require(
                    parent(path, second) == owner, path + ": distinct statement owners"
                )
                verify_statement_expression_edges(
                    path, first, call, second, restart, targets
                )
                children = targets(path, owner, "statement-child")
                firsts = [i for i, x in children if x == first]
                require(
                    firsts == [owner_spec["index"]]
                    and (firsts[0] + 1, second) in children,
                    path + ": statement adjacency",
                )
                adjacency.append((path, call, restart, owner, firsts[0], first, second))
    require(len(real_variables) == 1, "real receiver variable identity")
    actual = Counter(
        (r[0], *(v["id"] for v in r[1:])) for r in oracle.tuples(results["association"])
    )
    require(actual == Counter(expected), "association exact identities or multiplicity")
    success = Counter(r[0]["url"]["uri"] for r in oracle.tuples(results["success"]))
    require(
        success
        == Counter(
            (stage / e["path"]).as_uri()
            for e in entries
            if e["path"] != "controls/malformed.uc"
        ),
        "successful file identities",
    )
    require(
        [c["kind"] for c in results["errors"]["#select"]["columns"]]
        == ["Entity", "String", "Integer"],
        "diagnostic schema",
    )
    errors = oracle.tuples(results["errors"])
    label = "A parse error occurred. Check the syntax of the file. If the file is invalid, correct the error or exclude the file from analysis."
    require(
        len(errors) == 1
        and errors[0][0].get("label") == label
        and errors[0][1]
        == f"Extraction failed in {stage / 'controls/malformed.uc'} with error {label}"
        and errors[0][0]["url"]
        == {
            "uri": (stage / "controls/malformed.uc").as_uri(),
            "startLine": 3,
            "startColumn": 12,
            "endLine": 3,
            "endColumn": 12,
        }
        and errors[0][2] == 2,
        "diagnostic identity",
    )
    rows = Counter(
        (r[0], r[1]["id"], r[2]["id"], r[3]["id"], r[4], r[5]["id"], r[6]["id"])
        for r in oracle.tuples(results["adjacency"])
    )
    require(
        len(adjacency) == 4 and rows == Counter(adjacency),
        "consumer adjacency identities",
    )
    bypath = {e["path"]: e for e in entries}
    verify_guard_witnesses(bypath, access, node, targets, parent)
    verify_mutation_witnesses(expected, bypath, results, node, targets)
    return expected


def verify_statement_expression_edges(path, first, call, second, restart, targets):
    require(
        targets(path, first, "statement-expression") == [(-1, call)]
        and targets(path, second, "statement-expression") == [(-1, restart)],
        path + ": statement expression edges",
    )


def verify_distinct_declaration_owners(path, first, second, parent):
    first_owner = parent(path, parent(path, first))
    second_owner = parent(path, parent(path, second))
    require(first_owner != second_owner, path + ": distinct declaration owners")


def verify_receiver_write_binding(path, operand, receiver, declaration, access):
    """Prove that a raw write and selected read resolve to one declaration."""
    writes = [
        r
        for r in access
        if r[0] == path and r[1] == "write" and r[3] == {"id": operand}
    ]
    reads = [
        r
        for r in access
        if r[0] == path and r[1] == "read" and r[3] == {"id": receiver}
    ]
    require(
        len(writes) == 1
        and len(reads) == 1
        and writes[0][9] == reads[0][9]
        and writes[0][10] == reads[0][10] == {"id": declaration},
        path + ": write targets selected receiver binding",
    )


def verify_guard_witnesses(bypath, access, node, targets, parent):
    for name in (
        "receiver-write",
        "computed-write",
        "delete-write",
        "parenthesized-delete",
        "parenthesized-base",
        "function-redeclare",
        "function-shadow",
        "other-scope-write",
        "other-scope-member",
        "cardinality-switch",
        "owner-after",
    ):
        path = "controls/" + name + ".uc"
        w = bypath[path]["guard_operation"]
        if name in ("receiver-write", "other-scope-write", "other-scope-member"):
            op = node(path, "AssignmentExpression", w["operation"])
            operand = node(path, "Identifier", w["operand"])
            if name == "other-scope-member":
                left = targets(path, op, "assignment-left")
                require(
                    len(left) == 1
                    and targets(path, left[0][1], "member-object") == [(-1, operand)],
                    path + ": member assignment witness",
                )
            else:
                require(
                    targets(path, op, "assignment-left") == [(-1, operand)],
                    path + ": assignment witness",
                )
            if name == "receiver-write":
                declaration = node(path, "VariableDeclarator", w["declaration"])
                receiver = node(
                    path, "Identifier", bypath[path]["guard_witness"]["receiver"]
                )
                verify_receiver_write_binding(
                    path, operand, receiver, declaration, access
                )
            if name.startswith("other-scope"):
                other = node(path, "VariableDeclarator", w["declaration"])
                kind = "read" if name == "other-scope-member" else "write"
                bindings = [
                    r
                    for r in access
                    if r[0] == path and r[1] == kind and r[3] == {"id": operand}
                ]
                require(
                    len(bindings) == 1 and bindings[0][10] == {"id": other},
                    path + ": disjoint binding witness",
                )
        if name in (
            "computed-write",
            "delete-write",
            "parenthesized-delete",
            "parenthesized-base",
        ):
            sub = node(path, "SubscriptExpression", w["subscript"])
            operand = node(path, "Identifier", w["operand"])
            base = targets(path, sub, "subscript-object")
            op = node(
                path,
                "AssignmentExpression"
                if name == "computed-write"
                else "DeleteExpression",
                w["operation"],
            )
            edge = targets(
                path,
                op,
                "assignment-left" if name == "computed-write" else "delete-argument",
            )
            if name == "parenthesized-base":
                require(
                    not any(
                        r[0] == path and r[1] == "write" and r[3] == {"id": operand}
                        for r in access
                    ),
                    path + ": unresolved write-access witness",
                )
                paren = node(path, "ParenthesizedExpression", w["paren"])
                require(
                    base == [(-1, op)]
                    and edge == [(-1, paren)]
                    and targets(path, paren, "parenthesized-child") == [(-1, operand)],
                    path + ": delete precedence witness",
                )
            else:
                require(base == [(-1, operand)], path + ": subscript base")
                if name == "parenthesized-delete":
                    require(
                        len(edge) == 1
                        and targets(path, edge[0][1], "parenthesized-child")
                        == [(-1, sub)],
                        path + ": wrapped delete",
                    )
                else:
                    require(edge == [(-1, sub)], path + ": mutation operand")
        if name in ("function-redeclare", "function-shadow"):
            op = node(path, "FunctionDeclaration", w["operation"])
            operand = node(path, "Identifier", w["operand"])
            require(
                targets(path, op, "function-name") == [(-1, operand)],
                path + ": function binding witness",
            )
        if name == "owner-after":
            first = node(path, "VariableDeclarator", w["declaration_first"])
            second = node(path, "VariableDeclarator", w["declaration_second"])
            require(
                parent(path, parent(path, first)) == parent(path, parent(path, second)),
                path + ": same owner redeclaration witness",
            )
        if name == "cardinality-switch":
            receiver = node(
                path, "Identifier", bypath[path]["guard_witness"]["receiver"]
            )
            first = node(path, "VariableDeclarator", w["declaration_first"])
            second = node(path, "VariableDeclarator", w["declaration_second"])
            verify_distinct_declaration_owners(path, first, second, parent)
            bindings = [
                r
                for r in access
                if r[0] == path and r[1] == "read" and r[3] == {"id": receiver}
            ]
            require(
                len(bindings) == 2
                and {r[10]["id"] for r in bindings} == {first, second},
                path + ": cardinality witness",
            )


def verify_mutation_witnesses(expected, bypath, results, node, targets):
    baseline = Counter((p, c) for p, c, *_ in expected)
    added = {
        "alias": ["alias"],
        "optional-member": ["optional"],
        "optional-call": ["optional-call"],
        "diagnostic": ["malformed"],
        "owner": ["owner-after"],
        "cardinality": ["cardinality-switch"],
        "receiver-write": [
            "receiver-write",
            "computed-write",
            "delete-write",
            "parenthesized-delete",
            "parenthesized-base",
        ],
    }
    for mutation, names in added.items():
        want = baseline.copy()
        for name in names:
            path = "controls/" + name + ".uc"
            anchor = bypath[path]["guard_call"]
            call = node(path, "CallExpression", anchor)
            witness = bypath[path]["guard_witness"]
            member = node(path, "MemberExpression", witness["member"])
            receiver = node(path, "Identifier", witness["receiver"])
            prop = node(path, "PropertyIdentifier", witness["property"])
            arg = node(path, "String", witness["argument"])
            require(
                targets(path, call, "call-function") == [(-1, member)]
                and targets(path, member, "member-object") == [(-1, receiver)]
                and targets(path, member, "member-property") == [(-1, prop)],
                path + ": mutant witness member edges",
            )
            args = targets(path, call, "call-arguments")
            require(
                len(args) == 1 and targets(path, args[0][1], "argument") == [(0, arg)],
                path + ": mutant witness arguments",
            )
            require(
                bool(targets(path, member, "member-optional")) == (name == "optional")
                and bool(targets(path, call, "call-optional"))
                == (name == "optional-call"),
                path + ": optional witness",
            )
            want[(path, call)] += 1
        actual = Counter(
            (r[0], r[1]["id"]) for r in oracle.tuples(results["mutant_" + mutation])
        )
        require(
            actual == want and actual != baseline,
            mutation + ": intended mutant identities",
        )
    module_path = "controls/wrong-module.uc"
    module_call = node(module_path, "CallExpression", bypath[module_path]["guard_call"])
    module_rows = Counter(
        (r[0], r[1]["id"]) for r in oracle.tuples(results["mutant_module"])
    )
    require(
        module_rows == Counter([(module_path, module_call)])
        and module_rows != baseline,
        "module mutation identities",
    )


def execute(base):
    common.LOG_DIR = base / "commands"
    common.LOG_DIR.mkdir()
    run = common.run
    stage = base / "stage"
    stage.mkdir()
    entries = stage_inputs(stage)
    cli = shutil.which("codeql")
    require(cli is not None, "CodeQL missing")
    db = base / "db"
    extra = os.environ.get("UCI_COMMIT_ADDITIONAL_PACKS")
    options = [f"--additional-packs={extra}"] if extra else []
    search = f"--search-path={PACK}:{ROOT / 'ql/lib'}:{ROOT / 'ql/src'}"
    queries = {
        "success": ROOT / "ql/src/diagnostics/SuccessfullyExtractedFiles.ql",
        "errors": ROOT / "ql/src/diagnostics/ExtractionErrors.ql",
    }
    queries.update(
        {
            k: ROOT / "ql/src/testing/issue53-uci-commit" / v
            for k, v in [
                ("raw", "Raw.ql"),
                ("edges", "Edges.ql"),
                ("access", "VariableAccesses.ql"),
                ("association", "Association.ql"),
                ("adjacency", "Adjacency.ql"),
            ]
        }
    )
    source = (ROOT / "ql/lib/codeql/ucode/internal/SourceDeclaredUci.qll").read_text()
    snippets = {
        "module": 'imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "uci"',
        "alias": 'spec.getName().(UCODE::Identifier).getValue() = "cursor" and not exists(spec.getAlias())',
        "optional-member": "not exists(member.getOptionalChain())",
        "optional-call": "not exists(call.getOptionalChain())",
        "diagnostic": "not exists(ExtractionError error | error.getLocation().getFile() = call.getLocation().getFile())",
        "owner": """not exists(UCODE::VariableDeclarator other |
      other != decl and other.getName().getValue() = receiver.getValue() and
      other.getParent().getParent() = decl.getParent().getParent()
    )""",
        "cardinality": "strictcount(VariableReadAccess candidate | toTreeSitter(candidate.getAstNode()) = receiver) = 1",
    }
    begin = source.index(
        "    not exists(UCODE::Identifier id |\n      id.getValue() = receiver.getValue()"
    )
    end = source.index("    not exists(ExtractionError", begin)
    receiver_guard = source[begin:end].strip()
    require(receiver_guard.endswith("and"), "write guard suffix")
    snippets["receiver-write"] = receiver_guard[:-3].strip()
    with tempfile.TemporaryDirectory(prefix="uci-mutants-", dir=ROOT / "ql/src") as tmp:
        for name, part in snippets.items():
            require(source.count(part) == 1, "mutant source anchor: " + name)
            replacement = (
                'spec.getName().(UCODE::Identifier).getValue() = "cursor"'
                if name == "alias"
                else 'imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "other"'
                if name == "module"
                else "1 = 1"
            )
            text = (
                "/** @name UCI mutant "
                + name
                + "\n * @kind table\n * @id test/uci-mutant-"
                + name
                + "\n */\n"
                + source.replace(part, replacement)
                + """
from UCODE::CallExpression call
where sourceDeclaredUciCommit(call, _, _, _, _, _, _)
select call.getLocation().getFile().getRelativePath() as path, call
"""
            )
            query = Path(tmp) / ("mutant_" + name + ".ql")
            query.write_text(text)
            (base / query.name).write_text(text)
            queries["mutant_" + name] = query
        for name, query in queries.items():
            resolved = run(
                cli,
                "resolve",
                "queries",
                "--format=bylanguage",
                search,
                *options,
                "--",
                query,
            )
            result = common.inputs.strict_json(resolved)
            bylang = result.get("byLanguage", {})
            require(
                set(bylang) == {"ucode"}
                and set(bylang["ucode"]) == {str(query.resolve())}
                and not result.get("noDeclaredLanguage")
                and not result.get("multipleDeclaredLanguages"),
                "query resolver: " + name,
            )
            libs = common.inputs.strict_json(
                run(
                    cli,
                    "resolve",
                    "library-path",
                    "--format=json",
                    search,
                    *options,
                    f"--query={query}",
                )
            )
            expected_prefix = [str(ROOT / "ql/src"), str(ROOT / "ql/lib")]
            require(
                libs["libraryPath"][:2] == expected_prefix
                and libs["dbscheme"] == str(ROOT / "ql/lib/ucode.dbscheme"),
                "query library identity: " + name,
            )
            if extra:
                require(
                    libs["libraryPath"] == expected_prefix + extra.split(":"),
                    "query dependency identities: " + name,
                )
        if os.environ.get("UCI_COMMIT_PREFLIGHT_ONLY") == "1":
            for query in queries.values():
                run(
                    cli,
                    "query",
                    "compile",
                    "--check-only",
                    "--threads=1",
                    "--ram=2048",
                    search,
                    *options,
                    "--",
                    query,
                )
            print("query resolver and check-only preflight passed; no extraction")
            return
        run(
            cli,
            "database",
            "init",
            db,
            "--language=ucode",
            f"--search-path={PACK}",
            f"--source-root={stage}",
        )
        env = os.environ.copy()
        env["CODEQL_UCODE_STAGED_ROOT"] = str(stage)
        run(
            cli,
            "database",
            "index-files",
            db,
            "--language=ucode",
            "--include=**/*",
            f"--working-dir={stage}",
            env=env,
        )
        routing = common.inputs.load(db / "trap/ucode/routing.json")
        (base / "routing.json").write_text(json.dumps(routing, indent=2) + "\n")
        common.inputs.check_routes(routing, stage, entries)
        run(cli, "database", "finalize", db)
        common.inputs.check_archive(db / "src.zip", stage, entries)
        results = {}
        for name, query in queries.items():
            bqrs = base / (name + ".bqrs")
            run(
                cli,
                "query",
                "run",
                query,
                f"--database={db}",
                search,
                *options,
                f"--output={bqrs}",
                "--threads=1",
                "--ram=2048",
            )
            decoded = run(
                cli,
                "bqrs",
                "decode",
                "--format=json",
                "--entities="
                + ("url,string" if name in ("success", "errors") else "id"),
                bqrs,
            )
            (base / (name + ".json")).write_text(decoded)
            results[name] = common.inputs.strict_json(decoded)
        verify(stage, entries, results)
        common.inputs.check_sources(stage, entries)
    print("UCI commit source associations: exact selected identities verified")


def main():
    requested = os.environ.get("UCI_COMMIT_OUT")
    if requested:
        base = Path(requested)
        require(
            base.is_absolute() and not base.exists(),
            "UCI_COMMIT_OUT must be fresh and absolute",
        )
        base.mkdir()
    else:
        base = Path(tempfile.mkdtemp(prefix="uci-commit-ci-"))
    base = base.resolve()
    print("UCI commit evidence directory:", base, flush=True)
    try:
        execute(base)
    except Exception as exc:
        print(
            f"UCI commit smoke failed: {exc}; evidence retained at {base}",
            file=sys.stderr,
            flush=True,
        )
        raise


if __name__ == "__main__":
    main()
