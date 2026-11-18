#!/usr/bin/env python3
"""Require CodeQL's resolved database source prefix to be the M3 fixture root."""
import json
import subprocess
import sys


def main():
    db, expected = sys.argv[1:]
    try:
        result = subprocess.run(['codeql', 'resolve', 'database', '--format=json', db],
                                check=True, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        actual = metadata['sourceLocationPrefix']
        if not isinstance(actual, str) or actual != expected:
            raise ValueError(f'expected {expected!r}, got {actual!r}')
    except (OSError, subprocess.CalledProcessError, ValueError, TypeError, KeyError) as exc:
        sys.exit(f'M3 database source root rejected: {exc}')


if __name__ == '__main__':
    main()
