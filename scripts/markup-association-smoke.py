"""Test-only syntax association. No rendering or data-flow claim is made."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tests/data/markup-association'
PACK = ROOT / 'extractor-pack'
EXPECTED_FILES = {
    'clean.ut', 'mismatch.ut', 'competing.ut', 'nested.ut', 'write-same.ut',
    'write-other.ut', 'write-after.ut', 'intervening.ut', 'repeated.ut',
    'property.ut', 'malformed.ut', 'unsupported-target.ut', 'footstrap-header.ut',
    'export-lexical.ut', 'export-function.ut', 'import-alias-same.ut', 'import-alias-other.ut',
    'unbraced-if.ut', 'unbraced-else.ut', 'unbraced-while.ut', 'braced-shadow.ut', 'unbraced-other.ut',
    'augmented-same.ut', 'augmented-other.ut', 'update-same.ut', 'update-other.ut', 'delete-prefix.ut',
}


def run(*args):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE).stdout


def rows(db, q, out):
    run('codeql', 'query', 'run', q, f'--database={db}', f'--search-path={PACK}',
        f'--output={out}', '--threads=1', '--ram=2048')
    return json.loads(run('codeql', 'bqrs', 'decode', '--format=json',
                          '--entities=id,url,string', out))['#select']['tuples']


def loc(entity):
    u = entity['url']
    return (Path(u['uri']).name, u['startLine'], u['startColumn'], u['endLine'], u['endColumn'])


def main():
    if not __debug__:
        raise RuntimeError('This evidence check requires Python assertions; do not use -O')
    assert {p.name for p in SOURCE.glob('*.ut')} == EXPECTED_FILES
    assert hashlib.sha256((SOURCE / 'footstrap-header.ut').read_bytes()).hexdigest() == \
        '7653f8353e5bb1062b3f5a901e6b2488af5ed59b530f3c5721169f0e8fa32977'
    # Predeclared exact tag/read positions; all other files must have no association.
    sites = {'clean.ut': [(26, 29)], 'write-other.ut': [(41, 44)],
             'write-after.ut': [(26, 29)], 'repeated.ut': [(26, 29), (36, 39)],
             'footstrap-header.ut': [(54, 57)], 'import-alias-other.ut': [(61, 64)],
             'braced-shadow.ut': [(59, 62)], 'unbraced-other.ut': [(56, 59)],
             'augmented-other.ut': [(42, 45)], 'update-other.ut': [(39, 42)]}
    with tempfile.TemporaryDirectory(prefix='ucode-issue173-') as tmp:
        tmp = Path(tmp)
        db = tmp / 'db'
        run('codeql', 'database', 'init', db, '--language=ucode', f'--search-path={PACK}',
            f'--source-root={SOURCE}')
        run('codeql', 'database', 'index-files', db, '--language=ucode', '--include=**/*.ut',
            f'--working-dir={SOURCE}')
        routing = json.loads((db / 'trap/ucode/routing.json').read_text())
        assert routing['input_count'] == len(EXPECTED_FILES) and routing['markup_count'] == len(EXPECTED_FILES)
        assert {Path(r['path']).name for r in routing['decisions']} == EXPECTED_FILES
        assert all(r['status'] == 'inconclusive' and r['inconclusive_reason'] == 'markup_not_modeled'
                   for r in routing['decisions'])
        run('codeql', 'database', 'finalize', db)
        query = ROOT / 'ql/src/issue173'
        results = rows(db, query / 'Associations.ql', tmp / 'associations.bqrs')
        witnesses = rows(db, query / 'Witnesses.ql', tmp / 'witnesses.bqrs')
        diagnostics = rows(db, query / 'Diagnostics.ql', tmp / 'diagnostics.bqrs')
        files = rows(db, ROOT / 'ql/src/diagnostics/SuccessfullyExtractedFiles.ql', tmp / 'files.bqrs')
        assert {r[0]['url']['uri'] for r in files} == {(SOURCE / n).resolve().as_uri() for n in EXPECTED_FILES - {'malformed.ut'}}, files
        assert len(files) == len(EXPECTED_FILES) - 1
        assert len(diagnostics) == 2 and all(loc(r[0])[0] == 'malformed.ut' and r[2] == 'parse_error' for r in diagnostics), diagnostics

        # Entity IDs and parent indices establish the relationships, not just coincident spans.
        by_id = {r[0]['id']: r for r in witnesses}
        def assert_link(child, parent, index):
            witness = by_id[child['id']]
            assert witness[1]['id'] == parent['id'] and witness[2] == index, witness
        def validate(result_rows):
            observed = {}
            for root, decl, declarator, name, value, text, tag, read in result_rows:
                file, line, col, endline, endcol = loc(tag)
                observed.setdefault(file, []).append((col, loc(read)[2]))
                assert loc(read)[0] == file and read['label'] == name['label']
                assert len({x['id'] for x in (root, decl, declarator, name, value, text, tag, read)}) == 8
                assert by_id[root['id']][1]['id'] == root['id'] and by_id[root['id']][2] == -1
                assert_link(decl, root, 15 if file == 'footstrap-header.ut' else (2 if file in ('import-alias-other.ut', 'braced-shadow.ut', 'unbraced-other.ut') else 1))
                assert_link(declarator, decl, 1)
                assert_link(name, declarator, 0)
                assert_link(value, declarator, 2)
                assert_link(text, root, 16 if file == 'footstrap-header.ut' else (3 if file in ('import-alias-other.ut', 'braced-shadow.ut', 'unbraced-other.ut') else 2))
                expected_tag_index = 4 if file == 'footstrap-header.ut' else (2 if file in ('write-other.ut', 'augmented-other.ut', 'update-other.ut') or file == 'repeated.ut' and col == 36 else 1)
                assert_link(tag, text, expected_tag_index)
                assert_link(read, tag, 1)
                if file == 'footstrap-header.ut':
                    assert [loc(e)[1:] for e in (decl, declarator, name, value, text, tag, read)] == [
                        (86, 5, 86, 97), (86, 11, 86, 97), (86, 11, 86, 17),
                        (86, 21, 86, 97), (86, 99, 138, 4), (87, 54, 87, 66), (87, 57, 87, 63)]
                else:
                    assert (line, endline, endcol) == (1, 1, col + 9)
            assert {k: sorted(v) for k, v in observed.items()} == sites, observed
        validate(results)

        # The two qualifying read entities are distinct. Swapping one while retaining
        # both tag identities and row count must violate the parent-identity oracle.
        repeated = [r for r in results if loc(r[0])[0] == 'repeated.ut']
        assert len(repeated) == 2 and repeated[0][6]['id'] != repeated[1][6]['id']
        assert repeated[0][7]['id'] != repeated[1][7]['id']
        mutated_rows = [list(r) for r in results]
        first = next(i for i, r in enumerate(mutated_rows) if r[6]['id'] == repeated[0][6]['id'])
        swapped_read = dict(mutated_rows[first][7])
        swapped_read['id'] = repeated[1][7]['id']
        mutated_rows[first][7] = swapped_read
        assert loc(mutated_rows[first][7]) == loc(results[first][7])
        assert by_id[swapped_read['id']][1]['id'] != mutated_rows[first][6]['id']
        assert len(mutated_rows) == len(results)
        try:
            validate(mutated_rows)
        except AssertionError:
            pass
        else:
            raise AssertionError('swapped read identity was accepted')

        # Both write controls preserve the adjacent declaration and direct tag;
        # their assignment LHS identity and owning expression differ as intended.
        for file, spelling, write_index, read_index in [
            ('write-same.ut', 'page', 1, 2), ('write-other.ut', 'other', 1, 2),
            ('write-after.ut', 'page', 2, 1),
        ]:
            lhs = [r for r in witnesses if loc(r[0])[0] == file and r[0]['label'] == spelling
                   and r[3] == 'Identifier' and r[2] == 0 and r[1]['label'] == 'AssignmentExpression']
            assert len(lhs) == 1, lhs
            assignment = by_id[lhs[0][1]['id']]
            assert assignment[1]['label'] == 'ExpressionTag' and assignment[2] == 1
            write_tag = by_id[assignment[1]['id']]
            assert write_tag[2] == write_index and write_tag[1]['label'] == 'TextStatement'
            direct = [r for r in witnesses if loc(r[0])[0] == file and r[0]['label'] == 'page'
                      and r[3] == 'Identifier' and r[2] == 1 and r[1]['label'] == 'ExpressionTag']
            assert len(direct) == 1, direct
            read_tag = by_id[direct[0][1]['id']]
            assert read_tag[2] == read_index and read_tag[1]['id'] == write_tag[1]['id']
            assert (write_tag[2] < read_tag[2]) == (file != 'write-after.ut')
        for file, spelling, kind in [
            ('augmented-same.ut', 'page', 'AugmentedAssignmentExpression'),
            ('augmented-other.ut', 'other', 'AugmentedAssignmentExpression'),
            ('update-same.ut', 'page', 'UpdateExpression'),
            ('update-other.ut', 'other', 'UpdateExpression'),
        ]:
            targets = [r for r in witnesses if loc(r[0])[0] == file and r[3] == 'Identifier'
                       and r[0]['label'] == spelling and r[1]['label'] == kind]
            assert len(targets) == 1, targets
            expr = by_id[targets[0][1]['id']]
            assert expr[1]['label'] == 'ExpressionTag' and expr[2] == 1
            write_tag = by_id[expr[1]['id']]
            direct = [r for r in witnesses if loc(r[0])[0] == file and r[0]['label'] == 'page'
                      and r[3] == 'Identifier' and r[1]['label'] == 'ExpressionTag']
            assert len(direct) == 1
            read_tag = by_id[direct[0][1]['id']]
            assert write_tag[1]['id'] == read_tag[1]['id'] and write_tag[2] == 1 and read_tag[2] == 2
        deletes = [r for r in witnesses if loc(r[0])[0] == 'delete-prefix.ut'
                   and r[3] == 'DeleteExpression' and r[1]['label'] == 'ExpressionTag']
        direct = [r for r in witnesses if loc(r[0])[0] == 'delete-prefix.ut'
                  and r[3] == 'Identifier' and r[0]['label'] == 'page'
                  and r[1]['label'] == 'ExpressionTag']
        assert len(deletes) == len(direct) == 1
        write_tag = by_id[deletes[0][1]['id']]
        read_tag = by_id[direct[0][1]['id']]
        assert write_tag[1]['id'] == read_tag[1]['id'] and write_tag[2] == 1 and read_tag[2] == 2
        real = [r for r in witnesses if loc(r[0])[0] == 'footstrap-header.ut']
        member_tags = [r for r in real if r[3] == 'ExpressionTag' and loc(r[0])[1:] == (87, 20, 87, 40)]
        nested_tags = [r for r in real if r[3] == 'ExpressionTag' and loc(r[0])[1:] == (207, 40, 207, 52)]
        assert len(member_tags) == len(nested_tags) == 1
        assert member_tags[0][2] == 2 and nested_tags[0][2] == 8
        member_children = [r for r in real if r[1]['id'] == member_tags[0][0]['id'] and r[3] == 'MemberExpression']
        nested_children = [r for r in real if r[1]['id'] == nested_tags[0][0]['id'] and r[3] == 'Identifier']
        assert len(member_children) == len(nested_children) == 1
        assert member_children[0][2] == nested_children[0][2] == 1
        assert nested_children[0][0]['label'] == 'fs_page'
        assert by_id[nested_tags[0][1]['id']][1]['label'] != 'Markup'
        competitors = [r for r in witnesses if loc(r[0])[0] == 'competing.ut'
                       and r[3] == 'VariableDeclarator']
        assert len(competitors) == 2 and competitors[0][0]['id'] != competitors[1][0]['id']
        # Mutate the actual name-equality predicate in a disposable local QL pack.
        # The original positive must disappear, demonstrating this check detects
        # the regression rather than merely checking that evaluation succeeds.
        with tempfile.TemporaryDirectory(prefix='mutation-', dir=query) as mutation_dir:
            mutation_dir = Path(mutation_dir)
            original = (query / 'Association.qll').read_text()
            needle = 'read.toString() = declarator.getName().toString()'
            assert original.count(needle) == 1
            (mutation_dir / 'Association.qll').write_text(original.replace(
                needle, 'read.toString() != declarator.getName().toString()'))
            (mutation_dir / 'Associations.ql').write_text((query / 'Associations.ql').read_text())
            mutated = rows(db, mutation_dir / 'Associations.ql', tmp / 'mutation.bqrs')
            assert not any(loc(r[0])[0] in ('clean.ut', 'footstrap-header.ut') for r in mutated), mutated
        for file, kind in [('export-lexical.ut', 'LexicalDeclaration'),
                           ('export-function.ut', 'FunctionDeclaration')]:
            wrapped = [r for r in witnesses if loc(r[0])[0] == file and r[3] == kind
                       and r[1]['label'] == 'ExportStatement']
            assert len(wrapped) == 1, wrapped
        for file in ('import-alias-same.ut', 'import-alias-other.ut'):
            specifiers = [r for r in witnesses if loc(r[0])[0] == file and r[3] == 'ImportSpecifier']
            assert len(specifiers) == 1, specifiers
        print('markup association controls, full entity ownership and failure mutation verified')


if __name__ == '__main__':
    main()
