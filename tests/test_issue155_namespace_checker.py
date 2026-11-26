import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("namespace_ci", ROOT / "scripts/issue155-namespace-ci.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

class NamespaceCheckerTest(unittest.TestCase):
    def test_route_rejects_wrong_installed_path_and_counts(self):
        stage = Path("/tmp/namespace-route-check").resolve()
        installed = "usr/share/rpcd/ucode/luci.advanced-reboot"
        row = {"path": str(stage / installed), "installed_path": installed,
               "classification": "plain", "reason": "rpcd_raw_mode_full_path", "status": "plain_route_selected"}
        routing = {"input_count": 1, "plain_count": 1, "markup_count": 0,
                   "markup_inconclusive_count": 0, "uncertain_count": 0, "excluded_count": 0,
                   "duplicate_input_count": 0, "decisions": [row]}
        ci.check_routing(routing, stage, {"luci.advanced-reboot": {}})
        wrong = copy.deepcopy(routing)
        wrong["decisions"][0]["installed_path"] = "luci.advanced-reboot"
        with self.assertRaisesRegex(RuntimeError, "routing differs"):
            ci.check_routing(wrong, stage, {"luci.advanced-reboot": {}})
        wrong = copy.deepcopy(routing)
        wrong["duplicate_input_count"] = 1
        with self.assertRaisesRegex(RuntimeError, "summary counts"):
            ci.check_routing(wrong, stage, {"luci.advanced-reboot": {}})

    def test_optimized_python_fails_closed(self):
        env = dict(os.environ, PYTHONOPTIMIZE="1")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/issue155-namespace-check.py"), "/missing"], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run this checker without Python -O", result.stderr)

    def test_optimized_runner_fails_before_start(self):
        env = dict(os.environ, PYTHONOPTIMIZE="1")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/issue155-namespace-ci.py")], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run this smoke without Python -O", result.stderr)

if __name__ == "__main__":
    unittest.main()
