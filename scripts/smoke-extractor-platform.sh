#!/usr/bin/env bash
# Match the platform directories created by create-extractor-pack.sh.
smoke_extractor_platform() {
  case "$1" in
    linux-gnu*) printf '%s\n' linux64 ;;
    darwin*) printf '%s\n' osx64 ;;
    *) printf 'Unsupported OS: %s\n' "$1" >&2; return 1 ;;
  esac
}
