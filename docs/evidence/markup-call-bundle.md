# Bounded callable call observation on the pinned LuCI profile

The base observation in [markup-cfg-real](markup-cfg-real/README.md) is pinned to
producer d3981986ac685d6fcbb78a3b369aa4ed526c1e4b, consumer
1f01e0a1529b5edf0f9b2e7d6215712bf87e994a and LuCI
b2e0be4b46ec0fd43394c081fa7c50657af14011. The new question is whether the
bounded call shapes in `uhttpd.uc` suffice to cover its callable. The expected
change, specified from the source, is exactly one callable changing from
unsupported to covered, with all 12 root observations unchanged. Its source
contains `request(env, uhttpd.recv, uhttpd.send)`, `dispatch(req)` and
`req.close()` in that order. The full projected callable node and immediate-edge path is
specified in `scripts/markup-creation-smoke.py`; it includes the exact AST
witnesses, not just spans. The new graph describes source order only.

For a fresh measurement use the same pinned sources, stage, CodeQL 2.27.4 and
extractor pack as the base evidence. Run `docs/evidence/markup-cfg-real/run.sh`
with the same five arguments and a new output directory, followed by
`--call-bundle`. The runner checks source and stage hashes, selected and
extracted identities, routing receipt and empty ExtractionErrors, then applies
the strict source-aware call-bundle oracle to the 12 roots, callable, controls,
logical AST node witnesses and edges. Without the flag the original historical
expectations remain in effect. `test_call_bundle_check.py OUTPUT STAGE
CONTROLS_ROOT` exercises missing and mutated outputs under optimized Python.

The projected query rows describe logical AST witnesses (node class, location,
parent class and index); they do not prove distinct internal AST identities when
projections collide. The checks compare row multiplicities and complete projected
node and edge sets, subject to that limitation.

The fresh creation smoke tests exact paths and AST witnesses for the pinned real
file and fresh positive and negative controls; optional calls and members, computed and multi-hop members,
spread and nested calls are rejected, as is malformed input. The baseline and
new run are bounded predicate observations, not evidence of runtime behavior,
complete parsing, data flow, security coverage, or trusted execution.

## Local review-fix run, 2026-11-23 UTC

The implementation parent was `2fe6745c482d29cd83d5e38940077a2aea5e11db`;
the checked-in review fixes add the strict runner and controls described above.
The call-bundle run used the CLI at
`/Users/lalbers/gitroot/ucode/.tools/codeql-2.27.4/codeql/codeql` (release
2.27.4) and reused the extractor built at the producer base, whose macOS binary
SHA-256 was `35aeb3a59305c7fb21b9ead30d658add5d255645f3f73efc877f5363abf242a8`.
The pinned consumer manifest SHA-256 was
`8f84bf665718d36972c8b4f3d8648e1bd0c660b016cca80fa430453bb1b47a8f`.
Both the historical default runner (against producer d398198) and the call-bundle
runner completed successfully on fresh databases. The latter returned the same
12 root observations and changed the sole callable to covered. The strict
checker, source/stage/routing/diagnostic validator and creation smoke passed;
the optimized-Python test rejected missing outputs and mutated result, header,
node, edge and source witnesses. The optional-member and multi-hop cases each
had their designated extracted AST witness and no callable graph.

The retained local command logs are `/tmp/markup-review-historical.log`,
`/tmp/markup-review-call-bundle.log`, and `/tmp/markup-review-smoke.log`;
outputs are under the matching `/tmp/markup-review-historical` and
`/tmp/markup-review-call-bundle` directories. Those paths are local and may be
removed by the environment. For the call-bundle run, SHA-256 of the root,
callable, projected nodes and projected edges CSVs respectively were:

- `b9b682ab2751c0afa34a3c767403aa4db92807bdd09cb51097fa8af3731f5d06`
- `c4b0e4f2fa926d58147855cc478ad9f4646e88b903e62d0c9b3ca6698745d517`
- `a5680e65f04e1083e3f325a865ec639900757d0f5008a6079e2a7148e1eb81df`
- `8e1804bd0fed7446c78d7092a84924d6871f34f8b567af94cd0eabb5df287838`
