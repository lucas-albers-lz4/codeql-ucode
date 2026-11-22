# Bounded callable call observation on the pinned LuCI profile

The base observation in [markup-cfg-real](markup-cfg-real/README.md) is pinned to
producer d3981986ac685d6fcbb78a3b369aa4ed526c1e4b, consumer
1f01e0a1529b5edf0f9b2e7d6215712bf87e994a and LuCI
b2e0be4b46ec0fd43394c081fa7c50657af14011. The new question is whether the
bounded call shapes in `uhttpd.uc` suffice to cover its callable. The expected
change, specified from the source, is exactly one callable changing from
unsupported to covered, with all 12 root observations unchanged. Its source
contains `request(env, uhttpd.recv, uhttpd.send)`, `dispatch(req)` and
`req.close()` in that order. The full callable node and immediate-edge path is
specified in `scripts/markup-creation-smoke.py`; it includes the exact AST
identities, not just spans. The new graph describes source order only.

For a fresh measurement use the same pinned sources, stage, CodeQL 2.27.4 and
extractor pack as the base evidence, then run `docs/evidence/markup-cfg-real/run.sh`
with a new output directory. The historical check at the end intentionally
fails because it expects the old unsupported callable. Run
`python3 scripts/markup-call-measure-check.py OUTPUT` on that directory: it
requires all 12 root and witness rows, all control rows and extracted control
identities, and the complete real top-level and callable node and edge sets.
The runner's preceding consumer validator checks source and stage hashes,
selected and extracted identities, routing receipt and empty ExtractionErrors.
The command's final historical-check failure must not be interpreted as a passing
runner. The updated checker is a separate verification of the intended delta.

The fresh creation smoke tests exact paths and AST witnesses for the pinned real
file and fresh positive and negative controls; optional calls, computed members,
spread and nested calls are rejected, as is malformed input. The baseline and
new run are bounded predicate observations, not evidence of runtime behavior,
complete parsing, data flow, security coverage, or trusted execution.
