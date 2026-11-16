from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rpc_ownership_verify", ROOT / "scripts/rpc-ownership-verify.py")
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
HISTORICAL = json.loads((ROOT / "tests/fixtures/rpc-ownership-historical-extracted.json").read_text())
# Actual fresh --entities=url,string row from the bounded focused DB run.
URL_DECODE = json.loads((ROOT / "tests/fixtures/rpc-ownership-extracted-url.json").read_text())
# One actual row retained from query-probes/extracted.json (decoded without
# --entities=url,string); its absolute-path label and empty message are real.
HISTORICAL_ROOT = Path("/root/workspace/cross-repo-audit/round-20261115T200608Z/lanes/integration/tmp/query-probes/ql/test/extractor-smoke")


class FileIdentityTests(unittest.TestCase):
    def test_retained_real_label_only_decode_matches_full_path_and_empty_scalar(self) -> None:
        path = "taint_xfile_a"
        self.assertEqual(VERIFY.file_identities(HISTORICAL, HISTORICAL_ROOT, [path], require_url=False), [path])

    def test_fresh_real_url_decode_matches_full_source_uri(self) -> None:
        rel = "modules/ownership-cross-sink/root/usr/share/rpcd/ucode/luci"
        uri = URL_DECODE["#select"]["tuples"][0][0]["url"]["uri"]
        absolute = Path(uri.removeprefix("file://"))
        source = absolute.parents[len(Path(rel).parts) - 1]
        self.assertEqual(VERIFY.file_identities(URL_DECODE, source, [rel]), [rel])

    def test_zero_position_url_identity_is_canonical_and_label_independent(self) -> None:
        source = Path("/tmp/rpc-source")
        rel = "modules/pkg/root/usr/share/rpcd/ucode/luci"
        uri = "file:///tmp/rpc-source/" + rel
        result = {"#select": {"tuples": [[
            {"label": "not the QL class name", "url": {
                "uri": uri, "startLine": 0, "startColumn": 0, "endLine": 0, "endColumn": 0}}, ""
        ]]}}
        self.assertEqual(VERIFY.file_identities(result, source, [rel]), [rel])

    def test_duplicate_diagnostics_fail_exact_multiplicity(self) -> None:
        row = HISTORICAL["#select"]["tuples"][0]
        duplicate = {"#select": {"tuples": [row, row]}}
        with self.assertRaises(SystemExit):
            VERIFY.file_identities(duplicate, HISTORICAL_ROOT, ["taint_xfile_a"], require_url=False)

    def test_missing_or_extra_diagnostic_identity_fails(self) -> None:
        with self.assertRaises(SystemExit):
            VERIFY.file_identities(HISTORICAL, HISTORICAL_ROOT, ["taint_xfile_a", "taint_xfile_b"], require_url=False)
        extra = {"#select": {"tuples": [HISTORICAL["#select"]["tuples"][0], [
            {"label": "/outside/taint_xfile_b"}, ""
        ]]}}
        with self.assertRaises(SystemExit):
            VERIFY.file_identities(extra, HISTORICAL_ROOT, ["taint_xfile_a", "taint_xfile_b"], require_url=False)

    def test_second_scalar_must_be_empty(self) -> None:
        result = {"#select": {"tuples": [[HISTORICAL["#select"]["tuples"][0][0], "unexpected"]]}}
        with self.assertRaises(SystemExit):
            VERIFY.file_identities(result, HISTORICAL_ROOT, ["taint_xfile_a"], require_url=False)

    def test_current_url_mode_requires_url(self) -> None:
        with self.assertRaises(SystemExit):
            VERIFY.file_identities(HISTORICAL, HISTORICAL_ROOT, ["taint_xfile_a"])


if __name__ == "__main__":
    unittest.main()
