"""Offline checks for the pinned grammar bootstrap and dependency rewrite."""
import gzip
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
            patches = root / "patches"
            patches.mkdir()
            shutil.copy(ROOT / "patches/0005-newer-wifi-ucode-grammar.patch", patches)
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
            mock_log = root / "mock.log"
            patch = bindir / "patch"
            patch.write_text('#!/bin/sh\nprintf "patch\\n" >> "$MOCK_LOG"\n')
            patch.chmod(0o755)
            npm = bindir / "npm"
            npm.write_text('''#!/bin/sh
printf "npm %s\\n" "$*" >> "$MOCK_LOG"
case "$*" in
  'ci --ignore-scripts') mkdir -p node_modules/tree-sitter-cli ;;
  'run build') node_modules/tree-sitter-cli/tree-sitter ;;
esac
''')
            npm.chmod(0o755)
            uname = bindir / "uname"
            uname.write_text('#!/bin/sh\ncase "$1" in -s) echo Linux ;; -m) echo x86_64 ;; esac\n')
            uname.chmod(0o755)
            curl = bindir / "curl"
            curl.write_text('''#!/bin/sh
test "$7" = https://github.com/tree-sitter/tree-sitter/releases/download/v0.27.1/tree-sitter-linux-x64.gz || exit 1
cp "$MOCK_CLI_ARCHIVE" "$6"
''')
            curl.chmod(0o755)
            checksum = bindir / "shasum"
            checksum.write_text('''#!/bin/sh
read -r digest filename
case "$filename" in
  package-lock.json) test "$digest" = 57aad774d0d6cb3095d98986bf8425724347b475082604bfb1ab1d32eb7cae4f ;;
  *) test "$digest" = d01042f94ba3d6827ddc9788e235f75d8366431be42bdf90ade534d960c98b7d &&
     test "${MOCK_BAD_ARCHIVE:-0}" = 0 ;;
esac
''')
            checksum.chmod(0o755)
            archive = root / "mock-cli.gz"
            archive.write_bytes(gzip.compress(b'#!/bin/sh\nprintf "cli\\n" >> "$MOCK_LOG"\n'))
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["SYSTEM_SED"] = system_sed
            env["MOCK_LOG"] = str(mock_log)
            env["MOCK_CLI_ARCHIVE"] = str(archive)
            env.pop("CODEQL_UCODE_HIDE_EXTRA_NODE_TYPES", None)
            failed = subprocess.run(["bash", str(scripts / "clone-grammar.sh")],
                                    env=dict(env, MOCK_BAD_ARCHIVE="1"), text=True, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(mock_log.read_text().splitlines(), ["patch"])
            self.assertFalse((grammar / "node_modules/tree-sitter-cli/tree-sitter").exists())
            mock_log.unlink()
            for _ in range(2):
                result = subprocess.run(["bash", str(scripts / "clone-grammar.sh")], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(cargo.read_text(), expected)
                self.assertEqual(cargo.stat().st_mode & 0o777, 0o644)
                self.assertEqual(list(grammar.glob(".Cargo.toml.*")), [])
            self.assertEqual(mock_log.read_text().splitlines(),
                             ["patch", "npm ci --ignore-scripts", "npm run build", "cli", "npm test"] * 2)

            # Ensure the shim rejects the former GNU-only invocation on all hosts.
            cargo.write_text(original)
            result = subprocess.run(["sed", "-i", 's/tree-sitter = "0.27.1"/tree-sitter = "=0.26.8"/', str(cargo)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertEqual(cargo.read_text(), original)


if __name__ == "__main__":
    unittest.main()
