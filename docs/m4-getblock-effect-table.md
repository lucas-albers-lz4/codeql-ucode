# getBlockDevices source observation table

`GetBlockDevicesEffectTable.ql` emits a CSV/BQRS table with named columns:
`observation_kind`, `method`, `sink_kind`, `command`, `source_path`,
`start_line`, `start_column`, `end_line`, and `end_column`. Each row is a
syntactic observation of the direct identifier call `popen` with the exact
literal `/sbin/block info 2>/dev/null` in a `getBlockDevices.call` function,
with an unaliased `popen` import from `fs` in the same file. The path is
relative to the database source root; the coordinates are the call expression.
The pinned LuCI copy in `ql/test/extractor-smoke` yields the row at line 481.

The row is not itself a `handler_effect`: the table establishes only source
shape and containment. It does not prove the callback is registered or reached,
resolve lexical shadowing of the import, execute the call, follow data flow, or
assess authorization. Nested function bodies are syntactically contained too.
Aliases, nonliteral commands, unresolved imports and unsupported shapes are not
covered; no match is not proof that no effect exists. This table does not read
grants or assert `path_found`, `no_path`, or an authorization violation.

A downstream OpenWrt driver may map a verified observation to the existing
interchange shape only after checking the pinned source and supplying its own
`corpus_revision`, `profile`, entrypoint binding, conditions, uncertainty, and
policy context. That mapping, policy joins and assessments are not implemented
here. The focused smoke indexes the pinned file and synthetic positive and
negative controls; it checks source hash, extraction errors, table column names,
exact values and source locations.
