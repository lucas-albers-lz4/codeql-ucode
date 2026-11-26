#!/usr/bin/env python3
"""Focused ZIP boundary controls; no GitHub or CodeQL access."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "r25_artifact", Path(__file__).with_name("download-pinned-r25-artifact.py"))
artifact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ipk = b"pinned IPK bytes"
        self.expected = hashlib.sha256(self.ipk).hexdigest()
        self.target = self.root / "luci-base.ipk"

    def make_zip(self, entries):
        path = self.root / "artifact.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, data, mode in entries:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        return path

    def test_multimember_extracts_only_pinned_ipk(self):
        path = self.make_zip([("run.log", b"log" * 1000, stat.S_IFREG | 0o644),
                              ("luci-base.ipk", self.ipk, stat.S_IFREG | 0o644)])
        receipt = artifact.extract_ipk(path, "luci-base.ipk", self.expected, self.target)
        self.assertEqual(receipt["ipk_sha256"], self.expected)
        self.assertEqual(self.target.read_bytes(), self.ipk)
        self.assertFalse((self.root / "run.log").exists())

    def test_rejects_unsafe_and_duplicate_members_before_output(self):
        for name in ("../escape", "/absolute", "a/../escape", "a\\escape", "./run.log"):
            with self.subTest(name=name):
                path = self.make_zip([(name, b"bad", stat.S_IFREG | 0o644),
                                      ("luci-base.ipk", self.ipk, stat.S_IFREG | 0o644)])
                with self.assertRaisesRegex(ValueError, "unsafe member path"):
                    artifact.extract_ipk(path, "luci-base.ipk", self.expected, self.target)
                self.assertFalse(self.target.exists())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            path = self.make_zip([("run.log", b"one", stat.S_IFREG | 0o644),
                                  ("run.log", b"two", stat.S_IFREG | 0o644),
                                  ("luci-base.ipk", self.ipk, stat.S_IFREG | 0o644)])
        with self.assertRaisesRegex(ValueError, "duplicate member"):
            artifact.extract_ipk(path, "luci-base.ipk", self.expected, self.target)
        self.assertFalse(self.target.exists())

    def test_rejects_symlink_and_ignores_other_ipk(self):
        path = self.make_zip([("link", b"outside", stat.S_IFLNK | 0o777),
                              ("luci-base.ipk", self.ipk, stat.S_IFREG | 0o644)])
        with self.assertRaisesRegex(ValueError, "link, directory or special"):
            artifact.extract_ipk(path, "luci-base.ipk", self.expected, self.target)
        path = self.make_zip([("other.ipk", b"other", stat.S_IFREG | 0o644),
                              ("luci-base.ipk", self.ipk, stat.S_IFREG | 0o644)])
        artifact.extract_ipk(path, "luci-base.ipk", self.expected, self.target)
        self.assertEqual(self.target.read_bytes(), self.ipk)
        self.assertFalse((self.root / "other.ipk").exists())

    def test_bounds_and_digest_reject_without_retained_ipk(self):
        path = self.make_zip([("luci-base.ipk", self.ipk, stat.S_IFREG | 0o644)])
        old = artifact.MAX_MEMBER_BYTES
        artifact.MAX_MEMBER_BYTES = len(self.ipk) - 1
        self.addCleanup(setattr, artifact, "MAX_MEMBER_BYTES", old)
        with self.assertRaisesRegex(ValueError, "member size"):
            artifact.extract_ipk(path, "luci-base.ipk", self.expected, self.target)
        artifact.MAX_MEMBER_BYTES = old
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            artifact.extract_ipk(path, "luci-base.ipk", "0" * 64, self.target)
        self.assertFalse(self.target.exists())

    def test_metadata_binds_id_name_run_and_zip_digest(self):
        data = b'{"id":12,"name":"pinned","expired":false,"workflow_run":{"id":34},"size_in_bytes":123,"digest":"sha256:' + b"a" * 64 + b'"}'
        artifact.check_metadata(data, artifact_id=12, run_id=34, name="pinned", zip_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "workflow run"):
            artifact.check_metadata(data, artifact_id=12, run_id=35, name="pinned", zip_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "API digest"):
            artifact.check_metadata(data, artifact_id=12, run_id=34, name="pinned", zip_sha256="b" * 64)

    def test_stream_cap_removes_partial_zip_without_exposing_stderr(self):
        fake = self.root / "gh"
        fake.write_text("#!/bin/sh\nprintf 'secret-test-token\\n' >&2\nhead -c 1024 /dev/zero\n")
        fake.chmod(0o755)
        target = self.root / "partial.zip"
        with mock.patch.dict(os.environ, {"PATH": f"{self.root}:{os.environ['PATH']}",
                                         "GH_TOKEN": "secret-test-token"}):
            with self.assertRaisesRegex(ValueError, "byte budget") as error:
                artifact.gh_bytes("/unused", 100, target)
        self.assertFalse(target.exists())
        self.assertNotIn("secret-test-token", str(error.exception))


if __name__ == "__main__":
    unittest.main()
