# M4: imported `'fs'` `open` as `viableLibraryCallable`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#40` inhabits identifier `access(...)` imported from `'fs'` as a
library callable. This slice inhabits identifier `open(...)` the
same way. It is not a global builtin. It does not score
`setInitAction`. `propagatesFlow` stays `none()`.
`jumpStep` does not enter `open`. `getARuntimeTarget` stays
`none()`.

## What compiles

- `ImportedFsOpenLibraryCallable` is the string key `open`.
  `getACall` matches `Call.getIdentifier` named `open` that is an
  unaliased `'fs'` specifier in the same file and is not a same-file
  FunctionDeclaration. `Call.getIdentifier` stays identifier-only;
  this does not walk `getAFieldOrChild`.
- `viableLibraryCallable` maps those calls to
  `TLibraryCallable("open")`. Smoke reports `library open` on
  `luci` and `sys.uc`. `ssa_pos` has no `open`.
- Builtin identifier `system` and imported `'fs'` `popen` /
  `basename` / `access` stay library callables. Unique same-file
  FunctionDeclarations stay source `CfgScope`s.
- Imported `readfile` from `'fs'` is a separate library callable
  (`docs/m4-imported-fs-readfile.md`). Imported `luci.sys`
  (`init_action`) and library members (`fd.read` / `fd.close`) do
  not resolve. Identifier `getACall` for Frameworks keys (`system` /
  `popen` / `shellquote`) is unchanged and is not through-flow.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- Imported `'fs'` `readfile` is a library callable
  (`docs/m4-imported-fs-readfile.md`). Do not treat it as a builtin.
- Member `getACall` stays `none()`. Do not walk `getAFieldOrChild`.
- `getARuntimeTarget` stays `none()`.
- Do not wire summary steps into `localFlowStep` / production taint.
- Subscript, parenthesized, and nested-call callees stay unresolved.
