# Source census: direct-copy receiver candidates in pinned LuCI

The pinned LuCI source text search below found **no candidate consisting of a `popen`-initialized variable declarator copied directly into another declarator** among the textual forms it inventories. It extends the earlier negative observation on two extracted LuCI files to the pinned LuCI repository's other ucode-related source files. This is a lexical census, not an extraction, a proof that every ucode syntactic form was found, a runtime identity claim, or a security result. No new query comparison was run because no qualifying real case was identified. The earlier two-file extraction and synthetic-control evidence is described in [PR #149](https://github.com/lucas-albers-lz4/codeql-ucode/pull/149).

## Scope and predicate

The input is every Git-tracked text file at LuCI commit `b2e0be4b46ec0fd43394c081fa7c50657af14011`, the `luci` repository pin in `codeql-openwrt/corpus/lock.json` for profile `luci-ssl-25.12` (lock SHA-256 `b4cbdabb76df90a807aba7d42ae675198c7b7b09c3b84db259a3a4c941b0ea9a`). This repository-wide source scope includes applications which are not necessarily installed by that profile; other pinned repositories are outside scope. The query under consideration is `ReceiverDirectCopy.ql` at producer `d3981986ac685d6fcbb78a3b369aa4ed526c1e4b`; its predicate and `SourceDeclaredFs.qll` have no diff against current main `1ccf5268e6915dc8d4cbb926b28be8ff79bcb0ed`.

The relation requires a variable declarator initialized by a direct unaliased named `popen` imported from `fs`, a second variable declarator initialized by a read of the first, and a direct non-optional `read` or `close` call on the copied variable, connected by the specified SSA local-flow steps. The census only investigates the first two textual shapes; it does not evaluate import guards, binding identity, SSA, optional chaining, extraction diagnostics or the receiver call. A textual candidate is therefore not necessarily a query row.

## Evidence and interpretation

[`popen-all.txt`](popen-all.txt) contains all 72 matching tracked text lines, including comments, mocks, C, Lua and test data. The first pass matched 25 files across the tree; the candidate pass filters these to 14 ucode-related files (`.uc` or a path containing `/ucode/`). [`initializers.txt`](initializers.txt) is a supplementary line-oriented search. [`candidates.txt`](candidates.txt) records the script's 22 direct `popen` assignment matches in these ucode-related files, including four assignments that are not declarators, and every textual `= identifier` occurrence in each matching file. The list includes the two previously measured LuCI files, preserving their negative evidence without repeating extraction.

For example, `luci-app-commands/ucode/controller/commands.uc:203` initializes `fd` with `popen`; lines 207 and 221 use `fd.read`, not a copy of `fd`. In `luci-app-rustdesk-server/.../rustdesk-server.uc:33`, `pp` is initialized by `popen` and line 35 initializes `output` from `pp.read('all')`, not `pp`. In `luci-app-weechat/.../weechat.uc:157`, `p` is reassigned rather than declared. Namespace `fs.popen` calls in `luci-app-lxc` do not match the query's direct named-import call predicate. These examples are source observations; they are not independent extracted controls.

The script scans only files whose text contains the literal `popen`, and then only `.uc` paths or paths containing `/ucode/`. The regex permits whitespace/newlines around `=` and `popen(`, and collects RHS occurrences whether or not they are declarations or complete identifier expressions. It does not parse comments, strings, templates or ucode syntax, and may produce false positives. It can miss comments between tokens, escapes, unusual identifier forms, encodings, alternate paths, or other syntactic representations. `git grep -I` excludes binary-classified files and decoding uses UTF-8 replacement. The result is limited to the enumerated text and search forms; it does not establish absence for every possible syntax or other corpus.

## Reproduction

From the ucode repository root, with a local LuCI Git repository containing the pinned object:

```sh
LUCI=/path/to/luci
REV=b2e0be4b46ec0fd43394c081fa7c50657af14011
OUT=docs/evidence/receiver-luci-census
git -C "$LUCI" cat-file -e "$REV^{commit}"
git -C "$LUCI" grep -n -I 'popen' "$REV" -- > /tmp/luci-popen-all.txt
git -C "$LUCI" grep -n -I -E '= *popen *\(' "$REV" -- > /tmp/luci-initializers.txt
python3 "$OUT/census.py" "$LUCI" > /tmp/luci-candidates.txt
cmp "$OUT/popen-all.txt" /tmp/luci-popen-all.txt
cmp "$OUT/initializers.txt" /tmp/luci-initializers.txt
cmp "$OUT/candidates.txt" /tmp/luci-candidates.txt
python3 -m unittest discover -s "$OUT" -p 'test_*.py'
```

On 2026-11-22 the three comparisons passed and all three lexical scanner tests passed with Python 3; tests demonstrate multiline matches, namespace exclusion and a comment false positive, not parser correctness. The script normalizes nested input paths to the repository root before searching. The two standalone `git grep` reproduction commands must be given the repository root as `LUCI`. Git reads objects at the explicit commit irrespective of working-tree state. Prior source-first evidence and the conditional stop rule mean there was no new CodeQL extraction, diagnostic run, real/synthetic row comparison, or production-query impact measurement for this census.
