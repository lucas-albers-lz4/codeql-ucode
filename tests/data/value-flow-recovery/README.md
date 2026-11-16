# Recovered value-flow output

These are actual CodeQL 2.27.4 decodes from a fresh extraction of the original
`ssa_value_flow` (SHA-256 `6c8bbc36671e90bb07d131ba7390498be79368260fa43f066e644e47436443a5`)
at main `35ab9c5211cb7400f0bd98f5b8345b124a08e3e7`, with the issue-105
smoke diagnostic gate added. The semantic queries produced 122, 56, and 2
rows and the semantic verifier passed; the diagnostic gate rejected the parse
error at 117:88 and the absence of a successful-file receipt.

Original decode SHA-256:

- `out.csv`: `c8af2280007d043a23e9a580a2d938feb1bc2fe33039bd08dc013c06c813a1cb`
- `expr.csv`: `0db1e34bbd0ad0a72125df9b1a82af36a001367a38892e90b982a25cca1afe01`
- `return.csv`: `a1d7c67f34d115fb2abe2a33663edf1a1312f6f9cfe751be3db5a80d3fab9747`
- `SuccessfullyExtractedFiles.json`: `f6fadf4ef24c7e643c82758f548c427e2c7d3f68d0135db83904a7d08fdfc707`
- `ExtractionErrors.json`: `8ae81f0671083f78e5bdea422f38316a714f661e5665c9ad92fa2fcbaca44394`

Only the absolute staged source-root prefix in `ExtractionErrors.json` was
replaced, twice, with `__SOURCE_ROOT__`; the test substitutes its own root.
The other four decodes and the original malformed fixture `ssa_value_flow`
are unmodified. These snapshots exercise the verifier without requiring
CodeQL during Python tests; they do not replace a fresh real smoke.
