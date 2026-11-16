# codeql-ucode

CodeQL language pack for OpenWrt ucode. Pack names: `lucas-albers-lz4/ucode-all`, `lucas-albers-lz4/ucode-queries`.

Corpus, policy, and reports live in [codeql-openwrt](https://github.com/lucas-albers-lz4/codeql-openwrt). Grammar pin and generator SHA are in that repo's `corpus/lock.json`.

## M1 bootstrap (do not skip steps)

The pinned generator (`advanced-security/codeql-extractor-generator@1d5c2de`) fails on a clean tree if `init` is run first.

1. This repo already has `.codeql/generator.yml` (`language_name: ucode`, empty extensions, `features.extractor: false`, full mappings with ucode loop aliases).
2. Clone the lockfile SHA of `m00qek/tree-sitter-ucode` into `extractor/tree-sitter` **before** `init`. `load_tree_sitter_info()` canonicalizes that path before clone.
3. Hide `ucode_markup/src/node-types.json` and `ucdocs/src/node-types.json` **only for `init`** (`CODEQL_UCODE_HIDE_EXTRA_NODE_TYPES=1 ./scripts/clone-grammar.sh`) so WalkDir cannot pick them. `init` must log `ucode/src/node-types.json`. Restore those files before `cargo test`: the grammar crate `include_str!`s all three node-type files.
4. Run `init` from the **generator checkout CWD** (`./target/release/codeql-extractor-generator --working-dir <abs this repo> --template-dir <abs generator/template> --config .codeql/generator.yml init --name ucode`). It reads `./ast-internal.qll.jinja` from process CWD. Pass `--name ucode`: clap defaults `--name` to `Some("")` and that overwrites `generator.yml` `language_name` before `create_config`, which then prompts and panics if stdin is not a TTY.
5. First `init` is render-only (`features.extractor: false`). Do not let `create-extractor-pack.sh` run on the unpatched tree. `init` still runs `codeql pack create ql/lib` at the end; that is expected to succeed or fail independently of the extractor binary.
6. After `init`, restore `.codeql/generator.yml` from git: `init` `save()`s absolute `template_dir`/`path` and clears `tree-sitter-repo.url`.
7. Apply `patches/` (`./patches/apply.sh`), lock `Cargo.lock`, `cargo test`, then run `scripts/create-extractor-pack.sh` by hand. Spike glob is literal basename `luci`.
8. `./scripts/m1-smoke.sh` runs parser-load, pack, extract of `ql/test/extractor-smoke/usr/share/rpcd/ucode/luci` only (`SuccessfullyExtractedFiles == 1`), and PrintLuciAst.
9. `./scripts/m3-smoke.sh` indexes `luci`, `taint_pos`, and `taint_neg` (`SuccessfullyExtractedFiles == 3`) and asserts the M3 queries.
10. `./scripts/m4-smoke.sh` reuses that database and asserts `RequestArgsExec.ql` methods (`getSwconfigFeatures`, `getSwconfigPortState`, `getRealtimeStats`, `setPassword`, `setLocaltime`).
11. `./scripts/m4-fixed-helpers-smoke.sh` asserts `GetFeaturesDirectExec.ql` (hostapd/wpa_supplicant `system`, dnsmasq/odhcpd/ipset `popen`).
12. `./scripts/m4-quote-smoke.sh` indexes those plus the `quote_*` controls and checks conservative candidate retention and necessary template shapes; no `shellquote` helper currently has trusted sanitizer semantics.
13. `./scripts/m4-imported-callee-smoke.sh` asserts `ImportedCalleeTaint.ql` sees `init_action` from `luci.sys`.
14. `./scripts/m4-sys-smoke.sh` indexes `luci` plus installed luci.sys (`sys.uc`) and asserts `InitActionSystem.ql` plus the `setInitAction` action-token switch (not a sanitizer of `name`).
15. `./scripts/m4-luci-sys-status-exec-smoke.sh` asserts `LuciSysStatusExec.ql` (`getConntrackList` / `getProcessList` helpers: fixed `conntrack` and `busybox top` popen in `sys.uc`; not interprocedural `path_found`).
16. `./scripts/m4-viable-source-callable-smoke.sh` asserts unique same-file identifier and member-property FunctionDeclarations resolve, builtin `system` and a bounded subset of imported `'fs'` `popen` / `basename` / `access` / `open` / `readfile` resolve as library callables, and imported `luci.sys` does not. The shared `fs` guard also covers `readlink`.

Templates also require mapping buckets named `StmtSequence`, `Calls`, and `Idents` (not only `Stmts`/`Call`). Those are in `generator.yml`.

`printAst.ql` is generated at `ql/lib/ide-contextual-queries/printAst.ql`. The M1 AST gate query is `ql/src/extractor-smoke/PrintLuciAst.ql` (basename `luci`).

Fresh checkouts: `./scripts/clone-grammar.sh` before `cargo test`. The grammar clone is gitignored.

## Extracting an installed staging root

The existing fixture and package-layout routing remains the default. To route
an ordinary installed filesystem tree, explicitly trust its root: pass
`--staged-root /absolute/path/to/stage` to the extractor's `extract` command,
or set `CODEQL_UCODE_STAGED_ROOT` to that path for `codeql database index-files`.
The caller must still select extensionless files with an `--include` pattern;
setting the root does not discover them automatically. For example:

```sh
codeql database init "$DB" --language=ucode --search-path="$PWD/extractor-pack" --source-root="$STAGE"
CODEQL_UCODE_STAGED_ROOT="$STAGE" codeql database index-files "$DB" --language=ucode \
  --include='**/rpcd/ucode/luci' --working-dir="$STAGE"
codeql database finalize "$DB"
```

The root must exist and be a directory. Both root and inputs are canonicalized;
an input resolving outside the root (including a symlink escape) is excluded
with `outside_staged_root`. In this explicit mode installed paths are relative
to that root, and embedded fixture/package path markers do not grant routing.
Point to the actual installed root, not its parent or a package source tree.
Do not leave the variable set for unrelated corpus-layout extractions. Without
the option, established fixture and package layouts retain their prior rules.
The extractor exit status alone does not establish completeness: check
`routing.json`, exact `SuccessfullyExtractedFiles` identities and empty
`ExtractionErrors` before accepting query results. The focused regression is
`bash scripts/m4-staged-routing-smoke.sh` after building the extractor pack.
On Windows the batch wrapper passes the static `--staged-root-from-env` option;
with that option the extractor reads `CODEQL_UCODE_STAGED_ROOT` directly as an
OS string, rejecting a missing or empty value. The option conflicts with
`--staged-root`. Without either option, a direct extractor invocation ignores
that environment variable and retains legacy routing. Native Windows wrapper
and filesystem execution are device-gated and have not been verified locally.

## Local SSA and data-flow status

The experimental CFG has partial coverage of ordered expression and access
nodes, branches, loops (including `for-in`), `switch`, `break`, and `continue`.
Its `try`/`catch` paths use an incomplete may-throw approximation, so some
runtime exception paths may be missed.
Named formals of block-bodied functions and expression-bodied arrows are
Variables with CFG nodes and SSA writes. Since #28, an expression-bodied
arrow's body expression is its inner `CfgScope`, analogous to the block scope
of a block-bodied function. Parameters still shadow outer variables. Lexical
`let`/`const` declarations become visible in source order; a later inner
declaration does not shadow an earlier read. Switch-body scope remains a
separate known limitation ([#93](https://github.com/lucas-albers-lz4/codeql-ucode/issues/93)).
See [`docs/m4-arrow-cfgscope.md`](docs/m4-arrow-cfgscope.md) for the supported
formal shapes and current limits.
The regression smoke covers same-statement ordering, joins, loop-carried flow,
short-circuit expressions, optional chains and return values.

`VariableWriteAccess` is the identifier LHS of `=`, augmented assignment,
updates, and assignment-form `for-in`. Lexical `let`/`const` declarators,
function parameters, and catch bindings are SSA writes but not that class.
`getAssignedRhs` is the `=` / `&&=` / `||=` / `??=` stored expression;
arithmetic `+=` and updates have none. That API is not taint and not
`path_found`.

`ql/src/m4/SsaReachesSystem.ql` is an additive pack query that imports
`codeql.ucode.DataFlow` and reports lexical SSA writes whose read is an access
in builtin `system()`'s command argument, on
`ssa_pos`/`ssa_neg` only, requiring `DataFlow::localFlowStep+` from that
write's SSA node to a read of the same definition. Production LocalTaint /
RequestArgsExec / ImportedCalleeTaint stay on Models. Public
`localFlowStep` connects expressions, SSA definitions and reads, copies and
return values through value-preserving edges. Value-transforming operations
such as arithmetic and `+=` have no local flow edge, and taint propagation
through those operations is not modeled here. Field content is
store/read only, not `localFlowStep`. Same-file identifier calls and
unique same-file member-property FunctionDeclarations can `jumpStep`
from `Call.getArgument` into that declaration's `ParameterNode`. That
node continues into the formal's SSA write through `parameterToSsaDef`;
`jumpStep` itself stays out of `localFlowStep`. That callee's
`ReturnValueNode` `jumpStep`s to the call expression (`OutNode`) for
the same `sameFileJumpCall`. An identity expression body (`x => x`) is
a read of that formal, so `parameterToSsaDef` continues into
`ssaDefToRead`. `viableSourceCallable` resolves unique same-file
identifier and member-property FunctionDeclarations; imported
`luci.sys` callees stay unresolved / inconclusive — not `setInitAction`
`path_found`. `viableLibraryCallable` resolves builtin identifier
`system` and a conservative source-declared subset of imported `'fs'`
`popen` / `basename` / `access` / `open` / `readfile` / `readlink`.
All six use the same guard described in
[`docs/m4-imported-fs-readlink.md`](docs/m4-imported-fs-readlink.md).
Its whole-file guard intentionally leaves genuine calls unresolved when any
competing same-name binding or write occurs, even in an unrelated scope,
after a shadow's scope, or later in the file. Optional calls are unresolved.
Missing results mean unknown, not safe, unreachable, or not an fs call.
Models `NamedFsPopenCall` now uses the shared source-declared guard for the
bounded `fs.popen` family (#87); other Models import observations still use
their separate generic matcher. See `docs/m4-imported-fs-popen.md` and
`scripts/m4-models-fs-popen-smoke.sh` for the contract and regression gate.
`luci.sys` / `fd.read` stay unresolved.
The shared `system` check uses visible imports, named formals, function names,
lexical declarations, loop bindings and catch parameters, including enclosing
scopes. Declarations are considered in source order. It is a syntactic
approximation, not dynamic call-target resolution: global reassignment and
local aliases of the builtin are not resolved, unsupported syntax may be
misclassified, and an excluded call is **not** a safety or no-execution result.
`scripts/m4-system-lexical-smoke.sh` and `scripts/m4-system-rpc-smoke.sh`
exercise positive and shadowed calls through Models-backed and experimental
queries.
`propagatesFlow` stays `none()`. Identifier `jumpStep` stays unfiltered
`simpleIdentifierCall`; member `jumpStep` uses the unique declaration.

## M1 spike status

Local gate passed on this branch:

- `cargo test`: `LANGUAGE_UCODE` loads; `luci` fixture parses with no error nodes. Runtime `LANGUAGE_VERSION=15`, `MIN_COMPATIBLE=13`, grammar ABI 15.
- Extractor glob is literal basename `luci` (skips `luci.uc`).
- `count(SuccessfullyExtractedFiles) == 1`, empty `ExtractionErrors`, source-archive basename `luci`.
- `printAst.ql` / `PrintLuciAst.ql` return TreeSitter nodes in that file (wrapper `AST.qll`/`CFG.qll` are generated but not imported; they do not compile).

Toolchain recorded here until `codeql-openwrt` `corpus/lock.json` is updated:

- `codeql-extractor` git rev `ce29d8a59af0d25517c622469db17aad826b8d7f`
- `tree-sitter` crate `0.26.8` (0.27.1 does not compile against that extractor)
- `Cargo.lock` sha256 `a88727b38d756abf989517742a355189360ba2bb500b04dab18b77307d6cc830`
- rustc 1.99.1 / rust-version 1.85 / edition 2024
- CodeQL CLI 2.27.4
