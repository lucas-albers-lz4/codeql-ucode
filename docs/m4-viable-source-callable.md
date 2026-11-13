# M4: same-file identifier and member FunctionDeclaration call targets

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#30` already `jumpStep`s same-file identifier `Call.getArgument` into
`ParameterNode` via `simpleIdentifierCall`. `#31` continues that node
into the formal's SSA write. `#33` `jumpStep`s that declaration's
`ReturnValueNode` to the call `OutNode`. `#34` inhabits
`viableSourceCallable` from unique same-file identifier
FunctionDeclarations. This slice also inhabits unique same-file
**member-property** FunctionDeclarations. It does not score
`setInitAction`. Identifier `jumpStep` still uses unfiltered
`simpleIdentifierCall`. Unique member FunctionDeclarations also
`jumpStep` (see `docs/m4-member-call-jump.md`).

## What compiles

- `uniqueSameFileFunctionDeclaration` maps an identifier `Call` to the
  body `CfgScope` of the unique same-file `function name(...)`
  declaration. `shellquote` / `callPackageVersionCheck` on `luci` and
  `formal_order` on `ssa_pos` resolve.
- `uniqueSameFileMemberFunctionDeclaration` maps a member `Call` whose
  property is a `PropertyIdentifier` to the unique same-file
  `function name(...)` body. `member_order` on `ssa_pos` resolves. The
  receiver object is not resolved. `Call.getIdentifier` stays
  identifier-only; this does not walk `getAFieldOrChild`.
- Imported names (`init_action` from `'luci.sys'`, `popen` from
  `'fs'`, `basename` from `'fs'`), builtins (`system`), and library
  member callees (`fd.read` / `fd.close`) do not resolve, including
  when `sys.uc` is in the database. Those members have no matching
  FunctionDeclaration.
- Duplicate same-file FunctionDeclaration names have no
  `viableSourceCallable` target. Identifier `jumpStep` still uses
  unfiltered `simpleIdentifierCall`. Unique member FunctionDeclarations
  also `jumpStep` (see `docs/m4-member-call-jump.md`).
- In-file `localFlowStep+` from `ssa_pos_src` to builtin `system`
  still holds. That is not interprocedural taint.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
- `viableLibraryCallable` stays `none()`. Identifier `getACall` is
  already inhabited and is not library-call resolution. Member
  `getACall` stays `none()`.
- Nested duplicate names and lexical shadowing.
- `getARuntimeTarget` stays `none()`.
- Subscript, parenthesized, and nested-call callees stay unresolved.
