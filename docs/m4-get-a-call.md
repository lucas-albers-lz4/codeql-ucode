# M4: FlowSummary `getACall` for identifier callees

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Builtin identifier `system` and imported `'fs'` `popen` / `basename`
/ `access` / `open` may resolve as library callables separately
(`docs/m4-viable-library-callable.md`, `docs/m4-imported-fs-popen.md`,
`docs/m4-imported-fs-basename.md`, `docs/m4-imported-fs-access.md`,
`docs/m4-imported-fs-open.md`).
Unique same-file
identifier and member-property FunctionDeclarations may resolve
separately. Member `getACall` stays empty. Production
`LocalTaint` / `RequestArgsExec` stay on Models.

## What compiles

- `FlowSummaryImpl` `getACall` returns a `DataFlowCall` when
  `Call.getIdentifier` matches a string-keyed summarized callable name.
  Frameworks contributes `system`, `popen`, and `shellquote` keys.
  `propagatesFlow` stays `none()`. MaD `summaryModel` rows still
  typecheck; they are not evaluated here (`qlpack.yml` has no
  `dataExtensions` yet).
- Smoke reports `system` on `ssa_pos` and `popen` / `shellquote` on
  `luci`. Member callees (`fd.read(...)`) have no identifier, so they
  are not returned.
- `Future` stays `none()`. The grammar has no async/future nodes.
- Summary steps are not wired into `localFlowStep`.

## Gaps (later PR)

- Member, subscript, parenthesized, and nested-call callees have no
  `getIdentifier`, so they have no `getACall`. Do not walk
  `getAFieldOrChild`: that would treat a member object or property as
  the callee name.
- Identifier `getACall` does not apply summary through-flow.
  Builtin `system` and imported `'fs'` `popen` / `basename` /
  `access` / `open` may resolve as `viableLibraryCallable` without
  `propagatesFlow`. Frameworks keys stay `system` / `popen` /
  `shellquote`, so identifier `getACall` does not grow a `basename`,
  `access`, or `open` row. `readfile` stays unresolved.
- Do not wire summary steps into `localFlowStep` / production taint.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
