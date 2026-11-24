#!/usr/bin/env bash
# Clone the lockfile grammar SHA into extractor/tree-sitter and hide extra node-types.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/extractor/tree-sitter"
URL="https://github.com/m00qek/tree-sitter-ucode.git"
REV="4a243af329fae2f4ff01e0fc80133cbab8314600"
CLI_VERSION="0.27.1"
NPM_LOCK_SHA256="57aad774d0d6cb3095d98986bf8425724347b475082604bfb1ab1d32eb7cae4f"

if [[ -d "$DEST/.git" ]]; then
	git -C "$DEST" fetch --depth=1 origin "$REV"
	git -C "$DEST" checkout --force "$REV"
else
	rm -rf "$DEST"
	git clone --depth=1 "$URL" "$DEST"
	git -C "$DEST" fetch --depth=1 origin "$REV"
	git -C "$DEST" checkout --force "$REV"
fi

got="$(git -C "$DEST" rev-parse HEAD)"
if [[ "$got" != "$REV" ]]; then
	echo "grammar SHA mismatch: got $got want $REV" >&2
	exit 1
fi

# Apply the reviewed source-only compatibility patch to the pinned grammar,
# then regenerate its tracked parser and node-type outputs with the locked CLI.
# The producer release gate verifies the patch and generated output hashes.
patch -d "$DEST" -p1 < "$ROOT/patches/0005-newer-wifi-ucode-grammar.patch"
(
  cd "$DEST"
  # The npm lock covers the CLI wrapper. Its install hook fetches a native
  # binary separately, so disable hooks and verify the release asset ourselves.
  case "$(uname -s):$(uname -m)" in
    Linux:x86_64) asset=linux-x64; cli_sha256=d01042f94ba3d6827ddc9788e235f75d8366431be42bdf90ade534d960c98b7d ;;
    Linux:aarch64) asset=linux-arm64; cli_sha256=404be5d54a4955571c4067c21d4699660eab3a534cefb0659341b207f7139ec5 ;;
    Darwin:x86_64) asset=macos-x64; cli_sha256=b740262cb0f35be64e39b50ad68b020433924a7bcee5ae5c8e40e68d71215647 ;;
    Darwin:arm64) asset=macos-arm64; cli_sha256=46cb97d9a2c52c94e22d9a76c2f1116156b8b61f98360e2a9cce05fcb197cd4d ;;
    *) echo "Unsupported platform for the pinned Tree-sitter CLI" >&2; exit 1 ;;
  esac
  printf '%s  %s\n' "$NPM_LOCK_SHA256" package-lock.json | shasum -a 256 -c
  archive="$(mktemp)"
  trap 'rm -f "$archive"' EXIT
  curl --fail --location --retry 3 --output "$archive" \
    "https://github.com/tree-sitter/tree-sitter/releases/download/v$CLI_VERSION/tree-sitter-$asset.gz"
  printf '%s  %s\n' "$cli_sha256" "$archive" | shasum -a 256 -c
  npm ci --ignore-scripts
  cli=node_modules/tree-sitter-cli/tree-sitter
  gzip -dc "$archive" > "$cli"
  chmod 755 "$cli"
  npm run build
  npm test
)

# The grammar crate's published tests want tree-sitter 0.27.1. Cargo cannot
# link two runtimes (`links = "tree-sitter"`). Extractor runtime is 0.26.8
# (ABI 15, compiles with codeql-extractor@ce29d8a). Lower the local clone's
# dev-dep; we do not run the grammar crate's own tests in M1.
if grep -q 'tree-sitter = "0.27.1"' "$DEST/Cargo.toml"; then
	tmp="$(mktemp "$DEST/.Cargo.toml.XXXXXXXX")"
	trap 'rm -f "$tmp"' EXIT
	cp -p "$DEST/Cargo.toml" "$tmp"
	sed 's/tree-sitter = "0.27.1"/tree-sitter = "=0.26.8"/' "$DEST/Cargo.toml" > "$tmp"
	mv "$tmp" "$DEST/Cargo.toml"
	trap - EXIT
fi

# Hide extra node-types only when CODEQL_UCODE_HIDE_EXTRA_NODE_TYPES=1 (generator init).
# The Rust crate include_str!s all three files, so cargo test needs them visible.
if [[ "${CODEQL_UCODE_HIDE_EXTRA_NODE_TYPES:-}" == "1" ]]; then
	for extra in ucode_markup ucdocs; do
		src="$DEST/$extra/src/node-types.json"
		if [[ -f "$src" ]]; then
			mv "$src" "$src.m1-hidden"
		fi
	done
	if [[ -f "$DEST/ucode_markup/src/node-types.json" ]] || [[ -f "$DEST/ucdocs/src/node-types.json" ]]; then
		echo "extra node-types.json still visible" >&2
		exit 1
	fi
fi

if [[ ! -f "$DEST/ucode/src/node-types.json" ]]; then
	echo "missing $DEST/ucode/src/node-types.json" >&2
	exit 1
fi

echo "grammar $REV plus reviewed compatibility patch ready at $DEST (ucode/src/node-types.json visible)"
