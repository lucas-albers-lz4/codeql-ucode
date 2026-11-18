"""Exercise standalone measured-set smoke wiring with a synthetic CLI adapter.

The adapter supplies synthetic diagnostic and semantic rows; real extraction
controls are separate from this fast regression.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKES = {'arrow-cfgscope': ('ArrowCfgScope', 'arrow.csv'),
          'call-get-argument': ('CallGetArgument', 'args.csv'),
          'call-get-identifier': ('CallGetIdentifier', 'idents.csv'),
          'formal-variables': ('FormalVariables', 'formals.csv'),
          'get-a-call': ('GetACall', 'calls.csv'),
          'identity-arrow': ('IdentityArrow', 'identity.csv'),
          'jump-local': ('JumpLocal', 'jump-local.csv'),
          'parameter-node': ('ParameterNode', 'params.csv'),
          'parameter-position': ('ParameterPosition', 'pos.csv'),
          'return-out': ('ReturnOut', 'return-out.csv'),
          'simple-call-jump': ('SimpleCallJump', 'jump.csv'),
          'content-encoding': ('ContentEncoding', 'content.csv'),
          'encode-content': ('EncodeContent', 'encode.csv'),
          'cfg': ('CfgEdges', 'cfg.csv'),
          'viable-source-callable': ('ViableSourceCallable', 'viable.csv'),
          'quote': ('CompleteQuotedArg', 'quoted.csv')}

SELECTIONS = {
    # Measured diagnostic identities, not derived from includes or globbing.
    'quote': (
        'quote_bad_ash_c.uc',
        'quote_bad_assignment.uc',
        'quote_bad_bash_c.uc',
        'quote_bad_conditional.uc',
        'quote_bad_echo',
        'quote_bad_import.uc',
        'quote_bad_local.uc',
        'quote_bad_parameter.uc',
        'quote_bad_pipe.uc',
        'quote_bad_prefix_join.uc',
        'quote_bad_separator.uc',
        'quote_bad_separator_space.uc',
        'quote_bad_sh_c',
        'quote_bad_sh_c_suffix.uc',
        'quote_bad_shell_flags.uc',
        'quote_bad_shell_path.uc',
        'quote_bad_shell_wrapper.uc',
        'quote_bad_suffix',
        'quote_bad_suffix_join.uc',
        'quote_bad_trailing_substitution.uc',
        'quote_bad_transform.uc',
        'quote_bad_unknown_command.uc',
        'quote_bad_variable.uc',
        'quote_exe',
        'quote_ok',
        'quote_ok_echo.uc',
        'quote_ok_printf.uc',
        'taint_neg',
        'taint_pos',
        'usr/share/rpcd/ucode/luci',
        'usr/share/ucode/luci/sys.uc',
    ),
    'content-encoding': ('usr/share/rpcd/ucode/luci', 'ssa_neg'),
    'encode-content': ('usr/share/rpcd/ucode/luci', 'ssa_neg'),
    'cfg': ('cfg_pos', 'cfg_neg'),
    'viable-source-callable': ('usr/share/rpcd/ucode/luci', 'ssa_pos', 'usr/share/ucode/luci/sys.uc'),
}
QUERY_DIRS = {'quote': 'ql/src/m4'}
DEFAULT_QUERY_DIR = 'ql/src/extractor-smoke'

INCLUDES = {
    'quote': ('**/luci', '**/taint_pos', '**/taint_neg', '**/quote_*'),
    'content-encoding': ('**/rpcd/ucode/luci', '**/ssa_neg'),
    'encode-content': ('**/rpcd/ucode/luci', '**/ssa_neg'),
    'cfg': ('**/cfg_pos', '**/cfg_neg'),
    'viable-source-callable': ('**/rpcd/ucode/luci', '**/ssa_pos', '**/sys.uc'),
}

# Minimal synthetic rows satisfying each standalone smoke's semantic assertions.
# They exercise gate wiring only; they are not extraction evidence.
MESSAGES = {
    'content-encoding': ['Field[args] in luci', 'Field[field] in ssa_neg', 'Element in luci'],
    'encode-content': ['Field[args] in luci', 'Field[field] in ssa_neg', 'Element in luci'],
    'viable-source-callable': ['shellquote in luci', 'callPackageVersionCheck in luci',
        'formal_order in ssa_pos', 'member_order in ssa_pos', 'library system in ssa_pos',
        'library system in luci', 'library system in sys.uc', 'library popen in luci',
        'library popen in sys.uc', 'library basename in luci', 'library basename in sys.uc',
        'library access in luci', 'library open in luci', 'library open in sys.uc',
        'library readfile in luci', 'library readfile in sys.uc'],
    'call-get-identifier': ['system in ssa_pos', 'popen in luci', 'shellquote in luci'],
    'formal-variables': ['param in ssa_pos', 'request in ssa_pos', 's in luci', 'b in ssa_pos'],
    'get-a-call': ['system in ssa_pos', 'popen in luci', 'shellquote in luci'],
    'identity-arrow': ['identity-access identx in ssa_pos', 'identity-local 0:identx in ssa_pos'],
    'jump-local': ['jump-local 0:s from shellquote in luci',
                   'jump-local 0:pkg from callPackageVersionCheck in luci',
                   'jump-local 1:b from formal_order in ssa_pos',
                   'jump-local 1:b from member_order in ssa_pos',
                   'param-local 0:request in ssa_pos', 'param-local 0:param in ssa_pos'],
    'parameter-node': ['param 0:param in ssa_pos', 'param 0:request in ssa_pos',
                       'param 1:b in ssa_pos', 'param 0:arrowx in ssa_pos',
                       'param 0:arrowa in ssa_pos', 'param 1:arrowb in ssa_pos',
                       'param 0:arrowxs in ssa_pos', 'param 0:s in luci',
                       'param 0:i in luci', 'param 1:n in luci', 'param 0:port in luci',
                       'arg-param 0 in ssa_pos', 'arg-param 0 in luci'],
    'parameter-position': ['0:param in ssa_pos', '0:s in luci', '1:n in luci'],
    'return-out': ['out shellquote in luci', 'out callPackageVersionCheck in luci',
                   'out formal_order in ssa_pos', 'out member_order in ssa_pos',
                   'jump-out shellquote in luci', 'jump-out callPackageVersionCheck in luci',
                   'jump-out formal_order in ssa_pos', 'jump-out member_order in ssa_pos'],
    'simple-call-jump': ['jump-param 0:s from shellquote in luci',
                         'jump-param 0:pkg from callPackageVersionCheck in luci',
                         'jump-param 0:a from formal_order in ssa_pos',
                         'jump-param 1:b from formal_order in ssa_pos',
                         'jump-param 0:a from member_order in ssa_pos',
                         'jump-param 1:b from member_order in ssa_pos'],
}

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
root = Path(os.environ['PAIR_ROOT'])
smoke = os.environ['PAIR_SMOKE']
semantic_query = os.environ['PAIR_QUERY']
extra_queries = [root / p for p in json.loads(os.environ['PAIR_EXTRA_QUERIES'])]
includes = json.loads(os.environ['PAIR_INCLUDES'])
expected_db = root / '.codeql-database' / ('m4-' + smoke)
source = root / 'ql/test/extractor-smoke'
def reject(s): sys.exit('fake codeql rejected: ' + s)
log_path = os.environ.get('PAIR_COMMAND_LOG')
if log_path:
    with open(log_path, 'a') as stream: stream.write(' '.join(a) + '\n')
def opt(key):
    values = [x[len(key):] for x in a if x.startswith(key)]
    if len(values) != 1: reject('missing or duplicate ' + key)
    return values[0]
if a[:2] == ['query', 'compile']:
    if len(a) != 4 or a[3] != '--search-path=' + ':'.join(str(root / p) for p in ('extractor-pack', 'ql/lib', 'ql/src')):
        reject('compile options')
    if Path(a[2]) not in [root / os.environ['PAIR_QUERY_DIR'] / (semantic_query + '.ql'),
                          root / 'ql/src/m3/LocalTaint.ql', root / 'ql/src/m4/RequestArgsExec.ql'] + extra_queries:
        reject('compile query')
elif a[:2] == ['database', 'init']:
    if a[2:] != [str(expected_db), '--language=ucode', '--search-path=' + str(root / 'extractor-pack'), '--source-root=' + str(source)]: reject('database init')
    expected_db.mkdir(parents=True)
elif a[:2] == ['database', 'index-files']:
    if a[2:] != ['--language=ucode'] + ['--include=' + item for item in includes] + ['--working-dir=' + str(source), str(expected_db)]: reject('database index selection')
elif a[:2] == ['database', 'finalize']:
    if a[2:] != [str(expected_db)]: reject('database finalize')
elif a[:2] == ['query', 'run']:
    if len(a) != 6 or sorted(x.split('=', 1)[0] for x in a[3:]) != ['--database', '--output', '--search-path']:
        reject('query run options')
    query = Path(a[2])
    semantic_path = root / os.environ['PAIR_QUERY_DIR'] / (semantic_query + '.ql')
    if query not in [root / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', root / 'ql/src/diagnostics/ExtractionErrors.ql', semantic_path] + extra_queries:
        reject('query path')
    db = Path(opt('--database='))
    if db != expected_db or not db.is_dir() or Path(opt('--output=')).parent != db: reject('database or output')
    if opt('--search-path=') != ':'.join(str(root / p) for p in ('extractor-pack', 'ql/lib', 'ql/src')): reject('search path')
    Path(opt('--output=')).write_text(query.stem)
elif a[:2] == ['bqrs', 'decode']:
    name = Path(a[-1]).read_text()
    if name in ('SuccessfullyExtractedFiles', 'ExtractionErrors'):
        if a[2:-1] != ['--format=json', '--entities=url,string']: reject('diagnostic decode flags')
        print(json.dumps(json.loads(Path(os.environ['PAIR_DIAGNOSTICS']).read_text())[name]))
    elif smoke == 'quote' and name in ('CompleteQuotedArg', 'ShellquoteTemplateShape', 'ShellInjection'):
        if a[2:-1] != ['--format=csv']: reject('semantic decode flags')
        import csv
        w = csv.writer(sys.stdout, lineterminator='\n')
        w.writerow(['entity', 'message', 'extra', 'sink', 'method', 'sinkline', 'srcline'])
        fixtures = json.loads(os.environ['PAIR_SELECTION'])
        if name == 'ShellquoteTemplateShape':
            for p in fixtures:
                if p.startswith('quote_ok'): w.writerow(['node', 'supported template shape in ' + p])
        elif name == 'ShellInjection':
            for p in fixtures:
                if p.startswith('quote_bad_') or p.startswith('quote_ok') or p == 'taint_pos':
                    w.writerow(['node', 'shell-injection candidate via system in ' + p])
            w.writerow(['node', 'shell-injection candidate via system in quote_exe (quoted executable selection)'])
            for method, sink, sinkline, srcline in [('getSwconfigFeatures', 'popen', 343, 343), ('getSwconfigPortState', 'popen', 400, 400), ('getRealtimeStats', 'popen', 585, 575), ('getRealtimeStats', 'popen', 585, 577), ('setPassword', 'system', 474, 470), ('setPassword', 'system', 474, 471), ('setLocaltime', 'system', 111, 108)]:
                w.writerow(['node', 'shell-injection candidate via ' + sink + ' in luci', '', sink, method, sinkline, srcline])
    elif name == semantic_query or name in ('LocalFlowStep', 'SsaReachesSystem') and smoke == 'viable-source-callable':
        if a[2:-1] != ['--format=csv']: reject('semantic decode flags')
        messages = {'ArrowCfgScope': ['arrowx in ssa_pos', 'arrowa in ssa_pos', 'arrowb in ssa_pos', 'arrowxs in ssa_pos', 'i in luci', 'n in luci', 'port in luci'], 'CallGetArgument': ['0:ssa_pos_src in ssa_pos', '0:pkg in luci', '1:r in luci']}.get(name, json.loads(os.environ['PAIR_MESSAGES']))
        messages = {'LocalFlowStep': ['ssa_pos_src -> ssa_pos_src in ssa_pos'], 'SsaReachesSystem': ['ssa_pos_src reaches system in ssa_pos']}.get(name, messages)
        print('"entity","message"')
        for message in messages: print('"node","' + message + '"')
    else: reject('unknown decode')
else: reject(repr(a))
'''


def receipt(path):
    return [{'label': str(path), 'url': {'uri': path.as_uri(), 'startLine': 0,
            'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']


class LuciSsaPairDiagnostics(unittest.TestCase):
    def run_smoke(self, name, fault, mutant=None):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            root = temp / 'checkout'
            shutil.copytree(ROOT / 'scripts', root / 'scripts')
            shutil.copytree(ROOT / 'ql', root / 'ql')
            if mutant in ('errors', 'identity'):
                verifier = root / 'scripts/m4-smoke-diagnostics.py'
                text = verifier.read_text()
                old = ('if errors:' if mutant == 'errors' else
                       'if Counter(map(encode, success)) != Counter(map(encode, wanted)):')
                self.assertEqual(text.count(old), 1)
                verifier.write_text(text.replace(old, old.replace('if ', 'if False and ', 1)))
            elif mutant == 'wiring':
                script = root / f'scripts/m4-{name}-smoke.sh'
                text = script.read_text()
                lines = text.splitlines(keepends=True)
                self.assertEqual(sum(line.startswith('check_m4_extraction ') for line in lines), 1)
                script.write_text(''.join(line for line in lines if not line.startswith('check_m4_extraction ')))
            elif mutant == 'late':
                script = root / f'scripts/m4-{name}-smoke.sh'
                lines = script.read_text().splitlines(keepends=True)
                check = [line for line in lines if line.startswith('check_m4_extraction ')]
                source = [line for line in lines if line.startswith('source "$ROOT/scripts/m4-smoke-diagnostics.sh"')]
                self.assertEqual(len(check), 1)
                self.assertEqual(len(source), 1)
                rest = [line for line in lines if line not in check + source]
                index = next(i for i, line in enumerate(rest) if 'query run' in line)
                script.write_text(''.join(rest[:index + 1] + source + check + rest[index + 1:]))
            elif mutant == 'bad-compile':
                script = root / f'scripts/m4-{name}-smoke.sh'
                text = script.read_text()
                old = 'codeql query compile "$Q"'
                self.assertEqual(text.count(old), 1)
                script.write_text(text.replace(old, 'codeql query compile "$ROOT/ql/src/extractor-smoke/Bogus.ql"'))
            elif mutant in ('wrong-query', 'wrong-flags', 'bad-option'):
                helper = root / 'scripts/m4-smoke-diagnostics.sh'
                text = helper.read_text()
                edits = {'wrong-query': ('ql/src/diagnostics/', 'ql/src/extractor-smoke/'),
                         'wrong-flags': ('--entities=url,string', '--entities=string'),
                         'bad-option': ('--output="$DB/$diagnostic.bqrs"', '--output="$DB/$diagnostic.bqrs" --bogus-pair')}
                old, new = edits[mutant]
                self.assertEqual(text.count(old), 1)
                helper.write_text(text.replace(old, new))
            extractor = root / 'extractor-pack/tools/linux64/extractor'
            extractor.parent.mkdir(parents=True)
            extractor.touch(mode=0o755)
            binary = temp / 'bin'
            binary.mkdir()
            (binary / 'codeql').write_text(FAKE)
            (binary / 'codeql').chmod(0o755)
            src = root / 'ql/test/extractor-smoke'
            files = [src / p for p in SELECTIONS.get(name, ('usr/share/rpcd/ucode/luci', 'ssa_pos'))]
            successes = list(map(receipt, files))
            errors = []
            if fault == 'error_only':
                errors = [[{'label': 'synthetic parse error'}, 'parse error', 2]]
            elif fault.startswith('omit'):
                successes.pop(int(fault.removeprefix('omit')))
            elif fault.startswith('duplicate'):
                successes.append(successes[int(fault.removeprefix('duplicate'))])
            elif fault.startswith('substitute'):
                substitute = src / ('cfg_pos' if name == 'quote' else 'taint_neg')
                self.assertTrue(substitute.is_file(), 'substitution fixture must exist')
                self.assertNotIn(substitute, files)
                successes[int(fault.removeprefix('substitute'))] = receipt(substitute)
            elif fault == 'bad_schema':
                successes = None
            data = {'SuccessfullyExtractedFiles': {'#select': {'columns': [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}], 'tuples': successes}},
                    'ExtractionErrors': {'#select': {'columns': [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}], 'tuples': errors}}}
            diag = temp / 'diagnostics.json'
            diag.write_text(json.dumps(data))
            messages = MESSAGES.get(name, [])
            if name == 'cfg':
                def line(fixture, marker):
                    return next(i for i, text in enumerate((src / fixture).read_text().splitlines(), 1) if marker in text)
                messages = []
                for fixture, before, after, scope in [('cfg_pos', '"cfg_pos_one"', '"cfg_pos_two"', 10), ('cfg_neg', '"cfg_neg_a"', '"cfg_neg_a_two"', 20), ('cfg_neg', '"cfg_neg_b"', '"cfg_neg_b_two"', 30)]:
                    messages.append(f'{fixture}:{line(fixture, before)} -> {fixture}:{line(fixture, after)} scopeEq=1 scopeLine={scope} kind=ast type=statement')
                n = line('cfg_pos', 'cfg_pos_return')
                messages.append(f'cfg_pos:{n} -> cfg_pos:{n} scopeEq=1 scopeLine=10 kind=exit type=return')
            env = os.environ.copy()
            commands = temp / 'commands.log'
            env.update(PATH=str(binary) + os.pathsep + env['PATH'], CODEQL_UCODE_SMOKE_PACKS_READY=str(root),
                       PAIR_ROOT=str(root), PAIR_SMOKE=name, PAIR_DIAGNOSTICS=str(diag),
                       PAIR_QUERY=SMOKES[name][0], PAIR_QUERY_DIR=QUERY_DIRS.get(name, DEFAULT_QUERY_DIR),
                       PAIR_MESSAGES=json.dumps(messages),
                       PAIR_INCLUDES=json.dumps(INCLUDES.get(name, ('**/rpcd/ucode/luci', '**/ssa_pos'))),
                       PAIR_EXTRA_QUERIES=json.dumps(['ql/src/extractor-smoke/LocalFlowStep.ql', 'ql/src/m4/SsaReachesSystem.ql'] if name == 'viable-source-callable' else ['ql/src/m4/CompleteQuotedArg.ql', 'ql/src/m4/ShellquoteTemplateShape.ql', 'ql/src/m4/ShellInjection.ql'] if name == 'quote' else []),
                       PAIR_SELECTION=json.dumps(SELECTIONS.get(name, ())),
                       PAIR_COMMAND_LOG=str(commands), PYTHONDONTWRITEBYTECODE='1',
                       PYTHONOPTIMIZE=str(sys.flags.optimize))
            result = subprocess.run(['bash', str(root / f'scripts/m4-{name}-smoke.sh')], cwd=root,
                                    env=env, text=True, capture_output=True)
            self.commands = commands.read_text() if commands.exists() else ''
            return result

    def semantic_executed(self, name):
        queries = [f"{SMOKES[name][0]}.ql"]
        if name == 'viable-source-callable':
            queries += ['LocalFlowStep.ql', 'SsaReachesSystem.ql']
        if name == 'quote':
            queries += ['ShellquoteTemplateShape.ql', 'ShellInjection.ql']
        return any(line.startswith('query run ') and any(query in line for query in queries)
                   for line in self.commands.splitlines())

    def test_pristine_diagnostics_accepted(self):
        for name in SMOKES:
            with self.subTest(smoke=name):
                result = self.run_smoke(name, 'valid')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('M4 extraction accepted', result.stdout)
                self.assertIn('smoke passed', result.stdout)

    def test_identity_guard_and_schema_independent_of_errors(self):
        for name in SMOKES:
            for fault in tuple(f'{kind}{i}' for i in range(len(SELECTIONS.get(name, (0, 1))))
                               for kind in ('omit', 'duplicate', 'substitute')) + ('bad_schema',):
                with self.subTest(smoke=name, fault=fault):
                    result = self.run_smoke(name, fault)
                    self.assertNotIn('fake codeql rejected', result.stderr)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('invalid diagnostic tuples' if fault == 'bad_schema' else
                                  'expected exact successful-file multiset', result.stderr)
                    self.assertNotIn('expected zero extraction errors', result.stderr)
                    self.assertTrue(self.commands, 'no commands were recorded')
                    self.assertFalse(self.semantic_executed(name),
                                     'semantic query ran before identity rejection')

    def test_individual_guard_and_wiring_mutants_false_green(self):
        for name in SMOKES:
            for mutant, fault in (('errors', 'error_only'), ('wiring', 'error_only')) + tuple(
                    ('identity', f'omit{i}') for i in range(len(SELECTIONS.get(name, (0, 1))))):
                with self.subTest(smoke=name, mutant=mutant, fault=fault):
                    result = self.run_smoke(name, fault, mutant)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('smoke passed', result.stdout)

    def test_adapter_rejects_corrupted_helper_cli_contract(self):
        for name in SMOKES:
            for mutant in ('wrong-query', 'wrong-flags', 'bad-option'):
                with self.subTest(smoke=name, mutant=mutant):
                    result = self.run_smoke(name, 'valid', mutant)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('fake codeql rejected', result.stderr)

    def test_error_guard_is_independent_of_success_receipts(self):
        for name in SMOKES:
            with self.subTest(smoke=name):
                result = self.run_smoke(name, 'error_only')
                self.assertNotIn('fake codeql rejected', result.stderr)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('expected zero extraction errors', result.stderr)
                self.assertNotIn('expected exact successful-file multiset', result.stderr)

    def test_rejection_precedes_every_semantic_query(self):
        for name in SMOKES:
            for fault in ('error_only', 'omit0'):
                with self.subTest(smoke=name, fault=fault):
                    result = self.run_smoke(name, fault)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertTrue(self.commands, 'no commands were recorded')
                    self.assertFalse(self.semantic_executed(name),
                                     'semantic query ran before the extraction guard rejected')

    def test_gate_after_semantics_mutation_is_detected(self):
        for name in SMOKES:
            with self.subTest(smoke=name):
                result = self.run_smoke(name, 'error_only', 'late')
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertTrue(self.semantic_executed(name),
                                'late-gate mutation did not run the semantic query')

    def test_adapter_rejects_corrupted_compile_operand(self):
        # quote does not invoke query compile; the adapter still validates it.
        for name in (name for name in SMOKES if name != 'quote'):
            with self.subTest(smoke=name):
                result = self.run_smoke(name, 'valid', 'bad-compile')
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('fake codeql rejected', result.stderr)
                self.assertNotIn('expected exact successful-file multiset', result.stderr)


if __name__ == '__main__':
    unittest.main()
