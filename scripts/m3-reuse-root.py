#!/usr/bin/env python3
"""Require CodeQL's resolved database source prefix to be the M3 fixture root."""
import json
import os
import subprocess
import sys
from typing import NoReturn


def fail(message: str) -> NoReturn:
    sys.exit('M3 database source root rejected: ' + message)


def main():
    if len(sys.argv) != 3:
        fail('usage: m3-reuse-root.py <database> <expected-source-root>')
    db, expected = sys.argv[1], sys.argv[2]
    try:
        result = subprocess.run(['codeql', 'resolve', 'database', '--format=json', db],
                                check=True, capture_output=True, text=True)
    except OSError as exc:
        fail(f'cannot run codeql: {exc}')
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or '').strip()
        fail(f'codeql resolve failed with status {exc.returncode}: {detail}')
    except ValueError as exc:
        fail(f'undecodable codeql output: {exc}')
    try:
        actual = json.loads(result.stdout)['sourceLocationPrefix']
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        fail(f'unreadable database metadata: {exc!r}')
    if not isinstance(actual, str):
        fail(f'expected a string prefix, got {actual!r}')
    try:
        same = os.path.realpath(actual) == os.path.realpath(expected)
    except ValueError as exc:
        fail(f'unusable source prefix: {exc}')
    if not same:
        fail(f'expected {expected!r}, got {actual!r}')


if __name__ == '__main__':
    main()
