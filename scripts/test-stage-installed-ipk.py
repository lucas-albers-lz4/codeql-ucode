#!/usr/bin/env python3
"""Safe IPK staging controls for the R2.5 package gate."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("stage_ipk", Path(__file__).with_name("stage-installed-ipk.py"))
stage_ipk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_ipk)


def archive(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return stream.getvalue()


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = b"#!/usr/bin/ucode\nreturn 1;\n"
        self.oracle = self.root / "oracle.json"
        self.oracle.write_text(json.dumps({"schema": "ucode-installed-stage-v1", "files": [
            {"path": "usr/bin/tool", "sha256": stage_ipk.digest(self.source),
             "route": {"classification": "plain"}},
            {"path": "usr/bin/shell", "sha256": stage_ipk.digest(b"#!/bin/sh\n"),
             "route": {"classification": "excluded"}}]}))

    def ipk(self, entries):
        path = self.root / "fixture.ipk"
        path.write_bytes(archive({"./data.tar.gz": archive(entries)}))
        return path

    def test_stages_exact_extensionless_ucode_member(self):
        path = self.ipk({"./usr/bin/tool": self.source, "./usr/bin/shell": b"#!/bin/sh\n"})
        receipt = stage_ipk.stage(path, stage_ipk.digest(path.read_bytes()), self.oracle,
                                  self.root / "stage")
        self.assertEqual(receipt["selected"], ["usr/bin/tool"])
        self.assertEqual(receipt["excluded"], ["usr/bin/shell"])
        self.assertEqual((self.root / "stage/usr/bin/tool").read_bytes(), self.source)

    def test_changed_ipk_and_extra_candidate_fail(self):
        path = self.ipk({"./usr/bin/tool": self.source, "./usr/bin/shell": b"#!/bin/sh\n"})
        with self.assertRaisesRegex(ValueError, "IPK digest"):
            stage_ipk.stage(path, "0" * 64, self.oracle, self.root / "stage")
        path = self.ipk({"./usr/bin/tool": self.source, "./usr/bin/extra.uc": b"return 2;\n"})
        with self.assertRaisesRegex(ValueError, "regular-member inventory"):
            stage_ipk.stage(path, stage_ipk.digest(path.read_bytes()), self.oracle,
                            self.root / "stage")

    def test_traversal_member_rejected(self):
        path = self.ipk({"../outside.uc": b"return 2;\n", "usr/bin/tool": self.source,
                         "usr/bin/shell": b"#!/bin/sh\n"})
        with self.assertRaisesRegex(ValueError, "unsafe archive member"):
            stage_ipk.stage(path, stage_ipk.digest(path.read_bytes()), self.oracle,
                            self.root / "stage")

    def test_selection_rules_cover_markup_and_uncertain_paths(self):
        self.assertTrue(stage_ipk.candidate("usr/share/ucode/luci/page", b"  {{ value }}\n"))
        self.assertTrue(stage_ipk.candidate("usr/share/ucode/unknown", b"plain text\n"))
        self.assertFalse(stage_ipk.candidate("etc/config/example", b"config example\n"))


if __name__ == "__main__":
    unittest.main()
