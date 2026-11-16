# M4: `jumpStep` for unique same-file member FunctionDeclarations

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#35` already maps `member_obj.member_order(...)` to the unique same-file
`function member_order` body. Before the member-call slice, identifier
`jumpStep` (`#30` / `#33`) did not follow that target. The member-call
slice added that support.

## What compiles

- `sameFileJumpCall` is unfiltered identifier `simpleIdentifierCall` or
  unique same-file member-property `FunctionDeclaration`
  (`uniqueSameFileMemberFunctionDeclaration` from `#35`).
- `jumpStep` takes `Call.getArgument` into the `ParameterNode` of that
  callee. It takes the `ReturnValueNode` of that callee to the call
  `OutNode`.
  `parameterToSsaDef` continues a named formal that already has an SSA
  read. Unused `member_order` `a` still has no jump-local row.
- Separate smokes report `jump-param` `0:a` / `1:b`, `jump-out`, and
  `jump-local 1:b` from `member_order` on `ssa_pos`. The jump-parameter
  smoke also reports `shellquote`, `callPackageVersionCheck`, and
  `formal_order`.
- `Call.getIdentifier` stays identifier-only. The member matcher does
  not resolve the receiver object. The identifier matcher uses the name
  and file only. It can match an unrelated same-name declaration.
  Neither matcher resolves imports or builtin targets. The smoke has no
  `system` jump to `formal_order`.
- `Call.getArguments()` stays `none()`. Summary steps stay out of
  `localFlowStep`. Public `localFlowStep` does not include `jumpStep`.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Subscript, parenthesized, and nested-call callees.
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
-   `getARuntimeTarget` stays `none()`. Builtin identifier `system`
  and imported `'fs'` `popen` / `basename` / `access` / `open` /
  `readfile` can resolve as `viableLibraryCallable` (see
  `docs/m4-viable-library-callable.md`, `docs/m4-imported-fs-popen.md`,
  `docs/m4-imported-fs-basename.md`, `docs/m4-imported-fs-access.md`,
  `docs/m4-imported-fs-open.md`, and
  `docs/m4-imported-fs-readfile.md`).
- Member `getACall` stays `none()`.
- Unused formals still have no SSA read. Do not invent a pseudo-read.
