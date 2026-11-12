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
12. `./scripts/m4-quote-smoke.sh` indexes those plus `quote_ok`/`quote_exe` and asserts the complete-argument `shellquote` barrier.
13. `./scripts/m4-imported-callee-smoke.sh` asserts `ImportedCalleeTaint.ql` sees `init_action` from `luci.sys`.
14. `./scripts/m4-sys-smoke.sh` indexes `luci` plus installed luci.sys (`sys.uc`) and asserts `InitActionSystem.ql` plus the `setInitAction` action-token switch (not a sanitizer of `name`).

Templates also require mapping buckets named `StmtSequence`, `Calls`, and `Idents` (not only `Stmts`/`Call`). Those are in `generator.yml`.

`printAst.ql` is generated at `ql/lib/ide-contextual-queries/printAst.ql`. The M1 AST gate query is `ql/src/extractor-smoke/PrintLuciAst.ql` (basename `luci`).

Fresh checkouts: `./scripts/clone-grammar.sh` before `cargo test`. The grammar clone is gitignored.

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
