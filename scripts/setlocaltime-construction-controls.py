#!/usr/bin/env python3
"""Execute real setLocaltime shape controls in an exclusive, temporary database."""
import collections
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / 'extractor-pack'
QUERY = ROOT / 'ql/src/extractor-smoke/SetLocaltimeConstructionInventory.ql'
PUBLIC = ROOT / 'ql/src/m4/SetLocaltimeConstructionTable.ql'
FIXTURE = ROOT / 'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci'
ORACLE = ROOT / 'ql/test/setlocaltime-construction-real-oracle.csv'
HASH = '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e'


def run(*argv, stdout=None):
    subprocess.run(argv, check=True, cwd=ROOT, stdout=stdout)


def decode(db, query, name, search, additional=None):
    output = db / (name + '.bqrs')
    command = ['codeql', 'query', 'run', str(query), '--database=' + str(db),
               '--search-path=' + search, '--output=' + str(output), '--ram=2048', '--threads=2']
    if additional:
        command.append('--additional-packs=' + additional)
    run(*command)
    text = subprocess.check_output(['codeql', 'bqrs', 'decode', '--format=csv', str(output)])
    (db / (name + '.csv')).write_bytes(text)
    return list(csv.DictReader(text.decode('utf-8').splitlines(), strict=True))


def row_counter(data):
    return collections.Counter(tuple(sorted(row.items())) for row in data)


def check_inventory(rows, expected):
    if row_counter(rows) != row_counter(expected):
        raise ValueError(f'inventory mismatch: missing={row_counter(expected)-row_counter(rows)} unexpected={row_counter(rows)-row_counter(expected)}')


def cases(source):
    controls = {'positive': source,
                'minimal': (ROOT / 'ql/test/setlocaltime-construction-controls/minimal.uc').read_text(encoding='utf-8'),
                'comment-whitespace': source.replace('let t = localtime(request.args.localtime);',
                    'let t = localtime(request.args.localtime); /* comment */'),
                'reflection-conditional': source + "\nglobal['sprintf'] = function(fmt) { return 'X'; };\n"}
    def replace_once(name, old, new):
        if source.count(old) != 1:
            raise ValueError(f'{name}: anchor is not unique: {old}')
        controls[name] = source.replace(old, new, 1)
    literal = 'date -s "%04d-%02d-%02d %02d:%02d:%02d" >/dev/null'
    for index in range(6):
        start = [i for i, c in enumerate(literal) if c == '%'][index]
        end = literal.index('d', start) + 1
        replacement = literal[:start] + '%s' + literal[end:]
        replace_once('conversion-' + str(index + 1), literal, replacement)
    replace_once('wrong-field-order', 't.year, t.mon, t.mday', 't.mon, t.year, t.mday')
    replace_once('wrong-receiver', 't.year, t.mon, t.mday', 'u.year, t.mon, t.mday')
    replace_once('computed-field', 't.year, t.mon, t.mday', "t['year'], t.mon, t.mday")
    replace_once('rebound', 'let t = localtime(request.args.localtime);',
                 'let t = localtime(request.args.localtime); t = {};')
    replace_once('t-update', 'let t = localtime(request.args.localtime);',
                 'let t = localtime(request.args.localtime); t++;')
    replace_once('t-field-write', 'let t = localtime(request.args.localtime);',
                 'let t = localtime(request.args.localtime); t.year = 0;')
    replace_once('t-shorthand', 'let t = localtime(request.args.localtime);',
                 'let t = localtime(request.args.localtime); let x = { t };')
    replace_once('t-alias', 'let t = localtime(request.args.localtime);',
                 'let t = localtime(request.args.localtime); let x = t;')
    replace_once('wrapped-field', 't.year, t.mon, t.mday', '(t.year), t.mon, t.mday')
    replace_once('raw-prefix', 'system(sprintf(', "system('x' + sprintf(")
    replace_once('extra-format-argument', 't.min, t.sec));', 't.min, t.sec, 0));')
    replace_once('missing-format-argument', 't.min, t.sec));', 't.min));')
    replace_once('wrapped-formatter', 'system(sprintf(', 'system((sprintf(')
    # Balance the extra wrapper introduced in the previous case.
    controls['wrapped-formatter'] = controls['wrapped-formatter'].replace('t.min, t.sec));', 't.min, t.sec)));', 1)
    replace_once('optional-formatter', 'system(sprintf(', 'system(sprintf?.(')
    replace_once('member-formatter', 'system(sprintf(', 'system(util.sprintf(')
    replace_once('dynamic-format', "sprintf('" + literal + "'", "sprintf(formatValue")
    replace_once('raw-suffix', 't.min, t.sec));', "t.min, t.sec) + 'x');")
    replace_once('wrong-shell', literal, literal.replace('>/dev/null', '>/dev/zero'))
    replace_once('format-escape', literal, literal.replace('date -s', r'date\x20-s'))
    replace_once('format-escape-suffix', literal, literal + r'\x20')
    replace_once('args-localtime-nonzero', 'localtime: 0', 'localtime: 1')
    replace_once('malformed', 'return { luci: methods };', 'return { luci: methods };\nconst broken = ;')
    replace_once('duplicate-method', 'setLocaltime: {', 'setLocaltime: { call: function() {} },\n\tsetLocaltime: {')
    replace_once('wrong-return', 'return { luci: methods };', 'return { luci: {} };')
    for name in ('system', 'sprintf', 'localtime'):
        variants = {
            'formal': f'function competitor({name}) {{ return 0; }}',
            'rest': f'function competitor(...{name}) {{ return 0; }}',
            'named-expression': f'let competitor = function {name}() {{ return 0; }};',
            'arrow': f'let competitor = ({name}) => 0;',
            'local': f'function competitor() {{ let {name} = 0; }}',
            'function': f'function {name}() {{ return 0; }}',
            'assignment': f'{name} = 0;',
            'update': f'{name}++;',
            'alias': f'let alias = {name};',
            'shorthand': f'let alias = {{ {name} }};',
            'catch': f'try {{ 0; }} catch ({name}) {{ 0; }}',
            'loop': f'for (let {name} in {{}}) {{ 0; }}',
            'import-default': f"import {name} from 'fake';",
            'import-named': f"import {{ {name} }} from 'fake';",
            'import-alias': f"import {{ other as {name} }} from 'fake';",
            'import-namespace': f"import * as {name} from 'fake';",
        }
        for kind, suffix in variants.items():
            controls[name + '-' + kind] = source + '\n' + suffix + '\n'
    return controls


