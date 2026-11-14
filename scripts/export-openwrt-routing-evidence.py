#!/usr/bin/env python3
"""Export routing cases classified by the pinned OpenWrt implementation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PINNED_OPENWRT_COMMIT = "ed6ec314d9796621bbcc98c43824189a44c9a0c2"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: export-openwrt-routing-evidence.py OPENWRT_REPO")

    repo = Path(sys.argv[1]).resolve()
    actual_commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_commit != PINNED_OPENWRT_COMMIT:
        raise SystemExit(
            f"expected OpenWrt {PINNED_OPENWRT_COMMIT}, got {actual_commit}"
        )

    module_path = repo / "corpus" / "luci_ssl_files.py"
    spec = importlib.util.spec_from_file_location("luci_ssl_files", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load OpenWrt classifier from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rows = []
    for evidence in module.ROUTING_EVIDENCE:
        if evidence["kind"] == "src-install":
            installed = evidence["installed"]
        else:
            installed = module.luci_mk_installed(evidence["kind"], evidence["rel"])
        classification, _reason, _rule = module.classify_installed(
            installed,
            shebang=evidence.get("shebang"),
            content_prefix=evidence.get("content_prefix") or "",
        )
        content = evidence.get("content_prefix") or ""
        shebang = evidence.get("shebang") or ""
        if shebang and not content.startswith(shebang):
            content = f"{shebang}\n{content}" if content else shebang
        rows.append(
            {
                "fs_path": installed,
                "classification": classification,
                "source": content,
            }
        )

    if len(rows) != 24:
        raise SystemExit(f"expected 24 pinned routing rows, got {len(rows)}")
    json.dump(rows, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
