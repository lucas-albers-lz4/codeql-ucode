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
  `getACall` matches `Call.getIdentifier` named `popen` that is an
  unaliased `'fs'` specifier in the same file and is not a same-file
  FunctionDeclaration. That is Models `NamedFsPopenCall`, not
  `BuiltinSystemCall`. `Call.getIdentifier` stays identifier-only;
  this does not walk `getAFieldOrChild`.
- `viableLibraryCallable` maps those calls to `TLibraryCallable("popen")`.
  Smoke reports `library popen` on `luci` and `sys.uc`. `ssa_pos` has
  no `popen`.
- Builtin identifier `system` stays a library callable
  (`docs/m4-viable-library-callable.md`). Unique same-file
  FunctionDeclarations stay source `CfgScope`s.
- Imported `basename` from `'fs'` is a separate library callable
  (`docs/m4-imported-fs-basename.md`). Imported `luci.sys`
  (`init_action`) and library members (`fd.read` / `fd.close`) do
  not resolve. Identifier `getACall` for Frameworks keys is unchanged
  and is not through-flow.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- Imported `'fs'` `basename` is a library callable
  (`docs/m4-imported-fs-basename.md`). `access` stays imported and
  unresolved. Do not treat it as a builtin.
- Member `getACall` stays `none()`. Do not walk `getAFieldOrChild`.
- `getARuntimeTarget` stays `none()`.
- Do not wire summary steps into `localFlowStep` / production taint.
- Subscript, parenthesized, and nested-call callees stay unresolved.
