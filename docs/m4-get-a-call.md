# M4: FlowSummary `getACall` for identifier callees

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableLibraryCallable` stays `none()`. Unique same-file identifier
and member-property FunctionDeclarations may resolve separately.
Member `getACall` stays empty. Production
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
- `viableLibraryCallable` stays `none()`. Identifier `getACall` does
  not resolve library targets or apply summary through-flow.
- Do not wire summary steps into `localFlowStep` / production taint.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
