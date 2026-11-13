# M4: builtin `system` as `viableLibraryCallable`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#34` / `#35` inhabit unique same-file identifier and member-property
FunctionDeclarations as source `CfgScope`s. This slice inhabits
`viableLibraryCallable` from identifier builtin `system(...)`.
It does not score `setInitAction`. `propagatesFlow` stays `none()`.
`jumpStep` does not enter `system`. `getARuntimeTarget` stays `none()`.

## What compiles

- `BuiltinSystemLibraryCallable` is the string key `system`.
  `getACall` matches `Call.getIdentifier` named `system` that is not an
  imported specifier and not a same-file FunctionDeclaration.
  `Call.getIdentifier` stays identifier-only; this does not walk
  `getAFieldOrChild`.
- `viableLibraryCallable` maps those calls to `TLibraryCallable("system")`.
  Smoke reports `library system` on `ssa_pos`, `luci`, and `sys.uc`.
- Unique same-file FunctionDeclarations stay source `CfgScope`s
  (`shellquote` / `callPackageVersionCheck` / `formal_order` /
  `member_order`). They are not library targets.
- Imported names (`init_action` from `'luci.sys'`, `popen` from
  `'fs'`, `basename` from `'fs'`) and library members (`fd.read` /
  `fd.close`) do not resolve. Identifier `getACall` for Frameworks
  keys is unchanged and is not through-flow.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- `popen` / `basename` stay imported and unresolved. Do not treat
  them as builtins.
- Member `getACall` stays `none()`. Do not walk `getAFieldOrChild`.
- `getARuntimeTarget` stays `none()`.
- Do not wire summary steps into `localFlowStep` / production taint.
- Subscript, parenthesized, and nested-call callees stay unresolved.
