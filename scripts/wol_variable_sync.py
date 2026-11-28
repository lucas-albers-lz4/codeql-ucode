"""Keep the WOL-scoped binding model synchronized with the shared model."""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / 'ql/lib/codeql/ucode/ast/Variables.qll'
SCOPED = ROOT / 'ql/src/testing/WolScopedVariables.qll'
SEED = ROOT / 'ql/src/testing/WolCandidateSeed.qll'
SEED_SHA256 = 'c5e30339bee263719b69a81364ce8770dc299304c8a9b8019abacbfbc0a53cc9'
IMPORTS = (
    'private import codeql.Locations',
    'private import AstNodes',
    'private import internal.AstNodes',
    'private import internal.TreeSitter',
    'private import Cached',
)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('missing or ambiguous synchronization anchor: ' + old)
    return text.replace(old, new, 1)


def scoped_source(shared):
    imports = tuple(re.findall(r'(?m)^\s*(?:private\s+)?import\s+[^\n]+', shared))
    # An unrecognized relative import could resolve differently after relocation.
    if tuple(line.strip() for line in imports) != IMPORTS or len(re.findall(r'\bimport\b', shared)) != len(IMPORTS):
        raise ValueError('shared import list changed; review relocated imports')
    shared = replace_once(shared, 'private import AstNodes\n', 'private import codeql.ucode.ast.AstNodes\n')
    shared = replace_once(shared, 'private import internal.AstNodes\n', 'private import codeql.ucode.ast.internal.AstNodes\n')
    shared = replace_once(shared, 'private import internal.TreeSitter\n',
                          'private import codeql.ucode.ast.internal.TreeSitter\nprivate import testing.WolCandidateSeed as Seed\n')
    for start, end in (
        ('private predicate variableDecl(AstNode node, string name) {\n', '\n}\n\n/** Identifier token of a `FormalParameters`'),
        ('private predicate access(AstNode node, Variable v, string name) {\n', '\n}\n\nprivate predicate simpleWrite('),
    ):
        shared = replace_once(shared, start, start + '  Seed::candidateFile(node.getLocation().getFile()) and\n  (\n')
        shared = replace_once(shared, end, '\n  )' + end)
    return shared


def verify(shared, scoped, seed):
    if hashlib.sha256(seed).hexdigest() != SEED_SHA256:
        raise ValueError('WOL seed changed; review candidate domain')
    if scoped_source(shared) != scoped:
        raise ValueError('WOL scoped Variables drifted from shared Variables')


def verify_files():
    verify(SHARED.read_bytes().decode('utf-8'), SCOPED.read_bytes().decode('utf-8'), SEED.read_bytes())
