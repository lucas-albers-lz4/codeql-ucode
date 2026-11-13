# M4: `jumpStep` for unique same-file member FunctionDeclarations

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Production `LocalTaint` / `RequestArgsExec` stay on Models.
`#35` already maps `member_obj.member_order(...)` to the unique same-file
`function member_order` body. Identifier `jumpStep` (`#30` / `#33`) did
not follow that target. This slice does.

## What compiles

- `sameFileJumpCall` is unfiltered identifier `simpleIdentifierCall` or
  unique same-file member-property `FunctionDeclaration`
  (`uniqueSameFileMemberFunctionDeclaration` from `#35`).
- `jumpStep` takes `Call.getArgument` into that callee's `ParameterNode`
  and that callee's `ReturnValueNode` out to the call `OutNode`.
  `parameterToSsaDef` continues a named formal that already has an SSA
  read. Unused `member_order` `a` still has no jump-local row.
- Smoke reports `jump-param` `0:a` / `1:b`, `jump-out`, and
  `jump-local 1:b` from `member_order` on `ssa_pos`, in addition to
  identifier `shellquote` / `callPackageVersionCheck` / `formal_order`.
- `Call.getIdentifier` stays identifier-only. This does not walk
  `getAFieldOrChild`. The receiver object is not resolved. Library
  members (`fd.read` / `fd.close`), imported `luci.sys` (`init_action`),
  builtins (`system`), and imported `'fs'` `popen` / `basename` /
  `access` / `open` / `readfile` still do not jump.
- `Call.getArguments()` stays `none()`. Summary steps stay out of
  `localFlowStep`. Public `localFlowStep` does not include `jumpStep`.

## Gaps (later PR)

- Function expressions and arrows assigned to locals (`let fn = function`).
- Subscript, parenthesized, and nested-call callees.
- Cross-file / import resolution for `luci.sys`. Do not claim
  `setInitAction` `path_found`.
-   `getARuntimeTarget` stays `none()`. Builtin identifier `system`
  and imported `'fs'` `popen` / `basename` / `access` / `open` /
  `readfile` may resolve as `viableLibraryCallable` (see
  `docs/m4-viable-library-callable.md`, `docs/m4-imported-fs-popen.md`,
  `docs/m4-imported-fs-basename.md`, `docs/m4-imported-fs-access.md`,
  `docs/m4-imported-fs-open.md`, and
  `docs/m4-imported-fs-readfile.md`).
- Member `getACall` stays `none()`.
- Unused formals still have no SSA read. Do not invent a pseudo-read.
