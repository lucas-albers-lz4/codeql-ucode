#!/usr/bin/env python3
"""Fail closed on incomplete M4 standalone-smoke extraction diagnostics."""
from collections import Counter
import json
from pathlib import Path
import sys


def rows(path, columns):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or set(data) != {'#select'}:
        raise ValueError(f'unexpected diagnostic schema in {path}')
    table = data['#select']
    if not isinstance(table, dict) or set(table) != {'columns', 'tuples'} or table['columns'] != columns:
        raise ValueError(f'unexpected diagnostic schema in {path}')
    if not isinstance(table['tuples'], list):
        raise ValueError(f'invalid diagnostic tuples in {path}')
    return table['tuples']


def main():
    success = rows(sys.argv[1], [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}])
    errors = rows(sys.argv[2], [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}])
    expected = [Path(arg) for arg in sys.argv[3:]]
    if not expected or any(not path.is_absolute() for path in expected):
        raise ValueError('expected absolute selected file paths')
    wanted = [[{'label': str(path), 'url': {'uri': path.as_uri(), 'startLine': 0,
               'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, ''] for path in expected]
    encode = lambda row: json.dumps(row, sort_keys=True, separators=(',', ':'))
    problems = []
    if errors:
        problems.append(f'expected zero extraction errors; got {json.dumps(errors)}')
    if Counter(map(encode, success)) != Counter(map(encode, wanted)):
        problems.append(f'expected exact successful-file multiset {json.dumps(wanted)}; got {json.dumps(success)}')
    if problems:
        raise ValueError('\n'.join(problems))
    print('M4 extraction accepted: exact successful-file multiset and zero errors')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        sys.exit(f'M4 extraction rejected: {exc}')
