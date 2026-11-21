"""Offline checks for the pinned grammar bootstrap's dependency rewrite."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REV = "4a243af329fae2f4ff01e0fc80133cbab8314600"


class CloneGrammarTest(unittest.TestCase):
    def test_dependency_rewrite_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy(ROOT / "scripts/clone-grammar.sh", scripts)
            grammar = root / "extractor/tree-sitter"
            (grammar / ".git").mkdir(parents=True)
            (grammar / "ucode/src").mkdir(parents=True)
            (grammar / "ucode/src/node-types.json").write_text("[]\n")
            cargo = grammar / "Cargo.toml"
            original = '[dev-dependencies]\ntree-sitter = "0.27.1"\nother = "unchanged"\n'
            expected = original.replace('tree-sitter = "0.27.1"', 'tree-sitter = "=0.26.8"')
            cargo.write_text(original)
            cargo.chmod(0o644)
            bindir = root / "bin"
            bindir.mkdir()
            git = bindir / "git"
            git.write_text('#!/bin/sh\ncase "$3" in\nfetch|checkout) exit 0 ;;\nrev-parse) echo ' + REV + ' ;;\n*) exit 1 ;;\nesac\n')
            git.chmod(0o755)
            system_sed = shutil.which("sed")
            self.assertIsNotNone(system_sed)
            sed = bindir / "sed"
            sed.write_text('#!/bin/sh\ncase "$1" in -i*) exit 42 ;; esac\nexec "$SYSTEM_SED" "$@"\n')
            sed.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["SYSTEM_SED"] = system_sed
            env.pop("CODEQL_UCODE_HIDE_EXTRA_NODE_TYPES", None)
            for _ in range(2):
                result = subprocess.run(["bash", str(scripts / "clone-grammar.sh")], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(cargo.read_text(), expected)
                self.assertEqual(cargo.stat().st_mode & 0o777, 0o644)
                self.assertEqual(list(grammar.glob(".Cargo.toml.*")), [])

            # Ensure the shim rejects the former GNU-only invocation on all hosts.
            cargo.write_text(original)
            result = subprocess.run(["sed", "-i", 's/tree-sitter = "0.27.1"/tree-sitter = "=0.26.8"/', str(cargo)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertEqual(cargo.read_text(), original)


if __name__ == "__main__":
    unittest.main()
