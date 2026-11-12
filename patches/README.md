# M1 patches

Apply **after** generator `init` and **before** `cargo check` / `scripts/create-extractor-pack.sh`.

| Patch | What it does |
| --- | --- |
| `0001-language-ucode-and-luci-glob.patch` | `LANGUAGE_UCODE` / `UCODE_NODE_TYPES`; `file_globs: ["luci"]` |
| `0002-tree-sitter-0.26.patch` | ABI 15 runtime `tree-sitter = "=0.26.8"` (0.27.1 does not compile with `codeql-extractor@ce29d8a`); edition 2024; rust-version 1.85 |
| `0003-pack-names.patch` | `lucas-albers-lz4/ucode-{all,queries,tests}` |
| `0004-remove-php-import.sh` | Drop leftover `codeql.php.ast.AstNodes` imports |

```sh
./patches/apply.sh
```

Do not re-run `init` over a patched tree: `init` `save()`s `generator.yml` and will clobber `tree-sitter-repo.url`.
