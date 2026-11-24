#!/usr/bin/env python3
"""Verify a focused Tailscale run receipt against its source-first manifest.

This checks file identities, extraction diagnostics, and candidate multiplicity.
It does not authenticate CodeQL execution or prove runtime shell behavior.
"""
import argparse
import hashlib
import json
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
        'parent': [('loginserver', 164, 3, 48), ('loginserver_authkey', 164, 3, 48)],
        'fixed': [],
        'controls': [('loginserver', 18, 5, 50)],
    }
    for case, want in field_expected.items():
        rows = tuples(run / 'out' / case / 'fields-decode.stdout')
        actual = [(row[1], row[4], row[5], row[6]) for row in rows]
        assert actual == want, (case, actual, want)
    sarif = json.loads((run / 'out/sarif-parent/candidate.sarif').read_text())
    sarif_run = sarif['runs'][0]
    assert [rule['id'] for rule in sarif_run['tool']['driver']['rules']] == [
        'ucode/m4/tailscale-nested-shell-candidate']
    results = sarif_run['results']
    assert len(results) == 1
    result = results[0]
    assert result['ruleId'] == 'ucode/m4/tailscale-nested-shell-candidate'
    location = result['locations'][0]['physicalLocation']
    assert location['artifactLocation']['uri'] == 'usr/share/rpcd/ucode/tailscale.uc'
    assert location['region'] == {'startLine': 164, 'startColumn': 3, 'endColumn': 49}
    print('source hashes and exact extraction/candidate counts match manifest')


if __name__ == '__main__':
    main()
