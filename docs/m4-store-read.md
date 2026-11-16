# M4: storeStep / readStep from extracted AST

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- `readStep` from extracted `MemberExpression` (`Field[name]`) and
  `SubscriptExpression` (`Element` and possible object fields). A literal
  string subscript selects its field. A dynamic subscript can select any
  extracted field. `readStep` excludes write-only assignment and deletion
  references.
  The object of the read is the
  matching expression CFG node, or the object/array container when the
  qualifier is a literal.
- `storeStep` from extracted object pairs and shorthand properties
  (`Field[name]`) and from array children (`Element`). Object and array
  wrappers are not `TExpr`, so they use `ContentContainerNode` as the
  store target.
- Assignment `obj.field = v` / `arr[i] = v` stores into
  `TExprPostUpdateNode` of the extracted base when that base already has
  an `ExprCfgNode`. The pre-update node is the same expression. Smoke
  reports `assign store Field[probe_field]` on `content_member_write` /
  `content_subscript_write` and `assign store Element` on
  `content_subscript_write`.
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

## Limits and related models

- Assignment post-update does not flow into later SSA reads of the same
  variable. That needs object-mutation SSA, not a `localFlowStep` summary
  wire.
- Compound assignment (`+=`) is a field read plus a computed write, not a
  store of the RHS.
- Object/array literal assignment bases and `this` have no `ExprCfgNode`
  (`This` is not `TExpr`). Do not widen `TExpr` here.
- The model does not decode escaped object-literal keys. It omits their
  stores until the extractor exposes the decoded values. It treats escaped
  subscript keys as dynamic.
- Dynamic subscripts can match every extracted field, so their results can
  grow with the number of field names in the database.
- Pair / array values that are not `TExpr` and not object/array
  (numbers, arrows, templates, `this`, regex, spreads) have no value
  node. Do not widen `TExpr` here. That change affects CFG membership.
- Named formals with CFG nodes have `ParameterNode`s. The separate
  position match does not resolve calls. See
  [parameter nodes](m4-parameter-node.md).
- MaD `encodeContent` lives in `FlowSummaryImpl`. See
  [m4-encode-content.md](m4-encode-content.md). The original store/read
  slice did not change that file.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
