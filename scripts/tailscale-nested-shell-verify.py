#!/usr/bin/env python3
"""Verify a focused Tailscale run receipt against its source-first manifest.

This checks file identities, extraction diagnostics, and candidate multiplicity.
It does not authenticate CodeQL execution or prove runtime shell behavior.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def tuples(path: Path):
    return json.loads(path.read_text())['#select']['tuples']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'ql/test/tailscale-nested-shell/expected.json')
    args = parser.parse_args()
    run = args.run.resolve()
    expected = json.loads(args.manifest.read_text())['files']
    assert all(hashlib.sha256((run / 'stage' / rel).read_bytes()).hexdigest() == info['sha256']
               for rel, info in expected.items()), 'staged source hash mismatch'
    for case in ('parent', 'fixed', 'controls'):
        selected = {rel for rel in expected if rel.startswith(case + '/')}
        observed = Counter(row[0]['label'] for row in tuples(run / 'out' / case / 'success-decode.stdout'))
        want = Counter({str(run / 'stage' / rel): 1 for rel in selected})
        assert observed == want, (case, observed, want)
        assert tuples(run / 'out' / case / 'errors-decode.stdout') == [], case
        candidates = tuples(run / 'out' / case / 'candidate-decode.stdout')
        want_count = sum(len(expected[rel]['candidate_sinks']) for rel in selected)
        assert len(candidates) == want_count, (case, candidates, want_count)
        assert all(row[0]['label'] == 'CallExpression' for row in candidates), case
        print(case, 'success_files', len(observed), 'errors', 0, 'candidates', len(candidates))
    field_expected = {
        'parent': [('usr/share/rpcd/ucode/tailscale.uc', 'loginserver', 164, 3, 48),
                   ('usr/share/rpcd/ucode/tailscale.uc', 'loginserver_authkey', 164, 3, 48)],
        'fixed': [],
        'controls': [('usr/share/rpcd/ucode/nested_pos.uc', 'loginserver', 18, 5, 50)],
    }
    for case, want in field_expected.items():
        rows = tuples(run / 'out' / case / 'fields-decode.stdout')
        actual = [(row[1], row[2], row[5], row[6], row[7]) for row in rows]
        assert actual == want, (case, actual, want)
    for case in ('parent', 'fixed', 'controls'):
        sarif = json.loads((run / 'out' / ('sarif-' + case) / 'candidate.sarif').read_text())
        sarif_run = sarif['runs'][0]
        assert [rule['id'] for rule in sarif_run['tool']['driver']['rules']] == [
            'ucode/m4/tailscale-nested-shell-candidate']
        observed = Counter()
        for result in sarif_run.get('results', []):
            assert result['ruleId'] == 'ucode/m4/tailscale-nested-shell-candidate'
            location = result['locations'][0]['physicalLocation']
            region = location['region']
            observed[(location['artifactLocation']['uri'], region['startLine'],
                      region['startColumn'], region['endColumn'])] += 1
        wanted = Counter()
        for rel, info in expected.items():
            if not rel.startswith(case + '/'):
                continue
            uri = rel[len(case) + 1:]
            for span in info['candidate_sinks']:
                match = re.fullmatch(r'(\d+):(\d+)-(\d+)', span)
                assert match, span
                line, start, end = map(int, match.groups())
                wanted[(uri, line, start, end + 1)] += 1
        assert observed == wanted, (case, observed, wanted)
    print('source hashes and exact extraction/candidate counts match manifest')


if __name__ == '__main__':
    main()
