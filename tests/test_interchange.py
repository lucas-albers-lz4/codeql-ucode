"""Offline checks for the classified, committed docs/*.json snapshots."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
TYPED_COUNTS = {
    'm3-findings.json': 4,
    'm4-findings.json': 5,
    'm4-getfeatures-direct-exec.json': 5,
    'm4-imported-callee-findings.json': 1,
    'm4-shellquote-findings.json': 4,
}
COVERAGE_KEYS = {
    'm3-coverage.json': {'analysis_revision', 'profile', 'entrypoint_id', 'status', 'extracted_files', 'analyzed', 'resolved_calls', 'unmodeled_branches', 'unsupported_constructs', 'trusted_summaries', 'unknowns'},
    'm4-coverage.json': {'analysis_revision', 'profile', 'status', 'extracted_files', 'analyzed', 'methods_with_request_args_exec', 'negative_controls', 'unmodeled_branches', 'unsupported_constructs', 'unknowns'},
    'm4-getfeatures-direct-exec-coverage.json': {'analysis_revision', 'profile', 'entrypoint_id', 'status', 'analyzed', 'call_sites', 'unmodeled_branches', 'out_of_slice'},
    'm4-shellquote-coverage.json': {'analysis_revision', 'profile', 'status', 'extracted_files', 'analyzed', 'unsupported_constructs'},
}
STATUSES = {'fact', 'candidate', 'path_found', 'no_path', 'counterexample', 'inconclusive'}
RECORD_TYPES = {'handler_effect', 'taint_path'}
PROFILE = 'luci-ssl-25.12'
LEGACY_MANIFEST = json.loads((ROOT / 'tests/fixtures/legacy-interchange-manifest.json').read_text(encoding='utf-8'))
LEGACY_COVERAGE = json.loads((ROOT / 'tests/fixtures/legacy-coverage-manifest.json').read_text(encoding='utf-8'))
COVERAGE_FAMILIES = {
    'm3-coverage.json': 'm3-findings.json',
    'm4-coverage.json': 'm4-findings.json',
    'm4-getfeatures-direct-exec-coverage.json': 'm4-getfeatures-direct-exec.json',
    'm4-shellquote-coverage.json': 'm4-shellquote-findings.json',
}
ASSESSED = {'intended_access', 'risky_delegation', 'authorization_violation'}
FAMILY_QUERIES = {
    'm4-findings.json': 'ql/src/m4/RequestArgsExec.ql',
    'm4-getfeatures-direct-exec.json': 'ql/src/m4/GetFeaturesDirectExec.ql',
    'm4-imported-callee-findings.json': 'ql/src/m4/ImportedCalleeTaint.ql',
    'm4-shellquote-findings.json': 'ql/src/m4/ShellInjection.ql',
}
M3_QUERIES = {
    'm3:getfeatures-netifd-popen': 'ql/src/m3/GetFeaturesPopen.ql',
    'm3:getfeatures-netifd-request-args-no-path': 'ql/src/m3/GetFeaturesHelperTaint.ql',
}
RESOURCE_IDENTITY_FIELDS = ('ingress', 'entrypoint_id', 'ubus_object', 'method', 'cgi_endpoint')


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def validate_record(record, seen):
    if not isinstance(record, dict):
        raise ValueError('typed record must be an object')
    record_id = record.get('record_id')
    if not nonempty_string(record_id) or record_id in seen:
        raise ValueError('record_id must be nonempty and globally unique')
    if not isinstance(record.get('record_type'), str) or record['record_type'] not in RECORD_TYPES:
        raise ValueError(f'{record_id}: unclassified record_type')
    status = record.get('evidence_status')
    if not isinstance(status, str) or status not in STATUSES:
        raise ValueError(f'{record_id}: unclassified evidence_status')
    if record.get('producer') != 'step3':
        raise ValueError(f'{record_id}: producer must be step3')
    revision = record.get('analysis_revision')
    if not isinstance(revision, str) or not re.fullmatch(r'step3:[^\s:]+', revision):
        raise ValueError(f'{record_id}: invalid producer-local analysis_revision')
    corpus = record.get('corpus_revision')
    if not isinstance(corpus, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', corpus):
        raise ValueError(f'{record_id}: invalid corpus_revision')
    if record.get('profile') != PROFILE:
        raise ValueError(f'{record_id}: unclassified profile')
    for key in ('assumptions', 'unknowns'):
        value = record.get(key)
        if key not in record and status in ('fact', 'candidate'):
            continue
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f'{record_id}: {key} must be an array of strings')

    if status == 'inconclusive' and not any(nonempty_string(item) for item in record['unknowns']):
        raise ValueError(f'{record_id}: inconclusive record requires meaningful unknowns')

    if record['record_type'] == 'handler_effect' and 'session_class' in record:
        raise ValueError(f'{record_id}: aggregate effect cannot declare session_class')
    if 'session_class' in record and not nonempty_string(record['session_class']):
        raise ValueError(f'{record_id}: invalid session_class')
    refs = record.get('evidence_refs', [])
    if not isinstance(refs, list) or not all(nonempty_string(ref) for ref in refs):
        raise ValueError(f'{record_id}: invalid evidence_refs')
    if 'assessment' in record and (not isinstance(record['assessment'], str)
                                   or record['assessment'] not in ASSESSED | {'unassessed'}):
        raise ValueError(f'{record_id}: invalid assessment')
    if any(ref == 'policy:grant:' for ref in refs):
        raise ValueError(f'{record_id}: empty grant reference')
    grants = [ref for ref in refs if ref.startswith('policy:grant:')]
    if record.get('assessment') in ASSESSED and (not nonempty_string(record.get('expectation_id')) or not grants):
        raise ValueError(f'{record_id}: assessed record requires expectation and grant reference')
    if record['record_type'] == 'taint_path' and grants and not nonempty_string(record.get('expectation_id')):
        raise ValueError(f'{record_id}: grant reference requires expectation')
    seen.add(record_id)
    return corpus


def validate_documents(documents):
    if set(documents) != set(TYPED_COUNTS) | set(COVERAGE_KEYS):
        raise ValueError('unclassified or missing docs/*.json file')
    seen, revisions = set(), set()
    for name, count in TYPED_COUNTS.items():
        rows = documents[name]
        if not isinstance(rows, list) or len(rows) != count:
            raise ValueError(f'{name}: expected classified array of {count} records')
        for row in rows:
            revisions.add(validate_record(row, seen))
            if row['analysis_revision'] != LEGACY_MANIFEST[name]['analysis_revision']:
                raise ValueError(f'{name}: wrong family analysis_revision')
            if row['record_type'] != LEGACY_MANIFEST[name]['record_type'].get(row['record_id']):
                raise ValueError(f"{row['record_id']}: unexpected snapshot record_type")
            if row['evidence_status'] != LEGACY_MANIFEST[name]['evidence_status'].get(row['record_id']):
                raise ValueError(f"{row['record_id']}: unexpected snapshot status")
            identity = {key: row[key] for key in RESOURCE_IDENTITY_FIELDS if key in row}
            if identity != LEGACY_MANIFEST[name]['resource_identity'][row['record_id']]:
                raise ValueError(f"{row['record_id']}: unexpected snapshot resource identity")
            required_unknowns = LEGACY_MANIFEST[name]['unknowns'][row['record_id']]
            if not set(required_unknowns).issubset(row.get('unknowns', [])):
                raise ValueError(f"{row['record_id']}: unexpected snapshot unknowns")
            required = LEGACY_MANIFEST[name]['required_evidence'].get(row['record_id'], [])
            if not set(required).issubset(row.get('evidence_refs', [])):
                raise ValueError(f"{row['record_id']}: missing required snapshot evidence")
            for ref in required:
                if ref.startswith('ql/') and not (ROOT / ref).is_file():
                    raise ValueError(f"{row['record_id']}: missing required query evidence {ref}")
            query = M3_QUERIES.get(row['record_id']) if name == 'm3-findings.json' else FAMILY_QUERIES[name]
            if query and (query not in row.get('evidence_refs', []) or not (ROOT / query).is_file()):
                raise ValueError(f"{row['record_id']}: missing required query evidence")
            if row['record_id'] == 'm4:setInitAction-init_action-unresolved':
                if row['evidence_status'] != 'inconclusive' or not row.get('unknowns'):
                    raise ValueError(f"{row['record_id']}: unresolved call must remain inconclusive")
        if {row['record_id'] for row in rows} != set(LEGACY_MANIFEST[name]['record_ids']):
            raise ValueError(f'{name}: snapshot record identities differ')
    if len(revisions) != 1:
        raise ValueError('snapshot corpus revisions differ')
    for name, expected_keys in COVERAGE_KEYS.items():
        report = documents[name]
        if (not isinstance(report, dict) or set(report) != expected_keys
                or report.get('profile') != PROFILE or report.get('status') != 'partial'
                or not isinstance(report.get('analyzed'), list)
                or report.get('analysis_revision') != LEGACY_MANIFEST[COVERAGE_FAMILIES[name]]['analysis_revision']):
            raise ValueError(f'{name}: expected report-only coverage object')
        if 'entrypoint_id' in report and report['entrypoint_id'] != 'ubus_http:luci.getFeatures':
            raise ValueError(f'{name}: wrong coverage entrypoint')
        for key, value in report.items():
            if key in {'analysis_revision', 'profile', 'status', 'entrypoint_id', 'call_sites'}:
                continue
            if not isinstance(value, list) or not all(nonempty_string(item) for item in value):
                raise ValueError(f'{name}: invalid coverage {key}')
            if key != 'trusted_summaries' and not value:
                raise ValueError(f'{name}: missing coverage {key}')
        if 'call_sites' in report:
            sites = report['call_sites']
            if not isinstance(sites, list) or not sites or not all(
                isinstance(site, dict) and set(site) == {'line', 'kind', 'command'}
                and type(site['line']) is int and site['line'] > 0
                and site['kind'] in ('popen', 'system') and nonempty_string(site['command'])
                for site in sites
            ):
                raise ValueError(f'{name}: invalid call_sites')
        # Historical coverage matches the consumer's unordered membership rule.
        # Only uncertainty may gain members; other lists retain their length.
        for key, expected in LEGACY_COVERAGE[name].items():
            actual = report[key]
            if isinstance(expected, list):
                if ((key != 'unknowns' and len(actual) != len(expected))
                        or any(item not in actual for item in expected)):
                    raise ValueError(f'{name}: coverage {key} identity mismatch')
            elif actual != expected:
                raise ValueError(f'{name}: coverage {key} differs')
    return seen


def unique_json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def reject_json_constant(value):
    raise ValueError(f'invalid JSON constant: {value}')


def load_documents(directory):
    return {p.name: json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=unique_json_pairs,
                               parse_constant=reject_json_constant)
            for p in directory.glob('*.json')}


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = load_documents(DOCS)

    def test_classified_documents_and_records(self):
        self.assertEqual(len(validate_documents(self.documents)), 19)

    def test_shared_raw_interchange_v1_cases(self):
        raw = (ROOT / 'tests/fixtures/interchange-raw-v1.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '37d41d361d417f519b1523a25ddbb9a2ffd4d90b7fce2140d17c03c14eac68da')
        fixture = json.loads(raw)
        self.assertEqual(fixture['contract'], 'interchange-raw-v1')
        self.assertEqual(len(fixture['cases']), 14)
        for case in fixture['cases']:
            with self.subTest(name=case['name']), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                for source in DOCS.glob('*.json'):
                    (path / source.name).write_bytes(source.read_bytes())
                target = path / case['file']
                original = target.read_text(encoding='utf-8')
                self.assertEqual(original.count(case['anchor']), 1)
                target.write_text(original.replace(case['anchor'], case['replacement']), encoding='utf-8')
                # Require rejection by the raw loader, not a later snapshot check.
                with self.assertRaisesRegex(ValueError, case['error']):
                    load_documents(path)

    def test_raw_duplicate_status_rejected_before_validation(self):
        name = 'm4-imported-callee-findings.json'
        raw = (DOCS / name).read_text(encoding='utf-8')
        status = '"evidence_status": "inconclusive"'
        for replacement in (
            '"evidence_status": "no_path", ' + status,
            status + ', "evidence_status": "no_path"',
            status + ', ' + status,
        ):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                for source in DOCS.glob('*.json'):
                    (path / source.name).write_bytes(source.read_bytes())
                self.assertEqual(raw.count(status), 1)
                (path / name).write_text(raw.replace(status, replacement), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    load_documents(path)

    def test_raw_non_json_constants_rejected_before_validation(self):
        cases = (
            ('m4-imported-callee-findings.json', '"record_type": "taint_path"',
             lambda value: '"record_type": "taint_path", "additional": {"nested": [' + value + ']}'),
            ('m4-getfeatures-direct-exec-coverage.json', '"line": 268',
             lambda value: '"line": ' + value),
        )
        for name, anchor, replacement in cases:
            raw = (DOCS / name).read_text(encoding='utf-8')
            self.assertEqual(raw.count(anchor), 1)
            for constant in ('NaN', 'Infinity', '-Infinity'):
                with self.subTest(name=name, constant=constant), tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)
                    (path / name).write_text(raw.replace(anchor, replacement(constant)), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'invalid JSON constant'):
                        load_documents(path)

    def test_raw_duplicate_keys_at_other_locations_rejected(self):
        typed = 'm4-imported-callee-findings.json'
        coverage = 'm4-getfeatures-direct-exec-coverage.json'
        cases = (
            (typed, '"producer": "step3"', '"producer": "step4", "producer": "step3"'),
            (typed, '"producer": "step3"', '"producer": "step3", "producer": "step4"'),
            (typed, '"record_id": "m4:setInitAction-init_action-unresolved"',
             '"record_id": "wrong", "record_id": "m4:setInitAction-init_action-unresolved"'),
            (typed, '"unknowns": [', '"unknowns": [], "unknowns": ['),
            (typed, '"producer": "step3"', '"produc\\u0065r": "step3", "producer": "step3"'),
            (coverage, '"line": 268', '"line": 1, "line": 268'),
        )
        for name, anchor, replacement in cases:
            with self.subTest(name=name, replacement=replacement), tempfile.TemporaryDirectory() as directory:
                raw = (DOCS / name).read_text(encoding='utf-8')
                self.assertEqual(raw.count(anchor), 1)
                (Path(directory) / name).write_text(raw.replace(anchor, replacement), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    load_documents(Path(directory))

    def test_raw_valid_json_preserves_historical_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for source in DOCS.glob('*.json'):
                (path / source.name).write_bytes(source.read_bytes())
            name = 'm4-imported-callee-findings.json'
            rows = json.loads((path / name).read_text(encoding='utf-8'))
            rows[0]['additional'] = {'nested': [None, True, 1.25, 'NaN', {'x': 'Infinity'}]}
            rows[0]['unknowns'] = list(reversed(rows[0]['unknowns'])) + ['additional conservative unknown']
            rows[0] = dict(reversed(list(rows[0].items())))
            (path / name).write_text(json.dumps(rows), encoding='utf-8')
            name = 'm4-getfeatures-direct-exec-coverage.json'
            report = json.loads((path / name).read_text(encoding='utf-8'))
            report['call_sites'].reverse()
            (path / name).write_text(json.dumps(report, sort_keys=True), encoding='utf-8')
            docs = load_documents(path)
            self.assertEqual(len(docs), 9)
            self.assertEqual(len(validate_documents(docs)), 19)

    def structural_base(self):
        return {
            'record_type': 'taint_path', 'evidence_status': 'path_found',
            'producer': 'step3', 'record_id': 'ucode:test-path',
            'corpus_revision': self.documents['m3-findings.json'][0]['corpus_revision'],
            'profile': 'luci-ssl-25.12', 'analysis_revision': 'step3:request-args-exec-test-v1',
            'ingress': 'ubus_http', 'entrypoint_id': 'ubus_http:luci.getFeatures',
            'ubus_object': 'luci', 'method': 'getFeatures', 'assessment': 'unassessed',
            'assumptions': ['synthetic test row'], 'unknowns': ['authorization not assessed'],
            'evidence_refs': ['ql/src/m4/Synthetic.ql'],
        }

    def check_structural_cases(self, fixture):
        base = self.structural_base()
        for case in fixture['cases']:
            with self.subTest(name=case['name']):
                row = dict(base, **case['overrides'])
                if case['valid']:
                    validate_record(row, set())
                else:
                    with self.assertRaisesRegex(ValueError, case['error_field']):
                        validate_record(row, set())

    def test_shared_structural_v1_cases(self):
        path = ROOT / 'tests/fixtures/issue83-structural-v1.json'
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '86ab384ca31e2e448df5740f054640a9fd485f550b6d427a02a6e2b4143bebcc')
        fixture = json.loads(raw)
        self.assertEqual(fixture['contract'], 'issue83-structural-v1')
        self.assertEqual(len(fixture['cases']), 14)
        self.check_structural_cases(fixture)

    def test_shared_structural_v2_cases(self):
        path = ROOT / 'tests/fixtures/issue83-structural-v2.json'
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'ec2b76c8db2f36c96c7f8ee3bafa35e74fd2a5ce88e716aa8c1edb2e784c3a68')
        fixture = json.loads(raw)
        self.assertEqual(fixture['contract'], 'issue83-structural-v2')
        self.assertEqual(len(fixture['cases']), 24)
        self.check_structural_cases(fixture)

    def test_every_historical_status_and_unknowns_are_pinned(self):
        for name in TYPED_COUNTS:
            for index, original in enumerate(self.documents[name]):
                for field in ('evidence_status', 'unknowns'):
                    with self.subTest(record_id=original['record_id'], field=field):
                        if field == 'unknowns' and not original['unknowns']:
                            continue  # No historical unknown can be lost from an empty set.
                        docs = deepcopy(self.documents)
                        row = docs[name][index]
                        if field == 'evidence_status':
                            row[field] = 'fact' if original[field] != 'fact' else 'candidate'
                        else:
                            row[field] = ['substituted uncertainty']
                        with self.assertRaisesRegex(ValueError, 'snapshot status|snapshot unknowns'):
                            validate_documents(docs)

    def test_historical_unknowns_allow_additions_and_reordering(self):
        docs = deepcopy(self.documents)
        for name in TYPED_COUNTS:
            for row in docs[name]:
                row['unknowns'] = list(reversed(row['unknowns'])) + ['additional conservative unknown']
        validate_documents(docs)

    def test_historical_row_uncertainty_cannot_be_substituted(self):
        docs = deepcopy(self.documents)
        row = docs['m4-imported-callee-findings.json'][0]
        row['unknowns'] = ['different uncertainty']
        with self.assertRaisesRegex(ValueError, 'snapshot unknowns'):
            validate_documents(docs)

    def test_historical_type_cannot_be_retagged_to_aggregate(self):
        docs = deepcopy(self.documents)
        row = next(r for r in docs['m3-findings.json']
                   if r['record_id'] == 'm3:getfeatures-netifd-request-args-no-path')
        row['record_type'] = 'handler_effect'
        row['evidence_refs'].append('policy:grant:root:ubus_http:luci.getFeatures')
        with self.assertRaisesRegex(ValueError, 'snapshot record_type'):
            validate_documents(docs)

    def test_historical_resource_identity_cannot_be_changed(self):
        for key in ('ingress', 'entrypoint_id', 'ubus_object', 'method'):
            with self.subTest(key=key):
                docs = deepcopy(self.documents)
                docs['m4-findings.json'][0][key] = 'substitute'
                with self.assertRaisesRegex(ValueError, 'snapshot resource identity'):
                    validate_documents(docs)
        docs = deepcopy(self.documents)
        docs['m3-findings.json'][2]['method'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'snapshot resource identity'):
            validate_documents(docs)

    def test_every_required_historical_query_resolves_locally(self):
        original = Path.is_file
        def is_file(path):
            return path.name != 'CompleteQuotedArg.ql' and original(path)
        with patch.object(Path, 'is_file', autospec=True, side_effect=is_file):
            with self.assertRaisesRegex(ValueError, 'query evidence'):
                validate_documents(self.documents)

    def test_negative_and_inconclusive_are_explicit_snapshots(self):
        records = {r['record_id']: r for name in TYPED_COUNTS for r in self.documents[name]}
        no_path = records['m3:getfeatures-netifd-request-args-no-path']
        self.assertEqual(no_path['evidence_status'], 'no_path')
        self.assertIn('policy:grant:unauthenticated:ubus_http:luci.getFeatures', no_path['evidence_refs'])
        self.assertIn('ql/src/m3/GetFeaturesHelperTaint.ql', no_path['evidence_refs'])
        self.assertEqual(records['m4:setInitAction-init_action-unresolved']['evidence_status'], 'inconclusive')
        self.assertTrue(records['m4:setInitAction-init_action-unresolved']['unknowns'])

    def test_generic_inconclusive_requires_meaningful_unknown(self):
        row = self.structural_base()
        row['evidence_status'] = 'inconclusive'
        for unknowns in ([], [''], ['  \t', '\n']):
            with self.subTest(unknowns=unknowns):
                row['unknowns'] = unknowns
                with self.assertRaisesRegex(ValueError, 'unknowns'):
                    validate_record(row, set())
        row['unknowns'] = ['', '  ', 'unresolved call']
        validate_record(row, set())

    def test_assessed_row_without_grant_fails_independently_of_snapshot(self):
        row = deepcopy(self.documents['m3-findings.json'][1])
        row['assessment'] = 'intended_access'
        row['expectation_id'] = 'existing-expectation'
        row['evidence_refs'] = ['ql/src/m3/GetFeaturesHelperTaint.ql']
        with self.assertRaisesRegex(ValueError, 'assessed record requires expectation and grant'):
            validate_record(row, set())

    def test_unassessed_aggregate_may_cite_grant_without_expectation(self):
        row = deepcopy(self.documents['m3-findings.json'][0])
        row['assessment'] = 'unassessed'
        row.pop('expectation_id', None)
        self.assertTrue(any(ref.startswith('policy:grant:') for ref in row['evidence_refs']))
        validate_record(row, set())
        row['record_type'] = 'taint_path'
        with self.assertRaisesRegex(ValueError, 'grant reference requires expectation'):
            validate_record(row, set())

    def test_required_record_evidence_and_assessment(self):
        mutations = [
            ('m4-findings.json', 0, 'evidence_refs', []),
            ('m3-findings.json', 0, 'expectation_id', None),
            ('m3-findings.json', 1, 'evidence_refs', ['ql/src/m3/GetFeaturesHelperTaint.ql']),
            ('m4-imported-callee-findings.json', 0, 'evidence_refs', []),
            ('m4-imported-callee-findings.json', 0, 'evidence_status', 'no_path'),
            ('m4-imported-callee-findings.json', 0, 'unknowns', []),
            ('m3-findings.json', 0, 'session_class', 'root'),
        ]
        for name, index, key, value in mutations:
            with self.subTest(name=name, key=key, value=value):
                docs = deepcopy(self.documents)
                docs[name][index][key] = value
                with self.assertRaises(ValueError):
                    validate_documents(docs)

    def test_historical_coverage_allows_reordering_and_unknown_additions(self):
        docs = deepcopy(self.documents)
        for name in COVERAGE_KEYS:
            for key, value in docs[name].items():
                if isinstance(value, list):
                    value.reverse()
                    if key == 'unknowns':
                        value.append('additional conservative uncertainty')
        validate_documents(docs)

    def test_historical_non_unknown_coverage_rejects_additions(self):
        for name, report in LEGACY_COVERAGE.items():
            for key, values in report.items():
                if not isinstance(values, list) or key == 'unknowns':
                    continue
                with self.subTest(name=name, key=key):
                    docs = deepcopy(self.documents)
                    addition = ({'line': 9999, 'kind': 'popen', 'command': 'additional probe'}
                                if key == 'call_sites' else 'additional report item')
                    docs[name][key].append(addition)
                    with self.assertRaisesRegex(ValueError, 'coverage'):
                        validate_documents(docs)

    def test_historical_non_unknown_coverage_rejects_duplicate_additions(self):
        for name, report in LEGACY_COVERAGE.items():
            for key, values in report.items():
                if not isinstance(values, list) or key == 'unknowns' or not values:
                    continue
                with self.subTest(name=name, key=key):
                    docs = deepcopy(self.documents)
                    docs[name][key].append(deepcopy(values[0]))
                    with self.assertRaisesRegex(ValueError, 'coverage'):
                        validate_documents(docs)

    def test_historical_coverage_rejects_removal_of_each_member(self):
        for name, report in LEGACY_COVERAGE.items():
            for key, values in report.items():
                if not isinstance(values, list):
                    continue
                for index in range(len(values)):
                    with self.subTest(name=name, key=key, index=index):
                        docs = deepcopy(self.documents)
                        docs[name][key].pop(index)
                        with self.assertRaisesRegex(ValueError, 'coverage'):
                            validate_documents(docs)

    def test_each_historical_coverage_member_cannot_be_lost(self):
        for name, report in LEGACY_COVERAGE.items():
            for key, values in report.items():
                if not isinstance(values, list):
                    continue
                for index in range(len(values)):
                    with self.subTest(name=name, key=key, index=index):
                        docs = deepcopy(self.documents)
                        replacement = ({'line': 9999, 'kind': 'popen', 'command': 'replacement'}
                                       if key == 'call_sites' else 'replacement report item')
                        docs[name][key][index] = replacement
                        with self.assertRaisesRegex(ValueError, 'coverage'):
                            validate_documents(docs)

    def test_coverage_identity_and_uncertainty_cannot_be_substituted(self):
        mutations = [
            ('m3-coverage.json', 'analyzed'),
            ('m3-coverage.json', 'unknowns'),
            ('m4-coverage.json', 'methods_with_request_args_exec'),
            ('m4-coverage.json', 'negative_controls'),
            ('m4-shellquote-coverage.json', 'extracted_files'),
            ('m4-shellquote-coverage.json', 'unsupported_constructs'),
            ('m4-getfeatures-direct-exec-coverage.json', 'call_sites'),
        ]
        for name, key in mutations:
            with self.subTest(name=name, key=key):
                docs = deepcopy(self.documents)
                if key == 'call_sites':
                    docs[name][key][0]['command'] = 'different command'
                else:
                    docs[name][key][0] = 'different but nonempty'
                with self.assertRaisesRegex(ValueError, 'coverage'):
                    validate_documents(docs)

    def test_snapshot_identities_and_coverage_scope_are_bound(self):
        mutations = [
            ('m3-findings.json', lambda x: x[0].__setitem__('record_id', 'm3:substitute')),
            ('m3-coverage.json', lambda x: x.__setitem__('analysis_revision', 'step3:wrong')),
            ('m3-coverage.json', lambda x: x.__setitem__('entrypoint_id', 'ubus_http:luci.other')),
            ('m4-coverage.json', lambda x: x.__setitem__('status', 'complete')),
            ('m4-coverage.json', lambda x: x.__setitem__('unknowns', [None])),
            ('m4-shellquote-coverage.json', lambda x: x.__setitem__('extracted_files', [''])),
            ('m4-getfeatures-direct-exec-coverage.json', lambda x: x['call_sites'][0].__setitem__('line', True)),
            ('m4-getfeatures-direct-exec-coverage.json', lambda x: x['call_sites'][0].__setitem__('kind', 'unknown')),
            ('m4-getfeatures-direct-exec-coverage.json', lambda x: x['call_sites'][0].pop('command')),
            ('m4-findings.json', lambda x: x[0].__setitem__('analysis_revision', 'step3:wrong')),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name, mutate=mutate):
                docs = deepcopy(self.documents)
                mutate(docs[name])
                with self.assertRaises(ValueError):
                    validate_documents(docs)

    def test_preserves_declared_evidence_and_unknown_controls(self):
        mutations = [
            ('m3-findings.json', 0, 'assessment', 'other'),
            ('m3-findings.json', 0, 'evidence_refs', ['policy:grant:', 'ql/src/m3/GetFeaturesPopen.ql']),
            ('m4-findings.json', 3, 'evidence_refs', ['ql/src/m4/RequestArgsExec.ql']),
            ('m4-shellquote-findings.json', 0, 'evidence_refs', ['ql/src/m4/ShellInjection.ql']),
        ]
        for name, index, key, value in mutations:
            with self.subTest(name=name, key=key):
                docs = deepcopy(self.documents)
                docs[name][index][key] = value
                with self.assertRaises(ValueError):
                    validate_documents(docs)
        for name, key in [('m3-coverage.json', 'unknowns'), ('m4-coverage.json', 'negative_controls'),
                          ('m4-shellquote-coverage.json', 'extracted_files'),
                          ('m4-getfeatures-direct-exec-coverage.json', 'call_sites')]:
            with self.subTest(name=name, key=key):
                docs = deepcopy(self.documents)
                docs[name][key] = []
                with self.assertRaises(ValueError):
                    validate_documents(docs)

    def test_legacy_inconclusive_is_not_a_negative_finding(self):
        docs = deepcopy(self.documents)
        docs['m4-shellquote-findings.json'][0]['evidence_status'] = 'no_path'
        with self.assertRaisesRegex(ValueError, 'status'):
            validate_documents(docs)

    def test_inconclusive_must_retain_unknowns(self):
        docs = deepcopy(self.documents)
        docs['m4-shellquote-findings.json'][0]['unknowns'] = []
        with self.assertRaisesRegex(ValueError, 'unknowns'):
            validate_documents(docs)

    def test_unclassified_file_and_wrong_container_rejected(self):
        docs = deepcopy(self.documents)
        docs['new.json'] = {'status': 'partial'}
        with self.assertRaises(ValueError):
            validate_documents(docs)
        docs = deepcopy(self.documents)
        docs['m3-coverage.json'] = []
        with self.assertRaises(ValueError):
            validate_documents(docs)
        docs = deepcopy(self.documents)
        docs['m3-findings.json'] = {}
        with self.assertRaises(ValueError):
            validate_documents(docs)
        docs = deepcopy(self.documents)
        docs['m3-coverage.json']['new_field'] = []
        with self.assertRaises(ValueError):
            validate_documents(docs)

    def test_duplicate_and_invalid_fields_rejected(self):
        base = self.documents['m3-findings.json'][1]
        variants = {
            'record_id': '', 'record_type': 'other', 'evidence_status': 'other',
            'producer': 'step4', 'analysis_revision': 'policy:other',
            'corpus_revision': 'sha256:bad', 'profile': 'other',
            'assumptions': None, 'unknowns': None,
        }
        for key, value in variants.items():
            with self.subTest(key=key):
                row = deepcopy(base)
                row[key] = value
                with self.assertRaises(ValueError):
                    validate_record(row, set())
        for key in ('assumptions', 'unknowns'):
            row = deepcopy(base)
            del row[key]
            with self.assertRaises(ValueError):
                validate_record(row, set())
        seen = set()
        validate_record(base, seen)
        with self.assertRaises(ValueError):
            validate_record(base, seen)

    def test_cross_file_duplicate_and_revision_mismatch_rejected(self):
        docs = deepcopy(self.documents)
        docs['m4-findings.json'][0]['record_id'] = docs['m3-findings.json'][0]['record_id']
        with self.assertRaises(ValueError):
            validate_documents(docs)
        docs = deepcopy(self.documents)
        docs['m4-findings.json'][0]['corpus_revision'] = 'sha256:' + '0' * 64
        with self.assertRaises(ValueError):
            validate_documents(docs)

    def test_revision_and_record_capability_boundaries(self):
        base = self.documents['m3-findings.json'][0]
        for value in ('step3:', 'step3:has space', 'step3:a:b', 'step3:line\n', 'policy:valid'):
            with self.subTest(revision=value):
                row = deepcopy(base)
                row['analysis_revision'] = value
                with self.assertRaisesRegex(ValueError, 'analysis_revision'):
                    validate_record(row, set())
        for value in ('rpc_surface', 'backend_method', 'coverage'):
            with self.subTest(record_type=value):
                row = deepcopy(base)
                row['record_type'] = value
                with self.assertRaisesRegex(ValueError, 'record_type'):
                    validate_record(row, set())
        row = deepcopy(base)
        row['analysis_revision'] = 'step3:A-._/9'
        validate_record(row, set())

    def test_missing_typed_and_coverage_documents_rejected(self):
        for name in ('m4-imported-callee-findings.json', 'm4-coverage.json'):
            with self.subTest(name=name):
                docs = deepcopy(self.documents)
                del docs[name]
                with self.assertRaisesRegex(ValueError, 'missing'):
                    validate_documents(docs)

    def test_fact_and_candidate_can_omit_qualifier_arrays(self):
        for status in ('fact', 'candidate'):
            row = deepcopy(self.documents['m3-findings.json'][0])
            row['evidence_status'] = status
            row.pop('assumptions', None)
            row.pop('unknowns', None)
            validate_record(row, set())


if __name__ == '__main__':
    unittest.main()
