# Markup AST extraction (issue #56)

The extractor uses `ucode_markup` from `m00qek/tree-sitter-ucode` at
`4a243af329fae2f4ff01e0fc80133cbab8314600`, alongside the existing plain
`ucode` grammar. The existing classifier selects the markup parser for `.ut`
files or inputs with a line whose leading whitespace is followed by `{%`, `{{`,
or `{#`, subject to the existing installed-path routing rules. An inline tag
after non-whitespace text on a `.uc` line is not detected by this heuristic
and may take the plain route; raw-mode rpcd inputs continue to use plain ucode. The existing routing receipt still marks markup `inconclusive` with
`markup_not_modeled` because analysis coverage is not established. The AST is
extracted despite that classification. Routing is not proof of a clean parse. Check
`ExtractionErrors` as well as exact `SuccessfullyExtractedFiles` identities.

The generator adds separate `ucode_markup_*` relations. Import
`codeql.ucode.Markup` and use `UcodeMarkup::AstNode` and its generated
subclasses, including `Markup`, `RawText`, `ExpressionTag`, and the ucode
syntax nodes. Nodes have source locations and parent relationships. Markup
nodes are distinct from the existing plain `UCODE` AST; the existing CFG and
flow libraries do not operate on these nodes.

The checked shapes are literal text, `{{ expression }}`, a `{%` statement
region, and a transition from that region back to literal text and expressions.
The real control is `modules/luci-base/ucode/uhttpd.uc` from
`openwrt/luci@b2e0be4b46ec0fd43394c081fa7c50657af14011`, SHA-256
`a2b2694f52c021af16dd06ac8c988b8a0a726d9e8186d308708268ebb8849493`.
It starts with `{%` and contains imports, assignment, function, calls and
lexical declaration without a closing tag. Other grammar constructs may parse,
but are not established by these controls; HTML structure and template
runtime semantics are not modeled. A malformed `{{ }}` is recovered with a
missing identifier and produces two extraction diagnostics (expected identifier
and missing `expression_tag::child`); the recovered tree is not a clean or
complete extraction.

This milestone provides AST extraction only. It does not establish markup CFG,
data flow, runtime execution, authorization, a security finding, or dispatcher
coverage. Markup CFG and flow remain deferred to #57; dispatcher analysis is
separate under #58.

Validation: `cargo test`, `bash scripts/create-extractor-pack.sh`, and
`python3 scripts/markup-ast-smoke.py` passed locally with CodeQL 2.27.4 on macOS.
The smoke makes fresh valid and malformed databases and checks selected file
identities, valid diagnostics, selected independently specified AST identities
and source positions, and malformed diagnostics. The existing `m1-smoke.sh`
assumes a `linux64` extractor path and failed on macOS. The staged-routing
gate also assumes `linux64`; with a local untracked compatibility symlink its
first run failed because macOS canonicalizes `/var` to `/private/var`.
A subsequent `m4-staged-routing-smoke.sh` run passed with
`extractor-pack/tools/linux64` symlinked to the locally built `osx64` directory
and `TMPDIR=/private/tmp`; neither workaround changes tracked files. This is
not an unmodified gate result. Linux CI remains necessary for the unmodified
gates.
A temporary copy of `m1-smoke.sh` with only `tools/linux64/extractor` changed
to `tools/osx64/extractor` also passed on macOS; the copy was removed. The
original script was not changed and did not pass unmodified on this platform.

The default autobuilder discovers `.ut` files; the smoke exercises it without
explicit include patterns. The QL smoke checks exact selected node kinds, full
spans, parent kinds, and parent indexes for mixed and pinned real inputs.
