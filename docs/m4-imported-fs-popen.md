# M4: imported `'fs'` `popen` as `viableLibraryCallable`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#37` inhabits builtin identifier `system(...)` as a library callable.
This slice inhabits identifier `popen(...)` that is an unaliased import
from `'fs'` the same way, not as a global builtin. It does not score
`setInitAction`. `propagatesFlow` stays `none()`. `jumpStep` does not
enter `popen`. `getARuntimeTarget` stays `none()`.

## What compiles

- `ImportedFsPopenLibraryCallable` is the string key `popen`.
  `getACall` uses the [shared conservative binding guard](m4-imported-fs-readlink.md)
  for a source-declared `fs` import. It requires a preceding top-level,
  unaliased named import in the same file, with exactly one raw `fs` source
  fragment and no other source child. The file must have one local import
  binding for the key, no competing same-name binding or write, and no
  extraction error.
  Only nonoptional identifier calls qualify. The whole-file guard intentionally
  contracts recall: sibling or expired shadows and later declarations can leave
  genuine calls unresolved. A missing result means unknown, not safe.
  This identifies source declarations, not runtime targets, taint, or security.
  Production Models uses a separate matcher, tracked in
  [#87](https://github.com/lucas-albers-lz4/codeql-ucode/issues/87).
- `viableLibraryCallable` maps those calls to `TLibraryCallable("popen")`.
  The historical smoke baseline reports `library popen` on `luci` and
  `sys.uc`. `ssa_pos` has no `popen` in that baseline.
- Builtin identifier `system` stays a library callable
  (`docs/m4-viable-library-callable.md`). Unique same-file
  FunctionDeclarations stay source `CfgScope`s.
- Imported `basename` / `access` / `open` / `readfile` from `'fs'`
  are separate library callables (`docs/m4-imported-fs-basename.md`,
  `docs/m4-imported-fs-access.md`, `docs/m4-imported-fs-open.md`,
  `docs/m4-imported-fs-readfile.md`). Imported `luci.sys`
  (`init_action`) and library members (`fd.read` / `fd.close`) do
  not resolve. Identifier `getACall` for Frameworks keys is unchanged
  and is not through-flow.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- Imported `'fs'` `basename` / `access` / `open` / `readfile` are
  library callables (`docs/m4-imported-fs-basename.md`,
  `docs/m4-imported-fs-access.md`, `docs/m4-imported-fs-open.md`,
  `docs/m4-imported-fs-readfile.md`). Do not treat them as builtins.
- Member `getACall` stays `none()`. Do not walk `getAFieldOrChild`.
- `getARuntimeTarget` stays `none()`.
- Do not wire summary steps into `localFlowStep` / production taint.
- Subscript, parenthesized, and nested-call callees stay unresolved.
