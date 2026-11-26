# Linux producer bundle contract (draft)

The R2 gate may produce a **CI candidate** with
`python3 scripts/package-linux-release.py`. The archive is for exercising the
consumer download and verification path; it is not an immutable GitHub
Release. An Actions artifact is identified by workflow run/attempt and has
retention limits. A release asset requires a separately reviewed version tag,
publication workflow, immutable-release repository setting, and an
independent SHA-256 pin in `codeql-openwrt`.

## Included files

The archive contains four producer payload trees:

- `extractor-pack/`: generated Linux extractor, routing configuration,
  dbscheme, downgrade data and helper tools.
- `ql/lib/`: the versioned `ucode-all` QL library pack and lockfile.
- `ql/src/`: the versioned `ucode-queries` QL query pack, default suite,
  queries and lockfile.
- `runner/`: the installed-stage entry point.

It also carries the small root `.codeqlmanifest.json`, which declares the
`ql/*/qlpack.yml` workspace packs needed to resolve the local `${workspace}`
dependency between `ucode-queries` and `ucode-all`.

Transient `.codeql` caches, compiled `.qlx` files, Python caches and databases
are excluded. The CodeQL CLI is **not** included. A consumer must download the
separately pinned official Linux CLI archive, verify its archive SHA-256, and
check its reported version before use.

`bundle-manifest.json` records the producer commit and clean-source assertion,
CodeQL CLI version and Linux ZIP digest, Rust/Cargo versions, grammar revision,
Cargo and QL lock digests, extractor binary digest, pack names/versions,
default suite digest, each `.ql` source digest, and every payload member's
path, size, digest and executable bit. The outer tar.gz is normalized for
timestamps and ownership; this makes the archive deterministic for identical
payload bytes and modes. It does not claim that a native extractor rebuild is
byte-for-byte reproducible. The manifest is integrity metadata, not a
signature: pin the outer archive SHA-256 through a trusted release reference.

## Consumer verification sequence

1. Resolve a producer release tag to its full commit and pin the release asset
   SHA-256 in the OpenWrt lock/acceptance manifest. Do not use a run-scoped
   Actions artifact as the long-lived producer pin.
2. Download the CodeQL CLI archive and producer archive. Verify both archive
   digests before unpacking.
3. Use `python3 scripts/verify-linux-release-bundle.py --archive <tar.gz>
   --expected-sha256 <digest> --output-dir <new-directory>`. This rejects
   traversal paths, duplicate names, links and special files before writing;
   then it verifies exact payload membership, modes, sizes and hashes.
4. In a run-owned writable copy/cache, run `codeql pack install` on extracted
   `ql/lib` and `ql/src`; require both lockfiles to retain their pinned digests.
   The bundle excludes CodeQL dependency caches, so it is not a standalone
   offline artifact. Dependency bootstrap uses the separately pinned CLI and
   locked CodeQL packs; record whether the run used registry/network access.
5. Use the extracted `extractor-pack` as the database extractor search path and
   all three directories as the query search path. Resolve the default suite
   with the pinned CLI and require the reviewed rule/query identities. Verify
   the fresh extraction multiset and actual SARIF at the consumer gate.

## Installed-stage entry point (R2.5 candidate)

Prepare a stage containing every installed-path-shaped regular member of the
selected package. Before running CodeQL, derive a JSON oracle from the actual package
members. Its schema is `ucode-installed-stage-v1`; `files` is a nonempty array
of objects with `path` (stage-relative POSIX path), `sha256` (member bytes),
`expect_success` (boolean), and `route` (the exact expected
`classification`, `reason`, `status`, and `inconclusive_reason`, using JSON
`null` when absent). Include excluded or inconclusive members explicitly.
The runner rejects any staged file missing from the oracle, duplicate path,
changed byte, symlink or special file before invoking CodeQL.

After independently verifying and extracting the release archive and pinned
CodeQL CLI, run from a fresh Linux workspace:

```sh
python3 codeql-ucode-linux/runner/run-installed-stage.py \
  --bundle codeql-ucode-linux \
  --bundle-sha256 '<pinned bundle-manifest.json SHA-256>' \
  --codeql /absolute/path/to/codeql \
  --codeql-archive /absolute/path/to/pinned-codeql-linux64.zip \
  --stage /absolute/path/to/stage \
  --oracle /absolute/path/to/oracle.json \
  --output /absolute/path/to/new-run
```

