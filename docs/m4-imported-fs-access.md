# M4: imported `'fs'` `access` as `viableLibraryCallable`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#39` inhabits identifier `basename(...)` imported from `'fs'` as a
library callable. This slice inhabits identifier `access(...)` the
same way. It is not a global builtin and not a modeled sanitizer.
It does not score `setInitAction`. `propagatesFlow` stays `none()`.
`jumpStep` does not enter `access`. `getARuntimeTarget` stays
`none()`.

## What compiles

- `ImportedFsAccessLibraryCallable` is the string key `access`.
  `getACall` matches `Call.getIdentifier` named `access` that is an
  unaliased `'fs'` specifier in the same file and is not a same-file
  FunctionDeclaration. `Call.getIdentifier` stays identifier-only;
  this does not walk `getAFieldOrChild`.
- `viableLibraryCallable` maps those calls to
  `TLibraryCallable("access")`. Smoke reports `library access` on
  `luci`. `sys.uc` does not import `access`. `ssa_pos` has no
  `access`.
- Builtin identifier `system` and imported `'fs'` `popen` /
  `basename` stay library callables. Unique same-file
  FunctionDeclarations stay source `CfgScope`s.
- Imported `open` / `readfile` from `'fs'`, imported `luci.sys`
  (`init_action`), and library members (`fd.read` / `fd.close`) do
  not resolve. Identifier `getACall` for Frameworks keys (`system` /
  `popen` / `shellquote`) is unchanged and is not through-flow.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- `open` / `readfile` stay imported and unresolved. Do not treat them
  as builtins.
- Member `getACall` stays `none()`. Do not walk `getAFieldOrChild`.
- `getARuntimeTarget` stays `none()`.
- Do not wire summary steps into `localFlowStep` / production taint.
- Subscript, parenthesized, and nested-call callees stay unresolved.
