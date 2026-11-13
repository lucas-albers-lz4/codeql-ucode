# M4: `codeql/threat-models` pack dependency

Typecheck slice only. Not production taint and not `path_found`.

## What this adds

- `ql/lib/qlpack.yml` depends on `codeql/threat-models` with
  `codeql-pack.lock.yml` pinning.
- `Concepts.qll` imports `codeql.threatmodels.ThreatModels` and uses the pack's
  `currentThreatModel` predicate (no local stub).
- `ActiveThreatModelSource` typechecks and stays uninhabited because ucode has
  no `ThreatModelSource::Range` subclasses yet.

## Gaps (later PR)

- ucode-specific threat-model sources (e.g. LuCI/UCI) when honestly modeled.
- Do not wire `ActiveThreatModelSource` into production `LocalTaint` /
  `RequestArgsExec` until explicitly scoped.
