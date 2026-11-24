# Draft direct RPC producer release gate

This additive workflow prepares a Linux R2 check for the default
`ucode/m4/direct-rpc-shell-word` rule. It is limited to pinned source bytes:
OpenVPN's historical parent and fix plus LuCI's current `swconfig` methods.
A separate explicit query run exercises the historical Tailscale testing rule;
that result is not part of the default suite.

The workflow runs on manual dispatch and pull requests that touch the producer,
query, suite, grammar, or this gate. It is a draft gate. A passing R2 run does
not establish package installation, incoming-change coverage, vulnerability,
runtime reachability, or downstream R3 consumer acceptance.

## Run layout and checks

`scripts/direct-rpc-release-gate.py` creates a unique run root under
`$RUNNER_TEMP`. It requires that path to be new. Databases, extraction roots,
outputs, caches, `HOME`, and temporary files are run-owned. The build copy is
created from the workflow checkout with `git archive`, so extractor-pack
creation does not edit the checkout used by Actions.

Before query output is examined, the runner verifies the full LuCI Git commit
pins, clean source worktrees, Git blob IDs, and SHA-256 digests for the three
source inputs. It checks the source and stage bytes, records a source oracle,
then builds the extractor from the pinned `Cargo.lock` and grammar revision.
The existing pack script invokes `cargo build --release` without `--locked`;
the runner checks the lock digest before and after that command. It records
Rust/Cargo versions, the grammar `Cargo.toml` input digest, the one pinned
`tree-sitter` dev-dependency adjustment performed by `clone-grammar.sh`, pack
file hashes, and both CodeQL pack lock digests.

Each source case gets its own database, common cache, compilation cache, and
output directory. The runner checks the extractor routing receipt, exact
successful-file path multiset, zero extraction errors, default suite contents,
rule descriptor, SARIF result count, and the OpenVPN parent's exact SARIF URI
and region. The two diagnostic queries are also run explicitly so their exact
file identities and errors are retained independently of SARIF notifications.
After `codeql pack install` places locked dependencies in the run-owned HOME
cache, the runner copies those pack bytes into each case's separate common
cache. CodeQL query commands use `--common-caches` and otherwise cannot find
the packages installed under HOME.

The 21 direct-rule control fixtures have a pinned source-first manifest. They
are freshly extracted in one owned database and analyzed with the default
suite; the gate requires five exact positive SARIF locations and no results
at the remaining eligible near misses. Query/database/resolve warnings fail
the gate unless they are the CLI's known low-heap query-cache performance
warning. Zero command exit alone is insufficient.

The Tailscale regression uses its committed `expected.json` manifest and
separate databases for parent, fixed source, and controls. It runs
`TailscaleNestedShell.ql` explicitly, verifies source hashes and extraction
identities, then checks the expected SARIF locations. The query remains
`testing`-tagged and outside the default-suite result contract.

The workflow downloads the official CodeQL CLI 2.27.4 Linux asset and checks
its pinned SHA-256 before unzipping. It installs Rust 1.100.0 with `rustup`
under a unique run-specific `RUSTUP_HOME`; Cargo's build cache, `HOME`, and
`TMPDIR` also belong to the run. It runs on `ubuntu-24.04`. The checkout and
artifact actions are pinned to full action commits (`actions/checkout` v4.2.2
and `actions/upload-artifact` v4.6.2). Every timed command records exit status,
wall time, and GNU
`time` peak RSS when available. The upload excludes databases and caches; it
contains the normalized receipt, source oracle, command log, and raw query
outputs needed to review the R2 result.

## Limitations

The source-pinned Linux gate passed in
[run 45435176723](https://github.com/lucas-albers-lz4/codeql-ucode/actions/runs/45435176723)
on the PR's synthetic merge commit. That run verifies a CI candidate bundle;
it does not publish or test an immutable release asset.
It does not build an OpenWrt image/IPK, inspect package-installed bytes, or
run the downstream consumer. The pinned LuCI `swconfig` zero-result is a
bounded query observation, not a security-negative or safety conclusion.
