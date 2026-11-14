"""Exercise the real aggregate runner with cheap child smokes and a fake CLI."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class SmokePackInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("ci-ql-smoke.sh", "ql-smoke-pack-install.sh"):
            shutil.copy(REPO / "scripts" / name, scripts / name)
        child = '''#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
printf '%s\\n' "$(basename "$0")" >> "$SMOKE_LOG"
'''
        (scripts / "m3-smoke.sh").write_text(child)
        # A nested M3 invocation must inherit aggregate readiness.
        (scripts / "m4-block-device-smoke.sh").write_text(
            child + 'bash "$ROOT/scripts/m3-smoke.sh"\n'
        )
        (scripts / "m4-smoke.sh").write_text(child)
        fake = self.root / "codeql"
        fake.write_text('''#!/usr/bin/env bash
set -euo pipefail
[[ "$1 $2" == 'pack install' ]]
printf '%s\\n' "$3" >> "$INSTALL_LOG"
[[ "${FAIL_PACK:-}" != "$(basename "$3")" ]] || exit 23
''')
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.root}:{os.environ['PATH']}",
                        INSTALL_LOG=str(self.root / "installs"),
                        SMOKE_LOG=str(self.root / "smokes"))
        self.env.pop("CODEQL_UCODE_SMOKE_PACKS_READY", None)
        self.env.pop("FAIL_PACK", None)

    def run_script(self, name, **env):
        return subprocess.run(["bash", f"scripts/{name}"], cwd=self.root,
                              env=dict(self.env, **env), capture_output=True, text=True)

    def lines(self, name):
        path = self.root / name
        return path.read_text().splitlines() if path.exists() else []

    def test_aggregate_installs_once_and_preserves_order(self):
        result = self.run_script("ci-ql-smoke.sh",
                                 CODEQL_UCODE_SMOKE_PACKS_READY=str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.lines("installs"),
                         [str(self.root / "ql/lib"), str(self.root / "ql/src")])
        self.assertEqual(self.lines("smokes"), ["m3-smoke.sh", "m4-smoke.sh",
                                               "m4-block-device-smoke.sh", "m3-smoke.sh"])

    def test_both_install_failures_stop_before_smokes(self):
        for pack, count in (("lib", 1), ("src", 2)):
            with self.subTest(pack=pack):
                (self.root / "installs").unlink(missing_ok=True)
                result = self.run_script("ci-ql-smoke.sh", FAIL_PACK=pack)
                self.assertEqual(result.returncode, 23)
                self.assertEqual(len(self.lines("installs")), count)
                self.assertEqual(self.lines("smokes"), [])

    def test_standalone_and_nested_standalone_install(self):
        for script, pairs in (("m3-smoke.sh", 1), ("m4-smoke.sh", 1),
                              ("m4-block-device-smoke.sh", 2)):
            with self.subTest(script=script):
                (self.root / "installs").unlink(missing_ok=True)
                result = self.run_script(script)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(self.lines("installs")), pairs * 2)

    def test_readiness_for_another_checkout_does_not_skip(self):
        result = self.run_script("m3-smoke.sh", CODEQL_UCODE_SMOKE_PACKS_READY="/other")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.lines("installs")), 2)

    def test_all_real_smokes_use_shared_installer(self):
        paths = [REPO / "scripts/m3-smoke.sh", *(REPO / "scripts").glob("m4*smoke.sh")]
        for path in paths:
            with self.subTest(script=path.name):
                source = path.read_text()
                self.assertIn('source "$ROOT/scripts/ql-smoke-pack-install.sh"', source)
                self.assertIn("\ninstall_smoke_packs\n", source)
                self.assertNotIn("codeql pack install", source)


if __name__ == "__main__":
    unittest.main()
