"""Offline checks for the classified, committed docs/*.json snapshots."""
from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

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
    if len(revisions) != 1:
        raise ValueError('snapshot corpus revisions differ')
    for name, expected_keys in COVERAGE_KEYS.items():
        report = documents[name]
        if (not isinstance(report, dict) or set(report) != expected_keys
                or report.get('profile') != PROFILE or not nonempty_string(report.get('status'))
                or not isinstance(report.get('analyzed'), list)
                or not isinstance(report.get('analysis_revision'), str)
                or not re.fullmatch(r'step3:[^\s:]+', report['analysis_revision'])):
            raise ValueError(f'{name}: expected report-only coverage object')
    return seen


def load_documents(directory):
    return {p.name: json.loads(p.read_text(encoding='utf-8')) for p in directory.glob('*.json')}


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = load_documents(DOCS)

    def test_classified_documents_and_records(self):
        self.assertEqual(len(validate_documents(self.documents)), 19)

    def test_negative_and_inconclusive_are_explicit_snapshots(self):
        records = {r['record_id']: r for name in TYPED_COUNTS for r in self.documents[name]}
        self.assertEqual(records['m3:getfeatures-netifd-request-args-no-path']['evidence_status'], 'no_path')
        self.assertEqual(records['m4:setInitAction-init_action-unresolved']['evidence_status'], 'inconclusive')
        self.assertTrue(records['m4:setInitAction-init_action-unresolved']['unknowns'])

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

    def test_fact_and_candidate_can_omit_qualifier_arrays(self):
        for status in ('fact', 'candidate'):
            row = deepcopy(self.documents['m3-findings.json'][0])
            row['evidence_status'] = status
            row.pop('assumptions', None)
            row.pop('unknowns', None)
            validate_record(row, set())


if __name__ == '__main__':
    unittest.main()
