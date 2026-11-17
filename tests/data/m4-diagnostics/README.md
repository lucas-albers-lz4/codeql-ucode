# M4 extraction diagnostic replay

Snapshots are from CodeQL CLI 2.27.4 on commit
`ecfc24e992674891c5305f7d2505156238868df9`, using the real ucode extractor
SHA-256 `b8338cfd1a4dc3d70e2615bb11d079a5410cf7da2a5f1113d8c4d6bfc3d63929`.
The malformed input is the committed `ssa_neg` plus the exact bytes
`\nlet integrity_probe = ;\n`; its SHA-256 is
`05fe483a0bdcb349f1baf9382efa3128306311ec853d9c1f391642b3d5053f34`.
The clean input SHA-256 is
`cffb1f7331ea25cf4bb6a8dbf8e1e7092e016003533413376a0738c49cf11e3a`.

The semantic CSVs were produced by each standalone smoke with the malformed
fixture; the corresponding clean and malformed CSV row multisets matched.
`store-read.csv.gz` is losslessly compressed (`gzip -n`). The diagnostic JSON
files are the actual `codeql bqrs decode --format=json --entities=url,string`
output from both legs. They were re-decoded byte-for-byte from the retained
BQRS before replacing only the absolute source-root prefix with
`__SOURCE_ROOT__`; the test replaces that prefix with its temporary source
root. Digests of all portable files are pinned in the test. The fake CLI
validates diagnostic query paths and decode options; this is snapshot replay,
not fresh extraction or a production-analysis result.
