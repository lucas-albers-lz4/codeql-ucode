#!/usr/bin/env python3
"""Lexical inventory for a pinned Git tree; deliberately not a ucode parser."""
import re
import subprocess
import sys

REV = 'b2e0be4b46ec0fd43394c081fa7c50657af14011'
INITIALIZER = re.compile(r'\b([A-Za-z_$][\w$]*)\s*=\s*popen\s*\(')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', repo, *args]).decode('utf-8', 'replace')


def candidates(source):
    for match in INITIALIZER.finditer(source):
        name = match.group(1)
        uses = re.finditer(r'=\s*' + re.escape(name) + r'\b', source)
        yield name, source.count('\n', 0, match.start()) + 1, list(uses)


def main(repo):
    repo = git(repo, 'rev-parse', '--show-toplevel').strip()
    # git grep's object argument reads the pin even if the checkout is dirty.
    paths = [x.split(':', 1)[1] for x in git(repo, 'grep', '-l', '-I', 'popen', REV, '--').splitlines()]
    for path in paths:
        if not (path.endswith('.uc') or '/ucode/' in path):
            continue
        source = git(repo, 'show', f'{REV}:{path}')
        found = list(candidates(source))
        if not found:
            continue
        print('\n' + path)
        for name, line, uses in found:
            print(f' initializer/assignment {line}: {name}')
            for use in uses:
                start = source.rfind('\n', 0, use.start()) + 1
                end = source.find('\n', use.end())
                if end < 0:
                    end = len(source)
                print(f'  RHS candidate {source.count(chr(10), 0, use.start()) + 1}: {source[start:end].strip()}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('usage: census.py PATH_TO_LUCI_GIT_REPOSITORY')
    main(sys.argv[1])
