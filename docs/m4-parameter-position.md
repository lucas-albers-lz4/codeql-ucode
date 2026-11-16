# M4: ParameterPosition from extracted formals

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier and member-property FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `TParameterPosition` is inhabited from extracted `FormalParameters`
  children (`identifier` or `rest_element`) and from a bare arrow
  `parameter` field (`x => ...`).
- Smoke reports `pos:name` on `luci` and `ssa_pos`. Position `1` is
  extractable (`(_, n) =>` in the luci plugin).
- The original position smoke tests `ParameterPosition` only. Named
  formals with CFG nodes also have `ParameterNode`s. Extracted call
  arguments can have `ArgumentPosition`s. `parameterMatch` compares
  their positions. This comparison does not resolve calls or prove
  value identity. See [parameter nodes](m4-parameter-node.md).

## Limits and related models

- Same-file call `jumpStep` has separate controls. See
  [identifier call jumps](m4-simple-call-jump.md) and
  [member call jumps](m4-member-call-jump.md).
- `TContent` includes extracted field and element content. See
  [content encoding](m4-content-encoding.md). These content steps are
  not production taint.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
- Do not wire summary steps into `localFlowStep` / production taint.
