#!/usr/bin/env python3
"""Check decoded table against a source-reviewed exact oracle, preserving rows."""
import csv
import sys
from collections import Counter
from pathlib import Path


def read(path):
    with Path(path).open(encoding='utf-8', newline='') as f:
        reader = csv.reader(f, strict=True)
        rows = list(reader)
    if not rows:
        raise ValueError('missing CSV header')
    if len(set(rows[0])) != len(rows[0]) or any(len(r) != len(rows[0]) for r in rows[1:]):
        raise ValueError('duplicate header or wrong row width')
    return rows[0], Counter(tuple(row) for row in rows[1:])


def verify(actual, expected):
    ah, ar = read(actual)
    eh, er = read(expected)
    if ah != eh or ar != er:
        raise ValueError(f'table differs from independent exact oracle: missing={er-ar}, extra={ar-er}')


if __name__ == '__main__':
    try:
        verify(sys.argv[1], sys.argv[2])
    except (ValueError, OSError, csv.Error, IndexError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print('exact table oracle matched')
