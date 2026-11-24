#!/usr/bin/env bash
# Clone the lockfile grammar SHA into extractor/tree-sitter and hide extra node-types.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/extractor/tree-sitter"
URL="https://github.com/m00qek/tree-sitter-ucode.git"
REV="4a243af329fae2f4ff01e0fc80133cbab8314600"

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
  npm ci
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
