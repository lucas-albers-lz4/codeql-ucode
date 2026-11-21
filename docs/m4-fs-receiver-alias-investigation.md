# Investigation: one identifier-copy receiver alias

This is a design investigation for #48 beyond the direct-declarator source observer from #132. It considers exactly one source-level transfer, `let alias = fd`, where `fd` is initialized by the source-declared `fs.popen` and a member call uses `alias`. It does not define a runtime resource identity or imply that `popen` succeeded.

`ql/test/receiver-provenance/alias-transfer-controls.uc` separates three cases:

- `direct_copy`: one identifier copy, then `alias.read` and `alias.close`. A bounded analysis would need to connect the alias initializer's identifier read to each member-call receiver.
- `reassigned_before_use`: the alias is overwritten before either call. A flow-sensitive relation must not attribute either call to the original `popen` value.
- `reassigned_after_use`: `alias.read` precedes the overwrite while `alias.close` follows it. This distinguishes per-use reaching identity from a same-function lexical association.

These cases are not included in the #132 expected rows: its allowlist rejects assignment writes, and its observer follows the lexical binding to the `popen` declarator. Adding the alias case therefore requires extracted evidence of the relevant write/read relationship and separate outcomes at the two uses; source spelling alone is insufficient. Controls should also include unrelated same-name locals and a direct non-alias baseline before any relation is proposed.

## Result and limitation

No receiver identity extension is justified by this checkout's available evidence. At investigation time, `codeql` is absent from `PATH`, and `extractor-pack` is not present. Consequently, no database was extracted, no candidate relation was compiled, and no outcomes for these controls are asserted. The fixture is a precise pending discriminator, not evidence that the extractor preserves the necessary alias identity. Continue to treat #48 as blocked for production work; this artifact makes no production model, runtime-target, taint, flow, `path_found`, or security claim.
