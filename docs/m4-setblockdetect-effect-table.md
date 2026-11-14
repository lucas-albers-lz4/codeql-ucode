# setBlockDetect source observation table

`SetBlockDetectEffectTable.ql` emits a CSV/BQRS table using the columns
`observation_kind`, `method`, `sink_kind`, `command`, `source_path`,
`start_line`, `start_column`, `end_line`, and `end_column`. A row records a
direct identifier `system` call with exactly one argument, the literal
`/sbin/block detect > /etc/config/fstab`, syntactically inside a
`setBlockDetect.call` function. The `BuiltinSystemCall` model excludes a
same-file import binding named `system`. The source path is relative to the
database source root; coordinates cover the call expression. The pinned LuCI
copy in `ql/test/extractor-smoke` yields the call on line 532.

The row is a source observation, not a `handler_effect`: it does not establish
registration, reachability, execution, dataflow or authorization. The model
does not resolve local lexical shadowing, and nested function bodies are also
syntactically contained. Nonliteral commands, wrapped or member callees and
other unsupported shapes are outside this table; absence of a row is not proof
that no effect exists. This query does not read grants or assert `path_found`,
`no_path`, or an authorization violation.

A downstream OpenWrt driver would need to verify the pinned source and supply
its own corpus revision, profile, entrypoint binding, conditions, uncertainty,
and policy context before mapping an observation into interchange records.
That mapping and policy assessment are not implemented here. The focused smoke
checks the pinned file hash, extraction errors, table columns, exact values and
locations, plus synthetic positive and negative controls.
