#!/usr/bin/env python3
"""Check copied source-first fixture bytes, without claiming extraction."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
for manifest, key, prefix in (
    ("source-manifest.json", "controls", root),
    ("duplicate-source-manifest.json", "files", root / "duplicate"),
    ("model-manifest.json", "files", root),
):
    data = json.loads((root / manifest).read_text())
    for entry in data[key]:
        path = prefix / entry["path"]
        content = path.read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise SystemExit(f"fixture mismatch: {path}")
real = json.loads((root / "source-manifest.json").read_text())["real_source"]
content = (root / real["staged_path"]).read_bytes()
if len(content) != real["bytes"] or hashlib.sha256(content).hexdigest() != real["sha256"]:
    raise SystemExit("real DDNS fixture mismatch")
print("fixture bytes match source-first manifests; extraction not checked")
