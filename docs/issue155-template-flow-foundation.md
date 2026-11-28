# Issue #155 template-flow foundation experiment

Owner approval on 2026-11-28 authorized this bounded, testing-only experiment
and the scoped exception to the #51 usefulness gate. The exception applies to
the test foundation below. It does not authorize a production query, production
DataFlow model, report promotion, or security claim.

## What the experiment adds

The ucode DataFlow node union gains `TemplateStringArgumentNode`, which keeps
the identity and location of a template string used directly as a call
argument. A template string remains outside the ordinary expression node
classes, and the new node has no default flow steps. The testing query adds one
configuration-local taint edge from each direct template substitution
expression to its containing template-argument node.

The query restricts its source to a `request.args.service_name` member read
whose `request` identifier resolves to a function formal. It restricts the
sink to a direct, source-declared `fs.stat` call with a template string in
argument 0. The selected call and the candidate import specifier are both
returned with their AST locations. The testing result also includes the exact
request-formal, source expression, template argument, call, candidate
interpolation expression, and template-substitution identities.

The fixture set includes the pinned LuCI DDNS backend from `b2e0be4b46ec0fd43394c081fa7c50657af14011`, a direct positive, a local-variable positive,
and negative controls for fixed substitutions, wrong argument position,
formal reassignment including assignment-form `for-in`, same-scope `let` and
function shadowing (including a function declaration under `if`), `request.args`
and `service_name` replacement including parenthesized receivers and deletes
whose argument is parenthesized or a subscript, duplicate formals, helper and nested-function flow, extra
and spread arguments, unrelated same-name properties, and malformed syntax.
Same-name `request` function declarations anywhere inside the selected callback
are conservatively excluded. A nested block shadow write has a paired positive
that reads the outer formal after the block.
The expected paths and source positions are in
[`manifest.json`](../ql/test/issue155-template-flow/manifest.json). The
no-edge query uses the same source and sink definitions with the additional
taint edge omitted; it must return no flow rows.

The delete mutation query reports the parenthesized and subscript delete
argument node classes directly. These ensure the negative controls exercise
AST forms a direct-member-only deletion check would miss.

The flow table reports the interpolation expression only when local taint
reaches it from the selected request-property source. The additional edge is
then tested in the global configuration. The edge-disabled mutation must
remove all rows. This checks the reported source-to-substitution identity and
the configuration-local edge dependency; it does not establish complete
template semantics.

## Run

Use a physical CodeQL 2.27.4 CLI path and a physical extractor pack. Do not pass
an extractor-pack symlink as the search path; CodeQL cannot resolve the
extractor through it in this environment. Example:

```sh
export CODEQL=/absolute/path/to/codeql-2.27.4/codeql
export UCODE_EXTRACTOR_PACK=/absolute/path/to/extractor-pack
export UCODE_EXTRACTOR_PACK_SOURCE_REVISION='revision-that-produced-the-pack'
export ISSUE155_TEMPLATE_FLOW_OUT=/absolute/path/to/fresh-output
python3 scripts/issue155-template-flow-ci.py
```

The runner creates a fresh database and output directory. It checks the exact
fixture inventory, routes, successful-file identities, extraction diagnostic,
positive and negative result rows, and the edge-disabled mutation. The
extractor pack can be reused when its extractor inputs are verified equivalent
to the selected producer base; record the producing revision, executable hash,
and complete pack-tree hash with the run.

## Limits

This tests one real source shape, one direct request-property shape, and one
bounded interpolation edge. It does not resolve runtime imports, establish
callback execution or source reachability, model arbitrary templates, prove
sanitization or authorization, establish read behavior or path traversal, or
show exploitability. Production Models and `RequestArgsExec` are unchanged.
The query is not included in a default suite and emits no production result.
