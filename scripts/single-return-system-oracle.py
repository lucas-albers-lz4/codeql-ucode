#!/usr/bin/env python3
"""Exact multiset oracle for a bounded source-shape table, not a finding."""
from collections import Counter
import json
from pathlib import Path
import sys

PREFIX = 'modules/{}/root/usr/share/rpcd/ucode/luci'
EXPECTED = [
    [PREFIX.format('comment-positive'), 4, 22, 4, 40, '/bin/true'],
    [PREFIX.format('positive'), 3, 22, 3, 40, '/bin/true'],
    [PREFIX.format('real'), 532, 21, 532, 68, '/sbin/block detect > /etc/config/fstab'],
]
COLUMNS = [
    {'name': 'source_path', 'kind': 'String'},
    {'name': 'start_line', 'kind': 'Integer'},
    {'name': 'start_column', 'kind': 'Integer'},
    {'name': 'end_line', 'kind': 'Integer'},
    {'name': 'end_column', 'kind': 'Integer'},
    {'name': 'command', 'kind': 'String'},
]


def check_rows(rows):
    if not isinstance(rows, list) or any(
        not isinstance(row, list) or len(row) != 6 or
        type(row[0]) is not str or any(type(n) is not int for n in row[1:5]) or
        type(row[5]) is not str for row in rows
    ):
        raise ValueError('invalid shape table rows')
    encode = lambda r: json.dumps(r, ensure_ascii=False, separators=(',', ':'))
    actual, expected = Counter(map(encode, rows)), Counter(map(encode, EXPECTED))
    if actual != expected:
        raise ValueError(f'source-shape multiset mismatch: missing={expected-actual}; extra={actual-expected}')


def main():
    result = json.loads(Path(sys.argv[1]).read_text())
    if set(result) != {'#select'} or set(result['#select']) != {'columns', 'tuples'} or result['#select']['columns'] != COLUMNS:
        raise ValueError('unexpected source-shape table schema')
    check_rows(result['#select']['tuples'])
    print('exact source-shape multiset accepted')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        sys.exit(f'source-shape table rejected: {exc}')
