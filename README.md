# codeql-ucode

CodeQL language pack for OpenWrt ucode. Pack names: `lucas-albers-lz4/ucode-all`, `lucas-albers-lz4/ucode-queries`.

Corpus, policy, and reports live in [codeql-openwrt](https://github.com/lucas-albers-lz4/codeql-openwrt). Grammar pin and generator SHA are in that repo's `corpus/lock.json`.

## M1 bootstrap (do not skip steps)

The pinned generator (`advanced-security/codeql-extractor-generator@1d5c2de`) fails on a clean tree if `init` is run first.

1. This repo already has `.codeql/generator.yml` (`language_name: ucode`, empty extensions, `features.extractor: false`, full mappings with ucode loop aliases).
2. Clone the lockfile SHA of `m00qek/tree-sitter-ucode` into `extractor/tree-sitter` **before** `init`. `load_tree_sitter_info()` canonicalizes that path before clone.
3. Hide `ucode_markup/src/node-types.json` and `ucdocs/src/node-types.json` so WalkDir cannot pick them. `init` must log `ucode/src/node-types.json`.
4. Run `init` from the **generator checkout CWD** (`cargo run -- --working-dir <abs this repo> --template-dir <abs generator/template> init`). It reads `./ast-internal.qll.jinja` from process CWD.
5. First `init` is render-only (`features.extractor: false`). Do not let `create-extractor-pack.sh` run on the unpatched tree.
6. Apply `patches/`, lock `Cargo.lock`, `cargo check`, then run `scripts/create-extractor-pack.sh` by hand. Spike glob is literal basename `luci`.

`printAst.ql` is generated at `ql/lib/ide-contextual-queries/printAst.ql`.
