#!/usr/bin/env python3
"""Export one bounded setBlockDetect observation; input is not authenticated."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def read_csv(path):
    return list(csv.reader(io.StringIO(path.read_bytes().decode('utf-8'), newline=''), strict=True))


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate lock JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f'invalid JSON constant: {value}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('csv', 'extracted', 'errors', 'source-root', 'lock'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    header = ['observation_kind', 'method', 'sink_kind', 'command', 'source_path',
              'start_line', 'start_column', 'end_line', 'end_column']
    row = ['callback_body_call', 'setBlockDetect', 'system', '/sbin/block detect > /etc/config/fstab',
           'usr/share/rpcd/ucode/luci', '532', '21', '532', '68']
    try:
        if read_csv(args.csv) != [header, row]:
            raise ValueError('table does not contain exactly the supported observation')
        lock = args.lock.read_bytes()
        parsed = json.loads(lock.decode('utf-8'), object_pairs_hook=unique_pairs,
                            parse_constant=reject_constant)
        if parsed['repos']['luci']['sha'] != 'b2e0be4b46ec0fd43394c081fa7c50657af14011':
            raise ValueError('unsupported luci lock revision')
        source = (args.source_root / row[4]).read_bytes()
        if hashlib.sha256(source).hexdigest() != '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e':
            raise ValueError('unsupported source bytes')
        expected_file = str(args.source_root.resolve(strict=True) / row[4])
        if read_csv(args.extracted) != [['f', 'col1'], [expected_file, '']]:
            raise ValueError('successful extraction diagnostic mismatch')
        if read_csv(args.errors) != [['error', 'col1', 'col2']]:
            raise ValueError('extraction error diagnostic mismatch')
    except (OSError, UnicodeError, csv.Error, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'export: {exc}\n')
    record = {
        'record_type': 'handler_effect', 'evidence_status': 'fact', 'producer': 'step3',
        'record_id': 'm4:effect:luci-setBlockDetect-system',
        'corpus_revision': 'sha256:' + hashlib.sha256(lock).hexdigest(),
        'profile': 'luci-ssl-25.12', 'analysis_revision': 'step3:setblock-typed-v1',
        'ingress': 'ubus_http', 'entrypoint_id': 'ubus_http:luci.setBlockDetect',
        'ubus_object': 'luci', 'method': 'setBlockDetect',
        'effect_id': 'setBlockDetect.block-detect.system', 'target_id': 'command:block-detect',
        'op': 'exec', 'sink_kind': 'system', 'assessment': 'unassessed',
        'source_location': {'path': 'usr/share/rpcd/ucode/luci', 'start_line': 532,
                            'start_column': 21, 'end_line': 532, 'end_column': 68},
        'conditions': ['setBlockDetect.call body', 'builtin system of literal /sbin/block detect',
                       'call takes no request.args'],
        'assumptions': ['Source observation in the pinned callback body; not a taint path',
                        'The supplied CSV and typed JSON are not authenticated as CodeQL output',
                        'Fixed argv; this is not luci.sys and not request.args interpolation',
                        'shellquote and basename are not sanitizers; they are not present on this sink'],
        'evidence_refs': ["luci@b2e0be4b modules/luci-base/root/usr/share/rpcd/ucode/luci setBlockDetect.call system('/sbin/block detect > /etc/config/fstab')",
                          'ql/src/m4/SetBlockDetectEffectTable.ql',
                          'openwrt/luci@b2e0be4b46ec0fd43394c081fa7c50657af14011 modules/luci-base/root/usr/share/rpcd/ucode/luci:532'],
        'unknowns': ['live uhttpd/rpcd not executed',
                     'Callback registration, actual execution and live uhttpd/rpcd are not established by the table',
                     'Lexical shadowing and unmodeled call shapes are not resolved by the table'],
    }
    print(json.dumps([record], indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == '__main__':
    main()
