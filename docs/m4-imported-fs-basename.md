# M4: imported `'fs'` `basename` as `viableLibraryCallable`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#38` inhabits identifier `popen(...)` imported from `'fs'` as a
library callable. This slice inhabits identifier `basename(...)` the
same way. It is not a global builtin and not a modeled sanitizer.
It does not score `setInitAction`. `propagatesFlow` stays `none()`.
`jumpStep` does not enter `basename`. `getARuntimeTarget` stays
`none()`.

## What compiles

- `ImportedFsBasenameLibraryCallable` is the string key `basename`.
  `getACall` matches `Call.getIdentifier` named `basename` that is an
  unaliased `'fs'` specifier in the same file and is not a same-file
  FunctionDeclaration. `Call.getIdentifier` stays identifier-only;
  this does not walk `getAFieldOrChild`.
- `viableLibraryCallable` maps those calls to
  `TLibraryCallable("basename")`. Smoke reports `library basename` on
  `luci` and `sys.uc`. `ssa_pos` has no `basename`.
- Builtin identifier `system` and imported `'fs'` `popen` stay library
  callables. Unique same-file FunctionDeclarations stay source
  `CfgScope`s.
- Imported `access` / `open` from `'fs'` are separate library
  callables (`docs/m4-imported-fs-access.md`,
  `docs/m4-imported-fs-open.md`). Imported `luci.sys`
  (`init_action`) and library members (`fd.read` / `fd.close`) do
  not resolve.
  Identifier `getACall` for Frameworks keys (`system` / `popen` /
  `shellquote`) is unchanged and is not through-flow.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- Imported `'fs'` `access` / `open` are library callables
  (`docs/m4-imported-fs-access.md`, `docs/m4-imported-fs-open.md`).
  `readfile` stays imported and unresolved. Do not treat it as a
  builtin.
- Member `getACall` stays `none()`. Do not walk `getAFieldOrChild`.
- `getARuntimeTarget` stays `none()`.
- Do not wire summary steps into `localFlowStep` / production taint.
- Subscript, parenthesized, and nested-call callees stay unresolved.