The command copies the bundle into its new run directory, installs locked QL
dependencies into run-owned HOME and caches, creates a new database, checks
the route and exact successful-file multiset, requires zero extraction errors,
resolves and analyzes the default suite, and writes `receipt.json`,
`commands.json`, `output/coverage-manifest.json`, raw command logs, routing
and SARIF under `new-run/`. The coverage manifest records each package member's
actual route, digest, successful-file multiplicity, extraction-error count,
resolved suite, SARIF digest and command costs; the receipt pins its digest. It
records command wall times and Linux peak RSS where GNU time is available.
The successful-file diagnostic requires an extractor-emitted plain or markup
AST location. An excluded file can still be represented by CodeQL's general
file table, so a bare `File` row is insufficient evidence of Ucode extraction.
The runner hashes the supplied CodeQL ZIP against the bundle's pinned ZIP
digest and records that identity. The caller must point `--codeql` at the CLI
extracted from that verified ZIP; the runner checks its reported version but
does not reverify every installed CLI file against the archive.
This interface does not derive the oracle or authenticate a caller-supplied
manifest digest; the consuming lock must pin that digest independently. A
versioned release and clean Linux package tests are still required before
the candidate becomes a supported interface.

The producer's R2.5 CI gate uses actual `luci-base` and Ucode-enabled
`wifi-scripts` IPKs retained by `codeql-openwrt` runs 45513606386 and
45548269425. Their pinned archive SHA-256 values are
`1a2188f5206ce61c993fdcc451781a06994ae2175b489eef56595858ef22b363`
and `20f2e18297a10e2c2fc0f3457dee52e5ee2db01a8d17d52ba44dffaf79ba833a`.
The source-first oracle files under `tests/fixtures/r25-installed-stage/`
identify 18 and 17 selected members respectively, alongside all other regular
members as explicit exclusions. The first includes two
extensionless files and eight markup routes that remain inconclusive; the
second includes Ucode-shebang `mac80211.sh` and extensionless `iwinfo`.
`scripts/stage-installed-ipk.py` compares actual IPK member bytes and the
independently fixed oracle before staging. GitHub Actions artifacts expire;
the pinned runs are a temporary fixture source, not durable release custody.
The producer gate fetches each artifact by its numeric artifact ID into a
new run-owned directory. It caps the live response, checks the reviewed ZIP
SHA-256, validates every ZIP member's path, type, uniqueness and declared size,
then extracts only the named IPK with an exclusive create and checks its
independently pinned digest. Other members, including build logs and the
Wi-Fi `n` variant, are never expanded. The GitHub read token is removed from
the environment before staging and CodeQL execution. The gate retains a small
artifact receipt with the IDs, ZIP and IPK digests and byte counts.

The producer R2 CI job can upload the resulting archive as a short-lived
candidate beside its R2 receipt. Passing that job validates bundle creation
and manifest checks, not release publication or downstream acceptance. R2
release publication and R3 consumer acceptance remain separate gates.

## Versioned publication

The `publish-linux-release.yml` tag workflow rebuilds and reruns the R2 and
R2.5 gates
from the tagged commit in a read-only job. It requires a clean checkout, a
version-shaped tag that resolves to the event SHA, and a commit reachable
from `origin/main`. A separate publication job verifies the transferred
archive, manifest, commit and tag pins without a write token, then rechecks
the remote tag and main ancestry before refusing an existing release or
creating a draft. The archive is marked `versioned-release`; the draft job
refetches both assets and compares their bytes. It does not publish the draft:
the GitHub Actions token cannot establish the live immutable-release setting
through the admin-only repository API. Before publication, an administrator
must query that setting, verify it is enabled, verify the draft assets and
tag against the recorded pins, then publish the draft. A successful publish
must be followed by an `isImmutable=true` check and independent asset refetch.
The release operator should record the exact `gh api
repos/lucas-albers-lz4/codeql-ucode/immutable-releases` response immediately
before publishing, verify the draft tag and both downloaded asset hashes,
then publish with `gh release edit TAG --draft=false --prerelease=true
--latest=false`. If the live setting cannot be read with admin credentials,
leave the draft unpublished. A failed preparation job leaves a draft that
must be inspected and explicitly resolved; rerunning the tag workflow does
not overwrite an existing release.
The repository must protect release tags and enable immutable releases before
publication. Set the repository variable `RELEASE_POLICY_CONFIRMED=true`
only after checking both settings. The build job refuses to run without it;
the draft job checks the remote tag target. Workflow checks alone cannot stop
an administrator from later changing repository policy. The consumer must independently pin the
full commit, tag and archive digest and verify the downloaded bytes. A
successful publication still does not prove OpenWrt's downstream R3 handoff.
