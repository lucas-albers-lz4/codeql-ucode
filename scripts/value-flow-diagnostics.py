#!/usr/bin/env python3
"""Validate the decoded extraction diagnostics for the value-flow fixture."""
import json
import sys
from pathlib import Path


def rows(path, columns):
    data = json.loads(Path(path).read_text())
    if set(data) != {'#select'} or data['#select']['columns'] != columns:
        raise ValueError(f'unexpected diagnostic schema in {path}')
    tuples = data['#select']['tuples']
    if not isinstance(tuples, list):
        raise ValueError(f'invalid diagnostic tuples in {path}')
    return tuples


def main():
    expected = Path(sys.argv[1])
    success = rows(sys.argv[2], [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}])
    errors = rows(sys.argv[3], [{'name': 'error', 'kind': 'Entity'},
                                {'kind': 'String'}, {'kind': 'Integer'}])
    problems = []
    if errors:
        problems.append(f'expected zero extraction errors; got {json.dumps(errors)}')
    wanted = [[{'label': str(expected), 'url': {'uri': expected.as_uri(),
               'startLine': 0, 'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']]
    if success != wanted:
        problems.append(f'expected exactly one successful-file receipt for {expected}; got {json.dumps(success)}')
    if problems:
        raise ValueError('\n'.join(problems))
    print(f'value-flow extraction accepted: {expected}; zero errors')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        sys.exit(f'value-flow extraction rejected: {exc}')
