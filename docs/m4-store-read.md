# M4: storeStep / readStep from extracted AST

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `readStep` from extracted `MemberExpression` (`Field[name]`) and
  `SubscriptExpression` (`Element` and possible object fields). A literal
  string subscript selects its field; a dynamic subscript can select any
  extracted field. Write-only assignment and deletion references are excluded.
  The object of the read is the
  matching expression CFG node, or the object/array container when the
  qualifier is a literal.
- `storeStep` from extracted object pairs and shorthand properties
  (`Field[name]`) and from array children (`Element`). Object and array
  wrappers are not `TExpr`, so they use `ContentContainerNode` as the
  store target.
- Local value flow carries literal containers through assignments,
  value-preserving expressions, and returns. Shorthand properties read
  their lexical variable, so stores and subsequent reads can compose through
  the global data-flow graph.
- Smoke reports `store Field[field]` / `read Field[field]` on
  `ssa_neg`, `read Field[args]` on `luci`, and `store Element` /
  `read Element` on `luci`.
- No `Future` constructor. The grammar has no async/future nodes.
- Content stores and reads are separate from `localFlowStep`. They are not
  summary `storeStep` / `readStep`.

## Gaps (later PR)

- Assignment stores (`obj.field = v`, `arr[i] = v`) need
  `TExprPostUpdateNode`; that constructor stays `none()`.
- Escaped object-literal keys are not decoded. Their stores are omitted until
  the extractor exposes their decoded value; escaped subscript keys are
  conservatively treated as dynamic.
- Dynamic subscripts can match every extracted field, so their results can
  grow with the number of field names in the database.
- Pair / array values that are not `TExpr` and not object/array
  (numbers, arrows, templates, `this`, regex, spreads) have no value
  node. Do not widen `TExpr` here: that would change CFG membership.
- `ParameterNode` / argument-to-parameter flow.
- MaD `encodeContent` lives in `FlowSummaryImpl` (see
  [m4-encode-content.md](m4-encode-content.md)). This slice does not
  touch that file.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
