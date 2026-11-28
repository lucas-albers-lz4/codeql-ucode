import importlib.util
import copy
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "issue155_template_flow_ci", ROOT / "scripts/issue155-template-flow-ci.py"
)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def entity(identifier, path, location, label):
    line, start, end = location
    return {
        "id": identifier,
        "label": label,
        "url": {
            "uri": "file:///fixture/" + path,
            "startLine": line,
            "startColumn": start,
            "endLine": line,
            "endColumn": end,
        },
    }


class Issue155TemplateFlowRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = RUNNER.strict_json(RUNNER.MANIFEST.read_text())

    def test_fixture_inventory_matches_source_pins(self):
        self.assertEqual(RUNNER.fixture_inventory(self.manifest), self.manifest["files"])
        self.assertEqual(self.manifest["expected_indexed_count"], 26)
        self.assertIn("controls/malformed.uc", self.manifest["expected_negative_paths"])

    def test_witness_query_selects_raw_ast_independently(self):
        query = (ROOT / "ql/src/testing/issue155-template-flow/TemplateFlowWitnesses.ql").read_text()
        self.assertNotIn("Issue155TemplateFlow", query)
        self.assertNotIn("issue155TemplateFlowWitness", query)
        self.assertIn("rawFormalHasNoWrites", query)
        self.assertIn("rawCall.getFunction()", query)

    def test_expected_flow_rows_preserve_each_ast_role_and_candidate_edge(self):
        actual = []
        next_id = 1
        for record in self.manifest["expected_flow_rows"]:
            source = entity(next_id, record["path"], record["source"], "MemberExpression")
            next_id += 1
            argument = entity(next_id, record["path"], record["template_argument"], "template string argument")
            next_id += 1
            call = entity(next_id, record["path"], record["call"], "CallExpression")
            next_id += 1
            formal = entity(next_id, record["path"], record["formal"], "request")
            next_id += 1
            specifier = entity(next_id, record["path"], record["import_specifier"], "ImportSpecifier")
            next_id += 1
            for edge in record["edge_candidates"]:
                edge_source = (source if edge["source"] == record["source"] else
                               entity(next_id, record["path"], edge["source"], "Identifier"))
                if edge_source is not source:
                    next_id += 1
                substitution = entity(next_id, record["path"], edge["substitution"], "TemplateSubstitution")
                next_id += 1
                actual.append([
                    record["path"], source, argument, call, formal, specifier,
                    edge_source, substitution, record["source"][0],
                    record["template_argument"][0], record["call"][0],
                ])
        result = {"#select": {"columns": [{}] * 11, "tuples": actual}}
        self.assertEqual(RUNNER.actual_rows(result), RUNNER.expected_rows(self.manifest))
        RUNNER.verify_witness_identity(result, copy.deepcopy(result))

    def test_entity_id_only_mutation_fails_against_raw_witness(self):
        result = {"#select": {"columns": [{}] * 11, "tuples": [[
            "controls/direct.uc",
            entity(1, "controls/direct.uc", [8, 30, 54], "MemberExpression"),
            entity(2, "controls/direct.uc", [8, 19, 60], "template string argument"),
            entity(3, "controls/direct.uc", [8, 14, 61], "CallExpression"),
            entity(4, "controls/direct.uc", [6, 20, 26], "request"),
            entity(5, "controls/direct.uc", [1, 10, 13], "ImportSpecifier"),
            entity(1, "controls/direct.uc", [8, 30, 54], "MemberExpression"),
            entity(6, "controls/direct.uc", [8, 28, 55], "TemplateSubstitution"),
            8, 8, 8,
        ]]}}
        mutated = copy.deepcopy(result)
        mutated["#select"]["tuples"][0][4]["id"] = 404
        with self.assertRaisesRegex(ValueError, "entity IDs differ"):
            RUNNER.verify_witness_identity(mutated, result)

    def test_cross_file_entity_borrow_fails_against_raw_witness(self):
        result = {"#select": {"columns": [{}] * 11, "tuples": [[
            "controls/direct.uc",
            entity(1, "controls/direct.uc", [8, 30, 54], "MemberExpression"),
            entity(2, "controls/direct.uc", [8, 19, 60], "template string argument"),
            entity(3, "controls/direct.uc", [8, 14, 61], "CallExpression"),
            entity(4, "controls/direct.uc", [6, 20, 26], "request"),
            entity(5, "controls/direct.uc", [1, 10, 13], "ImportSpecifier"),
            entity(1, "controls/direct.uc", [8, 30, 54], "MemberExpression"),
            entity(6, "controls/direct.uc", [8, 28, 55], "TemplateSubstitution"),
            8, 8, 8,
        ]]}}
        mutated = copy.deepcopy(result)
        mutated["#select"]["tuples"][0][4]["url"]["uri"] = "file:///fixture/controls/assigned.uc"
        with self.assertRaisesRegex(ValueError, "entity IDs differ"):
            RUNNER.verify_witness_identity(mutated, result)

    def test_extra_result_row_fails_exact_multiset(self):
        result = {"#select": {"columns": [{}] * 11, "tuples": []}}
        self.assertNotEqual(RUNNER.actual_rows(result), RUNNER.expected_rows(self.manifest))

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            RUNNER.strict_json('{"route":"plain","route":"markup"}')


if __name__ == "__main__":
    unittest.main()