def main():
    original = FIXTURE.read_bytes()
    if hashlib.sha256(original).hexdigest() != HASH:
        raise SystemExit('pinned source mismatch')
    sources = cases(original.decode('utf-8'))
    positive = {'positive', 'comment-whitespace', 'reflection-conditional'}
    with tempfile.TemporaryDirectory(prefix='setlocaltime-controls-') as tmp:
        base = Path(tmp).resolve()
        src = base / 'source'
        paths = {}
        for name, text in sources.items():
            p = src / 'modules' / name / 'root/usr/share/rpcd/ucode/luci'
            p.parent.mkdir(parents=True)
            p.write_text(text, encoding='utf-8')
            paths[name] = p
        db = base / 'db'
        search = f'{PACK}:{ROOT}/ql/lib:{ROOT}/ql/src'
        run('codeql', 'database', 'init', str(db), '--language=ucode', '--search-path=' + str(PACK), '--source-root=' + str(src))
        run('codeql', 'database', 'index-files', '--language=ucode', '--include=**/rpcd/ucode/luci', '--working-dir=' + str(src), str(db))
        shutil.copy2(db / 'trap/ucode/routing.json', base / 'routing.json')
        routing = json.loads((db / 'trap/ucode/routing.json').read_text())
        decisions = routing['decisions']
        if len(decisions) != len(paths) or {d['path'] for d in decisions} != set(map(str, paths.values())) or any(d['classification'] != 'plain' or d['installed_path'] != 'usr/share/rpcd/ucode/luci' for d in decisions):
            raise SystemExit('routing did not identify all controls')
        run('codeql', 'database', 'finalize', str(db))
        extracted = decode(db, ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', 'extracted', search)
        errors = decode(db, ROOT / 'ql/src/diagnostics/ExtractionErrors.ql', 'errors', search)
        expected_extracted = {str(p) for n, p in paths.items() if n != 'malformed'}
        if {r['f'] for r in extracted} != expected_extracted or len(extracted) != len(expected_extracted):
            raise SystemExit(f'unexpected successfully-extracted identities: {extracted!r}')
        if len(errors) != 1 or str(paths['malformed']) not in str(errors):
            raise SystemExit(f'unexpected extraction errors: {errors!r}')
        rows = decode(db, QUERY, 'inventory', search)
        with ORACLE.open(newline='', encoding='utf-8') as f:
            expected_base = list(csv.DictReader(f))
        expected = []
        for name in sorted(positive):
            relative = paths[name].relative_to(src).as_posix()
            for row in expected_base:
                expected.append(dict(row, source_path=relative))
        # Reviewed directly against minimal.uc, independent of the query output.
        minimal_common = {
            'source_path': paths['minimal'].relative_to(src).as_posix(),
            'callback_start_line': '4', 'callback_start_column': '11',
            'callback_end_line': '11', 'callback_end_column': '5',
            'initializer_start_line': '5', 'initializer_start_column': '15',
            'initializer_end_line': '5', 'initializer_end_column': '47',
            'input_start_line': '5', 'input_start_column': '25',
            'input_end_line': '5', 'input_end_column': '46',
            'guard_start_line': '6', 'guard_start_column': '11',
            'guard_end_line': '6', 'guard_end_column': '11',
            'formatter_start_line': '7', 'formatter_start_column': '16',
            'formatter_end_line': '7', 'formatter_end_column': '121',
            'format_start_line': '7', 'format_start_column': '24',
            'format_end_line': '7', 'format_end_column': '75',
            'sink_start_line': '7', 'sink_start_column': '9',
            'sink_end_line': '7', 'sink_end_column': '122',
            'field_start_line': '7', 'field_end_line': '7',
        }
        for row, (start, end) in zip(expected_base, [(78, 83), (86, 90), (93, 98), (101, 106), (109, 113), (116, 120)]):
            expected.append(dict(row, **minimal_common, field_start_column=str(start), field_end_column=str(end)))
        check_inventory(rows, expected)
        evidence_env = os.environ.get('M4_SETLOCALTIME_EVIDENCE_DIR')
        evidence = Path(evidence_env).resolve() / 'controls' if evidence_env else None
        if evidence:
            evidence.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base / 'routing.json', evidence / 'routing.json')
            for name in ('extracted', 'errors', 'inventory'):
                for ext in ('csv', 'bqrs'):
                    shutil.copy2(db / f'{name}.{ext}', evidence / f'{name}.{ext}')
            (evidence / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
            for name in ('format-escape-suffix', 'args-localtime-nonzero'):
                shutil.copy2(paths[name], evidence / (name + '.uc'))
        public = decode(db, PUBLIC, 'public-wrong-path', search)
        if public:
            raise SystemExit(f'public query accepted wrong relative paths: {public!r}')
        # Isolate actual query mutations. The designated previously rejected case
        # must produce all six rows; a test that only counts failures is not enough.
        mutants = {
            'diagnostics': ('not exists(ExtractionError error | error.getLocation().getFile() = p.getLocation().getFile()) and', '1 = 1 and', 'malformed'),
            'format': ('plainString(format, "date -s \\\"%04d-%02d-%02d %02d:%02d:%02d\\\" >/dev/null")', 'exists(format.getChild(0))', 'conversion-1'),
            'order': ('field.getProperty().getValue() = n', '1 = 1', 'wrong-field-order'),
            'sprintf-binding': ('allowedCalleeName(p, "sprintf") and ', '', 'sprintf-formal'),
            'format-extra-child': ('not exists(s.getChild(1))', '1 = 1', 'format-escape-suffix'),
            'args-value': ('arg.getValue().(UCODE::Number).getValue() = "0"', 'exists(arg.getValue())', 'args-localtime-nonzero'),
        }
        for kind, (old, new, designated) in mutants.items():
            copied = base / ('mutant-' + kind)
            (copied / 'ql').mkdir(parents=True)
            shutil.copy2(ROOT / '.codeqlmanifest.json', copied)
            shutil.copytree(ROOT / 'ql/lib', copied / 'ql/lib')
            shutil.copytree(ROOT / 'ql/src', copied / 'ql/src')
            helper = copied / 'ql/lib/codeql/ucode/m4/SetLocaltimeConstruction.qll'
            text = helper.read_text(encoding='utf-8')
            if text.count(old) != 1:
                raise SystemExit(f'{kind}: mutant anchor mismatch')
            helper.write_text(text.replace(old, new, 1), encoding='utf-8')
            pack_roots = f'{copied}/ql/lib:{copied}/ql/src'
            mutated = decode(db, copied / 'ql/src/extractor-smoke/SetLocaltimeConstructionInventory.ql',
                             'mutant-' + kind, str(PACK), pack_roots)
            if evidence:
                shutil.copy2(helper, evidence / ('mutant-' + kind + '.qll'))
                for ext in ('csv', 'bqrs'):
                    shutil.copy2(db / f'mutant-{kind}.{ext}', evidence / f'mutant-{kind}.{ext}')
            target = paths[designated].relative_to(src).as_posix()
            hits = [r for r in mutated if r['source_path'] == target]
            if len(hits) != 6 or {r['slot_index'] for r in hits} != set('123456'):
                raise SystemExit(f'{kind}: mutant failed to expose designated {designated}: {hits!r}')
            if any(r['source_path'] == target for r in rows):
                raise SystemExit(f'{kind}: control was not negative in original output')
            if kind in ('format-extra-child', 'args-value'):
                try:
                    check_inventory(mutated, expected)
                except ValueError:
                    pass
                else:
                    raise SystemExit(f'{kind}: unchanged full inventory oracle accepted mutant')
                if row_counter(mutated) - row_counter(rows) != row_counter(hits) or row_counter(rows) - row_counter(mutated):
                    raise SystemExit(f'{kind}: mutation changed rows beyond the six designated rows')
                print(f'PASS: unchanged full inventory oracle rejected {kind}; only six designated rows added', flush=True)
            print(f'PASS: real-query {kind} mutant exposes {designated}', flush=True)
        print(f'PASS: {len(paths)} routed controls; {len(extracted)} extracted; one malformed error; {len(rows)} exact rows from {len(positive) + 1} conditional positives; public path filter rejected all')


if __name__ == '__main__':
    main()
