# M4: same-file identifier FunctionDeclaration call targets

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#30` already `jumpStep`s same-file identifier `Call.getArgument` into
`ParameterNode` via `simpleIdentifierCall`. `#31` continues that node
into the formal's SSA write. `#33` `jumpStep`s that declaration's
`ReturnValueNode` to the call `OutNode`. This slice inhabits
`viableSourceCallable` from the unique, non-imported subset of those
declarations. It does not score `setInitAction`.

## What compiles

- `uniqueSameFileFunctionDeclaration` maps an identifier `Call` to the
  body `CfgScope` of the unique same-file `function name(...)`
  declaration. `shellquote` / `callPackageVersionCheck` on `luci` and
  `formal_order` on `ssa_pos` resolve.
- Imported names (`init_action` from `'luci.sys'`, `popen` from
  `'fs'`, `basename` from `'fs'`), builtins (`system`), and member
  callees do not resolve, including when `sys.uc` is in the database.
- Duplicate same-file FunctionDeclaration names have no
  `viableSourceCallable` target. `jumpStep` still uses unfiltered
  `simpleIdentifierCall`.
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- `viableLibraryCallable` stays `none()`. Identifier `getACall` is
  already inhabited and is not library-call resolution.
- Nested duplicate names and lexical shadowing.
- `getARuntimeTarget` stays `none()`.
