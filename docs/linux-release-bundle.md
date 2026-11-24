# Linux producer bundle contract (draft)

The R2 gate may produce a **CI candidate** with
`python3 scripts/package-linux-release.py`. The archive is for exercising the
consumer download and verification path; it is not an immutable GitHub
Release. An Actions artifact is identified by workflow run/attempt and has
retention limits. A release asset requires a separately reviewed version tag,
publication workflow, immutable-release repository setting, and an
independent SHA-256 pin in `codeql-openwrt`.

## Included files

The archive contains exactly three producer payload trees:

- `extractor-pack/`: generated Linux extractor, routing configuration,
  dbscheme, downgrade data and helper tools.
- `ql/lib/`: the versioned `ucode-all` QL library pack and lockfile.
- `ql/src/`: the versioned `ucode-queries` QL query pack, default suite,
  queries and lockfile.

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

The producer R2 CI job can upload the resulting archive as a short-lived
candidate beside its R2 receipt. Passing that job validates bundle creation
and manifest checks, not release publication or downstream acceptance. R2
release publication and R3 consumer acceptance remain separate gates.
